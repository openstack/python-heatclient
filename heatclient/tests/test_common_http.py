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

import testtools

from heatclient.common import http
from heatclient import exc
from heatclient.tests import fakes
from mox3 import mox


class HttpClientTest(testtools.TestCase):

    # Patch os.environ to avoid required auth info.
    def setUp(self):
        super(HttpClientTest, self).setUp()
        self.m = mox.Mox()
        self.m.StubOutClassWithMocks(http.httplib, 'HTTPConnection')
        self.m.StubOutClassWithMocks(http.httplib, 'HTTPSConnection')
        self.addCleanup(self.m.UnsetStubs)
        self.addCleanup(self.m.ResetAll)

    def test_http_raw_request(self):
        # Record a 200
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/octet-stream'},
                ''))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.raw_request('GET', '')
        self.assertEqual(resp.status, 200)
        self.assertEqual(''.join([x for x in body]), '')
        self.m.VerifyAll()

    def test_token_or_credentials(self):
        # Record a 200
        fake200 = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/octet-stream'},
            '')

        # no token or credentials
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(fake200)

        # credentials
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'User-Agent': 'python-heatclient',
                                   'X-Auth-Key': 'pass',
                                   'X-Auth-User': 'user'})
        mock_conn.getresponse().AndReturn(fake200)

        # token suppresses credentials
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'User-Agent': 'python-heatclient',
                                   'X-Auth-Token': 'abcd1234'})
        mock_conn.getresponse().AndReturn(fake200)

        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.raw_request('GET', '')
        self.assertEqual(resp.status, 200)

        client.username = 'user'
        client.password = 'pass'
        resp, body = client.raw_request('GET', '')
        self.assertEqual(resp.status, 200)

        client.auth_token = 'abcd1234'
        resp, body = client.raw_request('GET', '')
        self.assertEqual(resp.status, 200)
        self.m.VerifyAll()

    def test_include_pass(self):
        # Record a 200
        fake200 = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/octet-stream'},
            '')

        # no token or credentials
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(fake200)

        # credentials
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'User-Agent': 'python-heatclient',
                                   'X-Auth-Key': 'pass',
                                   'X-Auth-User': 'user'})
        mock_conn.getresponse().AndReturn(fake200)

        # token suppresses credentials
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'User-Agent': 'python-heatclient',
                                   'X-Auth-Token': 'abcd1234',
                                   'X-Auth-Key': 'pass',
                                   'X-Auth-User': 'user'})
        mock_conn.getresponse().AndReturn(fake200)

        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.raw_request('GET', '')
        self.assertEqual(200, resp.status)

        client.username = 'user'
        client.password = 'pass'
        client.include_pass = True
        resp, body = client.raw_request('GET', '')
        self.assertEqual(200, resp.status)

        client.auth_token = 'abcd1234'
        resp, body = client.raw_request('GET', '')
        self.assertEqual(200, resp.status)
        self.m.VerifyAll()

    def test_not_include_pass(self):
        # Record a 200
        fake500 = fakes.FakeHTTPResponse(
            500, 'ERROR',
            {'content-type': 'application/octet-stream'},
            '(HTTP 401)')

        # no token or credentials
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(fake500)

        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        e = self.assertRaises(exc.HTTPUnauthorized,
                              client.raw_request, 'GET', '')
        self.assertIn('include-password', str(e))

    def test_region_name(self):
        # Record a 200
        fake200 = fakes.FakeHTTPResponse(
            200, 'OK',
            {'content-type': 'application/octet-stream'},
            '')

        # Specify region name
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/octet-stream',
                                   'X-Region-Name': 'RegionOne',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(fake200)

        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        client.region_name = 'RegionOne'
        resp, body = client.raw_request('GET', '')
        self.assertEqual(resp.status, 200)
        self.m.VerifyAll()

    def test_http_json_request(self):
        # Record a 200
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}'))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '')
        self.assertEqual(resp.status, 200)
        self.assertEqual(body, {})
        self.m.VerifyAll()

    def test_http_json_request_w_req_body(self):
        # Record a 200
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/', body='"test-body"',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}'))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '', body='test-body')
        self.assertEqual(resp.status, 200)
        self.assertEqual(body, {})
        self.m.VerifyAll()

    def test_http_json_request_non_json_resp_cont_type(self):
        # Record a 200
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/', body='"test-body"',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'not/json'},
                '{}'))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '', body='test-body')
        self.assertEqual(resp.status, 200)
        self.assertEqual(body, None)
        self.m.VerifyAll()

    def test_http_json_request_invalid_json(self):
        # Record a 200
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                'invalid-json'))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '')
        self.assertEqual(resp.status, 200)
        self.assertEqual(body, 'invalid-json')
        self.m.VerifyAll()

    def test_http_json_request_redirect(self):
        # Record the 302
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://example.com:8004'},
                ''))
        # Record the following 200
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                '{}'))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        resp, body = client.json_request('GET', '')
        self.assertEqual(resp.status, 200)
        self.assertEqual(body, {})
        self.m.VerifyAll()

    def test_http_json_request_prohibited_redirect(self):
        # Record the 302
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                302, 'Found',
                {'location': 'http://prohibited.example.com:8004'},
                ''))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        self.assertRaises(exc.InvalidEndpoint, client.json_request, 'GET', '')
        self.m.VerifyAll()

    def test_http_404_json_request(self):
        # Record a 404
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                404, 'OK', {'content-type': 'application/json'},
                '{}'))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        try:
            client.json_request('GET', '')
            self.fail('No exception raised')
        except exc.HTTPNotFound as e:
            # Assert that the raised exception can be converted to string
            self.assertNotEqual(e.message, None)
        self.m.VerifyAll()

    def test_http_300_json_request(self):
        # Record a 300
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                timeout=600.0)
        mock_conn.request('GET', '/',
                          headers={'Content-Type': 'application/json',
                                   'Accept': 'application/json',
                                   'User-Agent': 'python-heatclient'})
        mock_conn.getresponse().AndReturn(
            fakes.FakeHTTPResponse(
                300, 'OK', {'content-type': 'application/json'},
                '{}'))
        # Replay, create client, assert
        self.m.ReplayAll()
        client = http.HTTPClient('http://example.com:8004')
        try:
            client.json_request('GET', '')
            self.fail('No exception raised')
        except exc.HTTPMultipleChoices as e:
            # Assert that the raised exception can be converted to string
            self.assertNotEqual(e.message, None)
        self.m.VerifyAll()

    #def test_https_json_request(self):
    #    # Record a 200
    #    mock_conn = http.httplib.HTTPSConnection('example.com', 8004,
    #                                            '', timeout=600.0)
    #    mock_conn.request('GET', '/',
    #                      headers={'Content-Type': 'application/json',
    #                               'Accept': 'application/json',
    #                               'User-Agent': 'python-heatclient'})
    #    mock_conn.getresponse().AndReturn(fakes.FakeHTTPResponse(200, 'OK',
    #                                     {'content-type': 'application/json'},
    #                                     '{}'))
    #    # Replay, create client, assert
    #    self.m.ReplayAll()
    #    client = http.HTTPClient('https://example.com:8004',
    #                             ca_file='dummy',
    #                             cert_file='dummy',
    #                             key_file='dummy')
    #    resp, body = client.json_request('GET', '')
    #    self.assertEqual(resp.status, 200)
    #    self.assertEqual(body, {})
    #    self.m.VerifyAll()

    def test_fake_json_request(self):
        self.assertRaises(exc.InvalidEndpoint, http.HTTPClient,
                          'fake://example.com:8004')
