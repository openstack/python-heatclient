import json

from heatclient.v1 import client as v1client
from keystoneclient.v2_0 import client as ksclient


def script_keystone_client():
    ksclient.Client(auth_url='http://no.where',
                insecure=False,
                password='password',
                tenant_id='',
                tenant_name='tenant_name',
                username='username').AndReturn(
                FakeKeystone('abcd1234'))


def script_heat_list():
    resp_dict = {"stacks": [{
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        },
        {
            "id": "2",
            "stack_name": "teststack2",
            "stack_status": 'IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
        }]
    }
    resp = FakeHTTPResponse(200,
        'success, yo',
        {'content-type': 'application/json'},
        json.dumps(resp_dict))
    v1client.Client.json_request('GET',
        '/stacks?limit=20').AndReturn((resp, resp_dict))


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
