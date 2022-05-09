# -*- coding:utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
from unittest import mock

import io
from keystoneauth1 import adapter
from oslo_serialization import jsonutils
import testtools

from heatclient.common import http
from heatclient.common import utils
from heatclient import exc
from heatclient.tests.unit import fakes


@mock.patch('heatclient.common.http.requests.request')
class HttpClientTest(testtools.TestCase):

    def test_http_raw_request(self, mock_request):
        headers = {'Content-Type': 'application/octet-stream',
                   'User-Agent': 'python-heatclient'}

        # Record a 200
        mock_request.return_value = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/octet-stream'},
            '')
        # Replay, create client, assert
        client = http.HTTPClient('http://example.com:8004')
        resp = client.raw_request('GET', '')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('', ''.join([x for x in resp.content]))
        mock_request.assert_called_with('GET', 'http://example.com:8004',
                                        allow_redirects=False,
                                        headers=headers)

    def test_token_or_credentials(self, mock_request):
        # Record a 200
        fake200 = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/octet-stream'},
            '')

        mock_request.return_value = fake200
        # no token or credentials
        client = http.HTTPClient('http://example.com:8004')
        resp = client.raw_request('GET', '')
        self.assertEqual(200, resp.status_code)
        # credentials
        client.username = 'user'
        client.password = 'pass'
        resp = client.raw_request('GET', '')
        self.assertEqual(200, resp.status_code)
        # token suppresses credentials
        client.auth_token = 'abcd1234'
        resp = client.raw_request('GET', '')
        self.assertEqual(200, resp.status_code)
        mock_request.assert_has_calls([
            mock.call('GET', 'http://example.com:8004',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/octet-stream',
                               'User-Agent': 'python-heatclient'}),
            mock.call('GET', 'http://example.com:8004',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/octet-stream',
                               'User-Agent': 'python-heatclient',
                               'X-Auth-Key': 'pass',
                               'X-Auth-User': 'user'}),
            mock.call('GET', 'http://example.com:8004',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/octet-stream',
                               'User-Agent': 'python-heatclient',
                               'X-Auth-Token': 'abcd1234'})
        ])

    def test_include_pass(self, mock_request):
        # Record a 200
        fake200 = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/octet-stream'},
            '')
        mock_request.return_value = fake200
        # no token or credentials
        client = http.HTTPClient('http://example.com:8004')
        resp = client.raw_request('GET', '')
        self.assertEqual(200, resp.status_code)
        # credentials
        client.username = 'user'
        client.password = 'pass'
        client.include_pass = True
        resp = client.raw_request('GET', '')
        self.assertEqual(200, resp.status_code)
        # token suppresses credentials
        client.auth_token = 'abcd1234'
        resp = client.raw_request('GET', '')
        self.assertEqual(200, resp.status_code)
        mock_request.assert_has_calls([
            mock.call('GET', 'http://example.com:8004',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/octet-stream',
                               'User-Agent': 'python-heatclient'}),
            mock.call('GET', 'http://example.com:8004',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/octet-stream',
                               'User-Agent': 'python-heatclient',
                               'X-Auth-Key': 'pass',
                               'X-Auth-User': 'user'}),
            mock.call('GET', 'http://example.com:8004',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/octet-stream',
                               'User-Agent': 'python-heatclient',
                               'X-Auth-Token': 'abcd1234',
                               'X-Auth-Key': 'pass',
                               'X-Auth-User': 'user'})
        ])

    def test_not_include_pass(self, mock_request):
        # Record a 200
        fake500 = fakes.FakeHTTPResponse(
            500, 'ERROR',
            {'content-type': 'application/octet-stream'},
            b'(HTTP 401)')

        # no token or credentials
        mock_request.return_value = fake500

        # Replay, create client, assert
        client = http.HTTPClient('http://example.com:8004')
        e = self.assertRaises(exc.HTTPUnauthorized,
                              client.raw_request, 'GET', '')
        self.assertIn('Authentication failed', str(e))
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            allow_redirects=False,
            headers={'Content-Type': 'application/octet-stream',
                     'User-Agent': 'python-heatclient'})

    def test_region_name(self, mock_request):
        # Record a 200
        fake200 = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/octet-stream'},
            '')

        # Specify region name
        mock_request.return_value = fake200

        # Replay, create client, assert
        client = http.HTTPClient('http://example.com:8004')
        client.region_name = 'RegionOne'
        resp = client.raw_request('GET', '')
        self.assertEqual(200, resp.status_code)
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            allow_redirects=False,
            headers={'Content-Type': 'application/octet-stream',
                     'X-Region-Name': 'RegionOne',
                     'User-Agent': 'python-heatclient'})

    def test_http_json_request(self, mock_request):
        # Record a 200
        mock_request.return_value = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/json'},
            '{}')
        # Replay, create client, assert
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, body)
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'User-Agent': 'python-heatclient'})

    def test_http_json_request_argument_passed_to_requests(self, mock_request):
        """Check that we have sent the proper arguments to requests."""
        # Record a 200
        mock_request.return_value = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/json'},
            '{}')

        client = http.HTTPClient('http://example.com:8004')
        client.verify_cert = True
        client.cert_file = 'RANDOM_CERT_FILE'
        client.key_file = 'RANDOM_KEY_FILE'
        client.auth_url = 'http://AUTH_URL'
        resp, body = client.json_request('GET', '', data='text')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, body)
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            allow_redirects=False,
            cert=('RANDOM_CERT_FILE', 'RANDOM_KEY_FILE'),
            verify=True,
            data='"text"',
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'X-Auth-Url': 'http://AUTH_URL',
                     'User-Agent': 'python-heatclient'})

    def test_http_json_request_w_req_body(self, mock_request):
        # Record a 200
        mock_request.return_value = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/json'},
            '{}')
        # Replay, create client, assert
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '', body='test-body')
        self.assertEqual(200, resp.status_code)
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            body='test-body',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'User-Agent': 'python-heatclient'})

    def test_http_json_request_non_json_resp_cont_type(self, mock_request):
        # Record a 200i
        mock_request.return_value = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'not/json'},
            '{}')
        # Replay, create client, assert
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '', body='test-body')
        self.assertEqual(200, resp.status_code)
        self.assertIsNone(body)
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            body='test-body',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'User-Agent': 'python-heatclient'})

    def test_http_json_request_invalid_json(self, mock_request):
        # Record a 200
        mock_request.return_value = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/json'},
            'invalid-json')

        # Replay, create client, assert
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('invalid-json', body)
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'User-Agent': 'python-heatclient'})

    def test_http_manual_redirect_delete(self, mock_request):
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8004/foo/bar'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                'invalid-json')
        ]

        client = http.HTTPClient('http://example.com:8004/foo')
        resp, body = client.json_request('DELETE', '')

        mock_request.assert_has_calls([
            mock.call('DELETE', 'http://example.com:8004/foo',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'}),
            mock.call('DELETE', 'http://example.com:8004/foo/bar',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'})
        ])

    def test_http_manual_redirect_post(self, mock_request):
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8004/foo/bar'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                'invalid-json')
        ]

        client = http.HTTPClient('http://example.com:8004/foo')
        resp, body = client.json_request('POST', '')

        mock_request.assert_has_calls([
            mock.call('POST', 'http://example.com:8004/foo',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'}),
            mock.call('POST', 'http://example.com:8004/foo/bar',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'})
        ])

    def test_http_manual_redirect_put(self, mock_request):
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8004/foo/bar'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                'invalid-json')
        ]

        client = http.HTTPClient('http://example.com:8004/foo')
        resp, body = client.json_request('PUT', '')

        mock_request.assert_has_calls([
            mock.call('PUT', 'http://example.com:8004/foo',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'}),
            mock.call('PUT', 'http://example.com:8004/foo/bar',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'})
        ])

    def test_http_manual_redirect_put_uppercase(self, mock_request):
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8004/foo/bar'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                'invalid-json')
        ]
        client = http.HTTPClient('http://EXAMPLE.com:8004/foo')
        resp, body = client.json_request('PUT', '')
        self.assertEqual(200, resp.status_code)

        mock_request.assert_has_calls([
            mock.call('PUT', 'http://EXAMPLE.com:8004/foo',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'}),
            mock.call('PUT', 'http://example.com:8004/foo/bar',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'})
        ])

    def test_http_manual_redirect_error_without_location(self, mock_request):
        mock_request.return_value = fakes.FakeHTTPResponse(
            302, 'Found',
            {},
            '')
        client = http.HTTPClient('http://example.com:8004/foo')
        self.assertRaises(exc.InvalidEndpoint,
                          client.json_request, 'DELETE', '')
        mock_request.assert_called_once_with(
            'DELETE', 'http://example.com:8004/foo',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'User-Agent': 'python-heatclient'})

    def test_http_json_request_redirect(self, mock_request):
        # Record the 302
        mock_request.side_effect = [
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8004'},
                ''),
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}')
        ]
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, body)
        mock_request.assert_has_calls([
            mock.call('GET', 'http://example.com:8004',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'}),
            mock.call('GET', 'http://example.com:8004',
                      allow_redirects=False,
                      headers={'Content-Type': 'application/json',
                               'Accept': 'application/json',
                               'User-Agent': 'python-heatclient'})
        ])

    def test_http_404_json_request(self, mock_request):
        # Record a 404
        mock_request.return_value = fakes.FakeHTTPResponse(
            404, 'OK', {'content-type': 'application/json'},
            '{}')
        client = http.HTTPClient('http://example.com:8004')
        e = self.assertRaises(exc.HTTPNotFound, client.json_request, 'GET', '')
        # Assert that the raised exception can be converted to string
        self.assertIsNotNone(str(e))
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'User-Agent': 'python-heatclient'})

    def test_http_300_json_request(self, mock_request):
        # Record a 300
        mock_request.return_value = fakes.FakeHTTPResponse(
            300, 'OK', {'content-type': 'application/json'},
            '{}')
        # Assert that the raised exception can be converted to string
        client = http.HTTPClient('http://example.com:8004')
        e = self.assertRaises(
            exc.HTTPMultipleChoices, client.json_request, 'GET', '')
        self.assertIsNotNone(str(e))
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'User-Agent': 'python-heatclient'})

    def test_fake_json_request(self, mock_request):
        headers = {'User-Agent': 'python-heatclient'}
        mock_request.side_effect = [socket.gaierror]
        client = http.HTTPClient('fake://example.com:8004')
        self.assertRaises(exc.InvalidEndpoint,
                          client._http_request, "/", "GET")

        mock_request.assert_called_with('GET', 'fake://example.com:8004/',
                                        allow_redirects=False,
                                        headers=headers)

    def test_debug_curl_command(self, mock_request):
        with mock.patch('logging.Logger.debug') as mock_logging_debug:

            ssl_connection_params = {'ca_file': 'TEST_CA',
                                     'cert_file': 'TEST_CERT',
                                     'key_file': 'TEST_KEY',
                                     'insecure': 'TEST_NSA'}

            headers = {'key': 'value'}
            mock_logging_debug.return_value = None
            client = http.HTTPClient('http://foo')
            client.ssl_connection_params = ssl_connection_params
            client.log_curl_request('GET', '/bar', {'headers': headers,
                                                    'data': 'text'})
            mock_logging_debug.assert_called_with(
                "curl -g -i -X GET -H 'key: value' --key TEST_KEY "
                "--cert TEST_CERT --cacert TEST_CA "
                "-k -d 'text' http://foo/bar"
            )

    def test_http_request_socket_error(self, mock_request):
        headers = {'User-Agent': 'python-heatclient'}
        mock_request.side_effect = [socket.error]

        client = http.HTTPClient('http://example.com:8004')
        self.assertRaises(exc.CommunicationError,
                          client._http_request, "/", "GET")
        mock_request.assert_called_with('GET', 'http://example.com:8004/',
                                        allow_redirects=False,
                                        headers=headers)

    def test_http_request_socket_timeout(self, mock_request):
        headers = {'User-Agent': 'python-heatclient'}
        mock_request.side_effect = [socket.timeout]

        client = http.HTTPClient('http://example.com:8004')
        self.assertRaises(exc.CommunicationError,
                          client._http_request, "/", "GET")
        mock_request.assert_called_with('GET', 'http://example.com:8004/',
                                        allow_redirects=False,
                                        headers=headers)

    def test_http_request_specify_timeout(self, mock_request):
        mock_request.return_value = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/json'},
            '{}')
        client = http.HTTPClient('http://example.com:8004', timeout='123')
        resp, body = client.json_request('GET', '')
        self.assertEqual(200, resp.status_code)
        mock_request.assert_called_with(
            'GET', 'http://example.com:8004',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'User-Agent': 'python-heatclient'},
            timeout=float(123))

    def test_get_system_ca_file(self, mock_request):
        chosen = '/etc/ssl/certs/ca-certificates.crt'
        with mock.patch('os.path.exists') as mock_os:
            mock_os.return_value = chosen
            ca = http.get_system_ca_file()
            self.assertEqual(chosen, ca)
            mock_os.assert_called_once_with(chosen)

    def test_insecure_verify_cert_None(self, mock_request):
        client = http.HTTPClient('https://foo', insecure=True)
        self.assertFalse(client.verify_cert)

    def test_passed_cert_to_verify_cert(self, mock_request):
        client = http.HTTPClient('https://foo', ca_file="NOWHERE")
        self.assertEqual("NOWHERE", client.verify_cert)

        with mock.patch('heatclient.common.http.get_system_ca_file') as gsf:
            gsf.return_value = "SOMEWHERE"
            client = http.HTTPClient('https://foo')
            self.assertEqual("SOMEWHERE", client.verify_cert)

    @mock.patch('logging.Logger.debug', return_value=None)
    def test_curl_log_i18n_headers(self, mock_log, mock_request):
        kwargs = {'headers': {'Key': b'foo\xe3\x8a\x8e'}}

        client = http.HTTPClient('http://somewhere')
        client.log_curl_request("GET", '', kwargs=kwargs)
        mock_log.assert_called_once_with(
            u"curl -g -i -X GET -H 'Key: foo㊎' http://somewhere")


