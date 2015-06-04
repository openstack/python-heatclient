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

from oslo_serialization import jsonutils

from heatclient.common import http
from heatclient import exc


def script_heat_list(url=None, show_nested=False, client=http.HTTPClient):
    if url is None:
        url = '/stacks?'

    resp_dict = {"stacks": [
        {
            "id": "1",
            "stack_name": "teststack",
            "stack_owner": "testowner",
            "project": "testproject",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        },
        {
            "id": "2",
            "stack_name": "teststack2",
            "stack_owner": "testowner",
            "project": "testproject",
            "stack_status": 'IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
        }]
    }
    if show_nested:
        nested = {
            "id": "3",
            "stack_name": "teststack_nested",
            "stack_status": 'IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z",
            "parent": "theparentof3"
        }
        resp_dict["stacks"].append(nested)
    resp = FakeHTTPResponse(200,
                            'success, you',
                            {'content-type': 'application/json'},
                            jsonutils.dumps(resp_dict))
    if client == http.SessionClient:
        client.request(url, 'GET').AndReturn(resp)
    else:
        client.json_request('GET', url).AndReturn((resp, resp_dict))


def mock_script_heat_list(show_nested=False):
    resp_dict = {"stacks": [
        {
            "id": "1",
            "stack_name": "teststack",
            "stack_owner": "testowner",
            "project": "testproject",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        },
        {
            "id": "2",
            "stack_name": "teststack2",
            "stack_owner": "testowner",
            "project": "testproject",
            "stack_status": 'IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
        }]
    }
    if show_nested:
        nested = {
            "id": "3",
            "stack_name": "teststack_nested",
            "stack_status": 'IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z",
            "parent": "theparentof3"
        }
        resp_dict["stacks"].append(nested)
    resp = FakeHTTPResponse(200,
                            'success, you',
                            {'content-type': 'application/json'},
                            jsonutils.dumps(resp_dict))
    return resp, resp_dict


def mock_script_event_list(
        stack_name="teststack", resource_name=None,
        rsrc_eventid1="7fecaeed-d237-4559-93a5-92d5d9111205",
        rsrc_eventid2="e953547a-18f8-40a7-8e63-4ec4f509648b",
        action="CREATE", final_state="COMPLETE", fakehttp=True):

    resp_dict = {"events": [
        {"event_time": "2013-12-05T14:14:31Z",
         "id": rsrc_eventid1,
         "links": [{"href": "http://heat.example.com:8004/foo",
                    "rel": "self"},
                   {"href": "http://heat.example.com:8004/foo2",
                    "rel": "resource"},
                   {"href": "http://heat.example.com:8004/foo3",
                    "rel": "stack"}],
         "logical_resource_id": "myDeployment",
         "physical_resource_id": None,
         "resource_name": resource_name if resource_name else "testresource",
         "resource_status": "%s_IN_PROGRESS" % action,
         "resource_status_reason": "state changed"},
        {"event_time": "2013-12-05T14:14:32Z",
         "id": rsrc_eventid2,
         "links": [{"href": "http://heat.example.com:8004/foo",
               "rel": "self"},
              {"href": "http://heat.example.com:8004/foo2",
               "rel": "resource"},
              {"href": "http://heat.example.com:8004/foo3",
               "rel": "stack"}],
         "logical_resource_id": "myDeployment",
         "physical_resource_id": "bce15ec4-8919-4a02-8a90-680960fb3731",
         "resource_name": resource_name if resource_name else "testresource",
         "resource_status": "%s_%s" % (action, final_state),
         "resource_status_reason": "state changed"}]}

    if resource_name is None:
        # if resource_name is not specified,
        # then request is made for stack events. Hence include the stack event
        stack_event1 = "0159dccd-65e1-46e8-a094-697d20b009e5"
        stack_event2 = "8f591a36-7190-4adb-80da-00191fe22388"
        resp_dict["events"].insert(
            0, {"event_time": "2013-12-05T14:14:30Z",
                "id": stack_event1,
                "links": [{"href": "http://heat.example.com:8004/foo",
                           "rel": "self"},
                          {"href": "http://heat.example.com:8004/foo2",
                           "rel": "resource"},
                          {"href": "http://heat.example.com:8004/foo3",
                           "rel": "stack"}],
                "logical_resource_id": "aResource",
                "physical_resource_id": None,
                "resource_name": stack_name,
                "resource_status": "%s_IN_PROGRESS" % action,
                "resource_status_reason": "state changed"})
        resp_dict["events"].append(
            {"event_time": "2013-12-05T14:14:33Z",
             "id": stack_event2,
             "links": [{"href": "http://heat.example.com:8004/foo",
                        "rel": "self"},
                       {"href": "http://heat.example.com:8004/foo2",
                        "rel": "resource"},
                       {"href": "http://heat.example.com:8004/foo3",
                        "rel": "stack"}],
             "logical_resource_id": "aResource",
             "physical_resource_id": None,
             "resource_name": stack_name,
             "resource_status": "%s_%s" % (action, final_state),
             "resource_status_reason": "state changed"})

    resp = FakeHTTPResponse(
        200,
        'OK',
        {'content-type': 'application/json'},
        jsonutils.dumps(resp_dict)) if fakehttp else None

    return resp, resp_dict


def script_heat_normal_error(client=http.HTTPClient):
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
                            jsonutils.dumps(resp_dict))
    if client == http.SessionClient:
        client.request('/stacks/bad', 'GET').AndRaise(exc.from_response(resp))
    else:
        client.json_request('GET',
                            '/stacks/bad').AndRaise(exc.from_response(resp))


def script_heat_error(resp_string, client=http.HTTPClient):
    resp = FakeHTTPResponse(400,
                            'The resource could not be found',
                            {'content-type': 'application/json'},
                            resp_string)
    if client == http.SessionClient:
        client.request('/stacks/bad', 'GET').AndRaise(exc.from_response(resp))
    else:
        client.json_request('GET',
                            '/stacks/bad').AndRaise(exc.from_response(resp))


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


class FakeRaw():
    version = 110


class FakeHTTPResponse():

    version = 1.1

    def __init__(self, status_code, reason, headers, content):
        self.headers = headers
        self.content = content
        self.status_code = status_code
        self.reason = reason
        self.raw = FakeRaw()

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def getheaders(self):
        return self.headers.items()

    def read(self, amt=None):
        b = self.content
        self.content = None
        return b

    def iter_content(self, chunksize):
        return self.content

    def json(self):
        return jsonutils.loads(self.content)
