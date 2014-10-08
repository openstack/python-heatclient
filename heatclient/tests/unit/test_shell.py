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

import fixtures
import os
from oslotest import mockpatch
import re
import requests
import six
from six.moves.urllib import parse
from six.moves.urllib import request
import sys
import tempfile
import testscenarios
import testtools
import uuid
import yaml

from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from requests_mock.contrib import fixture as rm_fixture

from keystoneclient import fixture as keystone_fixture

from mox3 import mox

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
        super(TestCase, self).setUp()
        self.requests = self.useFixture(rm_fixture.Fixture())
        # httpretty doesn't work as expected if http proxy environmen
        # variable is set.
        self.useFixture(fixtures.EnvironmentVariable('http_proxy'))
        self.useFixture(fixtures.EnvironmentVariable('https_proxy'))

    def set_fake_env(self, fake_env):
        client_env = ('OS_USERNAME', 'OS_PASSWORD', 'OS_TENANT_ID',
                      'OS_TENANT_NAME', 'OS_AUTH_URL', 'OS_REGION_NAME',
                      'OS_AUTH_TOKEN', 'OS_NO_CLIENT_AUTH', 'OS_SERVICE_TYPE',
                      'OS_ENDPOINT_TYPE', 'HEAT_URL')

        for key in client_env:
            self.useFixture(
                fixtures.EnvironmentVariable(key, fake_env.get(key)))

    # required for testing with Python 2.6
    def assertRegexpMatches(self, text, expected_regexp, msg=None):
        """Fail the test unless the text matches the regular expression."""
        if isinstance(expected_regexp, six.string_types):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(text):
            msg = msg or "Regexp didn't match"
            msg = '%s: %r not found in %r' % (
                msg, expected_regexp.pattern, text)
            raise self.failureException(msg)

    # required for testing with Python 2.6
    def assertNotRegexpMatches(self, text, expected_regexp, msg=None):
        try:
            self.assertRegexpMatches(text, expected_regexp, msg)
        except self.failureException:
            pass
        else:
            raise self.failureException(msg)

    def shell_error(self, argstr, error_match):
        orig = sys.stderr
        sys.stderr = six.StringIO()
        _shell = heatclient.shell.HeatShell()
        e = self.assertRaises(Exception, _shell.main, argstr.split())
        self.assertRegexpMatches(e.__str__(), error_match)
        err = sys.stderr.getvalue()
        sys.stderr.close()
        sys.stderr = orig
        return err

    def register_keystone_v2_token_fixture(self):
        v2_token = keystone_fixture.V2Token(token_id=self.tokenid)
        service = v2_token.add_service('orchestration')
        service.add_endpoint('http://heat.example.com',
                             admin='http://heat-admin.localdomain',
                             internal='http://heat.localdomain',
                             region='RegionOne')
        self.requests.post('%s/tokens' % V2_URL, json=v2_token)

    def register_keystone_v3_token_fixture(self):
        v3_token = keystone_fixture.V3Token()
        service = v3_token.add_service('orchestration')
        service.add_standard_endpoints(public='http://heat.example.com',
                                       admin='http://heat-admin.localdomain',
                                       internal='http://heat.localdomain')
        self.requests.post('%s/auth/tokens' % V3_URL,
                           json=v3_token,
                           headers={'X-Subject-Token': self.tokenid})

    def register_keystone_auth_fixture(self):
        self.register_keystone_v2_token_fixture()
        self.register_keystone_v3_token_fixture()

        version_list = keystone_fixture.DiscoveryList(href=BASE_URL)
        self.requests.get(BASE_URL, json=version_list)

    # NOTE(tlashchova): this overrides the testtools.TestCase.patch method
    # that does simple monkey-patching in favor of mock's patching
    def patch(self, target, **kwargs):
        mockfixture = self.useFixture(mockpatch.Patch(target, **kwargs))
        return mockfixture.mock


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

        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        fake_env[self.remove] = None
        self.set_fake_env(fake_env)
        self.shell_error('stack-list', self.err)


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

        fake_env = {
            'OS_AUTH_TOKEN': 'atoken',
            'OS_TENANT_ID': 'tenant_id',
            'OS_AUTH_URL': 'http://no.where',
        }
        fake_env[self.remove] = None
        self.set_fake_env(fake_env)
        self.shell_error('stack-list', self.err)


class ShellParamValidationTest(TestCase):

    scenarios = [
        ('stack-create', dict(
            command='stack-create ts -P "ab"',
            err='Malformed parameter')),
        ('stack-update', dict(
            command='stack-update ts -P "a-b"',
            err='Malformed parameter')),
    ]

    def setUp(self):
        super(ShellParamValidationTest, self).setUp()
        self.m = mox.Mox()
        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def test_bad_parameters(self):
        self.register_keystone_auth_fixture()
        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': BASE_URL,
        }
        self.set_fake_env(fake_env)
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        cmd = '%s --template-file=%s ' % (self.command, template_file)
        self.shell_error(cmd, self.err)


class ShellValidationTest(TestCase):

    def setUp(self):
        super(ShellValidationTest, self).setUp()
        self.m = mox.Mox()
        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def test_failed_auth(self):
        self.register_keystone_auth_fixture()
        self.m.StubOutWithMock(http.SessionClient, 'request')
        failed_msg = 'Unable to authenticate user with credentials provided'
        http.SessionClient.request(
            '/stacks?', 'GET').AndRaise(exc.Unauthorized(failed_msg))

        self.m.ReplayAll()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)
        self.shell_error('stack-list', failed_msg)

    def test_stack_create_validation(self):
        self.register_keystone_auth_fixture()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)
        self.shell_error(
            'stack-create teststack '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"',
            'Need to specify exactly one of')

    def test_stack_create_with_paramfile_validation(self):
        self.register_keystone_auth_fixture()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)
        self.shell_error(
            'stack-create teststack '
            '--parameter-file private_key=private_key.env '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"',
            'Need to specify exactly one of')

    def test_stack_create_validation_keystone_v3(self):
        self.register_keystone_auth_fixture()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V3)
        self.shell_error(
            'stack-create teststack '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"',
            'Need to specify exactly one of')


class ShellBase(TestCase):

    def setUp(self):
        super(ShellBase, self).setUp()
        self.m = mox.Mox()
        self.m.StubOutWithMock(http.HTTPClient, 'json_request')
        self.m.StubOutWithMock(http.HTTPClient, 'raw_request')
        self.m.StubOutWithMock(http.SessionClient, 'request')
        self.client = http.SessionClient
        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

        # Some tests set exc.verbose = 1, so reset on cleanup
        def unset_exc_verbose():
            exc.verbose = 0

        self.addCleanup(unset_exc_verbose)

    def shell(self, argstr):
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


class ShellTestNoMox(TestCase):
    # NOTE(dhu):  This class is reserved for no Mox usage.  Instead,
    # use requests_mock to expose errors from json_request.
    def setUp(self):
        super(ShellTestNoMox, self).setUp()
        self._set_fake_env()

    def _set_fake_env(self):
        self.set_fake_env({
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'HEAT_URL': 'http://heat.example.com',
            'OS_AUTH_URL': BASE_URL,
            'OS_NO_CLIENT_AUTH': 'True'
        })

    def shell(self, argstr):
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

    # This function tests err msg handling
    def test_stack_create_parameter_missing_err_msg(self):
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
                         'The Parameter \(key_name\) was not provided.')

    def test_event_list(self):
        eventid1 = uuid.uuid4().hex
        eventid2 = uuid.uuid4().hex
        self.register_keystone_auth_fixture()

        h = {'Content-Type': 'text/plain; charset=UTF-8',
             'location': 'http://heat.example.com/stacks/myStack/60f83b5e'}
        self.requests.get('http://heat.example.com/stacks/myStack',
                          status_code=302,
                          headers=h)

        resp, resp_dict = fakes.mock_script_event_list(
            resource_name="myDeployment", rsrc_eventid1=eventid1,
            rsrc_eventid2=eventid2, fakehttp=False
        )

        self.requests.get('http://heat.example.com/stacks/myStack%2F60f83b5e/'
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
            '2013-12-05T14:14:31Z',
            '2013-12-05T14:14:32Z',
        ]

        for r in required:
            self.assertRegexpMatches(list_text, r)


class ShellTestNoMoxV3(ShellTestNoMox):

    def _set_fake_env(self):
        fake_env_kwargs = {'OS_NO_CLIENT_AUTH': 'True',
                           'HEAT_URL': 'http://heat.example.com'}
        fake_env_kwargs.update(FAKE_ENV_KEYSTONE_V3)
        self.set_fake_env(fake_env_kwargs)


class ShellTestEndpointType(TestCase):

    def setUp(self):
        super(ShellTestEndpointType, self).setUp()
        self.m = mox.Mox()
        self.m.StubOutWithMock(http, '_construct_http_client')
        self.m.StubOutWithMock(heatclient.v1.shell, 'do_stack_list')
        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_endpoint_type_public_url(self):
        self.register_keystone_auth_fixture()
        kwargs = {
            'auth_url': 'http://keystone.example.com:5000/',
            'session': mox.IgnoreArg(),
            'auth': mox.IgnoreArg(),
            'service_type': 'orchestration',
            'endpoint_type': 'publicURL',
            'region_name': '',
            'username': 'username',
            'password': 'password',
            'include_pass': False
        }
        http._construct_http_client(u'http://heat.example.com', **kwargs)
        heatclient.v1.shell.do_stack_list(mox.IgnoreArg(), mox.IgnoreArg())

        self.m.ReplayAll()
        heatclient.shell.main(('stack-list',))

    def test_endpoint_type_admin_url(self):
        self.register_keystone_auth_fixture()
        kwargs = {
            'auth_url': 'http://keystone.example.com:5000/',
            'session': mox.IgnoreArg(),
            'auth': mox.IgnoreArg(),
            'service_type': 'orchestration',
            'endpoint_type': 'adminURL',
            'region_name': '',
            'username': 'username',
            'password': 'password',
            'include_pass': False
        }
        http._construct_http_client(u'http://heat-admin.localdomain', **kwargs)
        heatclient.v1.shell.do_stack_list(mox.IgnoreArg(), mox.IgnoreArg())

        self.m.ReplayAll()
        heatclient.shell.main(('--os-endpoint-type=adminURL', 'stack-list',))

    def test_endpoint_type_internal_url(self):
        self.register_keystone_auth_fixture()
        self.useFixture(fixtures.EnvironmentVariable('OS_ENDPOINT_TYPE',
                                                     'internalURL'))
        kwargs = {
            'auth_url': 'http://keystone.example.com:5000/',
            'session': mox.IgnoreArg(),
            'auth': mox.IgnoreArg(),
            'service_type': 'orchestration',
            'endpoint_type': 'internalURL',
            'region_name': '',
            'username': 'username',
            'password': 'password',
            'include_pass': False
        }
        http._construct_http_client(u'http://heat.localdomain', **kwargs)
        heatclient.v1.shell.do_stack_list(mox.IgnoreArg(), mox.IgnoreArg())

        self.m.ReplayAll()
        heatclient.shell.main(('stack-list',))


