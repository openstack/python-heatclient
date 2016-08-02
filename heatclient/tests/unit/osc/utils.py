#   Copyright 2012-2013 OpenStack Foundation
#   Copyright 2013 Nebula Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

import os

import fixtures
import mock
import sys
import testtools

from heatclient.tests.unit.osc import fakes


class TestCase(testtools.TestCase):
    def setUp(self):
        testtools.TestCase.setUp(self)

        if (os.environ.get("OS_STDOUT_CAPTURE") == "True" or
                os.environ.get("OS_STDOUT_CAPTURE") == "1"):
            stdout = self.useFixture(fixtures.StringStream("stdout")).stream
            self.useFixture(fixtures.MonkeyPatch("sys.stdout", stdout))

        if (os.environ.get("OS_STDERR_CAPTURE") == "True" or
                os.environ.get("OS_STDERR_CAPTURE") == "1"):
            stderr = self.useFixture(fixtures.StringStream("stderr")).stream
            self.useFixture(fixtures.MonkeyPatch("sys.stderr", stderr))

    def assertNotCalled(self, m, msg=None):
        """Assert a function was not called"""

        if m.called:
            if not msg:
                msg = 'method %s should not have been called' % m
            self.fail(msg)

    # 2.6 doesn't have the assert dict equals so make sure that it exists
    if tuple(sys.version_info)[0:2] < (2, 7):

        def assertIsInstance(self, obj, cls, msg=None):
            """self.assertTrue(isinstance(obj, cls)), with a nicer message"""

            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (obj, cls)
                self.fail(self._formatMessage(msg, standardMsg))


class TestCommand(TestCase):
    """Test cliff command classes"""

    def setUp(self):
        super(TestCommand, self).setUp()
        # Build up a fake app
        self.fake_stdout = fakes.FakeStdout()
        self.app = mock.MagicMock()
        self.app.stdout = self.fake_stdout
        self.app.stdin = sys.stdin
        self.app.stderr = sys.stderr

    def check_parser(self, cmd, args, verify_args):
        cmd_parser = cmd.get_parser('check_parser')
        try:
            parsed_args = cmd_parser.parse_args(args)
        except SystemExit:
            raise Exception("Argument parse failed")
        for av in verify_args:
            attr, value = av
            if attr:
                self.assertIn(attr, parsed_args)
                self.assertEqual(getattr(parsed_args, attr), value)
        return parsed_args
