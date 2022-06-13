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
import hashlib
import logging
import os
import socket

from keystoneauth1 import adapter
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import importutils
import requests
from urllib import parse

from heatclient._i18n import _
from heatclient.common import utils
from heatclient import exc

LOG = logging.getLogger(__name__)
USER_AGENT = 'python-heatclient'
CHUNKSIZE = 1024 * 64  # 64kB
SENSITIVE_HEADERS = ('X-Auth-Token',)
osprofiler_web = importutils.try_import("osprofiler.web")


def authenticated_fetcher(hc):
    """A wrapper around the heat client object to fetch a template."""

    def _do(*args, **kwargs):
        if isinstance(hc.http_client, SessionClient):
            method, url = args
            return hc.http_client.request(url, method, **kwargs).content
        else:
            return hc.http_client.raw_request(*args, **kwargs).content

    return _do


def get_system_ca_file():
    """Return path to system default CA file."""
    # Standard CA file locations for Debian/Ubuntu, RedHat/Fedora,
    # Suse, FreeBSD/OpenBSD, MacOSX, and the bundled ca
    ca_path = ['/etc/ssl/certs/ca-certificates.crt',
               '/etc/pki/tls/certs/ca-bundle.crt',
               '/etc/ssl/ca-bundle.pem',
               '/etc/ssl/cert.pem',
               '/System/Library/OpenSSL/certs/cacert.pem',
               requests.certs.where()]
    for ca in ca_path:
        LOG.debug("Looking for ca file %s", ca)
        if os.path.exists(ca):
            LOG.debug("Using ca file %s", ca)
            return ca
    LOG.warning("System ca file could not be found.")