class ShellTestCommon(ShellBase):

    def setUp(self):
        super(ShellTestCommon, self).setUp()
        self.client = http.SessionClient
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_help_unknown_command(self):
        self.assertRaises(exc.CommandError, self.shell, 'help foofoo')

    def test_help(self):
        required = [
            '^usage: heat',
            '(?m)^See "heat help COMMAND" for help on a specific command',
        ]
        for argstr in ['--help', 'help']:
            help_text = self.shell(argstr)
            for r in required:
                self.assertRegexpMatches(help_text, r)

    def test_command_help(self):
        output = self.shell('help help')
        self.assertIn('usage: heat help [<subcommand>]', output)
        subcommands = list(self.subcommands)
        for command in subcommands:
            if command.replace('_', '-') == 'bash-completion':
                continue
            output1 = self.shell('help %s' % command)
            output2 = self.shell('%s --help' % command)
            self.assertEqual(output1, output2)
            self.assertRegexpMatches(output1, '^usage: heat %s' % command)

    def test_debug_switch_raises_error(self):
        self.register_keystone_auth_fixture()
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks?', 'GET').AndRaise(exc.Unauthorized("FAIL"))
        else:
            self.client.json_request(
                'GET', '/stacks?').AndRaise(exc.Unauthorized("FAIL"))

        self.m.ReplayAll()

        args = ['--debug', 'stack-list']
        self.assertRaises(exc.Unauthorized, heatclient.shell.main, args)

    def test_dash_d_switch_raises_error(self):
        self.register_keystone_auth_fixture()
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks?', 'GET').AndRaise(exc.CommandError("FAIL"))
        else:
            self.client.json_request(
                'GET', '/stacks?').AndRaise(exc.CommandError("FAIL"))

        self.m.ReplayAll()

        args = ['-d', 'stack-list']
        self.assertRaises(exc.CommandError, heatclient.shell.main, args)

    def test_no_debug_switch_no_raises_errors(self):
        self.register_keystone_auth_fixture()
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks?', 'GET').AndRaise(exc.Unauthorized("FAIL"))
        else:
            self.client.json_request(
                'GET', '/stacks?').AndRaise(exc.Unauthorized("FAIL"))

        self.m.ReplayAll()

        args = ['stack-list']
        self.assertRaises(SystemExit, heatclient.shell.main, args)

    def test_help_on_subcommand(self):
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
                self.assertRegexpMatches(help_text, r)


