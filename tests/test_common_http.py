import mox
import unittest

import fakes
from heatclient.common import http
from heatclient import exc


class HttpClientTest(unittest.TestCase):

    # Patch os.environ to avoid required auth info.
    def setUp(self):
        self.m = mox.Mox()
        self.m.StubOutClassWithMocks(http.httplib, 'HTTPConnection')
        self.m.StubOutClassWithMocks(http.httplib, 'HTTPSConnection')

    def tearDown(self):
        self.m.UnsetStubs()
        self.m.ResetAll()

    def test_http_raw_request(self):
        # Record a 200
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                '', timeout=600.0)
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

    def test_http_json_request(self):
        # Record a 200
        mock_conn = http.httplib.HTTPConnection('example.com', 8004,
                                                '', timeout=600.0)
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
                                                '', timeout=600.0)
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
                                                '', timeout=600.0)
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
                                                '', timeout=600.0)
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
                                                '', timeout=600.0)
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
                                                '', timeout=600.0)
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
                                                '', timeout=600.0)
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
                                                '', timeout=600.0)
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
                                                '', timeout=600.0)
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
