import cStringIO
import os
import httplib2
import httplib
import sys

import mox
import unittest
from keystoneclient.v2_0 import client as ksclient

from heatclient import exc
from heatclient.v1 import client as v1client
import heatclient.shell
import fakes


class ShellTest(unittest.TestCase):

    # Patch os.environ to avoid required auth info.
    def setUp(self):
        self.m = mox.Mox()
        self.m.StubOutWithMock(ksclient, 'Client')
        self.m.StubOutWithMock(v1client.Client, 'json_request')
        #self.m.StubOutWithMock(httplib.HTTPConnection, 'request')
        #self.m.StubOutWithMock(httplib.HTTPConnection, 'getresponse')

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
            '^usage: heat list',
            "(?m)^List the user's stacks",
        ]
        argstrings = [
            'help list',
        ]
        for argstr in argstrings:
            help_text = self.shell(argstr)
            for r in required:
                self.assertRegexpMatches(help_text, r)

    def test_list(self):
        fakes.script_keystone_client()
        resp = fakes.FakeHTTPResponse(200,
                              'success, yo',
                              {'content-type': 'application/json'},
                              '{"stacks": {}}')
        v1client.Client.json_request('GET',
            '/stacks?limit=20').AndReturn((resp, {'stacks': []}))

        self.m.ReplayAll()

        list_text = self.shell('list')

        self.assertEqual('\n', list_text)
        self.m.VerifyAll()

    def test_create(self):
        fakes.script_keystone_client()
        resp = fakes.FakeHTTPResponse(201,
                                'Created',
                                {'content-type': 'application/json'},
                                '[{"foo": "bar"}]')
        v1client.Client.json_request('POST', '/stacks',
                          body=mox.IgnoreArg()).AndReturn((resp, [{'foo': 'bar'}]))

        self.m.ReplayAll()

        create_text = self.shell('create  teststack '
            '--template-file=minimal.template '
            '--parameters="InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17"')

        self.assertEqual('\n', create_text)
        self.m.VerifyAll()