class ShellTestUserPass(ShellBase):

    def setUp(self):
        super(ShellTestUserPass, self).setUp()
        if self.client is None:
            self.client = http.SessionClient
        self._set_fake_env()

    def _set_fake_env(self):
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_stack_list(self):
        self.register_keystone_auth_fixture()
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(list_text, r)
        self.assertNotRegexpMatches(list_text, 'parent')

    def test_stack_list_show_nested(self):
        self.register_keystone_auth_fixture()
        expected_url = '/stacks?%s' % parse.urlencode({
            'show_nested': True,
        }, True)
        fakes.script_heat_list(expected_url, show_nested=True,
                               client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(list_text, r)

    def test_stack_list_show_owner(self):
        self.register_keystone_auth_fixture()
        fakes.script_heat_list(client=self.client)
        self.m.ReplayAll()

        list_text = self.shell('stack-list --show-owner')

        required = [
            'stack_owner',
            'testowner',
        ]
        for r in required:
            self.assertRegexpMatches(list_text, r)

    def test_parsable_error(self):
        self.register_keystone_auth_fixture()
        message = "The Stack (bad) could not be found."
        resp_dict = {
            "explanation": "The resource could not be found.",
            "code": 404,
            "error": {
                "message": message,
                "type": "StackNotFound",
                "traceback": "",
            },
            "title": "Not Found"
        }

        fakes.script_heat_error(jsonutils.dumps(resp_dict),
                                client=self.client)

        self.m.ReplayAll()

        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertEqual("ERROR: " + message, str(e))

    def test_parsable_verbose(self):
        self.register_keystone_auth_fixture()
        message = "The Stack (bad) could not be found."
        resp_dict = {
            "explanation": "The resource could not be found.",
            "code": 404,
            "error": {
                "message": message,
                "type": "StackNotFound",
                "traceback": "<TRACEBACK>",
            },
            "title": "Not Found"
        }

        fakes.script_heat_error(jsonutils.dumps(resp_dict), self.client)

        self.m.ReplayAll()

        exc.verbose = 1

        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertIn(message, str(e))

    def test_parsable_malformed_error(self):
        self.register_keystone_auth_fixture()
        invalid_json = "ERROR: {Invalid JSON Error."
        fakes.script_heat_error(invalid_json, client=self.client)
        self.m.ReplayAll()
        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertEqual("ERROR: " + invalid_json, str(e))

    def test_parsable_malformed_error_missing_message(self):
        self.register_keystone_auth_fixture()
        missing_message = {
            "explanation": "The resource could not be found.",
            "code": 404,
            "error": {
                "type": "StackNotFound",
                "traceback": "",
            },
            "title": "Not Found"
        }

        fakes.script_heat_error(jsonutils.dumps(missing_message),
                                client=self.client)
        self.m.ReplayAll()

        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertEqual("ERROR: Internal Error", str(e))

    def test_parsable_malformed_error_missing_traceback(self):
        self.register_keystone_auth_fixture()
        message = "The Stack (bad) could not be found."
        resp_dict = {
            "explanation": "The resource could not be found.",
            "code": 404,
            "error": {
                "message": message,
                "type": "StackNotFound",
            },
            "title": "Not Found"
        }

        fakes.script_heat_error(jsonutils.dumps(resp_dict), client=self.client)
        self.m.ReplayAll()

        exc.verbose = 1

        e = self.assertRaises(exc.HTTPException, self.shell, "stack-show bad")
        self.assertEqual("ERROR: The Stack (bad) could not be found.\n",
                         str(e))

    def test_stack_show(self):
        self.register_keystone_auth_fixture()
        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1', 'GET').AndReturn(resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack/1').AndReturn((resp, resp_dict))

        self.m.ReplayAll()

        list_text = self.shell('stack-show teststack/1')

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
            self.assertRegexpMatches(list_text, r)

    def _output_fake_response(self):

        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z",
            "outputs": [
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
            ],
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))

        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1', 'GET').MultipleTimes().AndReturn(
                    resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack/1').MultipleTimes().AndReturn(
                    (resp, resp_dict))

        self.m.ReplayAll()

    def _error_output_fake_response(self):

        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z",
            "outputs": [
                {
                    "output_value": "null",
                    "output_key": "output1",
                    "description": "test output 1",
                    "output_error": "The Referenced Attribute (0 PublicIP) "
                                    "is incorrect."
                },
            ],
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))

        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1', 'GET').AndReturn(resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack/1').AndReturn((resp, resp_dict))

        self.m.ReplayAll()

    def test_output_list(self):
        self.register_keystone_auth_fixture()
        self._output_fake_response()
        list_text = self.shell('output-list teststack/1')
        for r in ['output1', 'output2', 'output_uni']:
            self.assertRegexpMatches(list_text, r)

    def test_output_show(self):
        self.register_keystone_auth_fixture()

        self._output_fake_response()
        list_text = self.shell('output-show teststack/1 output1')
        self.assertEqual('"value1"\n', list_text)

        list_text = self.shell('output-show  -F raw teststack/1 output1')
        self.assertEqual('value1\n', list_text)

        list_text = self.shell('output-show  -F raw teststack/1 output2')
        self.assertEqual('[\n  "output", \n  "value", \n  "2"\n]\n',
                         list_text)

        list_text = self.shell('output-show  -F json teststack/1 output2')
        self.assertEqual('[\n  "output", \n  "value", \n  "2"\n]\n',
                         list_text)

    def test_output_show_unicode(self):
        self.register_keystone_auth_fixture()
        self._output_fake_response()
        list_text = self.shell('output-show teststack/1 output_uni')
        self.assertEqual(u'"test\u2665"\n', list_text)

    def test_output_show_all(self):
        self.register_keystone_auth_fixture()
        self._output_fake_response()
        list_text = self.shell('output-show teststack/1 --all')
        for r in ['output1', 'value1', 'output2', 'test output unicode']:
            self.assertRegexpMatches(list_text, r)

    def test_output_show_missing_arg(self):
        self.register_keystone_auth_fixture()
        error = self.assertRaises(
            exc.CommandError, self.shell, 'output-show teststack/1')
        self.assertIn('either <OUTPUT NAME> or --all argument is needed.',
                      str(error))

    def test_output_show_error(self):
        self.register_keystone_auth_fixture()
        self._error_output_fake_response()
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'output-show teststack/1 output1')
        self.assertIn('The Referenced Attribute (0 PublicIP) is incorrect.',
                      str(error))

    def test_template_show_cfn(self):
        self.register_keystone_auth_fixture()
        template_data = open(os.path.join(TEST_VAR_DIR,
                                          'minimal.template')).read()
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            template_data)
        resp_dict = jsonutils.loads(template_data)
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/template', 'GET').AndReturn(resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack/template').AndReturn((resp,
                                                                resp_dict))

        self.m.ReplayAll()

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
            self.assertRegexpMatches(show_text, r)

    def test_template_show_cfn_unicode(self):
        self.register_keystone_auth_fixture()
        resp_dict = {"AWSTemplateFormatVersion": "2010-09-09",
                     "Description": u"test\u2665",
                     "Outputs": {},
                     "Resources": {},
                     "Parameters": {}}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/template', 'GET').AndReturn(resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack/template').AndReturn((resp,
                                                                resp_dict))

        self.m.ReplayAll()

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
            self.assertRegexpMatches(show_text, r)

    def test_template_show_hot(self):
        self.register_keystone_auth_fixture()
        resp_dict = {"heat_template_version": "2013-05-23",
                     "parameters": {},
                     "resources": {},
                     "outputs": {}}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/template', 'GET').AndReturn(resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack/template').AndReturn((resp,
                                                                resp_dict))

        self.m.ReplayAll()

        show_text = self.shell('template-show teststack')
        required = [
            "heat_template_version: '2013-05-23'",
            "outputs: {}",
            "parameters: {}",
            "resources: {}"
        ]
        for r in required:
            self.assertRegexpMatches(show_text, r)

    def _test_stack_preview(self, timeout=None, enable_rollback=False):
        self.register_keystone_auth_fixture()
        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "resources": {'1': {'name': 'r1'}},
            "creation_time": "2012-10-25T01:58:47Z",
            "timeout_mins": timeout,
            "disable_rollback": not(enable_rollback)
        }}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2',
             'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/preview', 'POST', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'POST', '/stacks/preview', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn((resp, resp_dict))

        self.m.ReplayAll()

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
        preview_text = self.shell(cmd)

        required = [
            'stack_name',
            'id',
            'teststack',
            '1',
            'resources',
            'timeout_mins',
            'disable_rollback'
        ]

        for r in required:
            self.assertRegexpMatches(preview_text, r)

    def test_stack_preview(self):
        self._test_stack_preview()

    def test_stack_preview_timeout(self):
        self._test_stack_preview(300, True)

    def test_stack_create(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks', 'POST', data=mox.IgnoreArg(),
                headers=headers).AndReturn(resp)
        else:
            self.client.json_request(
                'POST', '/stacks', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)
        self.m.ReplayAll()

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
            self.assertRegexpMatches(create_text, r)

    def test_create_success_with_poll(self):
        self.register_keystone_auth_fixture()

        stack_create_resp_dict = {"stack": {
            "id": "teststack2/2",
            "stack_name": "teststack2",
            "stack_status": 'CREATE_IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        stack_create_resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            jsonutils.dumps(stack_create_resp_dict))
        if self.client == http.SessionClient:
            headers = {}
            self.client.request(
                '/stacks', 'POST', data=mox.IgnoreArg(),
                headers=headers).AndReturn(stack_create_resp)
        else:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
            self.client.json_request(
                'POST', '/stacks', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn((stack_create_resp, None))
        fakes.script_heat_list(client=self.client)

        stack_show_resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        stack_show_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(stack_show_resp_dict))

        event_list_resp, event_list_resp_dict = fakes.mock_script_event_list(
            stack_name="teststack2")
        stack_id = 'teststack2'

        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2', 'GET').MultipleTimes().AndReturn(
                stack_show_resp)
            self.client.request(
                '/stacks/%s/events?sort_dir=asc' % stack_id, 'GET'
            ).MultipleTimes().AndReturn(event_list_resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack2').MultipleTimes().AndReturn(
                (stack_show_resp, stack_show_resp_dict))
            http.HTTPClient.json_request(
                'GET', '/stacks/%s/events?sort_dir=asc' % stack_id
            ).MultipleTimes().AndReturn((event_list_resp,
                                         event_list_resp_dict))
        self.m.ReplayAll()

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
            '14:14:30',  '2013-12-05', '0159dccd-65e1-46e8-a094-697d20b009e5',
            'CREATE_IN_PROGRESS', 'state changed',
            '14:14:31', '7fecaeed-d237-4559-93a5-92d5d9111205',
            'testresource',
            '14:14:32', 'e953547a-18f8-40a7-8e63-4ec4f509648b',
            'CREATE_COMPLETE',
            '14:14:33', '8f591a36-7190-4adb-80da-00191fe22388'
        ]

        for r in required:
            self.assertRegexpMatches(create_text, r)

    def test_create_failed_with_poll(self):
        self.register_keystone_auth_fixture()
        stack_create_resp_dict = {"stack": {
            "id": "teststack2/2",
            "stack_name": "teststack2",
            "stack_status": 'CREATE_IN_PROGRESS',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        stack_create_resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            jsonutils.dumps(stack_create_resp_dict))
        if self.client == http.SessionClient:
            headers = {}
            self.client.request(
                '/stacks', 'POST', data=mox.IgnoreArg(),
                headers=headers).AndReturn(stack_create_resp)
        else:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
            self.client.json_request(
                'POST', '/stacks', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn((stack_create_resp, None))
        fakes.script_heat_list(client=self.client)

        stack_show_resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        stack_show_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(stack_show_resp_dict))

        event_list_resp, event_list_resp_dict = fakes.mock_script_event_list(
            stack_name="teststack2", action="CREATE", final_state="FAILED")
        stack_id = 'teststack2'

        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2', 'GET').MultipleTimes().AndReturn(
                stack_show_resp)
            self.client.request(
                '/stacks/%s/events?sort_dir=asc' % stack_id, 'GET'
            ).MultipleTimes().AndReturn(event_list_resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack2').MultipleTimes().AndReturn(
                (stack_show_resp, stack_show_resp_dict))
            http.HTTPClient.json_request(
                'GET', '/stacks/%s/events?sort_dir=asc' % stack_id
            ).MultipleTimes().AndReturn((event_list_resp,
                                         event_list_resp_dict))

        self.m.ReplayAll()

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
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks', 'POST', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'POST', '/stacks', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.StubOutWithMock(utils, 'read_url_content')
        url = 'file://%s/private_key.env' % TEST_VAR_DIR
        utils.read_url_content(url).AndReturn('xxxxxx')
        self.m.ReplayAll()

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
            self.assertRegexpMatches(create_text, r)

    def test_stack_create_only_param_file(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks', 'POST', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'POST', '/stacks', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.StubOutWithMock(utils, 'read_url_content')
        url = 'file://%s/private_key.env' % TEST_VAR_DIR
        utils.read_url_content(url).AndReturn('xxxxxx')
        self.m.ReplayAll()

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
            self.assertRegexpMatches(create_text, r)

    def test_stack_create_timeout(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
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
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks', 'POST', data=expected_data,
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'POST', '/stacks', data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(create_text, r)

    def test_stack_update_timeout(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')

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
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'PUT',
                data=expected_data,
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'PUT', '/stacks/teststack2/2',
                data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_create_url(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        self.m.StubOutWithMock(request, 'urlopen')
        request.urlopen('http://no.where/minimal.template').AndReturn(
            six.StringIO('{"AWSTemplateFormatVersion" : "2010-09-09"}'))

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

        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks', 'POST', data=expected_data,
                headers=headers).AndReturn(resp)
        else:
            self.client.json_request(
                'POST', '/stacks', data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(create_text, r)

    def test_stack_create_object(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()

        raw_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {},
            template_data)

        if self.client == http.SessionClient:
            self.client.request(
                'http://no.where/container/minimal.template',
                'GET'
            ).AndReturn(raw_resp)
        else:
            self.client.raw_request(
                'GET',
                'http://no.where/container/minimal.template',
            ).AndReturn(raw_resp)

        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks', 'POST', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'POST', '/stacks', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn((resp, None))

        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(create_text, r)

    def test_stack_create_with_tags(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
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
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks', 'POST', data=expected_data,
                headers={}).AndReturn(resp)
        else:
            http.HTTPClient.json_request(
                'POST', '/stacks', data=expected_data,
                headers={'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(create_text, r)

    def test_stack_abandon(self):
        self.register_keystone_auth_fixture()

        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

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

        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        abandoned_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(abandoned_stack))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1', 'GET').AndReturn(resp)
            self.client.request(
                '/stacks/teststack/1/abandon',
                'DELETE').AndReturn(abandoned_resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/teststack/1').AndReturn((resp, resp_dict))
            http.HTTPClient.raw_request(
                'DELETE', '/stacks/teststack/1/abandon').AndReturn(
                    abandoned_resp)

        self.m.ReplayAll()
        abandon_resp = self.shell('stack-abandon teststack/1')
        self.assertEqual(abandoned_stack, jsonutils.loads(abandon_resp))

    def test_stack_abandon_with_outputfile(self):
        self.register_keystone_auth_fixture()

        resp_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

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

        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        abandoned_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(abandoned_stack))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1', 'GET').AndReturn(resp)
            self.client.request(
                '/stacks/teststack/1/abandon',
                'DELETE').AndReturn(abandoned_resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/teststack/1').AndReturn((resp, resp_dict))
            http.HTTPClient.raw_request(
                'DELETE', '/stacks/teststack/1/abandon').AndReturn(
                    abandoned_resp)

        self.m.ReplayAll()

        with tempfile.NamedTemporaryFile() as file_obj:
            self.shell('stack-abandon teststack/1 -O %s' % file_obj.name)
            result = jsonutils.loads(file_obj.read().decode())
            self.assertEqual(abandoned_stack, result)

    def test_stack_adopt(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack/1'},
            None)
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks', 'POST', data=mox.IgnoreArg(),
                headers=headers).AndReturn(resp)
        else:
            self.client.json_request(
                'POST', '/stacks', data=mox.IgnoreArg(),
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(adopt_text, r)

    def test_stack_adopt_without_data(self):
        self.register_keystone_auth_fixture()
        failed_msg = 'Need to specify --adopt-file'
        self.m.ReplayAll()
        self.shell_error('stack-adopt teststack ', failed_msg)

    def test_stack_update_enable_rollback(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        with open(template_file, 'rb') as f:
            template_data = jsonutils.load(f)
        expected_data = {'files': {},
                         'environment': {},
                         'template': template_data,
                         'disable_rollback': False,
                         'parameters': mox.IgnoreArg()
                         }
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'PUT',
                data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        else:
            self.client.json_request(
                'PUT', '/stacks/teststack2/2',
                data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)
        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_update_disable_rollback(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        with open(template_file, 'rb') as f:
            template_data = jsonutils.load(f)
        expected_data = {'files': {},
                         'environment': {},
                         'template': template_data,
                         'disable_rollback': True,
                         'parameters': mox.IgnoreArg()
                         }
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')

        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2', 'PUT',
                data=expected_data,
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'PUT', '/stacks/teststack2',
                data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)
        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_update_fault_rollback_value(self):
        self.register_keystone_auth_fixture()
        self.m.ReplayAll()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        self.shell_error('stack-update teststack2/2 '
                         '--rollback Foo '
                         '--template-file=%s' % template_file,
                         "Unrecognized value 'Foo', acceptable values are:"
                         )

    def test_stack_update_rollback_default(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        with open(template_file, 'rb') as f:
            template_data = jsonutils.load(f)
        expected_data = {'files': {},
                         'environment': {},
                         'template': template_data,
                         'parameters': mox.IgnoreArg()
                         }
        resp_update = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2', 'PUT',
                data=expected_data,
                headers=headers
            ).AndReturn(resp_update)
        else:
            self.client.json_request(
                'PUT', '/stacks/teststack2',
                data=expected_data,
                headers=headers
            ).AndReturn((resp_update, None))
        fakes.script_heat_list(client=self.client)
        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_update_with_existing_parameters(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {},
            'disable_rollback': False}
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'PATCH',
                data=expected_data,
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'PATCH', '/stacks/teststack2/2',
                data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_update_with_patched_existing_parameters(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'"KeyPairName': 'updated_key"'},
            'disable_rollback': False}
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'PATCH',
                data=expected_data,
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'PATCH', '/stacks/teststack2/2',
                data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_update_with_existing_and_default_parameters(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {},
            'clear_parameters': ['InstanceType', 'DBUsername',
                                 'DBPassword', 'KeyPairName',
                                 'LinuxDistribution'],
            'disable_rollback': False}
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'PATCH',
                data=expected_data,
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'PATCH', '/stacks/teststack2/2',
                data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_update_with_patched_and_default_parameters(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'"KeyPairName': 'updated_key"'},
            'clear_parameters': ['InstanceType', 'DBUsername',
                                 'DBPassword', 'KeyPairName',
                                 'LinuxDistribution'],
            'disable_rollback': False}
        if self.client is http.HTTPClient:
            headers = {'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        else:
            headers = {}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'PATCH',
                data=expected_data,
                headers=headers
            ).AndReturn(resp)
        else:
            self.client.json_request(
                'PATCH', '/stacks/teststack2/2',
                data=expected_data,
                headers=headers
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_update_with_tags(self):
        self.register_keystone_auth_fixture()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'"KeyPairName': 'updated_key"'},
            'disable_rollback': False,
            'tags': 'tag1,tag2'}
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'PATCH',
                data=expected_data, headers={}).AndReturn(resp)
        else:
            http.HTTPClient.json_request(
                'PATCH', '/stacks/teststack2/2',
                data=expected_data,
                headers={'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
            ).AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_text, r)

    def test_stack_update_dry_run(self):
        self.register_keystone_auth_fixture()

        resp_dict = {"stack": {
            "id": "2",
            "stack_name": "teststack2",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'GET').AndReturn(resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack2/2').AndReturn((resp, resp_dict))

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
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
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        expected_data = {
            'files': {},
            'environment': {},
            'template': jsonutils.loads(template_data),
            'parameters': {'"KeyPairName': 'updated_key"'},
            'disable_rollback': False,
            'existing': True}

        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2/preview', 'PUT',
                data=expected_data, headers={}).AndReturn(resp)
        else:
            http.HTTPClient.json_request(
                'PUT', '/stacks/teststack2/2/preview',
                data=expected_data,
                headers={'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
            ).AndReturn((resp, None))

        self.m.ReplayAll()

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
            self.assertRegexpMatches(update_preview_text, r)

    def test_stack_delete(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            204,
            'No Content',
            {},
            None)
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/2', 'DELETE').AndReturn(resp)
        else:
            self.client.raw_request(
                'DELETE', '/stacks/teststack2/2').AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

        delete_text = self.shell('stack-delete teststack2/2')

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(delete_text, r)

    def test_stack_delete_multiple(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            204,
            'No Content',
            {},
            None)
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack1/1', 'DELETE').AndReturn(resp)
            self.client.request(
                '/stacks/teststack2/2', 'DELETE').AndReturn(resp)
        else:
            self.client.raw_request(
                'DELETE', '/stacks/teststack1/1').AndReturn((resp, None))
            self.client.raw_request(
                'DELETE', '/stacks/teststack2/2').AndReturn((resp, None))
        fakes.script_heat_list(client=self.client)

        self.m.ReplayAll()

        delete_text = self.shell('stack-delete teststack1/1 teststack2/2')

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(delete_text, r)

    def test_build_info(self):
        self.register_keystone_auth_fixture()
        resp_dict = {
            'build_info': {
                'api': {'revision': 'api_revision'},
                'engine': {'revision': 'engine_revision'}
            }
        }
        resp_string = jsonutils.dumps(resp_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        response = (http_resp, resp_dict)
        if self.client == http.SessionClient:
            self.client.request('/build_info', 'GET').AndReturn(http_resp)
        else:
            self.client.json_request('GET', '/build_info').AndReturn(response)

        self.m.ReplayAll()

        build_info_text = self.shell('build-info')

        required = [
            'api',
            'engine',
            'revision',
            'api_revision',
            'engine_revision',
        ]
        for r in required:
            self.assertRegexpMatches(build_info_text, r)

    def test_stack_snapshot(self):
        self.register_keystone_auth_fixture()

        stack_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp_dict = {"snapshot": {
            "id": "1",
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request('/stacks/teststack/1', 'GET').AndReturn(
                fakes.FakeHTTPResponse(
                    200,
                    'OK',
                    {'content-type': 'application/json'},
                    jsonutils.dumps(stack_dict)))
            self.client.request(
                '/stacks/teststack/1/snapshots',
                'POST',
                data={}).AndReturn(resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/teststack/1').AndReturn(
                    (fakes.FakeHTTPResponse(
                        200,
                        'OK',
                        {'content-type': 'application/json'},
                        jsonutils.dumps(stack_dict)), stack_dict))
            http.HTTPClient.json_request(
                'POST',
                '/stacks/teststack/1/snapshots',
                data={}).AndReturn((resp, resp_dict))

        self.m.ReplayAll()
        resp = self.shell('stack-snapshot teststack/1')
        self.assertEqual(resp_dict, jsonutils.loads(resp))

    def test_snapshot_list(self):
        self.register_keystone_auth_fixture()

        stack_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp_dict = {"snapshots": [{
            "id": "2",
            "name": "snap1",
            "status": "COMPLETE",
            "status_reason": "",
            "data": {},
            "creation_time": "2014-12-05T01:25:52Z"
        }]}

        stack_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(stack_dict))
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1',
                'GET').AndReturn(stack_resp)
            self.client.request(
                '/stacks/teststack/1/snapshots',
                'GET').AndReturn(resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/teststack/1').AndReturn((stack_resp,
                                                         stack_dict))
            http.HTTPClient.json_request(
                'GET',
                '/stacks/teststack/1/snapshots').AndReturn((resp, resp_dict))

        self.m.ReplayAll()
        list_text = self.shell('snapshot-list teststack/1')

        required = [
            'id',
            'name',
            'status',
            'status_reason',
            'data',
            'creation_time',
            '2',
            'COMPLETE',
            '{}',
            '2014-12-05T01:25:52Z',
        ]
        for r in required:
            self.assertRegexpMatches(list_text, r)

    def test_snapshot_show(self):
        self.register_keystone_auth_fixture()

        stack_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp_dict = {"snapshot": {
            "id": "2",
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request('/stacks/teststack/1', 'GET').AndReturn(
                fakes.FakeHTTPResponse(
                    200,
                    'OK',
                    {'content-type': 'application/json'},
                    jsonutils.dumps(stack_dict)))
            self.client.request(
                '/stacks/teststack/1/snapshots/2',
                'GET').AndReturn(resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/teststack/1').AndReturn((
                    fakes.FakeHTTPResponse(
                        200,
                        'OK',
                        {'content-type': 'application/json'},
                        jsonutils.dumps(stack_dict)), stack_dict))
            http.HTTPClient.json_request(
                'GET',
                '/stacks/teststack/1/snapshots/2').AndReturn((resp, resp_dict))

        self.m.ReplayAll()
        resp = self.shell('snapshot-show teststack/1 2')
        self.assertEqual(resp_dict, jsonutils.loads(resp))

    def test_snapshot_delete(self):
        self.register_keystone_auth_fixture()

        stack_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp_dict = {"snapshot": {
            "id": "2",
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        resp = fakes.FakeHTTPResponse(
            204,
            'No Content',
            {'content-type': 'application/json'},
            jsonutils.dumps(stack_dict))
        second_resp = fakes.FakeHTTPResponse(
            204,
            'No Content',
            {},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1', 'GET').AndReturn(resp)
            self.client.request(
                '/stacks/teststack/1/snapshots/2',
                'DELETE').AndReturn(second_resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/teststack/1').AndReturn((resp, stack_dict))
            http.HTTPClient.raw_request(
                'DELETE',
                '/stacks/teststack/1/snapshots/2').AndReturn(second_resp)

        self.m.ReplayAll()
        resp = self.shell('snapshot-delete teststack/1 2')
        self.assertEqual("", resp)

    def test_stack_restore(self):
        self.register_keystone_auth_fixture()

        stack_dict = {"stack": {
            "id": "1",
            "stack_name": "teststack",
            "stack_status": 'CREATE_COMPLETE',
            "creation_time": "2012-10-25T01:58:47Z"
        }}

        stack_resp = fakes.FakeHTTPResponse(
            204,
            'No Content',
            {'content-type': 'application/json'},
            jsonutils.dumps(stack_dict))
        no_resp = fakes.FakeHTTPResponse(
            204,
            'No Content',
            {'content-type': 'application/json'},
            jsonutils.dumps({}))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1', 'GET').AndReturn(stack_resp)
            self.client.request(
                '/stacks/teststack/1/snapshots/2/restore',
                'POST').AndReturn(no_resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/teststack/1').AndReturn((stack_resp,
                                                         stack_dict))
            http.HTTPClient.json_request(
                'POST',
                '/stacks/teststack/1/snapshots/2/restore').AndReturn((no_resp,
                                                                     {}))

        self.m.ReplayAll()
        resp = self.shell('stack-restore teststack/1 2')
        self.assertEqual("", resp)


class ShellTestActions(ShellBase):

    def setUp(self):
        super(ShellTestActions, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_stack_cancel_update(self):
        self.register_keystone_auth_fixture()
        expected_data = {'cancel_update': None}
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/actions', 'POST',
                data=expected_data).AndReturn(resp)
            fakes.script_heat_list(client=self.client)
        else:
            http.HTTPClient.json_request(
                'POST', '/stacks/teststack2/actions',
                data=expected_data
            ).AndReturn((resp, None))
            fakes.script_heat_list()

        self.m.ReplayAll()

        update_text = self.shell('stack-cancel-update teststack2')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(update_text, r)

    def test_stack_check(self):
        self.register_keystone_auth_fixture()
        expected_data = {'check': None}
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/actions', 'POST',
                data=expected_data).AndReturn(resp)
            fakes.script_heat_list(client=self.client)
        else:
            http.HTTPClient.json_request(
                'POST', '/stacks/teststack2/actions',
                data=expected_data
            ).AndReturn((resp, None))
            fakes.script_heat_list()

        self.m.ReplayAll()

        check_text = self.shell('action-check teststack2')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(check_text, r)

    def test_stack_suspend(self):
        self.register_keystone_auth_fixture()
        expected_data = {'suspend': None}
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/actions', 'POST',
                data=expected_data
            ).AndReturn(resp)
            fakes.script_heat_list(client=self.client)
        else:
            http.HTTPClient.json_request(
                'POST', '/stacks/teststack2/actions',
                data=expected_data
            ).AndReturn((resp, None))
            fakes.script_heat_list()

        self.m.ReplayAll()

        suspend_text = self.shell('action-suspend teststack2')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(suspend_text, r)

    def test_stack_resume(self):
        self.register_keystone_auth_fixture()
        expected_data = {'resume': None}
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack2/actions', 'POST',
                data=expected_data
            ).AndReturn(resp)
            fakes.script_heat_list(client=self.client)
        else:
            http.HTTPClient.json_request(
                'POST', '/stacks/teststack2/actions',
                data=expected_data
            ).AndReturn((resp, None))
            fakes.script_heat_list()

        self.m.ReplayAll()

        resume_text = self.shell('action-resume teststack2')

        required = [
            'stack_name',
            'id',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(resume_text, r)


class ShellTestEvents(ShellBase):

    def setUp(self):
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
        self.register_keystone_auth_fixture()
        resp, resp_dict = fakes.mock_script_event_list(
            resource_name="aResource",
            rsrc_eventid1=self.event_id_one,
            rsrc_eventid2=self.event_id_two
        )
        stack_id = 'teststack/1'
        resource_name = 'testresource/1'
        http.SessionClient.request(
            '/stacks/%s/resources/%s/events?sort_dir=asc' % (
                parse.quote(stack_id, ''),
                parse.quote(encodeutils.safe_encode(
                    resource_name), '')), 'GET').AndReturn(resp)

        self.m.ReplayAll()

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
            '2013-12-05T14:14:31Z',
            '2013-12-05T14:14:32Z',
        ]
        for r in required:
            self.assertRegexpMatches(event_list_text, r)

    def test_stack_event_list_log(self):
        self.register_keystone_auth_fixture()
        resp, resp_dict = fakes.mock_script_event_list(
            resource_name="aResource",
            rsrc_eventid1=self.event_id_one,
            rsrc_eventid2=self.event_id_two
        )

        stack_id = 'teststack/1'
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/%s/events?sort_dir=asc' % stack_id,
                'GET').AndReturn(resp)
        else:
            http.HTTPClient.json_request(
                'GET',
                '/stacks/%s/events?sort_dir=asc' %
                stack_id).AndReturn((resp, resp_dict))

        self.m.ReplayAll()

        event_list_text = self.shell('event-list {0} --format log'.format(
            stack_id))

        expected = '14:14:31  2013-12-05  %s [aResource]: ' \
                   'CREATE_IN_PROGRESS  state changed\n' \
                   '14:14:32  2013-12-05  %s [aResource]: CREATE_COMPLETE  ' \
                   'state changed\n' % (self.event_id_one, self.event_id_two)

        self.assertEqual(expected, event_list_text)

    def test_event_show(self):
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
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        stack_id = 'teststack/1'
        resource_name = 'testresource/1'
        http.SessionClient.request(
            '/stacks/%s/resources/%s/events/%s' %
            (
                parse.quote(stack_id, ''),
                parse.quote(encodeutils.safe_encode(
                    resource_name), ''),
                parse.quote(self.event_id_one, '')
            ), 'GET').AndReturn(resp)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(event_list_text, r)


class ShellTestEventsNested(ShellBase):
    def setUp(self):
        super(ShellTestEventsNested, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_shell_nested_depth_invalid_xor(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'

        self.m.ReplayAll()

        error = self.assertRaises(
            exc.CommandError, self.shell,
            'event-list {0} --resource {1} --nested-depth 5'.format(
                stack_id, resource_name))
        self.assertIn('--nested-depth cannot be specified with --resource',
                      str(error))

    def test_shell_nested_depth_invalid_value(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'event-list {0} --nested-depth Z'.format(
                stack_id, resource_name))
        self.assertIn('--nested-depth invalid value Z', str(error))

    def test_shell_nested_depth_zero(self):
        self.register_keystone_auth_fixture()
        resp_dict = {"events": [{"id": 'eventid1'},
                                {"id": 'eventid2'}]}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        stack_id = 'teststack/1'

        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/%s/events?sort_dir=asc' % stack_id,
                'GET'
            ).AndReturn(resp)
        else:
            http.HTTPClient.json_request(
                'GET',
                '/stacks/%s/events?sort_dir=asc' % stack_id
            ).AndReturn((resp, resp_dict))
        self.m.ReplayAll()
        list_text = self.shell('event-list %s --nested-depth 0' % stack_id)
        required = ['id', 'eventid1', 'eventid2']
        for r in required:
            self.assertRegexpMatches(list_text, r)

    def _stub_event_list_response(self, stack_id, nested_id, timestamps):
        # Stub events for parent stack
        ev_resp_dict = {"events": [{"id": "p_eventid1",
                                    "event_time": timestamps[0]},
                                   {"id": "p_eventid2",
                                    "event_time": timestamps[3]}]}
        ev_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(ev_resp_dict))
        if self.client == http.SessionClient:
            self.client.request('/stacks/%s/events?sort_dir=asc' % stack_id,
                                'GET').AndReturn(ev_resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/%s/events?sort_dir=asc' % (
                    stack_id)).AndReturn((ev_resp, ev_resp_dict))

        # Stub resources for parent, including one nested
        res_resp_dict = {"resources": [
                         {"links": [{"href": "http://heat/foo", "rel": "self"},
                                    {"href": "http://heat/foo2",
                                     "rel": "resource"},
                                    {"href": "http://heat/%s" % nested_id,
                                     "rel": "nested"}],
                          "resource_type": "OS::Nested::Foo"}]}
        res_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(res_resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/%s/resources' % (
                    stack_id), 'GET').AndReturn(res_resp)

        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/%s/resources' % (
                    stack_id)).AndReturn((res_resp, res_resp_dict))

        # Stub the events for the nested stack
        nev_resp_dict = {"events": [{"id": 'n_eventid1',
                                     "event_time": timestamps[1]},
                                    {"id": 'n_eventid2',
                                     "event_time": timestamps[2]}]}
        nev_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(nev_resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/%s/events?sort_dir=asc' % (
                    nested_id), 'GET').AndReturn(nev_resp)
        else:
            http.HTTPClient.json_request(
                'GET', '/stacks/%s/events?sort_dir=asc' % (
                    nested_id)).AndReturn((nev_resp, nev_resp_dict))

    def test_shell_nested_depth(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        timestamps = ("2014-01-06T16:14:00Z",  # parent p_eventid1
                      "2014-01-06T16:15:00Z",  # nested n_eventid1
                      "2014-01-06T16:16:00Z",  # nested n_eventid2
                      "2014-01-06T16:17:00Z")  # parent p_eventid2
        self._stub_event_list_response(stack_id, nested_id, timestamps)
        self.m.ReplayAll()
        list_text = self.shell('event-list %s --nested-depth 1' % stack_id)
        required = ['id', 'p_eventid1', 'p_eventid2', 'n_eventid1',
                    'n_eventid2', 'stack_name', 'teststack', 'nested']
        for r in required:
            self.assertRegexpMatches(list_text, r)

        # Check event time sort/ordering
        self.assertRegexpMatches(list_text,
                                 "%s.*\n.*%s.*\n.*%s.*\n.*%s" % timestamps)

    def test_shell_nested_depth_marker(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        timestamps = ("2014-01-06T16:14:00Z",  # parent p_eventid1
                      "2014-01-06T16:15:00Z",  # nested n_eventid1
                      "2014-01-06T16:16:00Z",  # nested n_eventid2
                      "2014-01-06T16:17:00Z")  # parent p_eventid2
        self._stub_event_list_response(stack_id, nested_id, timestamps)
        self.m.ReplayAll()
        list_text = self.shell(
            'event-list %s --nested-depth 1 --marker n_eventid1' % stack_id)
        required = ['id', 'p_eventid2', 'n_eventid1', 'n_eventid2',
                    'stack_name', 'teststack', 'nested']
        for r in required:
            self.assertRegexpMatches(list_text, r)

        self.assertNotRegexpMatches(list_text, 'p_eventid1')

        self.assertRegexpMatches(list_text,
                                 "%s.*\n.*%s.*\n.*%s.*" % timestamps[1:])

    def test_shell_nested_depth_limit(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        timestamps = ("2014-01-06T16:14:00Z",  # parent p_eventid1
                      "2014-01-06T16:15:00Z",  # nested n_eventid1
                      "2014-01-06T16:16:00Z",  # nested n_eventid2
                      "2014-01-06T16:17:00Z")  # parent p_eventid2
        self._stub_event_list_response(stack_id, nested_id, timestamps)
        self.m.ReplayAll()
        list_text = self.shell(
            'event-list %s --nested-depth 1 --limit 2' % stack_id)
        required = ['id', 'p_eventid1', 'n_eventid1',
                    'stack_name', 'teststack', 'nested']
        for r in required:
            self.assertRegexpMatches(list_text, r)
        self.assertNotRegexpMatches(list_text, 'p_eventid2')
        self.assertNotRegexpMatches(list_text, 'n_eventid2')

        self.assertRegexpMatches(list_text,
                                 "%s.*\n.*%s.*\n" % timestamps[:2])


class ShellTestHookFunctions(ShellBase):
    def setUp(self):
        super(ShellTestHookFunctions, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def _stub_stack_response(self, stack_id, action='CREATE',
                             status='IN_PROGRESS'):
        # Stub parent stack show for status
        resp_dict = {"stack": {
            "id": stack_id.split("/")[1],
            "stack_name": stack_id.split("/")[0],
            "stack_status": '%s_%s' % (action, status),
            "creation_time": "2014-01-06T16:14:00Z",
        }}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/teststack/1', 'GET').AndReturn(resp)
        else:
            self.client.json_request(
                'GET', '/stacks/teststack/1').AndReturn((resp, resp_dict))

    def _stub_responses(self, stack_id, nested_id, action='CREATE'):
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
        ev_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(ev_resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/%s/events?sort_dir=asc' % (stack_id),
                'GET').AndReturn(ev_resp)
        else:
            self.client.json_request(
                'GET', '/stacks/%s/events?sort_dir=asc' % (
                    stack_id)).AndReturn((ev_resp, ev_resp_dict))

        # Stub resources for parent, including one nested
        res_resp_dict = {"resources": [
                         {"links": [{"href": "http://heat/foo", "rel": "self"},
                                    {"href": "http://heat/foo2",
                                     "rel": "resource"},
                                    {"href": "http://heat/%s" % nested_id,
                                     "rel": "nested"}],
                          "resource_type": "OS::Nested::Foo"}]}
        res_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(res_resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/%s/resources' % (stack_id),
                'GET').AndReturn(res_resp)
        else:
            self.client.json_request(
                'GET', '/stacks/%s/resources' % (
                    stack_id)).AndReturn((res_resp, res_resp_dict))

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
        nev_resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(nev_resp_dict))
        if self.client == http.SessionClient:
            self.client.request(
                '/stacks/%s/events?sort_dir=asc' % (nested_id),
                'GET').AndReturn(nev_resp)
        else:
            self.client.json_request(
                'GET', '/stacks/%s/events?sort_dir=asc' % (
                    nested_id)).AndReturn((nev_resp, nev_resp_dict))

    def test_hook_poll_pre_create(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        self._stub_responses(stack_id, nested_id, 'CREATE')
        self.m.ReplayAll()
        list_text = self.shell('hook-poll %s --nested-depth 1' % stack_id)
        hook_reason = 'CREATE paused until Hook pre-create is cleared'
        required = ['id', 'p_eventid2', 'stack_name', 'teststack', hook_reason]
        for r in required:
            self.assertRegexpMatches(list_text, r)
        self.assertNotRegexpMatches(list_text, 'p_eventid1')
        self.assertNotRegexpMatches(list_text, 'n_eventid1')
        self.assertNotRegexpMatches(list_text, 'n_eventid2')

    def test_hook_poll_pre_update(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        nested_id = 'nested/2'
        self._stub_responses(stack_id, nested_id, 'UPDATE')
        self.m.ReplayAll()
        list_text = self.shell('hook-poll %s --nested-depth 1' % stack_id)
        hook_reason = 'UPDATE paused until Hook pre-update is cleared'
        required = ['id', 'p_eventid2', 'stack_name', 'teststack', hook_reason]
        for r in required:
            self.assertRegexpMatches(list_text, r)
        self.assertNotRegexpMatches(list_text, 'p_eventid1')
        self.assertNotRegexpMatches(list_text, 'n_eventid1')
        self.assertNotRegexpMatches(list_text, 'n_eventid2')

    def test_hook_poll_bad_status(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        self._stub_stack_response(stack_id, status='COMPLETE')
        self.m.ReplayAll()
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'hook-poll %s --nested-depth 1' % stack_id)
        self.assertIn('Stack status CREATE_COMPLETE not IN_PROGRESS',
                      str(error))

    def test_shell_nested_depth_invalid_value(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        self.m.ReplayAll()
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'hook-poll %s --nested-depth Z' % stack_id)
        self.assertIn('--nested-depth invalid value Z', str(error))

    def test_hook_poll_clear_bad_status(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        self._stub_stack_response(stack_id, status='COMPLETE')
        self.m.ReplayAll()
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'hook-clear %s aresource' % stack_id)
        self.assertIn('Stack status CREATE_COMPLETE not IN_PROGRESS',
                      str(error))

    def test_hook_poll_clear_bad_action(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        self._stub_stack_response(stack_id, action='DELETE')
        self.m.ReplayAll()
        error = self.assertRaises(
            exc.CommandError, self.shell,
            'hook-clear %s aresource' % stack_id)
        self.assertIn('Unexpected stack status DELETE_IN_PROGRESS',
                      str(error))


class ShellTestResources(ShellBase):

    def setUp(self):
        super(ShellTestResources, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def _test_resource_list(self, with_resource_name):
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
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        stack_id = 'teststack/1'
        http.SessionClient.request(
            '/stacks/%s/resources' % (
                stack_id), 'GET').AndReturn(resp)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(resource_list_text, r)

    def test_resource_list(self):
        self._test_resource_list(True)

    def test_resource_list_no_resource_name(self):
        self._test_resource_list(False)

    def test_resource_list_empty(self):
        self.register_keystone_auth_fixture()
        resp_dict = {"resources": []}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        stack_id = 'teststack/1'
        http.SessionClient.request(
            '/stacks/%s/resources' % (
                stack_id), 'GET').AndReturn(resp)

        self.m.ReplayAll()

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

    def test_resource_list_nested(self):
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
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        stack_id = 'teststack/1'
        http.SessionClient.request(
            '/stacks/%s/resources?nested_depth=99' % (
                stack_id), 'GET').AndReturn(resp)

        self.m.ReplayAll()

        shell_cmd = 'resource-list {0} --nested-depth {1}'.format(stack_id, 99)
        resource_list_text = self.shell(shell_cmd)

        required = [
            'resource_name', 'foobar',
            'stack_name', 'foo',
        ]
        for field in required:
            self.assertRegexpMatches(resource_list_text, field)

    def test_resource_list_detail(self):
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
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        stack_id = 'teststack/1'
        http.SessionClient.request('/stacks/%s/resources?%s' % (
            stack_id,
            parse.urlencode({'with_detail': True}, True)
        ), 'GET').AndReturn(resp)

        self.m.ReplayAll()

        shell_cmd = 'resource-list {0} --with-detail'.format(stack_id)
        resource_list_text = self.shell(shell_cmd)

        required = [
            'resource_name', 'foobar',
            'stack_name', 'foo',
        ]
        for field in required:
            self.assertRegexpMatches(resource_list_text, field)

    def test_resource_show_with_attrs(self):
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
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        http.SessionClient.request(
            '/stacks/%s/resources/%s?with_attr=attr_a&with_attr=attr_b' %
            (
                parse.quote(stack_id, ''),
                parse.quote(encodeutils.safe_encode(
                    resource_name), '')
            ), 'GET').AndReturn(resp)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(resource_show_text, r)

    def test_resource_signal(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {},
            '')
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        http.SessionClient.request(
            '/stacks/%s/resources/%s/signal' %
            (
                parse.quote(stack_id, ''),
                parse.quote(encodeutils.safe_encode(
                    resource_name), '')
            ),
            'POST',
            data={'message': 'Content'}).AndReturn(resp)

        self.m.ReplayAll()

        text = self.shell(
            'resource-signal {0} {1} -D {{"message":"Content"}}'.format(
                stack_id, resource_name))
        self.assertEqual("", text)

    def test_resource_signal_no_data(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {},
            '')
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        http.SessionClient.request(
            '/stacks/%s/resources/%s/signal' %
            (
                parse.quote(stack_id, ''),
                parse.quote(encodeutils.safe_encode(
                    resource_name), '')
            ), 'POST', data=None).AndReturn(resp)

        self.m.ReplayAll()

        text = self.shell(
            'resource-signal {0} {1}'.format(stack_id, resource_name))
        self.assertEqual("", text)

    def test_resource_signal_no_json(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'

        self.m.ReplayAll()

        error = self.assertRaises(
            exc.CommandError, self.shell,
            'resource-signal {0} {1} -D [2'.format(
                stack_id, resource_name))
        self.assertIn('Data should be in JSON format', str(error))

    def test_resource_signal_no_dict(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'

        self.m.ReplayAll()

        error = self.assertRaises(
            exc.CommandError, self.shell,
            'resource-signal {0} {1} -D "message"'.format(
                stack_id, resource_name))
        self.assertEqual('Data should be a JSON dict', str(error))

    def test_resource_signal_both_data(self):
        self.register_keystone_auth_fixture()
        stack_id = 'teststack/1'
        resource_name = 'aResource'

        self.m.ReplayAll()

        error = self.assertRaises(
            exc.CommandError, self.shell,
            'resource-signal {0} {1} -D "message" -f foo'.format(
                stack_id, resource_name))
        self.assertEqual('Can only specify one of data and data-file',
                         str(error))

    def test_resource_signal_data_file(self):
        self.register_keystone_auth_fixture()
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {},
            '')
        stack_id = 'teststack/1'
        resource_name = 'aResource'
        http.SessionClient.request(
            '/stacks/%s/resources/%s/signal' %
            (
                parse.quote(stack_id, ''),
                parse.quote(encodeutils.safe_encode(
                    resource_name), '')
            ),
            'POST',
            data={'message': 'Content'}).AndReturn(resp)

        self.m.ReplayAll()

        with tempfile.NamedTemporaryFile() as data_file:
            data_file.write(b'{"message":"Content"}')
            data_file.flush()
            text = self.shell(
                'resource-signal {0} {1} -f {2}'.format(
                    stack_id, resource_name, data_file.name))
            self.assertEqual("", text)


class ShellTestResourceTypes(ShellBase):
    def setUp(self):
        super(ShellTestResourceTypes, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V3)

    def test_resource_type_template_yaml(self):
        self.register_keystone_auth_fixture()
        resp_dict = {"heat_template_version": "2013-05-23",
                     "parameters": {},
                     "resources": {},
                     "outputs": {}}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))

        http.SessionClient.request(
            '/resource_types/OS%3A%3ANova%3A%3AKeyPair/template'
            '?template_type=hot', 'GET'
        ).AndReturn(resp)

        self.m.ReplayAll()

        show_text = self.shell(
            'resource-type-template -F yaml -t hot OS::Nova::KeyPair')
        required = [
            "heat_template_version: '2013-05-23'",
            "outputs: {}",
            "parameters: {}",
            "resources: {}"
        ]
        for r in required:
            self.assertRegexpMatches(show_text, r)

    def test_resource_type_template_json(self):
        self.register_keystone_auth_fixture()
        resp_dict = {"AWSTemplateFormatVersion": "2013-05-23",
                     "Parameters": {},
                     "Resources": {},
                     "Outputs": {}}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))

        http.SessionClient.request(
            '/resource_types/OS%3A%3ANova%3A%3AKeyPair/template'
            '?template_type=cfn', 'GET'
        ).AndReturn(resp)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(show_text, r)


class ShellTestConfig(ShellBase):

    def setUp(self):
        super(ShellTestConfig, self).setUp()
        self._set_fake_env()

    def _set_fake_env(self):
        '''Patch os.environ to avoid required auth info.'''
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_config_create(self):
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
        resp_string = jsonutils.dumps(resp_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)

        self.m.StubOutWithMock(request, 'urlopen')
        request.urlopen('file:///tmp/defn').AndReturn(
            six.StringIO(yaml.safe_dump(definition, indent=2)))
        request.urlopen('file:///tmp/config_script').AndReturn(
            six.StringIO('the config script'))

        http.SessionClient.request(
            '/validate', 'POST', data=validate_template).AndReturn(http_resp)
        http.SessionClient.request(
            '/software_configs', 'POST', data=create_dict).AndReturn(http_resp)

        self.m.ReplayAll()

        text = self.shell('config-create -c /tmp/config_script '
                          '-g script -f /tmp/defn config_name')

        self.assertEqual(resp_dict['software_config'], jsonutils.loads(text))

    def test_config_show(self):
        self.register_keystone_auth_fixture()
        resp_dict = {'software_config': {
            'inputs': [],
            'group': 'script',
            'name': 'config_name',
            'outputs': [],
            'options': {},
            'config': 'the config script',
            'id': 'abcd'}}
        resp_string = jsonutils.dumps(resp_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        http.SessionClient.request(
            '/software_configs/abcd', 'GET').AndReturn(http_resp)
        http.SessionClient.request(
            '/software_configs/abcd', 'GET').AndReturn(http_resp)
        http.SessionClient.request(
            '/software_configs/abcde', 'GET').AndRaise(exc.HTTPNotFound())

        self.m.ReplayAll()

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
            self.assertRegexpMatches(text, r)

        self.assertEqual(
            'the config script\n',
            self.shell('config-show --config-only abcd'))
        self.assertRaises(exc.CommandError, self.shell, 'config-show abcde')

    def test_config_delete(self):
        self.register_keystone_auth_fixture()
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(204, 'OK', headers, None)
        http.SessionClient.request(
            '/software_configs/abcd', 'DELETE').AndReturn(http_resp)
        http.SessionClient.request(
            '/software_configs/qwer', 'DELETE').AndReturn(http_resp)
        http.SessionClient.request(
            '/software_configs/abcd', 'DELETE').AndRaise(exc.HTTPNotFound())
        http.SessionClient.request(
            '/software_configs/qwer', 'DELETE').AndRaise(exc.HTTPNotFound())

        self.m.ReplayAll()

        self.assertEqual('', self.shell('config-delete abcd qwer'))
        self.assertRaises(
            exc.CommandError, self.shell, 'config-delete abcd qwer')


class ShellTestDeployment(ShellBase):

    def setUp(self):
        super(ShellTestDeployment, self).setUp()
        self.client = http.SessionClient
        self._set_fake_env()

    def _set_fake_env(self):
        '''Patch os.environ to avoid required auth info.'''
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_deploy_create(self):
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

        config_string = jsonutils.dumps(config_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, config_string)
        response = (http_resp, config_dict)
        if self.client == http.SessionClient:
            http.SessionClient.request(
                '/software_configs/defg', 'GET').AndReturn(http_resp)
        else:
            self.client.json_request(
                'GET', '/software_configs/defg').AndReturn(response)

        derived_string = jsonutils.dumps(derived_dict)
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, derived_string)
        response = (http_resp, derived_dict)
        if self.client == http.SessionClient:
            http.SessionClient.request(
                '/software_configs', 'POST', data={}).AndReturn(http_resp)
        else:
            self.client.json_request(
                'POST', '/software_configs', data={}).AndReturn(response)

        resp_string = jsonutils.dumps(resp_dict)
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        response = (http_resp, resp_dict)
        if self.client == http.SessionClient:
            self.client.request(
                '/software_deployments', 'POST',
                data=deploy_data).AndReturn(http_resp)
        else:
            self.client.json_request(
                'POST',
                '/software_deployments', data=deploy_data).AndReturn(response)

        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, derived_string)
        response = (http_resp, derived_dict)
        if self.client == http.SessionClient:
            http.SessionClient.request(
                '/software_configs', 'POST', data={}).AndReturn(http_resp)
        else:
            self.client.json_request(
                'POST', '/software_configs', data={}).AndReturn(response)

        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        response = (http_resp, resp_dict)
        if self.client == http.SessionClient:
            self.client.request(
                '/software_deployments', 'POST',
                data=deploy_data).AndReturn(http_resp)
            self.client.request(
                '/software_configs/defgh', 'GET').AndRaise(
                    exc.HTTPNotFound())
        else:
            self.client.json_request(
                'POST', '/software_deployments').AndReturn(response)
            self.client.json_request(
                'GET', '/software_configs/defgh').AndRaise(
                    exc.HTTPNotFound())

        self.m.ReplayAll()

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
            self.assertRegexpMatches(text, r)

        text = self.shell('deployment-create -sinst01 xxx')
        for r in required:
            self.assertRegexpMatches(text, r)

        self.assertRaises(exc.CommandError, self.shell,
                          'deployment-create -c defgh -s inst01 yyy')
        self.m.VerifyAll()

    def test_deploy_list(self):
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
        resp_string = jsonutils.dumps(resp_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        response = (http_resp, resp_dict)
        if self.client == http.SessionClient:
            self.client.request(
                '/software_deployments?', 'GET').AndReturn(http_resp)
            self.client.request(
                '/software_deployments?server_id=123',
                'GET').AndReturn(http_resp)
        else:
            self.client.json_request(
                'GET', '/software_deployments?').AndReturn(response)
            self.client.json_request(
                'GET',
                '/software_deployments?server_id=123').AndReturn(response)

        self.m.ReplayAll()

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
            self.assertRegexpMatches(list_text, r)
        self.assertNotRegexpMatches(list_text, 'parent')

        list_text = self.shell('deployment-list -s 123')

        for r in required:
            self.assertRegexpMatches(list_text, r)
        self.assertNotRegexpMatches(list_text, 'parent')

    def test_deploy_show(self):
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

        resp_string = jsonutils.dumps(resp_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        response = (http_resp, resp_dict)
        if self.client == http.SessionClient:
            self.client.request(
                '/software_deployments/defg', 'GET').AndReturn(http_resp)
            self.client.request(
                '/software_deployments/defgh', 'GET').AndRaise(
                    exc.HTTPNotFound())
        else:
            self.client.json_request(
                'GET', '/software_deployments/defg').AndReturn(response)
            self.client.json_request(
                'GET', '/software_deployments/defgh').AndRaise(
                    exc.HTTPNotFound())

        self.m.ReplayAll()

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
            self.assertRegexpMatches(text, r)
        self.assertRaises(exc.CommandError, self.shell,
                          'deployment-show defgh')

    def test_deploy_delete(self):
        self.register_keystone_auth_fixture()
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(204, 'OK', headers, None)
        response = (http_resp, '')
        if self.client == http.SessionClient:
            self.client.request(
                '/software_deployments/defg',
                'DELETE').AndReturn(http_resp)
            self.client.request(
                '/software_deployments/qwer',
                'DELETE').AndReturn(http_resp)
            self.client.request(
                '/software_deployments/defg',
                'DELETE').AndRaise(exc.HTTPNotFound())
            self.client.request(
                '/software_deployments/qwer',
                'DELETE').AndRaise(exc.HTTPNotFound())
        else:
            self.client.raw_request(
                'DELETE', '/software_deployments/defg').AndReturn(response)
            self.client.raw_request(
                'DELETE', '/software_deployments/qwer').AndReturn(response)
            self.client.raw_request(
                'DELETE',
                '/software_deployments/defg').AndRaise(exc.HTTPNotFound())
            self.client.raw_request(
                'DELETE',
                '/software_deployments/qwer').AndRaise(exc.HTTPNotFound())

        self.m.ReplayAll()

        self.assertEqual('', self.shell('deployment-delete defg qwer'))
        self.assertRaises(exc.CommandError, self.shell,
                          'deployment-delete defg qwer')

    def test_deploy_metadata(self):
        self.register_keystone_auth_fixture()
        resp_dict = {'metadata': [
            {'id': 'abcd'},
            {'id': 'defg'}
        ]}

        resp_string = jsonutils.dumps(resp_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        response = (http_resp, resp_dict)
        if self.client == http.SessionClient:
            self.client.request(
                '/software_deployments/metadata/aaaa',
                'GET').AndReturn(http_resp)
        else:
            self.client.json_request(
                'GET', '/software_deployments/metadata/aaaa').AndReturn(
                    response)

        self.m.ReplayAll()

        build_info_text = self.shell('deployment-metadata-show aaaa')

        required = [
            'abcd',
            'defg',
            'id',
        ]
        for r in required:
            self.assertRegexpMatches(build_info_text, r)

    def test_deploy_output_show(self):
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

        resp_string = jsonutils.dumps(resp_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        response = (http_resp, resp_dict)
        if self.client == http.SessionClient:
            self.client.request(
                '/software_deployments/defgh', 'GET').AndRaise(
                    exc.HTTPNotFound())
            self.client.request(
                '/software_deployments/defg', 'GET').MultipleTimes().AndReturn(
                    http_resp)
        else:
            self.client.json_request(
                'GET', '/software_deployments/defgh').AndRaise(
                    exc.HTTPNotFound())
            self.client.json_request(
                'GET', '/software_deployments/defg').MultipleTimes().AndReturn(
                    response)

        self.m.ReplayAll()

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
        super(ShellTestBuildInfo, self).setUp()
        self._set_fake_env()

    def _set_fake_env(self):
        '''Patch os.environ to avoid required auth info.'''
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_build_info(self):
        self.register_keystone_auth_fixture()
        resp_dict = {
            'build_info': {
                'api': {'revision': 'api_revision'},
                'engine': {'revision': 'engine_revision'}
            }
        }
        resp_string = jsonutils.dumps(resp_dict)
        headers = {'content-type': 'application/json'}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        response = http_resp
        http.SessionClient.request(
            '/build_info', 'GET').AndReturn(response)

        self.m.ReplayAll()

        build_info_text = self.shell('build-info')

        required = [
            'api',
            'engine',
            'revision',
            'api_revision',
            'engine_revision',
        ]
        for r in required:
            self.assertRegexpMatches(build_info_text, r)


class ShellTestToken(ShellTestUserPass):

    # Rerun all ShellTestUserPass test with token auth
    def setUp(self):
        self.token = 'a_token'
        super(ShellTestToken, self).setUp()

    def _set_fake_env(self):
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
        self.set_fake_env(FAKE_ENV_KEYSTONE_V3)


class ShellTestStandaloneToken(ShellTestUserPass):

    # Rerun all ShellTestUserPass test in standalone mode, where we
    # specify --os-no-client-auth, a token and Heat endpoint
    def setUp(self):
        self.token = 'a_token'
        super(ShellTestStandaloneToken, self).setUp()
        self.client = http.HTTPClient

    def _set_fake_env(self):
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

    def test_bad_template_file(self):
        self.register_keystone_auth_fixture()
        failed_msg = 'Error parsing template '

        with tempfile.NamedTemporaryFile() as bad_json_file:
            bad_json_file.write(b"{foo:}")
            bad_json_file.flush()
            self.shell_error("stack-create ts -f %s" % bad_json_file.name,
                             failed_msg)

        with tempfile.NamedTemporaryFile() as bad_json_file:
            bad_json_file.write(b'{"foo": None}')
            bad_json_file.flush()
            self.shell_error("stack-create ts -f %s" % bad_json_file.name,
                             failed_msg)

    def test_commandline_args_passed_to_requests(self):
        """Check that we have sent the proper arguments to requests."""
        self.register_keystone_auth_fixture()

        # we need a mock for 'request' to check whether proper arguments
        # sent to request in the form of HTTP headers. So unset
        # stubs(json_request, raw_request) and create a new mock for request.
        self.m.UnsetStubs()
        self.m.StubOutWithMock(requests, 'request')

        # Record a 200
        mock_conn = http.requests.request(
            'GET', 'http://no.where/stacks?',
            allow_redirects=False,
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json',
                     'X-Auth-Token': self.token,
                     'X-Auth-Url': BASE_URL,
                     'User-Agent': 'python-heatclient'})
        resp_dict = {"stacks": [
            {
                "id": "1",
                "stack_name": "teststack",
                "stack_owner": "testowner",
                "project": "testproject",
                "stack_status": 'CREATE_COMPLETE',
                "creation_time": "2014-10-15T01:58:47Z"
            }]}
        mock_conn.AndReturn(
            fakes.FakeHTTPResponse(
                200, 'OK',
                {'content-type': 'application/json'},
                jsonutils.dumps(resp_dict)))

        # Replay, create client, assert
        self.m.ReplayAll()
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
            self.assertRegexpMatches(list_text, r)
        self.assertNotRegexpMatches(list_text, 'parent')


class MockShellBase(TestCase):

    def setUp(self):
        super(MockShellBase, self).setUp()
        self.jreq_mock = self.patch(
            'heatclient.common.http.HTTPClient.json_request')
        self.session_jreq_mock = self.patch(
            'heatclient.common.http.SessionClient.request')

        # Some tests set exc.verbose = 1, so reset on cleanup
        def unset_exc_verbose():
            exc.verbose = 0

        self.addCleanup(unset_exc_verbose)

    def shell(self, argstr):
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
        super(MockShellTestUserPass, self).setUp()
        self._set_fake_env()

    def _set_fake_env(self):
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def test_stack_list_with_args(self):
        self.register_keystone_auth_fixture()
        self.jreq_mock.return_value = fakes.mock_script_heat_list()
        self.session_jreq_mock.return_value = fakes.mock_script_heat_list()[0]

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
                               ' --show-hidden')

        required = [
            'stack_owner',
            'project',
            'testproject',
            'teststack',
            'teststack2',
        ]
        for r in required:
            self.assertRegexpMatches(list_text, r)
        self.assertNotRegexpMatches(list_text, 'parent')

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
                               'show_hidden': ['True']}
        self.assertEqual(expected_query_dict, query_params)


class MockShellTestToken(MockShellTestUserPass):

    # Rerun all ShellTestUserPass test with token auth
    def setUp(self):
        self.token = 'a_token'
        super(MockShellTestToken, self).setUp()

    def _set_fake_env(self):
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
        self.set_fake_env(FAKE_ENV_KEYSTONE_V3)


class MockShellTestStandaloneToken(MockShellTestUserPass):

    # Rerun all ShellTestUserPass test in standalone mode, where we
    # specify --os-no-client-auth, a token and Heat endpoint
    def setUp(self):
        self.token = 'a_token'
        super(MockShellTestStandaloneToken, self).setUp()

    def _set_fake_env(self):
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
        super(ShellTestManageService, self).setUp()
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def _set_fake_env(self):
        '''Patch os.environ to avoid required auth info.'''
        self.set_fake_env(FAKE_ENV_KEYSTONE_V2)

    def _test_error_case(self, code, message):
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
        (http.SessionClient.request('/services', 'GET').
         AndRaise(exc.from_response(resp)))

        exc.verbose = 1

        self.m.ReplayAll()
        e = self.assertRaises(exc.HTTPException,
                              self.shell, "service-list")
        self.assertIn(message, str(e))

    def test_service_list(self):
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
        resp_string = jsonutils.dumps(resp_dict)
        headers = {}
        http_resp = fakes.FakeHTTPResponse(200, 'OK', headers, resp_string)
        http.SessionClient.request('/services', 'GET').AndReturn(http_resp)

        self.m.ReplayAll()
        services_text = self.shell('service-list')

        required = [
            'hostname', 'binary', 'engine_id', 'host',
            'topic', 'updated_at', 'status'
        ]
        for r in required:
            self.assertRegexpMatches(services_text, r)

    def test_service_list_503(self):
        self._test_error_case(
            message='All heat engines are down',
            code=503)

    def test_service_list_403(self):
        self._test_error_case(
            message=('You are not authorized to '
                     'complete this action'),
            code=403)
