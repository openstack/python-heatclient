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

import os
import sys
import tempfile
from unittest import mock
import uuid

import fixtures
from keystoneauth1 import fixture as keystone_fixture
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from requests_mock.contrib import fixture as rm_fixture
import six
from six.moves.urllib import parse
from six.moves.urllib import request
import testscenarios
import testtools
import yaml

from heatclient._i18n import _
from heatclient.common import http
from heatclient.common import utils
from heatclient import exc
import heatclient.shell
from heatclient.tests.unit import fakes
import heatclient.v1.shell

load_tests = testscenarios.load_tests_apply_scenarios
TEST_VAR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'var'))

BASE_HOST = 'http://keystone.example.com'
BASE_URL = "%s:5000/" % BASE_HOST
V2_URL = "%sv2.0" % BASE_URL
V3_URL = "%sv3" % BASE_URL


FAKE_ENV_KEYSTONE_V2 = {
    'OS_USERNAME': 'username',
    'OS_PASSWORD': 'password',
    'OS_TENANT_NAME': 'tenant_name',
    'OS_AUTH_URL': BASE_URL,
}

FAKE_ENV_KEYSTONE_V3 = {
    'OS_USERNAME': 'username',
    'OS_PASSWORD': 'password',
    'OS_TENANT_NAME': 'tenant_name',
    'OS_AUTH_URL': BASE_URL,
    'OS_USER_DOMAIN_ID': 'default',
    'OS_PROJECT_DOMAIN_ID': 'default',
}


class TestCase(testtools.TestCase):

    tokenid = uuid.uuid4().hex

    def setUp(self):
        """
        Sets the variables.

        Args:
            self: (todo): write your description
        """
        super(TestCase, self).setUp()
        self.requests = self.useFixture(rm_fixture.Fixture())
        # httpretty doesn't work as expected if http proxy environmen
        # variable is set.
        self.useFixture(fixtures.EnvironmentVariable('http_proxy'))
        self.useFixture(fixtures.EnvironmentVariable('https_proxy'))
        self.patch('heatclient.v1.shell.show_deprecated')

    def set_fake_env(self, fake_env):
        """
        Sets the environment variables for the environment.

        Args:
            self: (todo): write your description
            fake_env: (todo): write your description
        """
        client_env = ('OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_ID',
                      'OS_TENANT_NAME', 'OS_AUTH_URL', 'OS_REGION_NAME',
                      'OS_AUTH_TOKEN', 'OS_NO_CLIENT_AUTH', 'OS_SERVICE_TYPE',
                      'OS_ENDPOINT_TYPE', 'HEAT_URL')

        for key in client_env:
            self.useFixture(
                fixtures.EnvironmentVariable(key, fake_env.get(key)))

    def shell_error(self, argstr, error_match, exception):
        """
        Handles an error.

        Args:
            self: (todo): write your description
            argstr: (str): write your description
            error_match: (todo): write your description
            exception: (todo): write your description
        """
        _shell = heatclient.shell.HeatShell()
        e = self.assertRaises(exception, _shell.main, argstr.split())
        self.assertRegex(e.__str__(), error_match)

    def register_keystone_v2_token_fixture(self):
        """
        Register a v2 v2 token.

        Args:
            self: (todo): write your description
        """
        v2_token = keystone_fixture.V2Token(token_id=self.tokenid)
        service = v2_token.add_service('orchestration')
        service.add_endpoint('http://heat.example.com',
                             admin='http://heat-admin.localdomain',
                             internal='http://heat.localdomain',
                             region='RegionOne')
        self.requests.post('%s/tokens' % V2_URL, json=v2_token)

    def register_keystone_v3_token_fixture(self):
        """
        Register v3 v3 v3 v3 v3 token.

        Args:
            self: (todo): write your description
        """
        v3_token = keystone_fixture.V3Token()
        service = v3_token.add_service('orchestration')
        service.add_standard_endpoints(public='http://heat.example.com',
                                       admin='http://heat-admin.localdomain',
                                       internal='http://heat.localdomain')
        self.requests.post('%s/auth/tokens' % V3_URL,
                           json=v3_token,
                           headers={'X-Subject-Token': self.tokenid})

    def register_keystone_auth_fixture(self):
        """
        Register a new auth_keystone keystone authentication.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_v2_token_fixture()
        self.register_keystone_v3_token_fixture()

        version_list = keystone_fixture.DiscoveryList(href=BASE_URL)
        self.requests.get(BASE_URL, json=version_list)

    # NOTE(tlashchova): this overrides the testtools.TestCase.patch method
    # that does simple monkey-patching in favor of mock's patching
    def patch(self, target, **kwargs):
        """
        Patch the given target.

        Args:
            self: (todo): write your description
            target: (todo): write your description
        """
        mockfixture = self.useFixture(fixtures.MockPatch(target, **kwargs))
        return mockfixture.mock

    def stack_list_resp_dict(self, show_nested=False, include_project=False):
        """
        List stack stack stack stack.

        Args:
            self: (todo): write your description
            show_nested: (bool): write your description
            include_project: (bool): write your description
        """
        stack1 = {
            "id": "1",
            "stack_name": "teststack",
            "stack_owner": "testowner",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"}
        stack2 = {
            "id": "2",
            "stack_name": "teststack2",
            "stack_owner": "testowner",
            "stack_status": 'IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
            }
        if include_project:
            stack1['project'] = 'testproject'
            stack1['project'] = 'testproject'

        resp_dict = {"stacks": [stack1, stack2]}
        if show_nested:
            nested = {
                "id": "3",
                "stack_name": "teststack_nested",
                "stack_status": 'IN_PROGRESS',
                "creation_time": "2012-10-25T01:58:47Z",
                "parent": "theparentof3"
            }
            if include_project:
                nested['project'] = 'testproject'
            resp_dict["stacks"].append(nested)

        return resp_dict

    def event_list_resp_dict(
            self,
            stack_name="teststack",
            resource_name=None,
            rsrc_eventid1="7fecaeed-d237-4559-93a5-92d5d9111205",
            rsrc_eventid2="e953547a-18f8-40a7-8e63-4ec4f509648b",
            final_state="COMPLETE"):
        """
        Return a list of events.

        Args:
            self: (todo): write your description
            stack_name: (str): write your description
            resource_name: (str): write your description
            rsrc_eventid1: (todo): write your description
            rsrc_eventid2: (todo): write your description
            final_state: (str): write your description
        """

        action = "CREATE"
        rn = resource_name if resource_name else "testresource"
        resp_dict = {"events": [
            {"event_time": "2013-12-05T14:14:31",
             "id": rsrc_eventid1,
             "links": [{"href": "http://heat.example.com:8004/foo",
                        "rel": "self"},
                       {"href": "http://heat.example.com:8004/foo2",
                        "rel": "resource"},
                       {"href": "http://heat.example.com:8004/foo3",
                        "rel": "stack"}],
             "logical_resource_id": "myDeployment",
             "physical_resource_id": None,
             "resource_name": rn,
             "resource_status": "%s_IN_PROGRESS" % action,
             "resource_status_reason": "state changed"},
            {"event_time": "2013-12-05T14:14:32",
             "id": rsrc_eventid2,
             "links": [{"href": "http://heat.example.com:8004/foo",
                        "rel": "self"},
                       {"href": "http://heat.example.com:8004/foo2",
                        "rel": "resource"},
                       {"href": "http://heat.example.com:8004/foo3",
                        "rel": "stack"}],
             "logical_resource_id": "myDeployment",
             "physical_resource_id": "bce15ec4-8919-4a02-8a90-680960fb3731",
             "resource_name": rn,
             "resource_status": "%s_%s" % (action, final_state),
             "resource_status_reason": "state changed"}]}

        if resource_name is None:
            # if resource_name is not specified,
            # then request is made for stack events. Hence include the stack
            # event
            stack_event1 = "0159dccd-65e1-46e8-a094-697d20b009e5"
            stack_event2 = "8f591a36-7190-4adb-80da-00191fe22388"
            resp_dict["events"].insert(
                0, {"event_time": "2013-12-05T14:14:30",
                    "id": stack_event1,
                    "links": [{"href": "http://heat.example.com:8004/foo",
                               "rel": "self"},
                              {"href": "http://heat.example.com:8004/foo2",
                               "rel": "resource"},
                              {"href": "http://heat.example.com:8004/foo3",
                               "rel": "stack"}],
                    "logical_resource_id": "aResource",
                    "physical_resource_id": 'foo3',
                    "resource_name": stack_name,
                    "resource_status": "%s_IN_PROGRESS" % action,
                    "resource_status_reason": "state changed"})
            resp_dict["events"].append(
                {"event_time": "2013-12-05T14:14:33",
                 "id": stack_event2,
                 "links": [{"href": "http://heat.example.com:8004/foo",
                            "rel": "self"},
                           {"href": "http://heat.example.com:8004/foo2",
                            "rel": "resource"},
                           {"href": "http://heat.example.com:8004/foo3",
                            "rel": "stack"}],
                 "logical_resource_id": "aResource",
                 "physical_resource_id": 'foo3',
                 "resource_name": stack_name,
                 "resource_status": "%s_%s" % (action, final_state),
                 "resource_status_reason": "state changed"})

        return resp_dict


class EnvVarTest(TestCase):

    scenarios = [
        ('username', dict(
            remove='OS_USERNAME',
            err='You must provide a username')),
        ('password', dict(
            remove='OS_PASSWORD',
            err='You must provide a password')),
        ('tenant_name', dict(
            remove='OS_TENANT_NAME',
            err='You must provide a tenant id')),
        ('auth_url', dict(
            remove='OS_AUTH_URL',
            err='You must provide an auth url')),
    ]

    def test_missing_auth(self):
        """
        .. version of missing environment variables.

        Args:
            self: (todo): write your description
        """

        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        fake_env[self.remove] = None
        self.set_fake_env(fake_env)
        self.shell_error('stack-list', self.err, exception=exc.CommandError)


class EnvVarTestToken(TestCase):

    scenarios = [
        ('tenant_id', dict(
            remove='OS_TENANT_ID',
            err='You must provide a tenant id')),
        ('auth_url', dict(
            remove='OS_AUTH_URL',
            err='You must provide an auth url')),
    ]

    def test_missing_auth(self):
        """
        Manage the environment authentication

        Args:
            self: (todo): write your description
        """

        fake_env = {
            'OS_AUTH_TOKEN': 'atoken',
            'OS_TENANT_ID': 'tenant_id',
            'OS_AUTH_URL': 'http://no.where',
        }
        fake_env[self.remove] = None
        self.set_fake_env(fake_env)
        self.shell_error('stack-list', self.err, exception=exc.CommandError)


class ShellParamValidationTest(TestCase):

    scenarios = [
        ('stack-create', dict(
            command='stack-create ts -P "ab"',
            with_tmpl=True,
            err='Malformed parameter')),
        ('stack-update', dict(
            command='stack-update ts -P "a-b"',
            with_tmpl=True,
            err='Malformed parameter')),
        ('stack-list-with-sort-dir', dict(
            command='stack-list --sort-dir up',
            with_tmpl=False,
            err='Sorting direction must be one of')),
        ('stack-list-with-sort-key', dict(
            command='stack-list --sort-keys owner',
            with_tmpl=False,
            err='Sorting key \'owner\' not one of')),
    ]

    def test_bad_parameters(self):
        """
        Determine command parameters

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': BASE_URL,
        }
        self.set_fake_env(fake_env)
        cmd = self.command

        if self.with_tmpl:
            template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
            cmd = '%s --template-file=%s ' % (self.command, template_file)

        self.shell_error(cmd, self.err, exception=exc.CommandError)


class ShellValidationTest(TestCase):

    def test_failed_auth(self):
        """
        Authenticates the authentication.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        failed_msg = 'Unable to authenticate user with credentials provided'

        with mock.patch.object(http.SessionClient, 'request',
                               side_effect=exc.Unauthorized(failed_msg)) as sc:
            self.set_fake_env(FAKE_ENV_KEYSTONE_V2)
            self.shell_error('stack-list', failed_msg,
                             exception=exc.Unauthorized)
            sc.assert_called_once_with('/stacks?', 'GET')

    def test_stack_create_validation(self):
        """
        Create stack stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)
        self.shell_error(
            'stack-create teststack '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"',
            'Need to specify exactly one of',
            exception=exc.CommandError)

    def test_stack_create_with_paramfile_validation(self):
        """
        Creates a stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)
        self.shell_error(
            'stack-create teststack '
            '--parameter-file private_key=private_key.env '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"',
            'Need to specify exactly one of',
            exception=exc.CommandError)

    def test_stack_create_validation_keystone_v3(self):
        """
        Determine stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V3)
        self.shell_error(
            'stack-create teststack '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"',
            'Need to specify exactly one of',
            exception=exc.CommandError
        )


