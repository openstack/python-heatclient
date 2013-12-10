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

import json

from heatclient.common import http
from heatclient import exc
from keystoneclient.v2_0 import client as ksclient


def script_keystone_client(token=None):
    if token:
        ksclient.Client(auth_url='http://no.where',
                        insecure=False,
                        tenant_id='tenant_id',
                        token=token).AndReturn(FakeKeystone(token))
    else:
        ksclient.Client(auth_url='http://no.where',
                        insecure=False,
                        password='password',
                        tenant_name='tenant_name',
                        username='username').AndReturn(FakeKeystone(
                                                       'abcd1234'))


def script_heat_list():
    resp_dict = {"stacks": [{
        "id": "1",
        "stack_name": "teststack",
        "stack_status": 'CREATE_COMPLETE',
        "creation_time": "2012-10-25T01:58:47Z"},
        {
            "id": "2",
            "stack_name": "teststack2",
            "stack_status": 'IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
        }]
    }
    resp = FakeHTTPResponse(200,
                            'success, you',
                            {'content-type': 'application/json'},
                            json.dumps(resp_dict))
    http.HTTPClient.json_request('GET', '/stacks?').AndReturn(
        (resp, resp_dict))


def script_heat_normal_error():
    resp_dict = {
        "explanation": "The resource could not be found.",
        "code": 404,
        "error": {
            "message": "The Stack (bad) could not be found.",
            "type": "StackNotFound",
            "traceback": "",
        },
        "title": "Not Found"
    }
    resp = FakeHTTPResponse(400,
                            'The resource could not be found',
                            {'content-type': 'application/json'},
                            json.dumps(resp_dict))
    http.HTTPClient.json_request('GET', '/stacks/bad').AndRaise(
        exc.from_response(resp, json.dumps(resp_dict)))


def script_heat_error(resp_string):
    resp = FakeHTTPResponse(400,
                            'The resource could not be found',
                            {'content-type': 'application/json'},
                            resp_string)
    http.HTTPClient.json_request('GET', '/stacks/bad').AndRaise(
        exc.from_response(resp, resp_string))


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
