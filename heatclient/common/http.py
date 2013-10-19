# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import logging
import os
import socket

from heatclient.openstack.common.py3kcompat import urlutils
from six.moves import http_client as httplib

try:
    import ssl
except ImportError:
    #TODO(bcwaldon): Handle this failure more gracefully
    pass

try:
    import json
except ImportError:
    import simplejson as json

# Python 2.5 compat fix
if not hasattr(urlutils, 'parse_qsl'):
    import cgi
    urlutils.parse_qsl = cgi.parse_qsl


from heatclient import exc


LOG = logging.getLogger(__name__)
if not LOG.handlers:
    LOG.addHandler(logging.StreamHandler())
USER_AGENT = 'python-heatclient'
CHUNKSIZE = 1024 * 64  # 64kB


class HTTPClient(object):

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint
        self.auth_url = kwargs.get('auth_url')
        self.auth_token = kwargs.get('token')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.region_name = kwargs.get('region_name')
        self.connection_params = self.get_connection_params(endpoint, **kwargs)

    @staticmethod
    def get_connection_params(endpoint, **kwargs):
        parts = urlutils.urlparse(endpoint)

        _args = (parts.hostname, parts.port, parts.path)
        _kwargs = {'timeout': float(kwargs.get('timeout', 600))}

        if parts.scheme == 'https':
            _class = VerifiedHTTPSConnection
            _kwargs['ca_file'] = kwargs.get('ca_file', None)
            _kwargs['cert_file'] = kwargs.get('cert_file', None)
            _kwargs['key_file'] = kwargs.get('key_file', None)
            _kwargs['insecure'] = kwargs.get('insecure', False)
        elif parts.scheme == 'http':
            _class = httplib.HTTPConnection
        else:
            msg = 'Unsupported scheme: %s' % parts.scheme
            raise exc.InvalidEndpoint(msg)

        return (_class, _args, _kwargs)

    def get_connection(self):
        _class = self.connection_params[0]
        try:
            return _class(*self.connection_params[1][0:2],
                          **self.connection_params[2])
        except httplib.InvalidURL:
            raise exc.InvalidEndpoint()

    def log_curl_request(self, method, url, kwargs):
        curl = ['curl -i -X %s' % method]

        for (key, value) in kwargs['headers'].items():
            header = '-H \'%s: %s\'' % (key, value)
            curl.append(header)

        conn_params_fmt = [
            ('key_file', '--key %s'),
            ('cert_file', '--cert %s'),
            ('ca_file', '--cacert %s'),
        ]
        for (key, fmt) in conn_params_fmt:
            value = self.connection_params[2].get(key)
            if value:
                curl.append(fmt % value)

        if self.connection_params[2].get('insecure'):
            curl.append('-k')

        if 'body' in kwargs:
            curl.append('-d \'%s\'' % kwargs['body'])

        curl.append('%s%s' % (self.endpoint, url))
        LOG.debug(' '.join(curl))

    @staticmethod
    def log_http_response(resp, body=None):
        status = (resp.version / 10.0, resp.status, resp.reason)
        dump = ['\nHTTP/%.1f %s %s' % status]
        dump.extend(['%s: %s' % (k, v) for k, v in resp.getheaders()])
        dump.append('')
        if body:
            dump.extend([body, ''])
        LOG.debug('\n'.join(dump))

    def _http_request(self, url, method, **kwargs):
        """Send an http request with the specified characteristics.

        Wrapper around httplib.HTTP(S)Connection.request to handle tasks such
        as setting headers and error handling.
        """
        # Copy the kwargs so we can reuse the original in case of redirects
        kwargs['headers'] = copy.deepcopy(kwargs.get('headers', {}))
        kwargs['headers'].setdefault('User-Agent', USER_AGENT)
        if self.auth_token:
            kwargs['headers'].setdefault('X-Auth-Token', self.auth_token)
        else:
            kwargs['headers'].update(self.credentials_headers())
        if self.auth_url:
            kwargs['headers'].setdefault('X-Auth-Url', self.auth_url)
        if self.region_name:
            kwargs['headers'].setdefault('X-Region-Name', self.region_name)

        self.log_curl_request(method, url, kwargs)
        conn = self.get_connection()

        try:
            conn_params = self.connection_params[1][2]
            conn_url = os.path.normpath('%s/%s' % (conn_params, url))
            conn.request(method, conn_url, **kwargs)
            resp = conn.getresponse()
        except socket.gaierror as e:
            message = ("Error finding address for %(url)s: %(e)s" %
                       {'url': url, 'e': e})
            raise exc.InvalidEndpoint(message=message)
        except (socket.error, socket.timeout) as e:
            endpoint = self.endpoint
            message = ("Error communicating with %(endpoint)s %(e)s" %
                       {'endpoint': endpoint, 'e': e})
            raise exc.CommunicationError(message=message)

        body_iter = ResponseBodyIterator(resp)
        body_str = ''.join([chunk for chunk in body_iter])
        self.log_http_response(resp, body_str)

        if 400 <= resp.status < 600:
            raise exc.from_response(resp, body_str)
        elif resp.status in (301, 302, 305):
            # Redirected. Reissue the request to the new location.
            location = resp.getheader('location', None)
            if location is None:
                message = "Location not returned with 302"
                raise exc.InvalidEndpoint(message=message)
            elif location.startswith(self.endpoint):
                # shave off the endpoint, it will be prepended when we recurse
                location = location[len(self.endpoint):]
            else:
                message = "Prohibited endpoint redirect %s" % location
                raise exc.InvalidEndpoint(message=message)
            return self._http_request(location, method, **kwargs)
        elif resp.status == 300:
            raise exc.from_response(resp, body_str)

        return resp, body_str

    def credentials_headers(self):
        creds = {}
        if self.username:
            creds['X-Auth-User'] = self.username
        if self.password:
            creds['X-Auth-Key'] = self.password
        return creds

    def json_request(self, method, url, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers'].setdefault('Content-Type', 'application/json')
        kwargs['headers'].setdefault('Accept', 'application/json')

        if 'body' in kwargs:
            kwargs['body'] = json.dumps(kwargs['body'])

        resp, body_str = self._http_request(url, method, **kwargs)

        if 'application/json' in resp.getheader('content-type', None):
            body = body_str
            try:
                body = json.loads(body)
            except ValueError:
                LOG.error('Could not decode response body as JSON')
        else:
            body = None

        return resp, body

    def raw_request(self, method, url, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers'].setdefault('Content-Type',
                                     'application/octet-stream')
        return self._http_request(url, method, **kwargs)


class VerifiedHTTPSConnection(httplib.HTTPSConnection):
    """httplib-compatibile connection using client-side SSL authentication

    :see http://code.activestate.com/recipes/
            577548-https-httplib-client-connection-with-certificate-v/
    """

    def __init__(self, host, port, key_file=None, cert_file=None,
                 ca_file=None, timeout=None, insecure=False):
        httplib.HTTPSConnection.__init__(self, host, port, key_file=key_file,
                                         cert_file=cert_file)
        self.key_file = key_file
        self.cert_file = cert_file
        if ca_file is not None:
            self.ca_file = ca_file
        else:
            self.ca_file = self.get_system_ca_file()
        self.timeout = timeout
        self.insecure = insecure

    def connect(self):
        """Connect to a host on a given (SSL) port.
        If ca_file is pointing somewhere, use it to check Server Certificate.

        Redefined/copied and extended from httplib.py:1105 (Python 2.6.x).
        This is needed to pass cert_reqs=ssl.CERT_REQUIRED as parameter to
        ssl.wrap_socket(), which forces SSL to check server certificate against
        our client certificate.
        """
        sock = socket.create_connection((self.host, self.port), self.timeout)

        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        if self.insecure is True:
            kwargs = {'cert_reqs': ssl.CERT_NONE}
        else:
            kwargs = {'cert_reqs': ssl.CERT_REQUIRED, 'ca_certs': self.ca_file}

        if self.cert_file:
            kwargs['certfile'] = self.cert_file
            if self.key_file:
                kwargs['keyfile'] = self.key_file

        self.sock = ssl.wrap_socket(sock, **kwargs)

    @staticmethod
    def get_system_ca_file():
        """Return path to system default CA file."""
        # Standard CA file locations for Debian/Ubuntu, RedHat/Fedora,
        # Suse, FreeBSD/OpenBSD
        ca_path = ['/etc/ssl/certs/ca-certificates.crt',
                   '/etc/pki/tls/certs/ca-bundle.crt',
                   '/etc/ssl/ca-bundle.pem',
                   '/etc/ssl/cert.pem']
        for ca in ca_path:
            if os.path.exists(ca):
                return ca
        return None


class ResponseBodyIterator(object):
    """A class that acts as an iterator over an HTTP response."""

    def __init__(self, resp):
        self.resp = resp

    def __iter__(self):
        while True:
            yield self.next()

    def next(self):
        chunk = self.resp.read(CHUNKSIZE)
        if chunk:
            return chunk
        else:
            raise StopIteration()