class ShellBase(TestCase):

    (JSON, RAW, SESSION) = ('json', 'raw', 'session')

    def setUp(self):
        """
        Sets the results of this class.

        Args:
            self: (todo): write your description
        """
        super(ShellBase, self).setUp()
        self._calls = {self.JSON: [], self.RAW: [], self.SESSION: []}
        self._results = {self.JSON: [], self.RAW: [], self.SESSION: []}
        self.useFixture(fixtures.MockPatchObject(
            http.HTTPClient,
            'json_request',
            side_effect=self._results[self.JSON]))
        self.useFixture(fixtures.MockPatchObject(
            http.HTTPClient,
            'raw_request',
            side_effect=self._results[self.RAW]))
        self.useFixture(fixtures.MockPatchObject(
            http.SessionClient,
            'request',
            side_effect=self._results[self.SESSION]))
        self.client = http.SessionClient

        # Some tests set exc.verbose = 1, so reset on cleanup
        def unset_exc_verbose():
            """
            Unset the exception traceback.

            Args:
            """
            exc.verbose = 0

        self.addCleanup(unset_exc_verbose)

    def tearDown(self):
        """
        Tear down the client.

        Args:
            self: (todo): write your description
        """
        http.HTTPClient.json_request.assert_has_calls(self._calls[self.JSON])
        http.HTTPClient.raw_request.assert_has_calls(self._calls[self.RAW])
        http.SessionClient.request.assert_has_calls(self._calls[self.SESSION])
        super(ShellBase, self).tearDown()

    def shell(self, argstr):
        """
        Execute a shell.

        Args:
            self: (todo): write your description
            argstr: (str): write your description
        """
        orig = sys.stdout
        try:
            sys.stdout = six.StringIO()
            _shell = heatclient.shell.HeatShell()
            _shell.main(argstr.split())
            self.subcommands = _shell.subcommands.keys()
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(0, exc_value.code)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out

    def mock_request_error(self, path, verb, error):
        """
        Makes a http request and return value.

        Args:
            self: (todo): write your description
            path: (str): write your description
            verb: (bool): write your description
            error: (todo): write your description
        """
        raw = verb == 'DELETE'
        if self.client == http.SessionClient:
            request = self.SESSION
            self._expect_call(request, path, verb)
        else:
            if raw:
                request = self.RAW
            else:
                request = self.JSON
            self._expect_call(request, verb, path)
        self._results[request].append(error)

    def mock_request_get(self, path, response, raw=False, **kwargs):
        """
        Perform a request.

        Args:
            self: (todo): write your description
            path: (str): write your description
            response: (todo): write your description
            raw: (bool): write your description
        """
        self.mock_request(path, 'GET', response, raw=raw, **kwargs)

    def mock_request_delete(self, path, response=None):
        """
        Make a delete request.

        Args:
            self: (todo): write your description
            path: (str): write your description
            response: (todo): write your description
        """
        self.mock_request(path, 'DELETE', response, raw=True, status_code=204)

    def mock_request_post(self, path, response, req_headers=False,
                          status_code=200, **kwargs):
        """
        Make a post request.

        Args:
            self: (todo): write your description
            path: (str): write your description
            response: (todo): write your description
            req_headers: (todo): write your description
            status_code: (int): write your description
        """
        self.mock_request(path, 'POST', response=response, raw=False,
                          status_code=status_code, req_headers=req_headers,
                          **kwargs)

    def mock_request_put(self, path, response, status_code=202, **kwargs):
        """
        Makes a request.

        Args:
            self: (todo): write your description
            path: (str): write your description
            response: (todo): write your description
            status_code: (int): write your description
        """
        self.mock_request(path, 'PUT', response=response, raw=False,
                          status_code=status_code, req_headers=True,
                          **kwargs)

    def mock_request_patch(self, path, response, req_headers=True,
                           status_code=202, **kwargs):
        """
        Make a mock patch.

        Args:
            self: (todo): write your description
            path: (str): write your description
            response: (todo): write your description
            req_headers: (todo): write your description
            status_code: (int): write your description
        """
        self.mock_request(path, 'PATCH', response=response, raw=False,
                          status_code=status_code, req_headers=req_headers,
                          **kwargs)

    def mock_request(self, path, verb, response=None, raw=False,
                     status_code=200, req_headers=False, **kwargs):
        """
        Make an http request.

        Args:
            self: (todo): write your description
            path: (str): write your description
            verb: (bool): write your description
            response: (todo): write your description
            raw: (bool): write your description
            status_code: (int): write your description
            req_headers: (dict): write your description
        """
        kwargs = dict(kwargs)
        if req_headers:
            if self.client is http.HTTPClient:
                kwargs['headers'] = {'X-Auth-Key': 'password',
                                     'X-Auth-User': 'username'}
            else:
                kwargs['headers'] = {}
        reason = 'OK'
        if response:
            headers = {'content-type': 'application/json'}
            content = jsonutils.dumps(response)
        else:
            headers = {}
            content = None
        if status_code == 201:
            headers['location'] = 'http://heat.example.com/stacks/myStack'

        resp = fakes.FakeHTTPResponse(status_code, reason, headers, content)
        if self.client == http.SessionClient:
            request = self.SESSION
            self._results[request].append(resp)
            self._expect_call(request, path, verb, **kwargs)
        else:
            if raw:
                request = self.RAW
                self._results[request].append(resp)
            else:
                request = self.JSON
                self._results[request].append((resp, response))
            self._expect_call(request, verb, path, **kwargs)

    def _expect_call(self, request, *args, **kwargs):
        """
        Expect the given call to call.

        Args:
            self: (todo): write your description
            request: (todo): write your description
        """
        self._calls[request].append(mock.call(*args, **kwargs))

    def mock_stack_list(self, path=None, show_nested=False):
        """
        Mock_stack

        Args:
            self: (todo): write your description
            path: (str): write your description
            show_nested: (bool): write your description
        """
        if path is None:
            path = '/stacks?'

        resp_dict = self.stack_list_resp_dict(show_nested)
        self.mock_request_get(path, resp_dict)


class ShellTestNoMoxBase(TestCase):
    # NOTE(dhu):  This class is reserved for no Mox usage.  Instead,
    # use requests_mock to expose errors from json_request.
    def setUp(self):
        """
        Sets the environment.

        Args:
            self: (todo): write your description
        """
        super(ShellTestNoMoxBase, self).setUp()
        self._set_fake_env()

    def _set_fake_env(self):
        """
        Set the fake environment variables for the fake environment.

        Args:
            self: (todo): write your description
        """
        self.set_fake_env({
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'HEAT_URL': 'http://heat.example.com',
            'OS_AUTH_URL': BASE_URL,
            'OS_NO_CLIENT_AUTH': 'True'
        })

    def shell(self, argstr):
        """
        Execute a shell.

        Args:
            self: (todo): write your description
            argstr: (str): write your description
        """
        orig = sys.stdout
        try:
            sys.stdout = six.StringIO()
            _shell = heatclient.shell.HeatShell()
            _shell.main(argstr.split())
            self.subcommands = _shell.subcommands.keys()
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(0, exc_value.code)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out


class ShellTestNoMox(ShellTestNoMoxBase):
    # This function tests err msg handling
    def test_stack_create_parameter_missing_err_msg(self):
        """
        Test for missing stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {"error":
                     {"message": 'The Parameter (key_name) was not provided.',
                      "type": "UserParameterMissing"}}

        self.requests.post('http://heat.example.com/stacks',
                           status_code=400,
                           headers={'Content-Type': 'application/json'},
                           json=resp_dict)

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')

        self.shell_error('stack-create -f %s stack' % template_file,
                         r'The Parameter \(key_name\) was not provided.',
                         exception=exc.HTTPBadRequest)

    def test_event_list(self):
        """
        Get list of eventid1 event.

        Args:
            self: (todo): write your description
        """
        eventid1 = uuid.uuid4().hex
        eventid2 = uuid.uuid4().hex
        self.register_keystone_auth_fixture()

        h = {'Content-Type': 'text/plain; charset=UTF-8',
             'location': 'http://heat.example.com/stacks/myStack/60f83b5e'}
        self.requests.get('http://heat.example.com/stacks/myStack',
                          status_code=302,
                          headers=h)

        resp_dict = self.event_list_resp_dict(
            resource_name="myDeployment", rsrc_eventid1=eventid1,
            rsrc_eventid2=eventid2
        )

        self.requests.get('http://heat.example.com/stacks/myStack/60f83b5e/'
                          'resources/myDeployment/events',
                          headers={'Content-Type': 'application/json'},
                          json=resp_dict)

        list_text = self.shell('event-list -r myDeployment myStack')

        required = [
            'resource_name',
            'id',
            'resource_status_reason',
            'resource_status',
            'event_time',
            'myDeployment',
            eventid1,
            eventid2,
            'state changed',
            'CREATE_IN_PROGRESS',
            '2013-12-05T14:14:31',
            '2013-12-05T14:14:32',
        ]

        for r in required:
            self.assertRegex(list_text, r)


class ShellTestNoMoxV3(ShellTestNoMox):

    def _set_fake_env(self):
        """
        Sets the environment variables for the environment.

        Args:
            self: (todo): write your description
        """
        fake_env_kwargs = {'OS_NO_CLIENT_AUTH': 'True',
                           'HEAT_URL': 'http://heat.example.com'}
        fake_env_kwargs.update(FAKE_ENV_KEYSTONE_V3)
        self.set_fake_env(fake_env_kwargs)


class ShellTestEndpointType(TestCase):

    def setUp(self):
        """
        Sets the mock for this connection.

        Args:
            self: (todo): write your description
        """
        super(ShellTestEndpointType, self).setUp()
        self.useFixture(fixtures.MockPatchObject(http,
                                                 '_construct_http_client'))
        self.useFixture(fixtures.MockPatchObject(heatclient.v1.shell,
                                                 'do_stack_list'))
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_endpoint_type_public_url(self):
        """
        Test if public endpoint type public_endpoint_public_url

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        kwargs = {
            'auth_url': 'http://keystone.example.com:5000/',
            'session': mock.ANY,
            'auth': mock.ANY,
            'service_type': 'orchestration',
            'endpoint_type': 'publicURL',
            'region_name': '',
            'username': 'username',
            'password': 'password',
            'include_pass': False,
            'endpoint_override': mock.ANY,
        }

        heatclient.shell.main(('stack-list',))

        http._construct_http_client.assert_called_once_with(**kwargs)
        heatclient.v1.shell.do_stack_list.assert_called_once()

    def test_endpoint_type_admin_url(self):
        """
        Type endpoint type endpoint endpoint

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        kwargs = {
            'auth_url': 'http://keystone.example.com:5000/',
            'session': mock.ANY,
            'auth': mock.ANY,
            'service_type': 'orchestration',
            'endpoint_type': 'adminURL',
            'region_name': '',
            'username': 'username',
            'password': 'password',
            'include_pass': False,
            'endpoint_override': mock.ANY,
        }

        heatclient.shell.main(('--os-endpoint-type=adminURL', 'stack-list',))

        http._construct_http_client.assert_called_once_with(**kwargs)
        heatclient.v1.shell.do_stack_list.assert_called_once()

    def test_endpoint_type_internal_url(self):
        """
        Register type endpoint type endpoint type endpoint

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.useFixture(fixtures.EnvironmentVariable('OS_ENDPOINT_TYPE',
                                                     'internalURL'))
        kwargs = {
            'auth_url': 'http://keystone.example.com:5000/',
            'session': mock.ANY,
            'auth': mock.ANY,
            'service_type': 'orchestration',
            'endpoint_type': 'internalURL',
            'region_name': '',
            'username': 'username',
            'password': 'password',
            'include_pass': False,
            'endpoint_override': mock.ANY,
        }

        heatclient.shell.main(('stack-list',))

        http._construct_http_client.assert_called_once_with(**kwargs)
        heatclient.v1.shell.do_stack_list.assert_called_once()


