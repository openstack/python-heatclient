import cStringIO
import os
import httplib2
import re
import sys

import mox
import unittest
try:
    import json
except ImportError:
    import simplejson as json
from keystoneclient.v2_0 import client as ksclient

from heatclient import exc
from heatclient.v1 import client as v1client
import heatclient.shell
import fakes

TEST_VAR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'var'))


class TestCase(unittest.TestCase):
    # required for testing with Python 2.6
    def assertRegexpMatches(self, text, expected_regexp, msg=None):
        """Fail the test unless the text matches the regular expression."""
        if isinstance(expected_regexp, basestring):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(text):
            msg = msg or "Regexp didn't match"
            msg = '%s: %r not found in %r' % (msg, expected_regexp.pattern,
                text)
            raise self.failureException(msg)


class ShellValidationTest(TestCase):

    def test_missing_auth(self):
        _old_env, os.environ = os.environ, {
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.shell_error('list', 'You must provide a username')

        os.environ = _old_env

        _old_env, os.environ = os.environ, {
            'OS_USERNAME': 'username',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.shell_error('list', 'You must provide a password')

        os.environ = _old_env

        _old_env, os.environ = os.environ, {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.shell_error('list', 'You must provide a tenant_id')

        os.environ = _old_env

        _old_env, os.environ = os.environ, {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
        }
        self.shell_error('list', 'You must provide an auth url')

        os.environ = _old_env

    def test_failed_auth(self):
        m = mox.Mox()
        m.StubOutWithMock(ksclient, 'Client')
        m.StubOutWithMock(v1client.Client, 'json_request')
        fakes.script_keystone_client()
        v1client.Client.json_request('GET',
            '/stacks?limit=20').AndRaise(exc.Unauthorized)

        m.ReplayAll()
        _old_env, os.environ = os.environ, {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.shell_error('list', 'Invalid OpenStack Identity credentials.')

        m.VerifyAll()

        os.environ = _old_env
        m.UnsetStubs()

    def test_create_validation(self):
        m = mox.Mox()
        m.StubOutWithMock(ksclient, 'Client')
        m.StubOutWithMock(v1client.Client, 'json_request')
        fakes.script_keystone_client()

        m.ReplayAll()
        _old_env, os.environ = os.environ, {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        self.shell_error('create teststack '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"',
            'Need to specify exactly one of')

        m.VerifyAll()

        os.environ = _old_env
        m.UnsetStubs()

    def shell_error(self, argstr, error_match):
        orig = sys.stderr
        try:
            sys.stderr = cStringIO.StringIO()
            _shell = heatclient.shell.HeatShell()
            _shell.main(argstr.split())
        except exc.CommandError as e:
            self.assertRegexpMatches(e.__str__(), error_match)
        else:
            self.fail('Expected error matching: %s' % error_match)
        finally:
            err = sys.stderr.getvalue()
            sys.stderr.close()
            sys.stderr = orig
        return err


class ShellTest(TestCase):

    # Patch os.environ to avoid required auth info.
    def setUp(self):
        self.m = mox.Mox()
        self.m.StubOutWithMock(ksclient, 'Client')
        self.m.StubOutWithMock(v1client.Client, 'json_request')
        self.m.StubOutWithMock(v1client.Client, 'raw_request')

        global _old_env
        fake_env = {
            'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where',
        }
        _old_env, os.environ = os.environ, fake_env.copy()

    def tearDown(self):
        self.m.UnsetStubs()
        global _old_env
        os.environ = _old_env

    def shell(self, argstr):
        orig = sys.stdout
        try:
            sys.stdout = cStringIO.StringIO()
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

    def test_list(self):
        fakes.script_keystone_client()
        fakes.script_heat_list()

        self.m.ReplayAll()

        list_text = self.shell('list')

        required = [
            'ID',
            'Status',
            'Created',
            'teststack',
            '1',
            'CREATE_COMPLETE',
            'IN_PROGRESS',
        ]
        for r in required:
            self.assertRegexpMatches(list_text, r)

        self.m.VerifyAll()

    def test_describe(self):
        fakes.script_keystone_client()
        resp_dict = {"stack": {
                "id": "1",
                "stack_name": "teststack",
                "stack_status": 'CREATE_COMPLETE',
                "creation_time": "2012-10-25T01:58:47Z"
            }
        }
        resp = fakes.FakeHTTPResponse(200,
            'OK',
            {'content-type': 'application/json'},
            json.dumps(resp_dict))
        v1client.Client.json_request('GET',
            '/stacks/teststack/1').AndReturn((resp, resp_dict))

        self.m.ReplayAll()

        list_text = self.shell('describe teststack/1')

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

        self.m.VerifyAll()

    def test_create(self):
        fakes.script_keystone_client()
        resp = fakes.FakeHTTPResponse(201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        v1client.Client.json_request('POST', '/stacks',
                          body=mox.IgnoreArg()).AndReturn((resp, None))
        fakes.script_heat_list()

        self.m.ReplayAll()

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        create_text = self.shell('create teststack '
            '--template-file=%s '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'Name',
            'ID',
            'teststack',
            '1'
        ]

        for r in required:
            self.assertRegexpMatches(create_text, r)

        self.m.VerifyAll()

    def test_create_url(self):

        fakes.script_keystone_client()
        resp = fakes.FakeHTTPResponse(201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        v1client.Client.json_request('POST', '/stacks',
                          body=mox.IgnoreArg()).AndReturn((resp, None))
        fakes.script_heat_list()

        self.m.ReplayAll()

        create_text = self.shell('create teststack '
            '--template-url=http://no.where/minimal.template '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"')

        required = [
            'Name',
            'ID',
            'teststack2',
            '2'
        ]
        for r in required:
            self.assertRegexpMatches(create_text, r)

        self.m.VerifyAll()

    def test_create_object(self):

        fakes.script_keystone_client()
        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        template_data = open(template_file).read()
        v1client.Client.raw_request('GET',
                          'http://no.where/container/minimal.template',
                          ).AndReturn(template_data)

        resp = fakes.FakeHTTPResponse(201,
            'Created',
            {'location': 'http://no.where/v1/tenant_id/stacks/teststack2/2'},
            None)
        v1client.Client.json_request('POST', '/stacks',
                          body=mox.IgnoreArg()).AndReturn((resp, None))

        fakes.script_heat_list()

        self.m.ReplayAll()

        create_text = self.shell('create teststack2 '
            '--template-object=http://no.where/container/minimal.template '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"')

        required = [
            'Name',
            'ID',
            'teststack2',
            '2'
        ]
        for r in required:
            self.assertRegexpMatches(create_text, r)

        self.m.VerifyAll()

    def test_update(self):
        fakes.script_keystone_client()
        resp = fakes.FakeHTTPResponse(202,
            'Accepted',
            {},
            'The request is accepted for processing.')
        v1client.Client.json_request('PUT', '/stacks/teststack2/2',
                          body=mox.IgnoreArg()).AndReturn((resp, None))
        fakes.script_heat_list()

        self.m.ReplayAll()

        template_file = os.path.join(TEST_VAR_DIR, 'minimal.template')
        create_text = self.shell('update teststack2/2 '
            '--template-file=%s '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"' % template_file)

        required = [
            'Name',
            'ID',
            'teststack2',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(create_text, r)

        self.m.VerifyAll()

    def test_delete(self):
        fakes.script_keystone_client()
        resp = fakes.FakeHTTPResponse(204,
            'No Content',
            {},
            None)
        v1client.Client.raw_request('DELETE', '/stacks/teststack2/2',
                          ).AndReturn((resp, None))
        fakes.script_heat_list()

        self.m.ReplayAll()

        create_text = self.shell('delete teststack2/2')

        required = [
            'Name',
            'ID',
            'teststack',
            '1'
        ]
        for r in required:
            self.assertRegexpMatches(create_text, r)

        self.m.VerifyAll()