class SessionClientTest(testtools.TestCase):
    def setUp(self):
        super(SessionClientTest, self).setUp()
        self.request = mock.patch.object(adapter.LegacyJsonAdapter,
                                         'request').start()

    def test_session_simple_request(self):
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/octet-stream'},
            '')
        self.request.return_value = (resp, '')

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY)
        response = client.request(method='GET', url='')
        self.assertEqual(200, response.status_code)
        self.assertEqual('', ''.join([x for x in response.content]))

    def test_session_json_request(self):
        fake = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps({'some': 'body'}))
        self.request.return_value = (fake, {})

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY)

        resp = client.request('', 'GET')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({'some': 'body'}, resp.json())

    def test_404_error_response(self):
        fake = fakes.FakeHTTPResponse(
            404,
            'FAIL',
            {'content-type': 'application/octet-stream'},
            '')
        self.request.return_value = (fake, '')

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY)
        e = self.assertRaises(exc.HTTPNotFound,
                              client.request, '', 'GET')
        # Assert that the raised exception can be converted to string
        self.assertIsNotNone(str(e))

    def test_redirect_302_location(self):
        fake1 = fakes.FakeHTTPResponse(
            302,
            'OK',
            {'location': 'http://no.where/ishere'},
            ''
        )
        fake2 = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps({'Mount': 'Fuji'})
        )
        self.request.side_effect = [
            (fake1, ''), (fake2, jsonutils.dumps({'Mount': 'Fuji'}))]

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY,
                                    endpoint_override='http://no.where/')
        resp = client.request('', 'GET', redirect=True)

        self.assertEqual(200, resp.status_code)
        self.assertEqual({'Mount': 'Fuji'}, utils.get_response_body(resp))

        self.assertEqual(('', 'GET'), self.request.call_args_list[0][0])
        self.assertEqual(('ishere', 'GET'), self.request.call_args_list[1][0])
        for call in self.request.call_args_list:
            self.assertEqual({'headers': {'Content-Type': 'application/json'},
                              'user_agent': 'python-heatclient',
                              'raise_exc': False,
                              'redirect': True}, call[1])

    def test_302_location_no_endpoint(self):
        fake1 = fakes.FakeHTTPResponse(
            302,
            'OK',
            {'location': 'http://no.where/ishere'},
            ''
        )
        fake2 = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps({'Mount': 'Fuji'})
        )
        self.request.side_effect = [
            (fake1, ''), (fake2, jsonutils.dumps({'Mount': 'Fuji'}))]

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY)
        resp = client.request('', 'GET', redirect=True)

        self.assertEqual(200, resp.status_code)
        self.assertEqual({'Mount': 'Fuji'}, utils.get_response_body(resp))

        self.assertEqual(('', 'GET'), self.request.call_args_list[0][0])
        self.assertEqual(('http://no.where/ishere',
                          'GET'), self.request.call_args_list[1][0])
        for call in self.request.call_args_list:
            self.assertEqual({'headers': {'Content-Type': 'application/json'},
                              'user_agent': 'python-heatclient',
                              'raise_exc': False,
                              'redirect': True}, call[1])

    def test_redirect_302_no_location(self):
        fake = fakes.FakeHTTPResponse(
            302,
            'OK',
            {},
            ''
        )
        self.request.side_effect = [(fake, '')]

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY)
        e = self.assertRaises(exc.InvalidEndpoint,
                              client.request, '', 'GET', redirect=True)
        self.assertEqual("Location not returned with 302", str(e))

    def test_no_redirect_302_no_location(self):
        fake = fakes.FakeHTTPResponse(
            302,
            'OK',
            {'location': 'http://no.where/ishere'},
            ''
        )
        self.request.side_effect = [(fake, '')]

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY)

        self.assertEqual(fake, client.request('', 'GET'))

    def test_300_error_response(self):
        fake = fakes.FakeHTTPResponse(
            300,
            'FAIL',
            {'content-type': 'application/octet-stream'},
            '')
        self.request.return_value = (fake, '')

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY)
        e = self.assertRaises(exc.HTTPMultipleChoices,
                              client.request, '', 'GET')
        # Assert that the raised exception can be converted to string
        self.assertIsNotNone(str(e))

    def test_504_error_response(self):
        # for 504 we don't have specific exception type
        fake = fakes.FakeHTTPResponse(
            504,
            'FAIL',
            {'content-type': 'application/octet-stream'},
            '')
        self.request.return_value = (fake, '')

        client = http.SessionClient(session=mock.ANY,
                                    auth=mock.ANY)
        e = self.assertRaises(exc.HTTPException,
                              client.request, '', 'GET')

        self.assertEqual(504, e.code)

    def test_kwargs(self):
        fake = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            {}
        )
        kwargs = dict(endpoint_override='http://no.where/',
                      data='some_data')

        client = http.SessionClient(mock.ANY)

        self.request.return_value = (fake, {})

        resp = client.request('', 'GET', **kwargs)

        self.assertEqual({'endpoint_override': 'http://no.where/',
                          'data': '"some_data"',
                          'headers': {'Content-Type': 'application/json'},
                          'user_agent': 'python-heatclient',
                          'raise_exc': False}, self.request.call_args[1])
        self.assertEqual(200, resp.status_code)

    @mock.patch.object(jsonutils, 'dumps')
    def test_kwargs_with_files(self, mock_dumps):
        fake = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            {}
        )
        mock_dumps.return_value = "{'files': test}}"
        data = io.BytesIO(b'test')
        kwargs = {'endpoint_override': 'http://no.where/',
                  'data': {'files': data}}
        client = http.SessionClient(mock.ANY)

        self.request.return_value = (fake, {})

        resp = client.request('', 'GET', **kwargs)

        self.assertEqual({'endpoint_override': 'http://no.where/',
                          'data': "{'files': test}}",
                          'headers': {'Content-Type': 'application/json'},
                          'user_agent': 'python-heatclient',
                          'raise_exc': False}, self.request.call_args[1])
        self.assertEqual(200, resp.status_code)

    def test_methods(self):
        fake = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            {}
        )
        self.request.return_value = (fake, {})

        client = http.SessionClient(mock.ANY)
        methods = [client.get, client.put, client.post, client.patch,
                   client.delete, client.head]
        for method in methods:
            resp = method('')
            self.assertEqual(200, resp.status_code)

    def test_credentials_headers(self):
        client = http.SessionClient(mock.ANY)
        self.assertEqual({}, client.credentials_headers())