class HTTPClient(object):

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint
        self.auth_url = kwargs.get('auth_url')
        self.auth_token = kwargs.get('token')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.region_name = kwargs.get('region_name')
        self.include_pass = kwargs.get('include_pass')
        self.endpoint_url = endpoint

        self.cert_file = kwargs.get('cert_file')
        self.key_file = kwargs.get('key_file')
        self.timeout = kwargs.get('timeout')

        self.ssl_connection_params = {
            'ca_file': kwargs.get('ca_file'),
            'cert_file': kwargs.get('cert_file'),
            'key_file': kwargs.get('key_file'),
            'insecure': kwargs.get('insecure'),
        }

        self.verify_cert = None
        if parse.urlparse(endpoint).scheme == "https":
            if kwargs.get('insecure'):
                self.verify_cert = False
            else:
                self.verify_cert = kwargs.get('ca_file', get_system_ca_file())

        # FIXME(shardy): We need this for compatibility with the oslo apiclient
        # we should move to inheriting this class from the oslo HTTPClient
        self.last_request_id = None

    def safe_header(self, name, value):
        if name in SENSITIVE_HEADERS:
            # because in python3 byte string handling is ... ug
            v = value.encode('utf-8')
            h = hashlib.sha1(v)
            d = h.hexdigest()
            return encodeutils.safe_decode(name), "{SHA1}%s" % d
        else:
            return (encodeutils.safe_decode(name),
                    encodeutils.safe_decode(value))

    def log_curl_request(self, method, url, kwargs):
        curl = ['curl -g -i -X %s' % method]

        for (key, value) in kwargs['headers'].items():
            header = '-H \'%s: %s\'' % self.safe_header(key, value)
            curl.append(header)

        conn_params_fmt = [
            ('key_file', '--key %s'),
            ('cert_file', '--cert %s'),
            ('ca_file', '--cacert %s'),
        ]
        for (key, fmt) in conn_params_fmt:
            value = self.ssl_connection_params.get(key)
            if value:
                curl.append(fmt % value)

        if self.ssl_connection_params.get('insecure'):
            curl.append('-k')

        if 'data' in kwargs:
            curl.append('-d \'%s\'' % kwargs['data'])

        if not parse.urlparse(url).netloc:
            url = self.endpoint + url

        curl.append(url)
        LOG.debug(' '.join(curl))

    @staticmethod
    def log_http_response(resp):
        status = (resp.raw.version / 10.0, resp.status_code, resp.reason)
        dump = ['\nHTTP/%.1f %s %s' % status]
        dump.extend(['%s: %s' % (k, v) for k, v in resp.headers.items()])
        dump.append('')
        if resp.content:
            content = resp.content
            if isinstance(content, bytes):
                content = content.decode()
            dump.extend([content, ''])
        LOG.debug('\n'.join(dump))

    def _http_request(self, url, method, **kwargs):
        """Send an http request with the specified characteristics.

        Wrapper around requests.request to handle tasks such as
        setting headers and error handling.
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
        if self.include_pass and 'X-Auth-Key' not in kwargs['headers']:
            kwargs['headers'].update(self.credentials_headers())
        if osprofiler_web:
            kwargs['headers'].update(osprofiler_web.get_trace_id_headers())

        self.log_curl_request(method, url, kwargs)

        if self.cert_file and self.key_file:
            kwargs['cert'] = (self.cert_file, self.key_file)

        if self.verify_cert is not None:
            kwargs['verify'] = self.verify_cert

        if self.timeout is not None:
            kwargs['timeout'] = float(self.timeout)

        # Allow caller to specify not to follow redirects, in which case we
        # just return the redirect response.  Useful for using stacks:lookup.
        redirect = kwargs.pop('redirect', True)

        # Since requests does not follow the RFC when doing redirection to sent
        # back the same method on a redirect we are simply bypassing it.  For
        # example if we do a DELETE/POST/PUT on a URL and we get a 302 RFC says
        # that we should follow that URL with the same method as before,
        # requests doesn't follow that and send a GET instead for the method.
        # Hopefully this could be fixed as they say in a comment in a future
        # point version i.e.: 3.x
        # See issue: https://github.com/kennethreitz/requests/issues/1704
        allow_redirects = False

        # Use fully qualified URL from response header for redirects
        if not parse.urlparse(url).netloc:
            url = self.endpoint_url + url

        try:
            resp = requests.request(
                method,
                url,
                allow_redirects=allow_redirects,
                **kwargs)
        except socket.gaierror as e:
            message = (_("Error finding address for %(url)s: %(e)s") %
                       {'url': self.endpoint_url + url, 'e': e})
            raise exc.InvalidEndpoint(message=message)
        except (socket.error, socket.timeout) as e:
            endpoint = self.endpoint
            message = (_("Error communicating with %(endpoint)s %(e)s") %
                       {'endpoint': endpoint, 'e': e})
            raise exc.CommunicationError(message=message)

        self.log_http_response(resp)
        txt_content = encodeutils.safe_decode(resp.content, 'utf-8')
        if not ('X-Auth-Key' in kwargs['headers']) and (
                resp.status_code == 401 or
                (resp.status_code == 500 and "(HTTP 401)" in txt_content)):
            raise exc.HTTPUnauthorized(_("Authentication failed: %s")
                                       % resp.content)
        elif 400 <= resp.status_code < 600:
            raise exc.from_response(resp)
        elif resp.status_code in (301, 302, 305):
            # Redirected. Reissue the request to the new location,
            # unless caller specified redirect=False
            if redirect:
                location = resp.headers.get('location')
                if not location:
                    message = _("Location not returned with redirect")
                    raise exc.InvalidEndpoint(message=message)
                resp = self._http_request(location, method, **kwargs)
        elif resp.status_code == 300:
            raise exc.from_response(resp)

        return resp

    def credentials_headers(self):
        creds = {}
        # NOTE(dhu): (shardy) When deferred_auth_method=password, Heat
        # encrypts and stores username/password.  For Keystone v3, the
        # intent is to use trusts since SHARDY is working towards
        # deferred_auth_method=trusts as the default.
        # TODO(dhu): Make Keystone v3 work in Heat standalone mode.  Maye
        # require X-Auth-User-Domain.
        if self.username:
            creds['X-Auth-User'] = self.username
        if self.password:
            creds['X-Auth-Key'] = self.password
        return creds

    def json_request(self, method, url, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers'].setdefault('Content-Type', 'application/json')
        kwargs['headers'].setdefault('Accept', 'application/json')

        if 'data' in kwargs:
            kwargs['data'] = jsonutils.dumps(kwargs['data'])

        resp = self._http_request(url, method, **kwargs)
        body = utils.get_response_body(resp)
        return resp, body

    def raw_request(self, method, url, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers'].setdefault('Content-Type',
                                     'application/octet-stream')
        return self._http_request(url, method, **kwargs)

    def client_request(self, method, url, **kwargs):
        resp, body = self.json_request(method, url, **kwargs)
        return resp

    def head(self, url, **kwargs):
        return self.client_request("HEAD", url, **kwargs)

    def get(self, url, **kwargs):
        return self.client_request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.client_request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.client_request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.raw_request("DELETE", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.client_request("PATCH", url, **kwargs)


class SessionClient(adapter.LegacyJsonAdapter):
    """HTTP client based on Keystone client session."""

    def request(self, url, method, **kwargs):
        redirect = kwargs.get('redirect')
        kwargs.setdefault('user_agent', USER_AGENT)

        headers = kwargs.setdefault('headers', {})
        headers.setdefault('Content-Type', 'application/json')

        if 'data' in kwargs:
            kwargs['data'] = jsonutils.dumps(kwargs['data'])

        resp, body = super(SessionClient, self).request(
            url, method,
            raise_exc=False,
            **kwargs)

        if 400 <= resp.status_code < 600:
            raise exc.from_response(resp)
        elif resp.status_code in (301, 302, 305):
            if redirect:
                location = resp.headers.get('location')
                path = self.strip_endpoint(location)
                resp = self.request(path, method, **kwargs)
        elif resp.status_code == 300:
            raise exc.from_response(resp)

        return resp

    def credentials_headers(self):
        return {}

    def strip_endpoint(self, location):
        if location is None:
            message = _("Location not returned with 302")
            raise exc.InvalidEndpoint(message=message)
        if (self.endpoint_override is not None and
                location.lower().startswith(self.endpoint_override.lower())):
            return location[len(self.endpoint_override):]
        else:
            return location


def _construct_http_client(endpoint=None, username=None, password=None,
                           include_pass=None, endpoint_type=None,
                           auth_url=None, **kwargs):
    session = kwargs.pop('session', None)
    auth = kwargs.pop('auth', None)

    if session:
        if 'endpoint_override' not in kwargs and endpoint:
            kwargs['endpoint_override'] = endpoint

        if 'service_type' not in kwargs:
            kwargs['service_type'] = 'orchestration'

        if 'interface' not in kwargs and endpoint_type:
            kwargs['interface'] = endpoint_type

        if 'region_name' in kwargs:
            kwargs['additional_headers'] = {
                'X-Region-Name': kwargs['region_name']}

        return SessionClient(session, auth=auth, **kwargs)
    else:
        return HTTPClient(endpoint=endpoint, username=username,
                          password=password, include_pass=include_pass,
                          endpoint_type=endpoint_type, auth_url=auth_url,
                          **kwargs)