class ShellTestCommon(ShellBase):

    def setUp(self):
        """
        Sets the environment.

        Args:
            self: (todo): write your description
        """
        super(ShellTestCommon, self).setUp()
        self.client = http.SessionClient
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_help_unknown_command(self):
        """
        Test if the help command is not help for a help command.

        Args:
            self: (todo): write your description
        """
        self.assertRaises(exc.CommandError, self.shell, 'help foofoo')

    def test_help(self):
        """
        Test for help

        Args:
            self: (todo): write your description
        """
        required = [
            '^usage: heat',
            '(?m)^See "heat help COMMAND" for help on a specific command',
        ]
        for argstr in ['--help', 'help']:
            help_text = self.shell(argstr)
            for r in required:
                self.assertRegex(help_text, r)

    def test_command_help(self):
        """
        Print the help

        Args:
            self: (todo): write your description
        """
        output = self.shell('help help')
        self.assertIn('usage: heat help [<subcommand>]', output)
        subcommands = list(self.subcommands)
        for command in subcommands:
            if command.replace('_', '-') == 'bash-completion':
                continue
            output1 = self.shell('help %s' % command)
            output2 = self.shell('%s --help' % command)
            self.assertEqual(output1, output2)
            self.assertRegex(output1, '^usage: heat %s' % command)

    def test_debug_switch_raises_error(self):
        """
        This method to make_debug.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_error('/stacks?', 'GET', exc.Unauthorized("FAIL"))

        args = ['--debug', 'stack-list']
        self.assertRaises(exc.Unauthorized, heatclient.shell.main, args)

    def test_dash_d_switch_raises_error(self):
        """
        Test for the dashboard.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_error('/stacks?', 'GET', exc.CommandError("FAIL"))

        args = ['-d', 'stack-list']
        self.assertRaises(exc.CommandError, heatclient.shell.main, args)

    def test_no_debug_switch_no_raises_errors(self):
        """
        Test if you want to be sent.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_error('/stacks?', 'GET', exc.Unauthorized("FAIL"))

        args = ['stack-list']
        self.assertRaises(SystemExit, heatclient.shell.main, args)

    def test_help_on_subcommand(self):
        """
        Test for subcommand

        Args:
            self: (todo): write your description
        """
        required = [
            '^usage: heat stack-list',
            "(?m)^List the user's stacks",
        ]
        argstrings = [
            'help stack-list',
        ]
        for argstr in argstrings:
            help_text = self.shell(argstr)
            for r in required:
                self.assertRegex(help_text, r)


class ShellTestUserPass(ShellBase):

    def setUp(self):
        """
        Sets the client.

        Args:
            self: (todo): write your description
        """
        super(ShellTestUserPass, self).setUp()
        if self.client is None:
            self.client = http.SessionClient
        self._set_fake_env()

    def _set_fake_env(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_stack_list(self):
        """
        Register stack stack stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_stack_list()

        list_text = self.shell('stack-list')

        required = [
            'id',
            'stack_status',
            'creation_time',
            'teststack',
            '1',
            'CREATE_COMPLETE',
            'IN_PROGRESS',
        ]
        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'parent')

    def test_stack_list_show_nested(self):
        """
        Show list of stack stack stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        expected_url = '/stacks?%s' % parse.urlencode({
            'show_nested': True,
        }, True)
        self.mock_stack_list(expected_url, show_nested=True)

        list_text = self.shell('stack-list'
                               ' --show-nested')

        required = [
            'teststack',
            'teststack2',
            'teststack_nested',
            'parent',
            'theparentof3'
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_stack_list_show_owner(self):
        """
        List the list of - test stack names.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_stack_list()

        list_text = self.shell('stack-list --show-owner')

        required = [
            'stack_owner',
            'testowner',
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_parsable_error(self):
        """
        Register the authentication error.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        message = "The Stack (bad) could not be found."

        self.mock_request_error('/stacks/bad', 'GET',
                                exc.HTTPBadRequest(message))

        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertEqual("ERROR: " + message, str(e))

    def test_parsable_verbose(self):
        """
        This function will be called with the authentication

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        message = "The Stack (bad) could not be found."
        self.mock_request_error('/stacks/bad', 'GET',
                                exc.HTTPBadRequest(message))

        exc.verbose = 1

        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertIn(message, str(e))

    def test_parsable_malformed_error(self):
        """
        Test for authentication

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        invalid_json = "ERROR: {Invalid JSON Error."
        self.mock_request_error('/stacks/bad', 'GET',
                                exc.HTTPBadRequest(invalid_json))
        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertEqual("ERROR: " + invalid_json, str(e))

    def test_parsable_malformed_error_missing_message(self):
        """
        Determine if the error message.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        message = 'Internal Error'

        self.mock_request_error('/stacks/bad', 'GET',
                                exc.HTTPBadRequest(message))

        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertEqual("ERROR: Internal Error", str(e))

    def test_parsable_malformed_error_missing_traceback(self):
        """
        Determine if the request to be sent.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        message = "The Stack (bad) could not be found."
        self.mock_request_error('/stacks/bad', 'GET',
                                exc.HTTPBadRequest(message))

        exc.verbose = 1

        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertEqual("ERROR: The Stack (bad) could not be found.\n",
                         str(e))

    def test_stack_show(self):
        """
        Show stack stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z",
            "tags": [u'tag1', u'tag2']
        }}
        self.mock_request_get('/stacks/teststack/1', resp_dict)

        list_text = self.shell('stack-show teststack/1')

        required = [
            'id',
            'stack_name',
            'stack_status',
            'creation_time',
            'tags',
            'teststack',
            'CREATE_COMPLETE',
            '2012-10-25T01:58:47Z',
            "['tag1', 'tag2']",
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_stack_show_without_outputs(self):
        """
        Show stack stack stack stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        params = {'resolve_outputs': False}
        self.mock_request_get('/stacks/teststack/1', resp_dict, params=params)

        list_text = self.shell(
            'stack-show teststack/1 --no-resolve-outputs')

        required = [
            'id',
            'stack_name',
            'stack_status',
            'creation_time',
            'teststack',
            'CREATE_COMPLETE',
            '2012-10-25T01:58:47Z'
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def _output_fake_response(self, output_key):
        """
        Generate the output_key

        Args:
            self: (todo): write your description
            output_key: (str): write your description
        """

        outputs = [
            {
                "output_value": "value1",
                "output_key": "output1",
                "description": "test output 1",
            },
            {
                "output_value": ["output", "value", "2"],
                "output_key": "output2",
                "description": "test output 2",
            },
            {
                "output_value": u"test\u2665",
                "output_key": "output_uni",
                "description": "test output unicode",
            },
        ]

        def find_output(key):
            """
            Find the output of a key.

            Args:
                key: (str): write your description
            """
            for out in outputs:
                if out['output_key'] == key:
                    return {'output': out}

        self.mock_request_get('/stacks/teststack/1/outputs/%s' % output_key,
                              find_output(output_key))

    def _error_output_fake_response(self, output_key):
        """
        : param output_key : : return :

        Args:
            self: (todo): write your description
            output_key: (str): write your description
        """

        resp_dict = {
            "output": {
                "output_value": "null",
                "output_key": "output1",
                "description": "test output 1",
                "output_error": "The Referenced Attribute (0 PublicIP) "
                                "is incorrect."
            }
        }

        self.mock_request_get('/stacks/teststack/1/outputs/%s' % output_key,
                              resp_dict)

    def test_template_show_cfn(self):
        """
        Show the cfn template

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_data = open(os.path.join(TEST_VAR_DIR,
                                          'minimal.template')).read()
        resp_dict = jsonutils.loads(template_data)
        self.mock_request_get('/stacks/teststack/template', resp_dict)

        show_text = self.shell('template-show teststack')
        required = [
            '{',
            '  "AWSTemplateFormatVersion": "2010-09-09"',
            '  "Outputs": {}',
            '  "Resources": {}',
            '  "Parameters": {}',
            '}'
        ]
        for r in required:
            self.assertRegex(show_text, r)

    def test_template_show_cfn_unicode(self):
        """
        Register cfn cfn cfn template

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"AWSTemplateFormatVersion": "2010-09-09",
                     "Description": u"test\u2665",
                     "Outputs": {},
                     "Resources": {},
                     "Parameters": {}}

        self.mock_request_get('/stacks/teststack/template', resp_dict)

        show_text = self.shell('template-show teststack')
        required = [
            '{',
            '  "AWSTemplateFormatVersion": "2010-09-09"',
            '  "Outputs": {}',
            '  "Parameters": {}',
            u'  "Description": "test\u2665"',
            '  "Resources": {}',
            '}'
        ]
        for r in required:
            self.assertRegex(show_text, r)

    def test_template_show_hot(self):
        """
        Show the hot_request

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"heat_template_version": "2013-05-23",
                     "parameters": {},
                     "resources": {},
                     "outputs": {}}
        self.mock_request_get('/stacks/teststack/template', resp_dict)

        show_text = self.shell('template-show teststack')
        required = [
            "heat_template_version: '2013-05-23'",
            "outputs: {}",
            "parameters: {}",
            "resources: {}"
        ]
        for r in required:
            self.assertRegex(show_text, r)

    def test_template_validate(self):
        """
        Test if the authentication

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"heat_template_version": "2013-05-23",
                     "parameters": {},
                     "resources": {},
                     "outputs": {}}
        self.mock_request_post('/validate', resp_dict, data=mock.ANY)

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        cmd = 'template-validate -f %s -P foo=bar' % template_file
        show_text = self.shell(cmd)
        required = [
            'heat_template_version',
            'outputs',
            'parameters',
            'resources'
        ]
        for r in required:
            self.assertRegex(show_text, r)

    def _test_stack_preview(self, timeout=None, enable_rollback=False,
                            tags=None):
        """
        Generate help

        Args:
            self: (todo): write your description
            timeout: (float): write your description
            enable_rollback: (bool): write your description
            tags: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "resources": {'1': {'name': 'r1'}},
            "creation_time": "2012-10-25T01:58:47Z",
            "timeout_mins": timeout,
            "disable_rollback": not(enable_rollback),
            "tags": tags
        }}
        self.mock_request_post('/stacks/preview', resp_dict,
                               data=mock.ANY, req_headers=True)

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        cmd = ('stack-preview teststack '
               '--template-file=%s '
               '--parameters="InstanceType=m1.large;DBUsername=wp;'
               'DBPassword=verybadpassword;KeyName=heat_key;'
               'LinuxDistribution=F17" ' % template_file)
        if enable_rollback:
            cmd += '-r '
        if timeout:
            cmd += '--timeout=%d ' % timeout
        if tags:
            cmd += '--tags=%s ' % tags
        preview_text = self.shell(cmd)

        required = [
            'stack_name',
            'id',
            'teststack',
            '1',
            'resources',
            'timeout_mins',
            'disable_rollback',
            'tags'
        ]

        for r in required:
            self.assertRegex(preview_text, r)

    def test_stack_preview(self):
        """
        Test if the current preview.

        Args:
            self: (todo): write your description
        """
        self._test_stack_preview()

    def test_stack_preview_timeout(self):
        """
        Test if the current preview_preview_timeout

        Args:
            self: (todo): write your description
        """
        self._test_stack_preview(300, True)

    def test_stack_preview_tags(self):
        """
        Test for preview tags.

        Args:
            self: (todo): write your description
        """
        self._test_stack_preview(tags='tag1,tag2')

    def test_stack_create(self):
        """
        Create stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_post('/stacks', None, data=mock.ANY,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        create_text = self.shell(
            'stack-create teststack '
            '--template-file=%s '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]

        for r in required:
            self.assertRegex(create_text, r)

    def test_create_success_with_poll(self):
        """
        Create a failure of stack responses

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        stack_create_resp_dict = {"stack": {
            "id": "teststack2/2",
            "stack_name": "teststack2",
            "stack_status": 'CREATE_IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        self.mock_request_post('/stacks', stack_create_resp_dict,
                               data=mock.ANY, req_headers=True,
                               status_code=201)
        self.mock_stack_list()

        stack_show_resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        event_list_resp_dict = self.event_list_resp_dict(
            stack_name="teststack2")
        stack_id = 'teststack2'

        self.mock_request_get('/stacks/teststack2', stack_show_resp_dict)
        self.mock_request_get('/stacks/%s/events?sort_dir=asc' % stack_id,
                              event_list_resp_dict)
        self.mock_request_get('/stacks/teststack2', stack_show_resp_dict)

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        create_text = self.shell(
            'stack-create teststack2 '
            '--poll 4 '
            '--template-file=%s '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'id',
            'stack_name',
            'stack_status',
            '2',
            'teststack2',
            'IN_PROGRESS',
            '14:14:30', '2013-12-05',
            'CREATE_IN_PROGRESS', 'state changed',
            '14:14:31',
            'testresource',
            '14:14:32',
            'CREATE_COMPLETE',
            '14:14:33',
        ]

        for r in required:
            self.assertRegex(create_text, r)

    def test_create_failed_with_poll(self):
        """
        Create failed failed failure.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_create_resp_dict = {"stack": {
            "id": "teststack2/2",
            "stack_name": "teststack2",
            "stack_status": 'CREATE_IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        self.mock_request_post('/stacks', stack_create_resp_dict,
                               data=mock.ANY, req_headers=True,
                               status_code=201)
        self.mock_stack_list()

        stack_show_resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        event_list_resp_dict = self.event_list_resp_dict(
            stack_name="teststack2", final_state="FAILED")
        stack_id = 'teststack2'

        self.mock_request_get('/stacks/teststack2', stack_show_resp_dict)
        self.mock_request_get('/stacks/%s/events?sort_dir=asc' % stack_id,
                              event_list_resp_dict)
        self.mock_request_get('/stacks/teststack2', stack_show_resp_dict)

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')

        e = self.assertRaises(exc.StackFailure, self.shell,
                              'stack-create teststack2 --poll '
                              '--template-file=%s --parameters="InstanceType='
                              'm1.large;DBUsername=wp;DBPassword=password;'
                              'KeyName=heat_key;LinuxDistribution=F17' %
                              template_file)
        self.assertEqual("\n Stack teststack2 CREATE_FAILED \n",
                         str(e))

    def test_stack_create_param_file(self):
        """
        Create stack stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_post('/stacks', None, data=mock.ANY,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        self.useFixture(fixtures.MockPatchObject(utils, 'read_url_content',
                                                 return_value='xxxxxx'))
        url = 'file://%s/private_key.env' % TEST_VAR_DIR

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        create_text = self.shell(
            'stack-create teststack '
            '--template-file=%s '
            '--parameter-file private_key=private_key.env '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]

        for r in required:
            self.assertRegex(create_text, r)
        utils.read_url_content.assert_called_once_with(url)

    def test_stack_create_only_param_file(self):
        """
        Create stack stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_post('/stacks', None, data=mock.ANY,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        self.useFixture(fixtures.MockPatchObject(utils, 'read_url_content',
                                                 return_value='xxxxxx'))
        url = 'file://%s/private_key.env' % TEST_VAR_DIR

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        create_text = self.shell(
            'stack-create teststack '
            '--template-file=%s '
            '--parameter-file private_key=private_key.env '
            % template_file)

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]

        for r in required:
            self.assertRegex(create_text, r)
        utils.read_url_content.assert_called_once_with(url)

    def test_stack_create_timeout(self):
        """
        Create a stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        expected_data = {
            'files': {},
            'disable_rollback': True,
            'parameters': {'DBUsername': 'wp',
                           'KeyName': 'heat_key',
                           'LinuxDistribution': 'F17"',
                           '"InstanceType': 'm1.large',
                           'DBPassword': 'verybadpassword'},
            'stack_name': 'teststack',
            'environment': {},
            'template': jsonutils.loads(template_data),
            'timeout_mins': 123}
        self.mock_request_post('/stacks', None, data=expected_data,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        create_text = self.shell(
            'stack-create teststack '
            '--template-file=%s '
            '--timeout=123 '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]

        for r in required:
            self.assertRegex(create_text, r)

    def test_stack_update_timeout(self):
        """
        Update stack stack stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()

        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'DBUsername': 'wp',
                           'KeyName': 'heat_key',
                           'LinuxDistribution': 'F17"',
                           '"InstanceType': 'm1.large',
                           'DBPassword': 'verybadpassword'},
            'timeout_mins': 123,
            'disable_rollback': True}
        self.mock_request_put(
            '/stacks/teststack2/2',
            'The request is accepted for processing.',
            data=expected_data)
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--timeout 123 '
            '--rollback off '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_create_url(self):
        """
        Create stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        url_content = six.StringIO(
            '{"AWSTemplateFormatVersion" : "2010-09-09"}')
        self.useFixture(fixtures.MockPatchObject(request, 'urlopen',
                                                 return_value=url_content))

        expected_data = {
            'files': {},
            'disable_rollback': True,
            'stack_name': 'teststack',
            'environment': {},
            'template': {"AWSTemplateFormatVersion": "2010-09-09"},
            'parameters': {'DBUsername': 'wp',
                           'KeyName': 'heat_key',
                           'LinuxDistribution': 'F17"',
                           '"InstanceType': 'm1.large',
                           'DBPassword': 'verybadpassword'}}

        self.mock_request_post('/stacks', None, data=expected_data,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        create_text = self.shell(
            'stack-create teststack '
            '--template-url=http://no.where/minimal.template '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '2'
        ]
        for r in required:
            self.assertRegex(create_text, r)
        request.urlopen.assert_called_once_with(
            'http://no.where/minimal.template')

    def test_stack_create_object(self):
        """
        Create a stack object

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()

        self.mock_request_get(
            'http://no.where/container/minimal.template',
            template_data,
            raw=True)

        self.mock_request_post('/stacks', None, data=mock.ANY,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        create_text = self.shell(
            'stack-create teststack2 '
            '--template-object=http://no.where/container/minimal.template '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '2'
        ]
        for r in required:
            self.assertRegex(create_text, r)

    def test_stack_create_with_tags(self):
        """
        Create stack tags

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        expected_data = {
            'files': {},
            'disable_rollback': True,
            'parameters': {'DBUsername': 'wp',
                           'KeyName': 'heat_key',
                           'LinuxDistribution': 'F17"',
                           '"InstanceType': 'm1.large',
                           'DBPassword': 'verybadpassword'},
            'stack_name': 'teststack',
            'environment': {},
            'template': jsonutils.loads(template_data),
            'tags': 'tag1,tag2'}
        self.mock_request_post('/stacks', None, data=expected_data,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        create_text = self.shell(
            'stack-create teststack '
            '--template-file=%s '
            '--tags=tag1,tag2 '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]

        for r in required:
            self.assertRegex(create_text, r)

    def test_stack_abandon(self):
        """
        Test stack stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        abandoned_stack = {
            "action": "CREATE",
            "status": "COMPLETE",
            "name": "teststack",
            "id": "1",
            "resources": {
                "foo": {
                    "name": "foo",
                    "resource_id": "test-res-id",
                    "action": "CREATE",
                    "status": "COMPLETE",
                    "resource_data": {},
                    "metadata": {},
                }
            }
        }

        self.mock_request_delete('/stacks/teststack/1/abandon',
                                 abandoned_stack)

        abandon_resp = self.shell('stack-abandon teststack/1')
        self.assertEqual(abandoned_stack, jsonutils.loads(abandon_resp))

    def test_stack_abandon_with_outputfile(self):
        """
        : return :

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        abandoned_stack = {
            "action": "CREATE",
            "status": "COMPLETE",
            "name": "teststack",
            "id": "1",
            "resources": {
                "foo": {
                    "name": "foo",
                    "resource_id": "test-res-id",
                    "action": "CREATE",
                    "status": "COMPLETE",
                    "resource_data": {},
                    "metadata": {},
                }
            }
        }

        self.mock_request_delete('/stacks/teststack/1/abandon',
                                 abandoned_stack)

        with tempfile.NamedTemporaryFile() as file_obj:
            self.shell('stack-abandon teststack/1 -O %s' % file_obj.name)
            result = jsonutils.loads(file_obj.read().decode())
            self.assertEqual(abandoned_stack, result)

    def test_stack_adopt(self):
        """
        Register stack stack stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_post('/stacks', None, data=mock.ANY,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        adopt_data_file = os.path.join(TEST_VAR_DIR, 'adopt_stack_data.json')
        adopt_text = self.shell(
            'stack-adopt teststack '
            '--adopt-file=%s '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % (adopt_data_file))

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]

        for r in required:
            self.assertRegex(adopt_text, r)

    def test_stack_adopt_with_environment(self):
        """
        Test stack stack stack stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_post('/stacks', None, data=mock.ANY,
                               status_code=201, req_headers=True)
        self.mock_stack_list()

        adopt_data_file = os.path.join(TEST_VAR_DIR, 'adopt_stack_data.json')
        environment_file = os.path.join(TEST_VAR_DIR, 'environment.json')
        self.shell(
            'stack-adopt teststack '
            '--adopt-file=%s '
            '--environment-file=%s' % (adopt_data_file, environment_file))

    def test_stack_adopt_without_data(self):
        """
        Register the stack stack stack needs to use.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        failed_msg = 'Need to specify --adopt-file'
        self.shell_error('stack-adopt teststack ', failed_msg,
                         exception=exc.CommandError)

    def test_stack_adopt_empty_data_file(self):
        """
        Returns the stack stack stack to be written to the stack

        Args:
            self: (todo): write your description
        """
        failed_msg = 'Invalid adopt-file, no data!'
        self.register_keystone_auth_fixture()
        with tempfile.NamedTemporaryFile() as file_obj:
            self.shell_error(
                'stack-adopt teststack '
                '--adopt-file=%s ' % (file_obj.name),
                failed_msg, exception=exc.CommandError)

    def test_stack_update_enable_rollback(self):
        """
        Update the stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        with open(template_file, 'rb') as f:
            template_data = jsonutils.load(f)
        expected_data = {'files': {},
                         'environment': {},
                         'template': template_data,
                         'disable_rollback': False,
                         'parameters': mock.ANY
                         }
        self.mock_request_put(
            '/stacks/teststack2/2',
            'The request is accepted for processing.',
            data=expected_data)
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2/2 '
            '--rollback on '
            '--template-file=%s '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_update_disable_rollback(self):
        """
        Update stack stack ::

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        with open(template_file, 'rb') as f:
            template_data = jsonutils.load(f)
        expected_data = {'files': {},
                         'environment': {},
                         'template': template_data,
                         'disable_rollback': True,
                         'parameters': mock.ANY
                         }
        self.mock_request_put(
            '/stacks/teststack2',
            'The request is accepted for processing.',
            data=expected_data)
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2 '
            '--template-file=%s '
            '--rollback off '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_update_fault_rollback_value(self):
        """
        Update the stack traceback

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        self.shell_error('stack-update teststack2/2 '
                         '--rollback Foo '
                         '--template-file=%s' % template_file,
                         "Unrecognized value 'Foo', acceptable values are:",
                         exception=exc.CommandError
                         )

    def test_stack_update_rollback_default(self):
        """
        Update the stack stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        with open(template_file, 'rb') as f:
            template_data = jsonutils.load(f)
        expected_data = {'files': {},
                         'environment': {},
                         'template': template_data,
                         'parameters': mock.ANY
                         }
        self.mock_request_put(
            '/stacks/teststack2',
            'The request is accepted for processing.',
            data=expected_data)
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2 '
            '--template-file=%s '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '2'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_update_with_existing_parameters(self):
        """
        Update existing stack stack with configuration

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {},
            'disable_rollback': False}
        self.mock_request_patch(
            '/stacks/teststack2/2',
            'The request is accepted for processing.',
            data=expected_data
        )
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--enable-rollback '
            '--existing' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_update_with_patched_existing_parameters(self):
        """
        Update stack stack stack ini configuration

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'"KeyPairName': 'updated_key"'},
            'disable_rollback': False}
        self.mock_request_patch(
            '/stacks/teststack2/2',
            'The request is accepted for processing.',
            data=expected_data
        )
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--enable-rollback '
            '--parameters="KeyPairName=updated_key" '
            '--existing' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_update_with_existing_and_default_parameters(self):
        """
        Generate stack stack stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {},
            'clear_parameters': ['InstanceType', 'DBUsername',
                                 'DBPassword', 'KeyPairName',
                                 'LinuxDistribution'],
            'disable_rollback': False}
        self.mock_request_patch(
            '/stacks/teststack2/2',
            'The request is accepted for processing.',
            data=expected_data
        )
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--enable-rollback '
            '--existing '
            '--clear-parameter=InstanceType '
            '--clear-parameter=DBUsername '
            '--clear-parameter=DBPassword '
            '--clear-parameter=KeyPairName '
            '--clear-parameter=LinuxDistribution' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_update_with_patched_and_default_parameters(self):
        """
        Generate stack stack stack_keystone

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'"KeyPairName': 'updated_key"'},
            'clear_parameters': ['InstanceType', 'DBUsername',
                                 'DBPassword', 'KeyPairName',
                                 'LinuxDistribution'],
            'disable_rollback': False}
        self.mock_request_patch(
            '/stacks/teststack2/2',
            'The request is accepted for processing.',
            data=expected_data
        )
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--enable-rollback '
            '--existing '
            '--parameters="KeyPairName=updated_key" '
            '--clear-parameter=InstanceType '
            '--clear-parameter=DBUsername '
            '--clear-parameter=DBPassword '
            '--clear-parameter=KeyPairName '
            '--clear-parameter=LinuxDistribution' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_update_with_existing_template(self):
        """
        Update stack stack stack stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        expected_data = {
            'files': {},
            'environment': {},
            'template': None,
            'parameters': {}}
        self.mock_request_patch(
            '/stacks/teststack2/2',
            'The request is accepted for processing.',
            data=expected_data
        )
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2/2 '
            '--existing')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_update_with_tags(self):
        """
        Update stack stack tags

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'"KeyPairName': 'updated_key"'},
            'disable_rollback': False,
            'tags': 'tag1,tag2'}
        self.mock_request_patch(
            '/stacks/teststack2/2',
            'The request is accepted for processing.',
            data=expected_data
        )
        self.mock_stack_list()

        update_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--enable-rollback '
            '--existing '
            '--parameters="KeyPairName=updated_key" '
            '--tags=tag1,tag2 ' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def _setup_stubs_update_dry_run(self, template_file, existing=False,
                                    show_nested=False):
        """
        Setup stubs template.

        Args:
            self: (todo): write your description
            template_file: (str): write your description
            existing: (dict): write your description
            show_nested: (bool): write your description
        """
        self.register_keystone_auth_fixture()

        template_data = open(template_file).read()

        replaced_res = {"resource_name": "my_res",
                        "resource_identity": {"stack_name": "teststack2",
                                              "stack_id": "2",
                                              "tenant": "1234",
                                              "path": "/resources/my_res"},
                        "description": "",
                        "stack_identity": {"stack_name": "teststack2",
                                           "stack_id": "2",
                                           "tenant": "1234",
                                           "path": ""},
                        "stack_name": "teststack2",
                        "creation_time": "2015-08-19T19:43:34.025507",
                        "resource_status": "COMPLETE",
                        "updated_time": "2015-08-19T19:43:34.025507",
                        "resource_type": "OS::Heat::RandomString",
                        "required_by": [],
                        "resource_status_reason": "",
                        "physical_resource_id": "",
                        "attributes": {"value": None},
                        "resource_action": "INIT",
                        "metadata": {}}
        resp_dict = {"resource_changes": {"deleted": [],
                                          "unchanged": [],
                                          "added": [],
                                          "replaced": [replaced_res],
                                          "updated": []}}
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'"KeyPairName': 'updated_key"'},
            'disable_rollback': False}

        if show_nested:
            path = '/stacks/teststack2/2/preview?show_nested=True'
        else:
            path = '/stacks/teststack2/2/preview'

        if existing:
            self.mock_request_patch(path, resp_dict, data=expected_data)
        else:
            self.mock_request_put(path, resp_dict, data=expected_data)

    def test_stack_update_dry_run(self):
        """
        Update the app_file

        Args:
            self: (todo): write your description
        """
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        self._setup_stubs_update_dry_run(template_file)
        update_preview_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--enable-rollback '
            '--parameters="KeyPairName=updated_key" '
            '--dry-run ' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '2',
            'state',
            'replaced'
        ]
        for r in required:
            self.assertRegex(update_preview_text, r)

    def test_stack_update_dry_run_show_nested(self):
        """
        Update the app_update_run.

        Args:
            self: (todo): write your description
        """
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        self._setup_stubs_update_dry_run(template_file, show_nested=True)
        update_preview_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--enable-rollback '
            '--show-nested '
            '--parameters="KeyPairName=updated_key" '
            '--dry-run ' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '2',
            'state',
            'replaced'
        ]
        for r in required:
            self.assertRegex(update_preview_text, r)

    def test_stack_update_dry_run_patch(self):
        """
        Generate cfgubs.

        Args:
            self: (todo): write your description
        """
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        self._setup_stubs_update_dry_run(template_file, existing=True)
        update_preview_text = self.shell(
            'stack-update teststack2/2 '
            '--template-file=%s '
            '--enable-rollback '
            '--existing '
            '--parameters="KeyPairName=updated_key" '
            '--dry-run ' % template_file)

        required = [
            'stack_name',
            'id',
            'teststack2',
            '2',
            'state',
            'replaced'
        ]
        for r in required:
            self.assertRegex(update_preview_text, r)

    # the main thing this @mock.patch is doing here is keeping
    # sys.stdin untouched for later tests
    @mock.patch('sys.stdin', new_callable=six.StringIO)
    def test_stack_delete_prompt_with_tty(self, ms):
        """
        Delete stack stack.

        Args:
            self: (todo): write your description
            ms: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        mock_stdin = mock.Mock()
        mock_stdin.isatty = mock.Mock()
        mock_stdin.isatty.return_value = True
        mock_stdin.readline = mock.Mock()
        mock_stdin.readline.return_value = 'n'
        mock_stdin.fileno.return_value = 0
        sys.stdin = mock_stdin

        self.mock_request_delete('/stacks/teststack2/2', None)

        resp = self.shell('stack-delete teststack2/2')
        resp_text = 'Are you sure you want to delete this stack(s) [y/N]? '
        self.assertEqual(resp_text, resp)

        mock_stdin.readline.return_value = 'y'
        resp = self.shell('stack-delete teststack2/2')
        msg = 'Request to delete stack teststack2/2 has been accepted.'
        self.assertRegex(resp, msg)

    # the main thing this @mock.patch is doing here is keeping
    # sys.stdin untouched for later tests
    @mock.patch('sys.stdin', new_callable=six.StringIO)
    def test_stack_delete_prompt_with_tty_y(self, ms):
        """
        Delete stack stack stack.

        Args:
            self: (todo): write your description
            ms: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        mock_stdin = mock.Mock()
        mock_stdin.isatty = mock.Mock()
        mock_stdin.isatty.return_value = True
        mock_stdin.readline = mock.Mock()
        mock_stdin.readline.return_value = ''
        mock_stdin.fileno.return_value = 0
        sys.stdin = mock_stdin

        self.mock_request_delete('/stacks/teststack2/2')

        # -y from the shell should skip the n/y prompt
        resp = self.shell('stack-delete -y teststack2/2')
        msg = 'Request to delete stack teststack2/2 has been accepted.'
        self.assertRegex(resp, msg)

    def test_stack_delete(self):
        """
        Delete the stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_delete('/stacks/teststack2/2')

        resp = self.shell('stack-delete teststack2/2')
        msg = 'Request to delete stack teststack2/2 has been accepted.'
        self.assertRegex(resp, msg)

    def test_stack_delete_multiple(self):
        """
        Deletes stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_delete('/stacks/teststack/1')
        self.mock_request_delete('/stacks/teststack2/2')

        resp = self.shell('stack-delete teststack/1 teststack2/2')
        msg1 = 'Request to delete stack teststack/1 has been accepted.'
        msg2 = 'Request to delete stack teststack2/2 has been accepted.'
        self.assertRegex(resp, msg1)
        self.assertRegex(resp, msg2)

    def test_stack_delete_failed_on_notfound(self):
        """
        Delete stack stack on stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_error('/stacks/teststack1/1', 'DELETE',
                                exc.HTTPNotFound())
        error = self.assertRaises(
            exc.CommandError, self.shell, 'stack-delete teststack1/1')
        self.assertIn('Unable to delete 1 of the 1 stacks.',
                      str(error))

    def test_stack_delete_failed_on_forbidden(self):
        """
        Delete stack stack stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_error('/stacks/teststack1/1', 'DELETE',
                                exc.Forbidden())
        error = self.assertRaises(
            exc.CommandError, self.shell, 'stack-delete teststack1/1')
        self.assertIn('Unable to delete 1 of the 1 stacks.',
                      str(error))

    def test_build_info(self):
        """
        Register build information.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {
            'build_info': {
                'api': {'revision': 'api_revision'},
                'engine': {'revision': 'engine_revision'}
            }
        }
        self.mock_request_get('/build_info', resp_dict)

        build_info_text = self.shell('build-info')

        required = [
            'api',
            'engine',
            'revision',
            'api_revision',
            'engine_revision',
        ]
        for r in required:
            self.assertRegex(build_info_text, r)

    def test_stack_snapshot(self):
        """
        Register snapshot snapshot snapshot of the snapshot

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {"snapshot": {
            "id": "1",
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        self.mock_request_post('/stacks/teststack/1/snapshots',
                               resp_dict, data={})

        resp = self.shell('stack-snapshot teststack/1')
        self.assertEqual(resp_dict, jsonutils.loads(resp))

    def test_snapshot_list(self):
        """
        Register snapshot of snapshot.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {"snapshots": [{
            "id": "2",
            "name": "snap1",
            "status": "COMPLETE",
            "status_reason": "",
            "creation_time": "2014-12-05T01:25:52Z"
        }]}

        self.mock_request_get('/stacks/teststack/1/snapshots', resp_dict)

        list_text = self.shell('snapshot-list teststack/1')

        required = [
            'id',
            'name',
            'status',
            'status_reason',
            'creation_time',
            '2',
            'COMPLETE',
            '2014-12-05T01:25:52Z',
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_snapshot_show(self):
        """
        Show snapshot details.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {"snapshot": {
            "id": "2",
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        self.mock_request_get('/stacks/teststack/1/snapshots/2', resp_dict)

        resp = self.shell('snapshot-show teststack/1 2')
        self.assertEqual(resp_dict, jsonutils.loads(resp))

    # the main thing this @mock.patch is doing here is keeping
    # sys.stdin untouched for later tests
    @mock.patch('sys.stdin', new_callable=six.StringIO)
    def test_snapshot_delete_prompt_with_tty(self, ms):
        """
        Delete snapshot snapshot ::

        Args:
            self: (todo): write your description
            ms: (str): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"snapshot": {
            "id": "2",
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        mock_stdin = mock.Mock()
        mock_stdin.isatty = mock.Mock()
        mock_stdin.isatty.return_value = True
        mock_stdin.readline = mock.Mock()
        mock_stdin.readline.return_value = 'n'
        sys.stdin = mock_stdin

        self.mock_request_delete('/stacks/teststack/1/snapshots/2', resp_dict)

        resp = self.shell('snapshot-delete teststack/1 2')
        resp_text = ('Are you sure you want to delete the snapshot of '
                     'this stack [Y/N]?')
        self.assertEqual(resp_text, resp)

        mock_stdin.readline.return_value = 'Y'
        resp = self.shell('snapshot-delete teststack/1 2')
        msg = _("Request to delete the snapshot 2 of the stack "
                "teststack/1 has been accepted.")
        self.assertRegex(resp, msg)

    # the main thing this @mock.patch is doing here is keeping
    # sys.stdin untouched for later tests
    @mock.patch('sys.stdin', new_callable=six.StringIO)
    def test_snapshot_delete_prompt_with_tty_y(self, ms):
        """
        Delete snapshot snapshot

        Args:
            self: (todo): write your description
            ms: (str): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"snapshot": {
            "id": "2",
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        mock_stdin = mock.Mock()
        mock_stdin.isatty = mock.Mock()
        mock_stdin.isatty.return_value = True
        mock_stdin.readline = mock.Mock()
        mock_stdin.readline.return_value = ''
        sys.stdin = mock_stdin

        self.mock_request_delete('/stacks/teststack/1/snapshots/2', resp_dict)

        # -y from the shell should skip the n/y prompt
        resp = self.shell('snapshot-delete -y teststack/1 2')
        msg = _("Request to delete the snapshot 2 of the stack "
                "teststack/1 has been accepted.")
        self.assertRegex(resp, msg)

    def test_snapshot_delete(self):
        """
        Delete snapshot snapshot.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {"snapshot": {
            "id": "2",
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        self.mock_request_delete('/stacks/teststack/1/snapshots/2', resp_dict)

        resp = self.shell('snapshot-delete teststack/1 2')
        msg = _("Request to delete the snapshot 2 of the stack "
                "teststack/1 has been accepted.")
        self.assertRegex(resp, msg)

    def test_stack_restore(self):
        """
        Restore stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        self.mock_request_post('/stacks/teststack/1/snapshots/2/restore',
                               None, status_code=204)

        resp = self.shell('stack-restore teststack/1 2')
        self.assertEqual("", resp)

    def test_output_list(self):
        """
        Register the list of the output devices

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {"outputs": [{
            "output_key": "key",
            "description": "description"
        }, {
            "output_key": "key1",
            "description": "description1"
        }]}

        self.mock_request_get('/stacks/teststack/1/outputs', resp_dict)

        list_text = self.shell('output-list teststack/1')

        required = [
            'output_key',
            'description',
            'key',
            'description',
            'key1',
            'description1'
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_output_list_api_400_error(self):
        """
        Test for bad test output to make_keystone.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        outputs = [{
            "output_key": "key",
            "description": "description"
        },
            {
                "output_key": "key1",
                "description": "description1"
            }]
        stack_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z",
            "outputs": outputs
        }}

        self.mock_request_error('/stacks/teststack/1/outputs', 'GET',
                                exc.HTTPNotFound())
        self.mock_request_get('/stacks/teststack/1', stack_dict)

        list_text = self.shell('output-list teststack/1')

        required = [
            'output_key',
            'description',
            'key',
            'description',
            'key1',
            'description1'
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_output_show_all(self):
        """
        Register the ::

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {'outputs': [
            {
                'output_key': 'key',
                'description': 'description'
            }
        ]}

        resp_dict1 = {"output": {
            "output_key": "key",
            "output_value": "value",
            'description': 'description'
        }}

        self.mock_request_get('/stacks/teststack/1/outputs', resp_dict)
        self.mock_request_get('/stacks/teststack/1/outputs/key', resp_dict1)

        list_text = self.shell('output-show --with-detail teststack/1 --all')
        required = [
            'output_key',
            'output_value',
            'description',
            'key',
            'value',
            'description',
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_output_show(self):
        """
        .. version of the app

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {"output": {
            "output_key": "key",
            "output_value": "value",
            'description': 'description'
        }}
        self.mock_request_get('/stacks/teststack/1/outputs/key', resp_dict)

        resp = self.shell('output-show --with-detail teststack/1 key')
        required = [
            'output_key',
            'output_value',
            'description',
            'key',
            'value',
            'description',
        ]
        for r in required:
            self.assertRegex(resp, r)

    def test_output_show_api_400_error(self):
        """
        Test for api keystone test.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        output = {
            "output_key": "key",
            "output_value": "value",
            'description': 'description'
        }
        stack_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z",
            'outputs': [output]
        }}

        self.mock_request_error('/stacks/teststack/1/outputs/key', 'GET',
                                exc.HTTPNotFound())
        self.mock_request_get('/stacks/teststack/1', stack_dict)

        resp = self.shell('output-show --with-detail teststack/1 key')
        required = [
            'output_key',
            'output_value',
            'description',
            'key',
            'value',
            'description',
        ]
        for r in required:
            self.assertRegex(resp, r)

    def test_output_show_output1_with_detail(self):
        """
        Show the ::

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        self._output_fake_response('output1')
        list_text = self.shell('output-show teststack/1 output1 --with-detail')
        required = [
            'output_key',
            'output_value',
            'description',
            'output1',
            'value1',
            'test output 1',
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_output_show_output1(self):
        """
        Manage the app output.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        self._output_fake_response('output1')
        list_text = self.shell('output-show -F raw teststack/1 output1')
        self.assertEqual('value1\n', list_text)

    def test_output_show_output2_raw(self):
        """
        Show test test test test test.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        self._output_fake_response('output2')
        list_text = self.shell('output-show -F raw teststack/1 output2')
        self.assertEqual('[\n  "output", \n  "value", \n  "2"\n]\n',
                         list_text)

    def test_output_show_output2_raw_with_detail(self):
        """
        Show the raw test headers

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        self._output_fake_response('output2')
        list_text = self.shell('output-show -F raw --with-detail '
                               'teststack/1 output2')
        required = [
            'output_key',
            'output_value',
            'description',
            'output2',
            "[u'output', u'value', u'2']",
            'test output 2',
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_output_show_output2_json(self):
        """
        Show the json output of the app

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        self._output_fake_response('output2')
        list_text = self.shell('output-show -F json teststack/1 output2')
        required = [
            '{',
            '"output_key": "output2"',
            '"description": "test output 2"',
            r'"output_value": \[',
            '"output"',
            '"value"',
            '"2"',
            '}'
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_output_show_output2_json_with_detail(self):
        """
        Show the json output of the app

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        self._output_fake_response('output2')
        list_text = self.shell('output-show -F json --with-detail '
                               'teststack/1 output2')
        required = [
            'output_key',
            'output_value',
            'description',
            'output2',
            '[\n    "output", \n    "value", \n    "2"\n  ]'
            'test output 2',
        ]
        for r in required:
            self.assertRegex(list_text, r)

    def test_output_show_unicode_output(self):
        """
        Test if the test output.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        self._output_fake_response('output_uni')
        list_text = self.shell('output-show teststack/1 output_uni')
        self.assertEqual(u'test\u2665\n', list_text)

    def test_output_show_error(self):
        """
        Register the error to be sent.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self._error_output_fake_response('output1')
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'output-show teststack/1 output1')
        self.assertIn('The Referenced Attribute (0 PublicIP) is incorrect.',
                      six.text_type(error))


class ShellTestActions(ShellBase):

    def setUp(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        super(ShellTestActions, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_stack_cancel_update(self):
        """
        Register the stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        expected_data = {'cancel_update': None}
        self.mock_request_post(
            '/stacks/teststack2/actions',
            'The request is accepted for processing.',
            data=expected_data,
            status_code=202)
        self.mock_stack_list()

        update_text = self.shell('stack-cancel-update teststack2')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(update_text, r)

    def test_stack_check(self):
        """
        Register stack stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        expected_data = {'check': None}
        self.mock_request_post(
            '/stacks/teststack2/actions',
            'The request is accepted for processing.',
            data=expected_data,
            status_code=202)
        self.mock_stack_list()

        check_text = self.shell('action-check teststack2')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(check_text, r)

    def test_stack_suspend(self):
        """
        Register stack stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        expected_data = {'suspend': None}
        self.mock_request_post(
            '/stacks/teststack2/actions',
            'The request is accepted for processing.',
            data=expected_data,
            status_code=202)
        self.mock_stack_list()

        suspend_text = self.shell('action-suspend teststack2')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(suspend_text, r)

    def test_stack_resume(self):
        """
        Resume stack stack.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        expected_data = {'resume': None}
        self.mock_request_post(
            '/stacks/teststack2/actions',
            'The request is accepted for processing.',
            data=expected_data,
            status_code=202)
        self.mock_stack_list()

        resume_text = self.shell('action-resume teststack2')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegex(resume_text, r)


class ShellTestEvents(ShellBase):

    def setUp(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        super(ShellTestEvents, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    scenarios = [
        ('integer_id', dict(
            event_id_one='24',
            event_id_two='42')),
        ('uuid_id', dict(
            event_id_one='3d68809e-c4aa-4dc9-a008-933823d2e44f',
            event_id_two='43b68bae-ed5d-4aed-a99f-0b3d39c2418a'))]

    def test_event_list(self):
        """
        Test for event list.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = self.event_list_resp_dict(
            resource_name="aResource",
            rsrc_eventid1=self.event_id_one,
            rsrc_eventid2=self.event_id_two
        )
        stack_id = 'teststack/1'
        resource_name = 'testresource/1'
        self.mock_request_get(
            '/stacks/%s/resources/%s/events?sort_dir=asc' % (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name))),
            resp_dict)

        event_list_text = self.shell('event-list {0} --resource {1}'.format(
                                     stack_id, resource_name))

        required = [
            'resource_name',
            'id',
            'resource_status_reason',
            'resource_status',
            'event_time',
            'aResource',
            self.event_id_one,
            self.event_id_two,
            'state changed',
            'CREATE_IN_PROGRESS',
            'CREATE_COMPLETE',
            '2013-12-05T14:14:31',
            '2013-12-05T14:14:32',
        ]
        for r in required:
            self.assertRegex(event_list_text, r)

    def test_stack_event_list_log(self):
        """
        Register event log events

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = self.event_list_resp_dict(
            resource_name="aResource",
            rsrc_eventid1=self.event_id_one,
            rsrc_eventid2=self.event_id_two
        )

        stack_id = 'teststack/1'
        self.mock_request_get('/stacks/%s/events?sort_dir=asc' % stack_id,
                              resp_dict)

        event_list_text = self.shell('event-list {0} --format log'.format(
            stack_id))

        expected = ('2013-12-05 14:14:31 [aResource]: '
                    'CREATE_IN_PROGRESS  state changed\n'
                    '2013-12-05 14:14:32 [aResource]: CREATE_COMPLETE  '
                    'state changed\n')

        self.assertEqual(expected, event_list_text)

    def test_event_show(self):
        """
        Show the details

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"event":
                     {"event_time": "2013-12-05T14:14:30Z",
                      "id": self.event_id_one,
                      "links": [{"href": "http://heat.example.com:8004/foo",
                                 "rel": "self"},
                                {"href": "http://heat.example.com:8004/foo2",
                                 "rel": "resource"},
                                {"href": "http://heat.example.com:8004/foo3",
                                 "rel": "stack"}],
                      "logical_resource_id": "aResource",
                      "physical_resource_id": None,
                      "resource_name": "aResource",
                      "resource_properties": {"admin_user": "im_powerful",
                                              "availability_zone": "nova"},
                      "resource_status": "CREATE_IN_PROGRESS",
                      "resource_status_reason": "state changed",
                      "resource_type": "OS::Nova::Server"
                      }}
        stack_id = 'teststack/1'
        resource_name = 'testresource/1'
        self.mock_request_get(
            '/stacks/%s/resources/%s/events/%s' %
            (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name)),
                parse.quote(self.event_id_one)
            ),
            resp_dict)

        event_list_text = self.shell('event-show {0} {1} {2}'.format(
                                     stack_id, resource_name,
                                     self.event_id_one))

        required = [
            'Property',
            'Value',
            'event_time',
            '2013-12-05T14:14:30Z',
            'id',
            self.event_id_one,
            'links',
            'http://heat.example.com:8004/foo[0-9]',
            'logical_resource_id',
            'physical_resource_id',
            'resource_name',
            'aResource',
            'resource_properties',
            'admin_user',
            'availability_zone',
            'resource_status',
            'CREATE_IN_PROGRESS',
            'resource_status_reason',
            'state changed',
            'resource_type',
            'OS::Nova::Server',
        ]
        for r in required:
            self.assertRegex(event_list_text, r)


class ShellTestEventsNested(ShellBase):
    def setUp(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        super(ShellTestEventsNested, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_shell_nested_depth_invalid_xor(self):
        """
        Test if the shell shell doesn t ignored

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'

        error = self.assertRaises(
            exc.CommandError, self.shell,
            'event-list {0} --resource {1} --nested-depth 5'.format(
                stack_id, resource_name))
        self.assertIn('--nested-depth cannot be specified with --resource',
                      str(error))

    def test_shell_nested_depth_invalid_value(self):
        """
        Test if the resource isvalidator

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'event-list {0} --nested-depth Z'.format(
                stack_id, resource_name))
        self.assertIn('--nested-depth invalid value Z', str(error))

    def test_shell_nested_depth_zero(self):
        """
        Test for zero zero zero zero zero zero.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"events": [{"id": 'eventid1'},
                                {"id": 'eventid2'}]}
        stack_id = 'teststack/1'

        self.mock_request_get('/stacks/%s/events?sort_dir=asc' % stack_id,
                              resp_dict)
        list_text = self.shell('event-list %s --nested-depth 0' % stack_id)
        required = ['id', 'eventid1', 'eventid2']
        for r in required:
            self.assertRegex(list_text, r)

    def _stub_event_list_response_old_api(self, stack_id, nested_id,
                                          timestamps, first_request):
        """
        Stub

        Args:
            self: (todo): write your description
            stack_id: (str): write your description
            nested_id: (int): write your description
            timestamps: (todo): write your description
            first_request: (todo): write your description
        """
        # Stub events for parent stack
        ev_resp_dict = {"events": [{"id": "p_eventid1",
                                    "event_time": timestamps[0]},
                                   {"id": "p_eventid2",
                                    "event_time": timestamps[3]}]}
        self.mock_request_get(first_request, ev_resp_dict)

        # response lacks root_stack link, fetch nested events recursively
        self.mock_request_get('/stacks/%s/events?sort_dir=asc'
                              % stack_id, ev_resp_dict)

        # Stub resources for parent, including one nested
        res_resp_dict = {"resources": [
                         {"links": [{"href": "http://heat/foo", "rel": "self"},
                                    {"href": "http://heat/foo2",
                                     "rel": "resource"},
                                    {"href": "http://heat/%s" % nested_id,
                                     "rel": "nested"}],
                          "resource_type": "OS::Nested::Foo"}]}
        self.mock_request_get('/stacks/%s/resources' % stack_id, res_resp_dict)

        # Stub the events for the nested stack
        nev_resp_dict = {"events": [{"id": 'n_eventid1',
                                     "event_time": timestamps[1]},
                                    {"id": 'n_eventid2',
                                     "event_time": timestamps[2]}]}
        self.mock_request_get('/stacks/%s/events?sort_dir=asc' % nested_id,
                              nev_resp_dict)

    def test_shell_nested_depth_old_api(self):
        """
        Test if a nested shell has a shell.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        timestamps = ("2014-01-06T16:14:00Z",  # parent p_eventid1
                      "2014-01-06T16:15:00Z",  # nested n_eventid1
                      "2014-01-06T16:16:00Z",  # nested n_eventid2
                      "2014-01-06T16:17:00Z")  # parent p_eventid2
        first_request = ('/stacks/%s/events?nested_depth=1&sort_dir=asc'
                         % stack_id)
        self._stub_event_list_response_old_api(
            stack_id, nested_id, timestamps, first_request)
        list_text = self.shell('event-list %s --nested-depth 1' % stack_id)
        required = ['id', 'p_eventid1', 'p_eventid2', 'n_eventid1',
                    'n_eventid2', 'stack_name', 'teststack', 'nested']
        for r in required:
            self.assertRegex(list_text, r)

        # Check event time sort/ordering
        self.assertRegex(list_text,
                         "%s.*\n.*%s.*\n.*%s.*\n.*%s" % timestamps)

    def test_shell_nested_depth_marker_old_api(self):
        """
        Test if the shell_nested.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        timestamps = ("2014-01-06T16:14:00Z",  # parent p_eventid1
                      "2014-01-06T16:15:00Z",  # nested n_eventid1
                      "2014-01-06T16:16:00Z",  # nested n_eventid2
                      "2014-01-06T16:17:00Z")  # parent p_eventid2
        first_request = ('/stacks/%s/events?marker=n_eventid1&nested_depth=1'
                         '&sort_dir=asc' % stack_id)
        self._stub_event_list_response_old_api(
            stack_id, nested_id, timestamps, first_request)
        list_text = self.shell(
            'event-list %s --nested-depth 1 --marker n_eventid1' % stack_id)
        required = ['id', 'p_eventid2', 'n_eventid1', 'n_eventid2',
                    'stack_name', 'teststack', 'nested']
        for r in required:
            self.assertRegex(list_text, r)

        self.assertNotRegex(list_text, 'p_eventid1')

        self.assertRegex(list_text,
                         "%s.*\n.*%s.*\n.*%s.*" % timestamps[1:])

    def test_shell_nested_depth_limit_old_api(self):
        """
        Test if the shell_nested api.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        timestamps = ("2014-01-06T16:14:00Z",  # parent p_eventid1
                      "2014-01-06T16:15:00Z",  # nested n_eventid1
                      "2014-01-06T16:16:00Z",  # nested n_eventid2
                      "2014-01-06T16:17:00Z")  # parent p_eventid2
        first_request = ('/stacks/%s/events?limit=2&nested_depth=1'
                         '&sort_dir=asc' % stack_id)
        self._stub_event_list_response_old_api(
            stack_id, nested_id, timestamps, first_request)
        list_text = self.shell(
            'event-list %s --nested-depth 1 --limit 2' % stack_id)
        required = ['id', 'p_eventid1', 'n_eventid1',
                    'stack_name', 'teststack', 'nested']
        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'p_eventid2')
        self.assertNotRegex(list_text, 'n_eventid2')

        self.assertRegex(list_text,
                         "%s.*\n.*%s.*\n" % timestamps[:2])

    def _nested_events(self):
        """
        Return a list of event information.

        Args:
            self: (todo): write your description
        """
        links = [
            {"rel": "self"},
            {"rel": "resource"},
            {"rel": "stack"},
            {"rel": "root_stack"}
        ]
        return [
            {
                "id": "p_eventid1",
                "event_time": '2014-01-06T16:14:00Z',
                "stack_id": '1',
                "resource_name": 'the_stack',
                "resource_status": 'CREATE_IN_PROGRESS',
                "resource_status_reason": 'Stack CREATE started',
                "links": links,
            }, {
                "id": 'n_eventid1',
                "event_time": '2014-01-06T16:15:00Z',
                "stack_id": '2',
                "resource_name": 'nested_stack',
                "resource_status": 'CREATE_IN_PROGRESS',
                "resource_status_reason": 'Stack CREATE started',
                "links": links,
            }, {
                "id": 'n_eventid2',
                "event_time": '2014-01-06T16:16:00Z',
                "stack_id": '2',
                "resource_name": 'nested_stack',
                "resource_status": 'CREATE_COMPLETE',
                "resource_status_reason": 'Stack CREATE completed',
                "links": links,
            }, {
                "id": "p_eventid2",
                "event_time": '2014-01-06T16:17:00Z',
                "stack_id": '1',
                "resource_name": 'the_stack',
                "resource_status": 'CREATE_COMPLETE',
                "resource_status_reason": 'Stack CREATE completed',
                "links": links,
            },
        ]

    def test_shell_nested_depth(self):
        """
        Register the nested depth is running.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_events = self._nested_events()
        ev_resp_dict = {'events': nested_events}

        url = '/stacks/%s/events?nested_depth=1&sort_dir=asc' % stack_id
        self.mock_request_get(url, ev_resp_dict)
        list_text = self.shell('event-list %s --nested-depth 1 --format log'
                               % stack_id)
        self.assertEqual('''\
2014-01-06 16:14:00Z [the_stack]: CREATE_IN_PROGRESS  Stack CREATE started
2014-01-06 16:15:00Z [nested_stack]: CREATE_IN_PROGRESS  Stack CREATE started
2014-01-06 16:16:00Z [nested_stack]: CREATE_COMPLETE  Stack CREATE completed
2014-01-06 16:17:00Z [the_stack]: CREATE_COMPLETE  Stack CREATE completed
''', list_text)

    def test_shell_nested_depth_marker(self):
        """
        Register the shell doesn tqual_depth_marker.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_events = self._nested_events()
        ev_resp_dict = {'events': nested_events[1:]}

        url = ('/stacks/%s/events?marker=n_eventid1&nested_depth=1'
               '&sort_dir=asc' % stack_id)
        self.mock_request_get(url, ev_resp_dict)
        list_text = self.shell('event-list %s --nested-depth 1 --format log '
                               '--marker n_eventid1'
                               % stack_id)
        self.assertEqual('''\
2014-01-06 16:15:00Z [nested_stack]: CREATE_IN_PROGRESS  Stack CREATE started
2014-01-06 16:16:00Z [nested_stack]: CREATE_COMPLETE  Stack CREATE completed
2014-01-06 16:17:00Z [the_stack]: CREATE_COMPLETE  Stack CREATE completed
''', list_text)

    def test_shell_nested_depth_limit(self):
        """
        Test if the depth - depth depth

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_events = self._nested_events()
        ev_resp_dict = {'events': nested_events[:2]}

        url = ('/stacks/%s/events?limit=2&nested_depth=1&sort_dir=asc'
               % stack_id)
        self.mock_request_get(url, ev_resp_dict)
        list_text = self.shell('event-list %s --nested-depth 1 --format log '
                               '--limit 2'
                               % stack_id)
        self.assertEqual('''\
2014-01-06 16:14:00Z [the_stack]: CREATE_IN_PROGRESS  Stack CREATE started
2014-01-06 16:15:00Z [nested_stack]: CREATE_IN_PROGRESS  Stack CREATE started
''', list_text)


class ShellTestHookFunctions(ShellBase):
    def setUp(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        super(ShellTestHookFunctions, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def _stub_stack_response(self, stack_id, action='CREATE',
                             status='IN_PROGRESS'):
        """
        Stub

        Args:
            self: (todo): write your description
            stack_id: (str): write your description
            action: (str): write your description
            status: (str): write your description
        """
        # Stub parent stack show for status
        resp_dict = {"stack": {
            "id": stack_id.split("/")[1],
            "stack_name": stack_id.split("/")[0],
            "stack_status": '%s_%s' % (action, status),
            "creation_time": "2014-01-06T16:14:00Z",
        }}
        self.mock_request_get('/stacks/teststack/1', resp_dict)

    def _stub_responses(self, stack_id, nested_id, action='CREATE'):
        """
        Stub

        Args:
            self: (todo): write your description
            stack_id: (str): write your description
            nested_id: (str): write your description
            action: (str): write your description
        """
        action_reason = 'Stack %s started' % action
        hook_reason = ('%s paused until Hook pre-%s is cleared' %
                       (action, action.lower()))
        hook_clear_reason = 'Hook pre-%s is cleared' % action.lower()

        self._stub_stack_response(stack_id, action)

        # Stub events for parent stack
        ev_resp_dict = {"events": [{"id": "p_eventid1",
                                    "event_time": "2014-01-06T16:14:00Z",
                                    "resource_name": None,
                                    "resource_status_reason": action_reason},
                                   {"id": "p_eventid2",
                                    "event_time": "2014-01-06T16:17:00Z",
                                    "resource_name": "p_res",
                                    "resource_status_reason": hook_reason}]}

        url = '/stacks/%s/events?nested_depth=1&sort_dir=asc' % stack_id
        self.mock_request_get(url, ev_resp_dict)
        # this api doesn't support nested_depth, fetch events recursively
        self.mock_request_get('/stacks/%s/events?sort_dir=asc' % stack_id,
                              ev_resp_dict)

        # Stub resources for parent, including one nested
        res_resp_dict = {"resources": [
                         {"links": [{"href": "http://heat/foo", "rel": "self"},
                                    {"href": "http://heat/foo2",
                                     "rel": "resource"},
                                    {"href": "http://heat/%s" % nested_id,
                                     "rel": "nested"}],
                          "resource_type": "OS::Nested::Foo"}]}
        self.mock_request_get('/stacks/%s/resources' % stack_id, res_resp_dict)

        # Stub the events for the nested stack
        nev_resp_dict = {"events": [{"id": 'n_eventid1',
                                     "event_time": "2014-01-06T16:15:00Z",
                                     "resource_name": "n_res",
                                     "resource_status_reason": hook_reason},
                                    {"id": 'n_eventid2',
                                     "event_time": "2014-01-06T16:16:00Z",
                                     "resource_name": "n_res",
                                     "resource_status_reason":
                                     hook_clear_reason}]}
        self.mock_request_get('/stacks/%s/events?sort_dir=asc' % nested_id,
                              nev_resp_dict)

    def test_hook_poll_pre_create(self):
        """
        Test for pre - pre - pre - pre - pre - hook.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        self._stub_responses(stack_id, nested_id, 'CREATE')
        list_text = self.shell('hook-poll %s --nested-depth 1' % stack_id)
        hook_reason = 'CREATE paused until Hook pre-create is cleared'
        required = ['id', 'p_eventid2', 'stack_name', 'teststack', hook_reason]
        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'p_eventid1')
        self.assertNotRegex(list_text, 'n_eventid1')
        self.assertNotRegex(list_text, 'n_eventid2')

    def test_hook_poll_pre_update(self):
        """
        Test for pre - pre - pre - pre - pre - pre - pre - pre - pre - pre - pre - print hook.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        self._stub_responses(stack_id, nested_id, 'UPDATE')
        list_text = self.shell('hook-poll %s --nested-depth 1' % stack_id)
        hook_reason = 'UPDATE paused until Hook pre-update is cleared'
        required = ['id', 'p_eventid2', 'stack_name', 'teststack', hook_reason]
        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'p_eventid1')
        self.assertNotRegex(list_text, 'n_eventid1')
        self.assertNotRegex(list_text, 'n_eventid2')

    def test_hook_poll_pre_delete(self):
        """
        Test if pre - pre - pre - pre - hook

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        self._stub_responses(stack_id, nested_id, 'DELETE')
        list_text = self.shell('hook-poll %s --nested-depth 1' % stack_id)
        hook_reason = 'DELETE paused until Hook pre-delete is cleared'
        required = ['id', 'p_eventid2', 'stack_name', 'teststack', hook_reason]
        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'p_eventid1')
        self.assertNotRegex(list_text, 'n_eventid1')
        self.assertNotRegex(list_text, 'n_eventid2')

    def test_hook_poll_bad_status(self):
        """
        Test for bad status of the current stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        self._stub_stack_response(stack_id, status='COMPLETE')
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'hook-poll %s --nested-depth 1' % stack_id)
        self.assertIn('Stack status CREATE_COMPLETE not IN_PROGRESS',
                      str(error))

    def test_shell_nested_depth_invalid_value(self):
        """
        Check if the test test test test test test test.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'hook-poll %s --nested-depth Z' % stack_id)
        self.assertIn('--nested-depth invalid value Z', str(error))

    def test_hook_poll_clear_bad_status(self):
        """
        Determine the status of an error stack

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        self._stub_stack_response(stack_id, status='COMPLETE')
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'hook-clear %s aresource' % stack_id)
        self.assertIn('Stack status CREATE_COMPLETE not IN_PROGRESS',
                      str(error))

    def test_hook_poll_clear_bad_action(self):
        """
        Determine whether the bad action is set.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        self._stub_stack_response(stack_id, action='BADACTION')
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'hook-clear %s aresource' % stack_id)
        self.assertIn('Unexpected stack status BADACTION_IN_PROGRESS',
                      str(error))


class ShellTestResources(ShellBase):

    def setUp(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        super(ShellTestResources, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def _test_resource_list(self, with_resource_name):
        """
        Register resource resource resource to resource.

        Args:
            self: (todo): write your description
            with_resource_name: (str): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"resources": [
                     {"links": [{"href": "http://heat.example.com:8004/foo",
                                 "rel": "self"},
                                {"href": "http://heat.example.com:8004/foo2",
                                 "rel": "resource"}],
                      "logical_resource_id": "aLogicalResource",
                      "physical_resource_id":
                      "43b68bae-ed5d-4aed-a99f-0b3d39c2418a",
                      "resource_status": "CREATE_COMPLETE",
                      "resource_status_reason": "state changed",
                      "resource_type": "OS::Nova::Server",
                      "updated_time": "2014-01-06T16:14:26Z"}]}
        if with_resource_name:
            resp_dict["resources"][0]["resource_name"] = "aResource"
        stack_id = 'teststack/1'
        self.mock_request_get('/stacks/%s/resources' % stack_id, resp_dict)

        resource_list_text = self.shell('resource-list {0}'.format(stack_id))

        required = [
            'physical_resource_id',
            'resource_type',
            'resource_status',
            'updated_time',
            '43b68bae-ed5d-4aed-a99f-0b3d39c2418a',
            'OS::Nova::Server',
            'CREATE_COMPLETE',
            '2014-01-06T16:14:26Z'
        ]
        if with_resource_name:
            required.append('resource_name')
            required.append('aResource')
        else:
            required.append('logical_resource_id')
            required.append("aLogicalResource")

        for r in required:
            self.assertRegex(resource_list_text, r)

    def test_resource_list(self):
        """
        Lists all resource list.

        Args:
            self: (todo): write your description
        """
        self._test_resource_list(True)

    def test_resource_list_no_resource_name(self):
        """
        Test if the resource name of the resource.

        Args:
            self: (todo): write your description
        """
        self._test_resource_list(False)

    def test_resource_list_empty(self):
        """
        Test if the resource has been empty resource

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"resources": []}
        stack_id = 'teststack/1'
        self.mock_request_get('/stacks/%s/resources' % stack_id, resp_dict)

        resource_list_text = self.shell('resource-list {0}'.format(stack_id))

        self.assertEqual('''\
+---------------+----------------------+---------------+-----------------+\
--------------+
| resource_name | physical_resource_id | resource_type | resource_status |\
 updated_time |
+---------------+----------------------+---------------+-----------------+\
--------------+
+---------------+----------------------+---------------+-----------------+\
--------------+
''', resource_list_text)

    def _test_resource_list_more_args(self, query_args, cmd_args,
                                      response_args):
        """
        Test if resource args

        Args:
            self: (todo): write your description
            query_args: (dict): write your description
            cmd_args: (dict): write your description
            response_args: (dict): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"resources": [{
            "resource_name": "foobar",
            "links": [{
                "href": "http://heat.example.com:8004/foo/12/resources/foobar",
                "rel": "self"
            }, {
                "href": "http://heat.example.com:8004/foo/12",
                "rel": "stack"
            }],
        }]}
        stack_id = 'teststack/1'
        self.mock_request_get('/stacks/%s/resources?%s' % (
            stack_id, query_args), resp_dict)

        shell_cmd = 'resource-list %s %s' % (stack_id, cmd_args)

        resource_list_text = self.shell(shell_cmd)

        for field in response_args:
            self.assertRegex(resource_list_text, field)

    def test_resource_list_nested(self):
        """
        Test if resource list.

        Args:
            self: (todo): write your description
        """
        self._test_resource_list_more_args(
            query_args='nested_depth=99',
            cmd_args='--nested-depth 99',
            response_args=['resource_name', 'foobar', 'stack_name', 'foo'])

    def test_resource_list_filter(self):
        """
        Filter resource filter list of all resource resource.

        Args:
            self: (todo): write your description
        """
        self._test_resource_list_more_args(
            query_args='name=foobar',
            cmd_args='--filter name=foobar',
            response_args=['resource_name', 'foobar'])

    def test_resource_list_detail(self):
        """
        Get list of resource resources.

        Args:
            self: (todo): write your description
        """
        self._test_resource_list_more_args(
            query_args=parse.urlencode({'with_detail': True}, True),
            cmd_args='--with-detail',
            response_args=['resource_name', 'foobar', 'stack_name', 'foo'])

    def test_resource_show_with_attrs(self):
        """
        Show resource attributes.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"resource":
                     {"description": "",
                      "links": [{"href": "http://heat.example.com:8004/foo",
                                 "rel": "self"},
                                {"href": "http://heat.example.com:8004/foo2",
                                 "rel": "resource"}],
                      "logical_resource_id": "aResource",
                      "physical_resource_id":
                      "43b68bae-ed5d-4aed-a99f-0b3d39c2418a",
                      "required_by": [],
                      "resource_name": "aResource",
                      "resource_status": "CREATE_COMPLETE",
                      "resource_status_reason": "state changed",
                      "resource_type": "OS::Nova::Server",
                      "updated_time": "2014-01-06T16:14:26Z",
                      "creation_time": "2014-01-06T16:14:26Z",
                      "attributes": {
                          "attr_a": "value_of_attr_a",
                          "attr_b": "value_of_attr_b"}}}
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        self.mock_request_get(
            '/stacks/%s/resources/%s?with_attr=attr_a&with_attr=attr_b' %
            (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name))
            ), resp_dict)

        resource_show_text = self.shell(
            'resource-show {0} {1} --with-attr attr_a '
            '--with-attr attr_b'.format(
                stack_id, resource_name))

        required = [
            'description',
            'links',
            'http://heat.example.com:8004/foo[0-9]',
            'logical_resource_id',
            'aResource',
            'physical_resource_id',
            '43b68bae-ed5d-4aed-a99f-0b3d39c2418a',
            'required_by',
            'resource_name',
            'aResource',
            'resource_status',
            'CREATE_COMPLETE',
            'resource_status_reason',
            'state changed',
            'resource_type',
            'OS::Nova::Server',
            'updated_time',
            '2014-01-06T16:14:26Z',
        ]
        for r in required:
            self.assertRegex(resource_show_text, r)

    def test_resource_signal(self):
        """
        Test if the resource.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        self.mock_request_post(
            '/stacks/%s/resources/%s/signal' %
            (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name))
            ),
            '',
            data={'message': 'Content'}
        )

        text = self.shell(
            'resource-signal {0} {1} -D {{"message":"Content"}}'.format(
                stack_id, resource_name))
        self.assertEqual("", text)

    def test_resource_signal_no_data(self):
        """
        Test if the resource resource.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        self.mock_request_post(
            '/stacks/%s/resources/%s/signal' %
            (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name))
            ),
            '',
            data=None
        )

        text = self.shell(
            'resource-signal {0} {1}'.format(stack_id, resource_name))
        self.assertEqual("", text)

    def test_resource_signal_no_json(self):
        """
        Test if the resource in the resource resource.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'

        error = self.assertRaises(
            exc.CommandError, self.shell,
            'resource-signal {0} {1} -D [2'.format(
                stack_id, resource_name))
        self.assertIn('Data should be in JSON format', str(error))

    def test_resource_signal_no_dict(self):
        """
        Register the resource resource resource resource resource.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'

        error = self.assertRaises(
            exc.CommandError, self.shell,
            'resource-signal {0} {1} -D "message"'.format(
                stack_id, resource_name))
        self.assertEqual('Data should be a JSON dict', str(error))

    def test_resource_signal_both_data(self):
        """
        Test if the resource resource resource.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'

        error = self.assertRaises(
            exc.CommandError, self.shell,
            'resource-signal {0} {1} -D "message" -f foo'.format(
                stack_id, resource_name))
        self.assertEqual('Can only specify one of data and data-file',
                         str(error))

    def test_resource_signal_data_file(self):
        """
        Register a new resource.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        self.mock_request_post(
            '/stacks/%s/resources/%s/signal' %
            (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name))
            ),
            '',
            data={'message': 'Content'}
        )

        with tempfile.NamedTemporaryFile() as data_file:
            data_file.write(b'{"message":"Content"}')
            data_file.flush()
            text = self.shell(
                'resource-signal {0} {1} -f {2}'.format(
                    stack_id, resource_name, data_file.name))
            self.assertEqual("", text)

    def test_resource_mark_unhealthy(self):
        """
        Mark unhealthy unhealthy unhealthy unhealthy.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        self.mock_request_patch(
            '/stacks/%s/resources/%s' %
            (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name))
            ),
            '',
            req_headers=False,
            data={'mark_unhealthy': True,
                  'resource_status_reason': 'Any'})

        text = self.shell(
            'resource-mark-unhealthy {0} {1} Any'.format(
                stack_id, resource_name))
        self.assertEqual("", text)

    def test_resource_mark_unhealthy_reset(self):
        """
        Reset unhealthy resource unhealthy unhealthy

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        self.mock_request_patch(
            '/stacks/%s/resources/%s' %
            (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name))
            ),
            '',
            req_headers=False,
            data={'mark_unhealthy': False,
                  'resource_status_reason': 'Any'})

        text = self.shell(
            'resource-mark-unhealthy --reset {0} {1} Any'.format(
                stack_id, resource_name))
        self.assertEqual("", text)

    def test_resource_mark_unhealthy_no_reason(self):
        """
        Test to unhealthy unhealthy.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        self.mock_request_patch(
            '/stacks/%s/resources/%s' %
            (
                parse.quote(stack_id),
                parse.quote(encodeutils.safe_encode(
                    resource_name))
            ),
            '',
            req_headers=False,
            data={'mark_unhealthy': True,
                  'resource_status_reason': ''})

        text = self.shell(
            'resource-mark-unhealthy {0} {1}'.format(
                stack_id, resource_name))
        self.assertEqual("", text)


class ShellTestResourceTypes(ShellBase):
    def setUp(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        super(ShellTestResourceTypes, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V3)

    def test_resource_type_template_yaml(self):
        """
        Register the resource type template type

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"heat_template_version": "2013-05-23",
                     "parameters": {},
                     "resources": {},
                     "outputs": {}}

        self.mock_request_get(
            '/resource_types/OS%3A%3ANova%3A%3AKeyPair/template'
            '?template_type=hot', resp_dict)

        show_text = self.shell(
            'resource-type-template -F yaml -t hot OS::Nova::KeyPair')
        required = [
            "heat_template_version: '2013-05-23'",
            "outputs: {}",
            "parameters: {}",
            "resources: {}"
        ]
        for r in required:
            self.assertRegex(show_text, r)

    def test_resource_type_template_json(self):
        """
        Register a new resource type template with_type

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {"AWSTemplateFormatVersion": "2013-05-23",
                     "Parameters": {},
                     "Resources": {},
                     "Outputs": {}}

        self.mock_request_get(
            '/resource_types/OS%3A%3ANova%3A%3AKeyPair/template'
            '?template_type=cfn', resp_dict)

        show_text = self.shell(
            'resource-type-template -F json OS::Nova::KeyPair')
        required = [
            '{',
            '  "AWSTemplateFormatVersion": "2013-05-23"',
            '  "Outputs": {}',
            '  "Resources": {}',
            '  "Parameters": {}',
            '}'
        ]
        for r in required:
            self.assertRegex(show_text, r)


class ShellTestConfig(ShellBase):

    def setUp(self):
        """
        Sets the configuration.

        Args:
            self: (todo): write your description
        """
        super(ShellTestConfig, self).setUp()
        self._set_fake_env()

    def _set_fake_env(self):
        '''Patch os.environ to avoid required auth info.'''
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_config_create(self):
        """
        Create a new config.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        definition = {
            'inputs': [
                {'name': 'foo'},
                {'name': 'bar'},
            ],
            'outputs': [
                {'name': 'result'}
            ],
            'options': {'a': 'b'}
        }
        validate_template = {'template': {
            'heat_template_version': '2013-05-23',
            'resources': {
                'config_name': {
                    'type': 'OS::Heat::SoftwareConfig',
                    'properties': {
                        'config': 'the config script',
                        'group': 'script',
                        'inputs': [
                            {'name': 'foo'},
                            {'name': 'bar'},
                        ],
                        'outputs': [
                            {'name': 'result'}
                        ],
                        'options': {'a': 'b'},
                        'config': 'the config script'
                    }
                }
            }
        }}

        create_dict = {
            'group': 'script',
            'name': 'config_name',
            'inputs': [
                {'name': 'foo'},
                {'name': 'bar'},
            ],
            'outputs': [
                {'name': 'result'}
            ],
            'options': {'a': 'b'},
            'config': 'the config script'
        }

        resp_dict = {'software_config': {
            'group': 'script',
            'name': 'config_name',
            'inputs': [
                {'name': 'foo'},
                {'name': 'bar'},
            ],
            'outputs': [
                {'name': 'result'}
            ],
            'options': {'a': 'b'},
            'config': 'the config script',
            'id': 'abcd'
        }}

        output = [
            six.StringIO(yaml.safe_dump(definition, indent=2)),
            six.StringIO('the config script'),
        ]
        self.useFixture(fixtures.MockPatchObject(request, 'urlopen',
                                                 side_effect=output))

        self.mock_request_post('/validate', resp_dict, data=validate_template)
        self.mock_request_post('/software_configs', resp_dict,
                               data=create_dict)

        text = self.shell('config-create -c /tmp/config_script '
                          '-g script -f /tmp/defn config_name')

        self.assertEqual(resp_dict['software_config'], jsonutils.loads(text))
        request.urlopen.assert_has_calls([
            mock.call('file:///tmp/defn'),
            mock.call('file:///tmp/config_script'),
        ])

    def test_config_show(self):
        """
        Show test configuration

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {'software_config': {
            'inputs': [],
            'group': 'script',
            'name': 'config_name',
            'outputs': [],
            'options': {},
            'config': 'the config script',
            'id': 'abcd'}}
        self.mock_request_get('/software_configs/abcd', resp_dict)
        self.mock_request_get('/software_configs/abcd', resp_dict)
        self.mock_request_error('/software_configs/abcde', 'GET',
                                exc.HTTPNotFound())

        text = self.shell('config-show abcd')

        required = [
            'inputs',
            'group',
            'name',
            'outputs',
            'options',
            'config',
            'id',
        ]
        for r in required:
            self.assertRegex(text, r)

        self.assertEqual(
            'the config script\n',
            self.shell('config-show --config-only abcd'))
        self.assertRaises(exc.CommandError, self.shell, 'config-show abcde')

    def test_config_delete(self):
        """
        Perform configuration.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.mock_request_delete('/software_configs/abcd')
        self.mock_request_delete('/software_configs/qwer')
        self.mock_request_error('/software_configs/abcd', 'DELETE',
                                exc.HTTPNotFound())
        self.mock_request_error('/software_configs/qwer', 'DELETE',
                                exc.HTTPNotFound())

        self.assertEqual('', self.shell('config-delete abcd qwer'))

        error = self.assertRaises(
            exc.CommandError, self.shell, 'config-delete abcd qwer')
        self.assertIn('Unable to delete 2 of the 2 configs.',
                      str(error))


class ShellTestDeployment(ShellBase):

    def setUp(self):
        """
        Sets the environment.

        Args:
            self: (todo): write your description
        """
        super(ShellTestDeployment, self).setUp()
        self.client = http.SessionClient
        self._set_fake_env()

    def _set_fake_env(self):
        '''Patch os.environ to avoid required auth info.'''
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_deploy_create(self):
        """
        Create deploy deploy deploy deploy

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        self.patch(
            'heatclient.common.deployment_utils.build_derived_config_params')
        self.patch(
            'heatclient.common.deployment_utils.build_signal_id')
        resp_dict = {'software_deployment': {
            'status': 'INPROGRESS',
            'server_id': '700115e5-0100-4ecc-9ef7-9e05f27d8803',
            'config_id': '18c4fc03-f897-4a1d-aaad-2b7622e60257',
            'output_values': {
                'deploy_stdout': '',
                'deploy_stderr': '',
                'deploy_status_code': 0,
                'result': 'The result value'
            },
            'input_values': {},
            'action': 'UPDATE',
            'status_reason': 'Outputs received',
            'id': 'abcd'
        }}

        config_dict = {'software_config': {
            'inputs': [],
            'group': 'script',
            'name': 'config_name',
            'outputs': [],
            'options': {},
            'config': 'the config script',
            'id': 'defg'}}

        derived_dict = {'software_config': {
            'inputs': [],
            'group': 'script',
            'name': 'config_name',
            'outputs': [],
            'options': {},
            'config': 'the config script',
            'id': 'abcd'}}

        deploy_data = {'action': 'UPDATE',
                       'config_id': u'abcd',
                       'server_id': 'inst01',
                       'status': 'IN_PROGRESS',
                       'tenant_id': 'asdf'}

        self.mock_request_get('/software_configs/defg', config_dict)
        self.mock_request_post('/software_configs', derived_dict, data={})
        self.mock_request_post('/software_deployments', resp_dict,
                               data=deploy_data)

        self.mock_request_post('/software_configs', derived_dict, data={})
        self.mock_request_post('/software_deployments', resp_dict,
                               data=deploy_data)
        self.mock_request_error('/software_configs/defgh', 'GET',
                                exc.HTTPNotFound())

        text = self.shell('deployment-create -c defg -sinst01 xxx')

        required = [
            'status',
            'server_id',
            'config_id',
            'output_values',
            'input_values',
            'action',
            'status_reason',
            'id',
        ]
        for r in required:
            self.assertRegex(text, r)

        text = self.shell('deployment-create -sinst01 xxx')
        for r in required:
            self.assertRegex(text, r)

        self.assertRaises(exc.CommandError, self.shell,
                          'deployment-create -c defgh -s inst01 yyy')

    def test_deploy_list(self):
        """
        Deploy the deployment list of the deployment

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {
            'software_deployments':
                [{'status': 'COMPLETE',
                  'server_id': '123',
                  'config_id': '18c4fc03-f897-4a1d-aaad-2b7622e60257',
                  'output_values': {
                      'deploy_stdout': '',
                      'deploy_stderr': '',
                      'deploy_status_code': 0,
                      'result': 'The result value'
                  },
                  'input_values': {},
                  'action': 'CREATE',
                  'status_reason': 'Outputs received',
                  'id': 'defg'}, ]
        }
        self.mock_request_get('/software_deployments?', resp_dict)
        self.mock_request_get('/software_deployments?server_id=123', resp_dict)

        list_text = self.shell('deployment-list')

        required = [
            'id',
            'config_id',
            'server_id',
            'action',
            'status',
            'creation_time',
            'status_reason',
        ]
        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'parent')

        list_text = self.shell('deployment-list -s 123')

        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'parent')

    def test_deploy_show(self):
        """
        Show the deployment todo.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {'software_deployment': {
            'status': 'COMPLETE',
            'server_id': '700115e5-0100-4ecc-9ef7-9e05f27d8803',
            'config_id': '18c4fc03-f897-4a1d-aaad-2b7622e60257',
            'output_values': {
                'deploy_stdout': '',
                'deploy_stderr': '',
                'deploy_status_code': 0,
                'result': 'The result value'
            },
            'input_values': {},
            'action': 'CREATE',
            'status_reason': 'Outputs received',
            'id': 'defg'
        }}
        self.mock_request_get('/software_deployments/defg', resp_dict)
        self.mock_request_error('/software_deployments/defgh', 'GET',
                                exc.HTTPNotFound())

        text = self.shell('deployment-show defg')

        required = [
            'status',
            'server_id',
            'config_id',
            'output_values',
            'input_values',
            'action',
            'status_reason',
            'id',
        ]
        for r in required:
            self.assertRegex(text, r)
        self.assertRaises(exc.CommandError, self.shell,
                          'deployment-show defgh')

    def test_deploy_delete(self):
        """
        Deletes the deploy request. deploy.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()

        deploy_resp_dict = {'software_deployment': {
            'config_id': 'dummy_config_id'
        }}

        def _get_deployment_request_except(id):
            """
            Get request to get the deployment request.

            Args:
                id: (str): write your description
            """
            self.mock_request_error('/software_deployments/%s' % id, 'GET',
                                    exc.HTTPNotFound())

        def _delete_deployment_request_except(id):
            """
            Deletes the deployment request.

            Args:
                id: (str): write your description
            """
            self.mock_request_get('/software_deployments/%s' % id,
                                  deploy_resp_dict)
            self.mock_request_error('/software_deployments/%s' % id, 'DELETE',
                                    exc.HTTPNotFound())

        def _delete_config_request_except(id):
            """
            Deletes the configuration request.

            Args:
                id: (str): write your description
            """
            self.mock_request_get('/software_deployments/%s' % id,
                                  deploy_resp_dict)
            self.mock_request_delete('/software_deployments/%s' % id)
            self.mock_request_error('/software_configs/dummy_config_id',
                                    'DELETE', exc.HTTPNotFound())

        def _delete_request_success(id):
            """
            Handles the delete request.

            Args:
                id: (str): write your description
            """
            self.mock_request_get('/software_deployments/%s' % id,
                                  deploy_resp_dict)
            self.mock_request_delete('/software_deployments/%s' % id)
            self.mock_request_delete('/software_configs/dummy_config_id')

        _get_deployment_request_except('defg')
        _get_deployment_request_except('qwer')
        _delete_deployment_request_except('defg')
        _delete_deployment_request_except('qwer')
        _delete_config_request_except('defg')
        _delete_config_request_except('qwer')
        _delete_request_success('defg')
        _delete_request_success('qwer')

        error = self.assertRaises(
            exc.CommandError, self.shell, 'deployment-delete defg qwer')
        self.assertIn('Unable to delete 2 of the 2 deployments.',
                      str(error))
        error2 = self.assertRaises(
            exc.CommandError, self.shell, 'deployment-delete defg qwer')
        self.assertIn('Unable to delete 2 of the 2 deployments.',
                      str(error2))
        output = self.shell('deployment-delete defg qwer')
        self.assertRegex(output, 'Failed to delete the correlative config '
                                 'dummy_config_id of deployment defg')
        self.assertRegex(output, 'Failed to delete the correlative config '
                                 'dummy_config_id of deployment qwer')

        self.assertEqual('', self.shell('deployment-delete defg qwer'))

    def test_deploy_metadata(self):
        """
        Deploy the deployment metadata

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {'metadata': [
            {'id': 'abcd'},
            {'id': 'defg'}
        ]}
        self.mock_request_get('/software_deployments/metadata/aaaa', resp_dict)

        build_info_text = self.shell('deployment-metadata-show aaaa')

        required = [
            'abcd',
            'defg',
            'id',
        ]
        for r in required:
            self.assertRegex(build_info_text, r)

    def test_deploy_output_show(self):
        """
        Show the ::

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {'software_deployment': {
            'status': 'COMPLETE',
            'server_id': '700115e5-0100-4ecc-9ef7-9e05f27d8803',
            'config_id': '18c4fc03-f897-4a1d-aaad-2b7622e60257',
            'output_values': {
                'deploy_stdout': '',
                'deploy_stderr': '',
                'deploy_status_code': 0,
                'result': 'The result value',
                'dict_output': {'foo': 'bar'},
                'list_output': ['foo', 'bar']
            },
            'input_values': {},
            'action': 'CREATE',
            'status_reason': 'Outputs received',
            'id': 'defg'
        }}
        self.mock_request_error('/software_deployments/defgh', 'GET',
                                exc.HTTPNotFound())
        for a in range(9):
            self.mock_request_get('/software_deployments/defg', resp_dict)

        self.assertRaises(exc.CommandError, self.shell,
                          'deployment-output-show defgh result')
        self.assertEqual(
            'The result value\n',
            self.shell('deployment-output-show defg result'))
        self.assertEqual(
            '"The result value"\n',
            self.shell('deployment-output-show --format json defg result'))

        self.assertEqual(
            '{\n  "foo": "bar"\n}\n',
            self.shell('deployment-output-show defg dict_output'))
        self.assertEqual(
            self.shell(
                'deployment-output-show --format raw defg dict_output'),
            self.shell(
                'deployment-output-show --format json defg dict_output'))

        self.assertEqual(
            '[\n  "foo", \n  "bar"\n]\n',
            self.shell('deployment-output-show defg list_output'))
        self.assertEqual(
            self.shell(
                'deployment-output-show --format raw defg list_output'),
            self.shell(
                'deployment-output-show --format json defg list_output'))

        self.assertEqual({
            'deploy_stdout': '',
            'deploy_stderr': '',
            'deploy_status_code': 0,
            'result': 'The result value',
            'dict_output': {'foo': 'bar'},
            'list_output': ['foo', 'bar']},
            jsonutils.loads(self.shell(
                'deployment-output-show --format json defg --all'))
        )


class ShellTestBuildInfo(ShellBase):

    def setUp(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        super(ShellTestBuildInfo, self).setUp()
        self._set_fake_env()

    def _set_fake_env(self):
        '''Patch os.environ to avoid required auth info.'''
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_build_info(self):
        """
        Register build information.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {
            'build_info': {
                'api': {'revision': 'api_revision'},
                'engine': {'revision': 'engine_revision'}
            }
        }
        self.mock_request_get('/build_info', resp_dict)

        build_info_text = self.shell('build-info')

        required = [
            'api',
            'engine',
            'revision',
            'api_revision',
            'engine_revision',
        ]
        for r in required:
            self.assertRegex(build_info_text, r)


class ShellTestToken(ShellTestUserPass):

    # Rerun all ShellTestUserPass test with token auth
    def setUp(self):
        """
        Set token as the token.

        Args:
            self: (todo): write your description
        """
        self.token = 'a_token'
        super(ShellTestToken, self).setUp()

    def _set_fake_env(self):
        """
        Sets up the environment.

        Args:
            self: (todo): write your description
        """
        fake_env = {
            'OS_AUTH_TOKEN': self.token,
            'OS_TENANT_ID': 'tenant_id',
            'OS_AUTH_URL': BASE_URL,
            # Note we also set username/password, because create/update
            # pass them even if we have a token to support storing credentials
            # Hopefully at some point we can remove this and move to only
            # storing trust id's in heat-engine instead..
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password'
        }
        self.set_fake_env(fake_env)


class ShellTestUserPassKeystoneV3(ShellTestUserPass):

    def _set_fake_env(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        self.set_fake_env(FAKE_ENV_KEYSTONE_V3)


class StandaloneTokenMixin(object):
    def setUp(self):
        """
        Set token.

        Args:
            self: (todo): write your description
        """
        self.token = 'a_token'
        super(StandaloneTokenMixin, self).setUp()
        self.client = http.HTTPClient

    def _set_fake_env(self):
        """
        Set up the environment variables for an environment variables.

        Args:
            self: (todo): write your description
        """
        fake_env = {
            'OS_AUTH_TOKEN': self.token,
            'OS_NO_CLIENT_AUTH': 'True',
            'HEAT_URL': 'http://no.where',
            'OS_AUTH_URL': BASE_URL,
            # Note we also set username/password, because create/update
            # pass them even if we have a token to support storing credentials
            # Hopefully at some point we can remove this and move to only
            # storing trust id's in heat-engine instead..
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password'
        }
        self.set_fake_env(fake_env)


class ShellTestStandaloneToken(StandaloneTokenMixin, ShellTestUserPass):
    # Rerun all ShellTestUserPass test in standalone mode, where we
    # specify --os-no-client-auth, a token and Heat endpoint

    def test_bad_template_file(self):
        """
        Register your json file as json

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        failed_msg = 'Error parsing template '

        with tempfile.NamedTemporaryFile() as bad_json_file:
            bad_json_file.write(b"{foo:}")
            bad_json_file.flush()
            self.shell_error("stack-create ts -f %s" % bad_json_file.name,
                             failed_msg, exception=exc.CommandError)

        with tempfile.NamedTemporaryFile() as bad_json_file:
            bad_json_file.write(b'{"foo": None}')
            bad_json_file.flush()
            self.shell_error("stack-create ts -f %s" % bad_json_file.name,
                             failed_msg, exception=exc.CommandError)


class ShellTestStandaloneTokenArgs(StandaloneTokenMixin, ShellTestNoMoxBase):

    def test_commandline_args_passed_to_requests(self):
        """Check that we have sent the proper arguments to requests."""
        self.register_keystone_auth_fixture()

        resp_dict = {"stacks": [
            {
                "id": "1",
                "stack_name": "teststack",
                "stack_owner": "testowner",
                "project": "testproject",
                "stack_status": 'CREATE_COMPLETE',
                "creation_time": "2014-10-15T01:58:47Z"
            }]}
        self.requests.get('http://no.where/stacks',
                          status_code=200,
                          headers={'Content-Type': 'application/json'},
                          json=resp_dict)

        # Replay, create client, assert
        list_text = self.shell('stack-list')
        required = [
            'id',
            'stack_status',
            'creation_time',
            'teststack',
            '1',
            'CREATE_COMPLETE',
        ]
        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'parent')


class MockShellBase(TestCase):

    def setUp(self):
        """
        Sets the mock.

        Args:
            self: (todo): write your description
        """
        super(MockShellBase, self).setUp()
        self.jreq_mock = self.patch(
            'heatclient.common.http.HTTPClient.json_request')
        self.session_jreq_mock = self.patch(
            'heatclient.common.http.SessionClient.request')

        # Some tests set exc.verbose = 1, so reset on cleanup
        def unset_exc_verbose():
            """
            Unset the exception traceback.

            Args:
            """
            exc.verbose = 0

        self.addCleanup(unset_exc_verbose)

    def shell(self, argstr):
        """
        Execute a shell.

        Args:
            self: (todo): write your description
            argstr: (str): write your description
        """
        orig = sys.stdout
        try:
            sys.stdout = six.StringIO()
            _shell = heatclient.shell.HeatShell()
            _shell.main(argstr.split())
            self.subcommands = _shell.subcommands.keys()
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(0, exc_value.code)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out


class MockShellTestUserPass(MockShellBase):

    def setUp(self):
        """
        Sets the environment.

        Args:
            self: (todo): write your description
        """
        super(MockShellTestUserPass, self).setUp()
        self._set_fake_env()

    def _set_fake_env(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_stack_list_with_args(self):
        """
        Register stack stack stack args

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = self.stack_list_resp_dict(include_project=True)
        resp = fakes.FakeHTTPResponse(
            200,
            'success, you',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        self.session_jreq_mock.return_value = resp
        self.jreq_mock.return_value = (resp, resp_dict)

        list_text = self.shell('stack-list'
                               ' --limit 2'
                               ' --marker fake_id'
                               ' --filters=status=COMPLETE'
                               ' --filters=status=FAILED'
                               ' --tags=tag1,tag2'
                               ' --tags-any=tag3,tag4'
                               ' --not-tags=tag5,tag6'
                               ' --not-tags-any=tag7,tag8'
                               ' --global-tenant'
                               ' --show-deleted'
                               ' --show-hidden'
                               ' --sort-keys=stack_name;creation_time'
                               ' --sort-keys=updated_time'
                               ' --sort-dir=asc')

        required = [
            'stack_owner',
            'project',
            'testproject',
            'teststack',
            'teststack2',
        ]
        for r in required:
            self.assertRegex(list_text, r)
        self.assertNotRegex(list_text, 'parent')

        if self.jreq_mock.call_args is None:
            self.assertEqual(1, self.session_jreq_mock.call_count)
            url, method = self.session_jreq_mock.call_args[0]
        else:
            self.assertEqual(1, self.jreq_mock.call_count)
            method, url = self.jreq_mock.call_args[0]
        self.assertEqual('GET', method)
        base_url, query_params = utils.parse_query_url(url)
        self.assertEqual('/stacks', base_url)
        expected_query_dict = {'limit': ['2'],
                               'status': ['COMPLETE', 'FAILED'],
                               'marker': ['fake_id'],
                               'tags': ['tag1,tag2'],
                               'tags_any': ['tag3,tag4'],
                               'not_tags': ['tag5,tag6'],
                               'not_tags_any': ['tag7,tag8'],
                               'global_tenant': ['True'],
                               'show_deleted': ['True'],
                               'show_hidden': ['True'],
                               'sort_keys': ['stack_name', 'creation_time',
                                             'updated_time'],
                               'sort_dir': ['asc']}
        self.assertEqual(expected_query_dict, query_params)


class MockShellTestToken(MockShellTestUserPass):

    # Rerun all ShellTestUserPass test with token auth
    def setUp(self):
        """
        Set the token.

        Args:
            self: (todo): write your description
        """
        self.token = 'a_token'
        super(MockShellTestToken, self).setUp()

    def _set_fake_env(self):
        """
        Sets up the environment.

        Args:
            self: (todo): write your description
        """
        fake_env = {
            'OS_AUTH_TOKEN': self.token,
            'OS_TENANT_ID': 'tenant_id',
            'OS_AUTH_URL': BASE_URL,
            # Note we also set username/password, because create/update
            # pass them even if we have a token to support storing credentials
            # Hopefully at some point we can remove this and move to only
            # storing trust id's in heat-engine instead..
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password'
        }
        self.set_fake_env(fake_env)


class MockShellTestUserPassKeystoneV3(MockShellTestUserPass):

    def _set_fake_env(self):
        """
        Sets the environment variables.

        Args:
            self: (todo): write your description
        """
        self.set_fake_env(FAKE_ENV_KEYSTONE_V3)


class MockShellTestStandaloneToken(MockShellTestUserPass):

    # Rerun all ShellTestUserPass test in standalone mode, where we
    # specify --os-no-client-auth, a token and Heat endpoint
    def setUp(self):
        """
        Sets the token.

        Args:
            self: (todo): write your description
        """
        self.token = 'a_token'
        super(MockShellTestStandaloneToken, self).setUp()

    def _set_fake_env(self):
        """
        Set up the environment variables for an environment variables.

        Args:
            self: (todo): write your description
        """
        fake_env = {
            'OS_AUTH_TOKEN': self.token,
            'OS_NO_CLIENT_AUTH': 'True',
            'HEAT_URL': 'http://no.where',
            'OS_AUTH_URL': BASE_URL,
            # Note we also set username/password, because create/update
            # pass them even if we have a token to support storing credentials
            # Hopefully at some point we can remove this and move to only
            # storing trust id's in heat-engine instead..
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password'
        }
        self.set_fake_env(fake_env)


class ShellTestManageService(ShellBase):

    def setUp(self):
        """
        Sets the environment.

        Args:
            self: (todo): write your description
        """
        super(ShellTestManageService, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def _set_fake_env(self):
        '''Patch os.environ to avoid required auth info.'''
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def _test_error_case(self, code, message):
        """
        : param code : : return :

        Args:
            self: (todo): write your description
            code: (int): write your description
            message: (str): write your description
        """
        self.register_keystone_auth_fixture()

        resp_dict = {
            'explanation': '',
            'code': code,
            'error': {
                'message': message,
                'type': '',
                'traceback': '',
            },
            'title': 'test title'
        }
        resp_string = jsonutils.dumps(resp_dict)
        resp = fakes.FakeHTTPResponse(
            code,
            'test reason',
            {'content-type': 'application/json'},
            resp_string)
        self.mock_request_error('/services', 'GET', exc.from_response(resp))

        exc.verbose = 1

        e = self.assertRaises(exc.HTTPException,
                              self.shell, "service-list")
        self.assertIn(message, str(e))

    def test_service_list(self):
        """
        Register a service list of the service.

        Args:
            self: (todo): write your description
        """
        self.register_keystone_auth_fixture()
        resp_dict = {
            'services': [
                {
                    "status": "up",
                    "binary": "heat-engine",
                    "engine_id": "9d9242c3-4b9e-45e1-9e74-7615fbf20e5d",
                    "hostname": "mrkanag",
                    "updated_at": "2015-02-03T05:57:59.000000",
                    "topic": "engine",
                    "host": "engine-1"
                }
            ]
        }
        self.mock_request_get('/services', resp_dict)

        services_text = self.shell('service-list')

        required = [
            'hostname', 'binary', 'engine_id', 'host',
            'topic', 'updated_at', 'status'
        ]
        for r in required:
            self.assertRegex(services_text, r)

    def test_service_list_503(self):
        """
        A test test test test test for test.

        Args:
            self: (todo): write your description
        """
        self._test_error_case(
            message='All heat engines are down',
            code=503)

    def test_service_list_403(self):
        """
        A test test for a test.

        Args:
            self: (todo): write your description
        """
        self._test_error_case(
            message=('You are not authorized to '
                     'complete this action'),
            code=403)
