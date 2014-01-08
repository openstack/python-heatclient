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
import re
import six
import sys
import yaml

import fixtures
import httplib2
import tempfile
import testscenarios
import testtools

from heatclient.openstack.common import jsonutils
from heatclient.openstack.common.py3kcompat import urlutils
from heatclient.openstack.common import strutils
from mox3 import mox

from keystoneclient.v2_0 import client as ksclient

from heatclient.common import http
from heatclient import exc
import heatclient.shell
from heatclient.tests import fakes
from heatclient.v1 import shell as v1shell


load_tests = testscenarios.load_tests_apply_scenarios
TEST_VAR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'var'))


class TestCase(testtools.TestCase):

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
        if isinstance(expected_regexp, basestring):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(text):
            msg = msg or "Regexp didn't match"
            msg = '%s: %r not found in %r' % (
                msg, expected_regexp.pattern, text)
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
            err='You must provide a tenant_id')),
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
            err='You must provide a tenant_id')),
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
        ('create', dict(
            command='create ts -P "a!b"',
            err='Malformed parameter')),
        ('stack-create', dict(
            command='stack-create ts -P "ab"',
            err='Malformed parameter')),
        ('update', dict(
            command='update ts -P "a~b"',
            err='Malformed parameter')),
        ('stack-update', dict(
            command='stack-update ts -P "a-b"',
            err='Malformed parameter')),
        ('validate', dict(
            command='validate -P "a=b;c"',
            err='Malformed parameter')),
        ('template-validate', dict(
            command='template-validate -P "a$b"',
            err='Malformed parameter')),
    ]

    def setUp(self):
        super(ShellParamValidationTest, self).setUp()
        self.m = mox.Mox()
        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def test_bad_parameters(self):
        self.m.StubOutWithMock(ksclient, 'Client')
        self.m.StubOutWithMock(http.HTTPClient, 'json_request')
        fakes.script_keystone_client()

        self.m.ReplayAll()
        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
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
        self.m.StubOutWithMock(ksclient, 'Client')
        self.m.StubOutWithMock(http.HTTPClient, 'json_request')
        fakes.script_keystone_client()
        failed_msg = 'Unable to authenticate user with credentials provided'
        http.HTTPClient.json_request(
            'GET', '/stacks?').AndRaise(exc.Unauthorized(failed_msg))

        self.m.ReplayAll()
        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.set_fake_env(fake_env)
        self.shell_error('stack-list', failed_msg)

    def test_stack_create_validation(self):
        self.m.StubOutWithMock(ksclient, 'Client')
        self.m.StubOutWithMock(http.HTTPClient, 'json_request')
        fakes.script_keystone_client()

        self.m.ReplayAll()
        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.set_fake_env(fake_env)
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
        self.m.StubOutWithMock(ksclient, 'Client')
        self.m.StubOutWithMock(http.HTTPClient, 'json_request')
        self.m.StubOutWithMock(http.HTTPClient, 'raw_request')
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
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(exc_value.code, 0)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out


