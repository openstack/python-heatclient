
import httplib

from keystoneclient.v2_0 import client as ksclient


def script_keystone_client():
    ksclient.Client(auth_url='http://no.where',
                insecure=False,
                password='password',
                tenant_id='',
                tenant_name='tenant_name',
                username='username').AndReturn(
                FakeKeystone('abcd1234'))


def script_get(url):
    httplib.HTTPConnection.request('GET',
            url,
            headers=fake_headers())


def script_response(status, reason, headers, body):
    httplib.HTTPConnection.getresponse().AndReturn(
    FakeHTTPResponse(status, reason, headers, body))


def fake_headers():
    return {'X-Auth-Token': 'abcd1234',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'python-heatclient'}


class FakeServiceCatalog():
    def url_for(self, endpoint_type, service_type):
        return 'http://192.168.1.5:8004/v1/f14b41234'


class FakeKeystone():
    service_catalog = FakeServiceCatalog()

    def __init__(self, auth_token):
        self.auth_token = auth_token


class FakeHTTPResponse():

    version = 1.1

    def __init__(self, status, reason, headers, body):
        self.headers = headers
        self.body = body
        self.status = status
        self.reason = reason

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def getheaders(self):
        return self.headers.items()

    def read(self, amt=None):
        b = self.body
        self.body = None
        return b