class ShellTestCommon(ShellBase):

    def setUp(self):
        super(ShellTestCommon, self).setUp()

    def test_help_unknown_command(self):
        self.assertRaises(exc.CommandError, self.shell, 'help foofoo')

    def test_debug(self):
        httplib2.debuglevel = 0
        self.shell('--debug help')
        self.assertEqual(httplib2.debuglevel, 1)

    def test_help(self):
        required = [
            '^usage: heat',
            '(?m)^See "heat help COMMAND" for help on a specific command',
        ]
        for argstr in ['--help', 'help']:
            help_text = self.shell(argstr)
            for r in required:
                self.assertRegexpMatches(help_text, r)

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
        self._set_fake_env()

    # Patch os.environ to avoid required auth info.
    def _set_fake_env(self):
        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.set_fake_env(fake_env)

    def _script_keystone_client(self):
        fakes.script_keystone_client()

    def test_stack_list(self):
        self._script_keystone_client()
        fakes.script_heat_list()

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

    def test_parsable_error(self):
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

        self._script_keystone_client()
        fakes.script_heat_error(jsonutils.dumps(resp_dict))

        self.m.ReplayAll()

        try:
            self.shell("stack-show bad")
        except exc.HTTPException as e:
            self.assertEqual(str(e), "ERROR: " + message)

    def test_parsable_verbose(self):
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

        self._script_keystone_client()
        fakes.script_heat_error(jsonutils.dumps(resp_dict))

        self.m.ReplayAll()

        exc.verbose = 1

        try:
            self.shell("stack-show bad")
        except exc.HTTPException as e:
            expect = 'ERROR: The Stack (bad) could not be found.\n<TRACEBACK>'
            self.assertEqual(str(e), expect)

    def test_parsable_malformed_error(self):
        invalid_json = "ERROR: {Invalid JSON Error."
        self._script_keystone_client()
        fakes.script_heat_error(invalid_json)
        self.m.ReplayAll()

        try:
            self.shell("stack-show bad")
        except exc.HTTPException as e:
            self.assertEqual(str(e), "ERROR: " + invalid_json)

    def test_parsable_malformed_error_missing_message(self):
        missing_message = {
            "explanation": "The resource could not be found.",
            "code": 404,
            "error": {
                "type": "StackNotFound",
                "traceback": "",
            },
            "title": "Not Found"
        }

        self._script_keystone_client()
        fakes.script_heat_error(jsonutils.dumps(missing_message))
        self.m.ReplayAll()

        try:
            self.shell("stack-show bad")
        except exc.HTTPException as e:
            self.assertEqual(str(e), "ERROR: Internal Error")

    def test_parsable_malformed_error_missing_traceback(self):
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

        self._script_keystone_client()
        fakes.script_heat_error(jsonutils.dumps(resp_dict))
        self.m.ReplayAll()

        exc.verbose = 1

        try:
            self.shell("stack-show bad")
        except exc.HTTPException as e:
            self.assertEqual(str(e),
                             "ERROR: The Stack (bad) could not be found.\n")

    def test_stack_show(self):
        self._script_keystone_client()
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
        http.HTTPClient.json_request(
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

    def test_template_show_cfn(self):
        self._script_keystone_client()
        template_data = open(os.path.join(TEST_VAR_DIR,
                                          'minimal.template')).read()
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            template_data)
        resp_dict = jsonutils.loads(template_data)
        http.HTTPClient.json_request(
            'GET', '/stacks/teststack/template').AndReturn((resp, resp_dict))

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

    def test_template_show_hot(self):
        self._script_keystone_client()
        resp_dict = {"heat_template_version": "2013-05-23",
                     "parameters": {},
                     "resources": {},
                     "outputs": {}}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        http.HTTPClient.json_request(
            'GET', '/stacks/teststack/template').AndReturn((resp, resp_dict))

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

    def test_stack_create(self):
        self._script_keystone_client()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        http.HTTPClient.json_request(
            'POST', '/stacks', body=mox.IgnoreArg(),
            headers={'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        ).AndReturn((resp, None))
        fakes.script_heat_list()

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

    def test_stack_create_url(self):

        self._script_keystone_client()
        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        http.HTTPClient.json_request(
            'POST', '/stacks', body=mox.IgnoreArg(),
            headers={'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        ).AndReturn((resp, None))
        fakes.script_heat_list()

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

        self._script_keystone_client()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        http.HTTPClient.raw_request(
            'GET',
            'http://no.where/container/minimal.template',
        ).AndReturn(template_data)

        resp = fakes.FakeHTTPResponse(
            201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        http.HTTPClient.json_request(
            'POST', '/stacks', body=mox.IgnoreArg(),
            headers={'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        ).AndReturn((resp, None))

        fakes.script_heat_list()

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

    def test_stack_update(self):
        self._script_keystone_client()
        resp = fakes.FakeHTTPResponse(
            202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        http.HTTPClient.json_request(
            'PUT', '/stacks/teststack2/2',
            body=mox.IgnoreArg(),
            headers={'X-Auth-Key': 'password', 'X-Auth-User': 'username'}
        ).AndReturn((resp, None))
        fakes.script_heat_list()

        self.m.ReplayAll()

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        create_text = self.shell(
            'stack-update teststack2/2 '
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
            self.assertRegexpMatches(create_text, r)

    def test_stack_delete(self):
        self._script_keystone_client()
        resp = fakes.FakeHTTPResponse(
            204,
            'No Content',
            {},
            None)
        http.HTTPClient.raw_request(
            'DELETE', '/stacks/teststack2/2',
        ).AndReturn((resp, None))
        fakes.script_heat_list()

        self.m.ReplayAll()

        create_text = self.shell('stack-delete teststack2/2')

        required = [
            'stack_name',
            'id',
            'teststack',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(create_text, r)


class ShellTestEvents(ShellBase):
    def setUp(self):
        super(ShellTestEvents, self).setUp()
        self._set_fake_env()

    # Patch os.environ to avoid required auth info.
    def _set_fake_env(self):
        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.set_fake_env(fake_env)

    def _script_keystone_client(self):
        fakes.script_keystone_client()

    scenarios = [
        ('integer_id', dict(
            event_id_one='24',
            event_id_two='42')),
        ('uuid_id', dict(
            event_id_one='3d68809e-c4aa-4dc9-a008-933823d2e44f',
            event_id_two='43b68bae-ed5d-4aed-a99f-0b3d39c2418a'))]

    def test_event_list(self):
        self._script_keystone_client()
        resp_dict = {"events": [
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
                      "resource_status": "CREATE_IN_PROGRESS",
                      "resource_status_reason": "state changed"},
                     {"event_time": "2013-12-05T14:14:30Z",
                      "id": self.event_id_two,
                      "links": [{"href": "http://heat.example.com:8004/foo",
                                 "rel": "self"},
                                {"href": "http://heat.example.com:8004/foo2",
                                 "rel": "resource"},
                                {"href": "http://heat.example.com:8004/foo3",
                                 "rel": "stack"}],
                      "logical_resource_id": "aResource",
                      "physical_resource_id":
                      "bce15ec4-8919-4a02-8a90-680960fb3731",
                      "resource_name": "aResource",
                      "resource_status": "CREATE_COMPLETE",
                      "resource_status_reason": "state changed"}]}
        resp = fakes.FakeHTTPResponse(
            200,
            'OK',
            {'content-type': 'application/json'},
            jsonutils.dumps(resp_dict))
        stack_id = 'teststack/1'
        resource_name = 'testresource/1'
        http.HTTPClient.json_request(
            'GET', '/stacks/%s/resources/%s/events' % (
                urlutils.quote(stack_id, ''),
                urlutils.quote(strutils.safe_encode(
                    resource_name), ''))).AndReturn((resp, resp_dict))

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
            '2013-12-05T14:14:30Z',
            '2013-12-05T14:14:30Z',
        ]
        for r in required:
            self.assertRegexpMatches(event_list_text, r)

    def test_event_show(self):
        self._script_keystone_client()
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
        http.HTTPClient.json_request(
            'GET', '/stacks/%s/resources/%s/events/%s' %
            (
                urlutils.quote(stack_id, ''),
                urlutils.quote(strutils.safe_encode(
                    resource_name), ''),
                urlutils.quote(self.event_id_one, '')
            )).AndReturn((resp, resp_dict))

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


class ShellTestToken(ShellTestUserPass):

    # Rerun all ShellTestUserPass test with token auth
    def setUp(self):
        self.token = 'a_token'
        super(ShellTestToken, self).setUp()

    def _set_fake_env(self):
        fake_env = {
            'OS_AUTH_TOKEN': self.token,
            'OS_TENANT_ID': 'tenant_id',
            'OS_AUTH_URL': 'http://no.where',
            # Note we also set username/password, because create/update
            # pass them even if we have a token to support storing credentials
            # Hopefully at some point we can remove this and move to only
            # storing trust id's in heat-engine instead..
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password'
        }
        self.set_fake_env(fake_env)

    def _script_keystone_client(self):
        fakes.script_keystone_client(token=self.token)


class ShellTestStandaloneToken(ShellTestUserPass):

    # Rerun all ShellTestUserPass test in standalone mode, where we
    # specify --os-no-client-auth, a token and Heat endpoint
    def setUp(self):
        self.token = 'a_token'
        super(ShellTestStandaloneToken, self).setUp()

    def _set_fake_env(self):
        fake_env = {
            'OS_AUTH_TOKEN': self.token,
            'OS_NO_CLIENT_AUTH': 'True',
            'HEAT_URL': 'http://no.where',
            # Note we also set username/password, because create/update
            # pass them even if we have a token to support storing credentials
            # Hopefully at some point we can remove this and move to only
            # storing trust id's in heat-engine instead..
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password'
        }
        self.set_fake_env(fake_env)

    def _script_keystone_client(self):
        # The StanaloneMode shouldn't need any keystoneclient stubbing
        pass

    def test_bad_template_file(self):
        failed_msg = 'Cannot parse template file:'

        with tempfile.NamedTemporaryFile() as bad_json_file:
            bad_json_file.write("{foo:}")
            bad_json_file.flush()
            self.shell_error("stack-create ts -f %s" % bad_json_file.name,
                             failed_msg)

        with tempfile.NamedTemporaryFile() as bad_json_file:
            bad_json_file.write('{"foo": None}')
            bad_json_file.flush()
            self.shell_error("stack-create ts -f %s" % bad_json_file.name,
                             failed_msg)


class ShellEnvironmentTest(TestCase):

    def setUp(self):
        super(ShellEnvironmentTest, self).setUp()
        self.m = mox.Mox()

        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def collect_links(self, env, content, url, env_base_url=''):

        jenv = yaml.safe_load(env)
        fields = {'files': {}}
        if url:
            self.m.StubOutWithMock(urlutils, 'urlopen')
            urlutils.urlopen(url).AndReturn(six.StringIO(content))
            self.m.ReplayAll()

        v1shell._resolve_environment_urls(fields, env_base_url, jenv)
        if url:
            self.assertEqual(fields['files'][url], content)

    def test_prepare_environment_file(self):
        with tempfile.NamedTemporaryFile() as env_file:
            env = '''
            resource_registry:
              "OS::Thingy": "file:///home/b/a.yaml"
            '''
            env_file.write(env)
            env_file.flush()
            env_url, env_dict = v1shell._prepare_environment_file(
                env_file.name)
            self.assertEqual(
                {'resource_registry': {'OS::Thingy': 'file:///home/b/a.yaml'}},
                env_dict)
            env_dir = os.path.dirname(env_file.name)
            self.assertEqual(env_url, 'file://%s' % env_dir)

    def test_prepare_environment_url(self):
        env = '''
        resource_registry:
            "OS::Thingy": "a.yaml"
        '''
        url = 'http://no.where/some/path/to/file.yaml'
        self.m.StubOutWithMock(urlutils, 'urlopen')
        urlutils.urlopen(url).AndReturn(six.StringIO(env))
        self.m.ReplayAll()
        env_url, env_dict = v1shell._prepare_environment_url(url)
        self.assertEqual({'resource_registry': {'OS::Thingy': 'a.yaml'}},
                         env_dict)
        self.assertEqual('http://no.where/some/path/to', env_url)

    def test_global_files(self):
        a = "A's contents."
        url = 'file:///home/b/a.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, a, url)

    def test_nested_files(self):
        a = "A's contents."
        url = 'file:///home/b/a.yaml'
        env = '''
        resource_registry:
          resources:
            freddy:
              "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, a, url)

    def test_http_url(self):
        a = "A's contents."
        url = 'http://no.where/container/a.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, a, url)

    def test_with_base_url(self):
        a = "A's contents."
        url = 'ftp://no.where/container/a.yaml'
        env = '''
        resource_registry:
          base_url: "ftp://no.where/container/"
          resources:
            server_for_me:
              "OS::Thingy": a.yaml
        '''
        self.collect_links(env, a, url)

    def test_with_built_in_provider(self):
        a = "A's contents."
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": OS::Compute::Server
        '''
        self.collect_links(env, a, None)

    def test_with_env_file_base_url_file(self):
        a = "A's contents."
        url = 'file:///tmp/foo/a.yaml'
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": a.yaml
        '''
        env_base_url = 'file:///tmp/foo'
        self.collect_links(env, a, url, env_base_url)

    def test_with_env_file_base_url_http(self):
        a = "A's contents."
        url = 'http://no.where/path/to/a.yaml'
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": to/a.yaml
        '''
        env_base_url = 'http://no.where/path'
        self.collect_links(env, a, url, env_base_url)

    def test_unsupported_protocol(self):
        env = '''
        resource_registry:
          "OS::Thingy": "sftp://no.where/dev/null/a.yaml"
        '''
        jenv = yaml.safe_load(env)
        fields = {'files': {}}
        self.assertRaises(exc.CommandError,
                          v1shell._get_file_contents,
                          jenv['resource_registry'],
                          fields)
