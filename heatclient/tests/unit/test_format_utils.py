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
#   Copyright 2015 IBM Corp.

import json
import six
import yaml

from heatclient.common import format_utils
from heatclient.tests.unit.osc import utils


columns = ['col1', 'col2', 'col3']
data = ['abcde', ['fg', 'hi', 'jk'], {'lmnop': 'qrstu'}]


class ShowJson(format_utils.JsonFormat):
    def take_action(self, parsed_args):
        return columns, data


class ShowYaml(format_utils.YamlFormat):
    def take_action(self, parsed_args):
        return columns, data


class ShowShell(format_utils.ShellFormat):
    def take_action(self, parsed_args):
        return columns, data


class ShowValue(format_utils.ValueFormat):
    def take_action(self, parsed_args):
        return columns, data


class TestFormats(utils.TestCommand):

    def test_json_format(self):
        self.cmd = ShowJson(self.app, None)
        parsed_args = self.check_parser(self.cmd, [], [])
        expected = json.dumps(dict(zip(columns, data)), indent=2)

        self.cmd.run(parsed_args)

        self.assertEqual(expected, self.app.stdout.make_string())

    def test_yaml_format(self):
        self.cmd = ShowYaml(self.app, None)
        parsed_args = self.check_parser(self.cmd, [], [])
        expected = yaml.safe_dump(dict(zip(columns, data)),
                                  default_flow_style=False)

        self.cmd.run(parsed_args)

        self.assertEqual(expected, self.app.stdout.make_string())

    def test_shell_format(self):
        self.cmd = ShowShell(self.app, None)
        parsed_args = self.check_parser(self.cmd, [], [])
        expected = '''\
col1="abcde"
col2="['fg', 'hi', 'jk']"
col3="{'lmnop': 'qrstu'}"
'''

        self.cmd.run(parsed_args)

        self.assertEqual(expected, self.app.stdout.make_string())

    def test_value_format(self):
        self.cmd = ShowValue(self.app, None)
        parsed_args = self.check_parser(self.cmd, [], [])
        expected = '''\
abcde
['fg', 'hi', 'jk']
{'lmnop': 'qrstu'}
'''

        self.cmd.run(parsed_args)

        self.assertEqual(expected, self.app.stdout.make_string())

    def test_indent_and_truncate(self):
        self.assertIsNone(format_utils.indent_and_truncate(None))
        self.assertIsNone(format_utils.indent_and_truncate(None,
                                                           truncate=True))
        self.assertEqual(
            '',
            format_utils.indent_and_truncate(''))
        self.assertEqual(
            'one',
            format_utils.indent_and_truncate('one'))
        self.assertIsNone(format_utils.indent_and_truncate(None, spaces=2))
        self.assertEqual(
            '',
            format_utils.indent_and_truncate('', spaces=2))
        self.assertEqual(
            '  one',
            format_utils.indent_and_truncate('one', spaces=2))
        self.assertEqual(
            'one\ntwo\nthree\nfour\nfive',
            format_utils.indent_and_truncate('one\ntwo\nthree\nfour\nfive'))
        self.assertEqual(
            'three\nfour\nfive',
            format_utils.indent_and_truncate(
                'one\ntwo\nthree\nfour\nfive',
                truncate=True,
                truncate_limit=3))
        self.assertEqual(
            '  and so on\n  three\n  four\n  five\n  truncated',
            format_utils.indent_and_truncate(
                'one\ntwo\nthree\nfour\nfive',
                spaces=2,
                truncate=True,
                truncate_limit=3,
                truncate_prefix='and so on',
                truncate_postfix='truncated'))

    def test_print_software_deployment_output(self):
        out = six.StringIO()
        format_utils.print_software_deployment_output(
            {'deploy_stdout': ''}, out=out, name='deploy_stdout')
        self.assertEqual(
            '  deploy_stdout: |\n\n',
            out.getvalue())
        ov = {'deploy_stdout': '', 'deploy_stderr': '1\n2\n3\n4\n5\n6\n7\n8\n9'
                                                    '\n10\n11',
              'deploy_status_code': 0}
        out = six.StringIO()
        format_utils.print_software_deployment_output(ov, out=out,
                                                      name='deploy_stderr')
        self.assertEqual(
            u'''\
  deploy_stderr: |
    ...
    2
    3
    4
    5
    6
    7
    8
    9
    10
    11
    (truncated, view all with --long)
''', out.getvalue())
        out = six.StringIO()
        format_utils.print_software_deployment_output(ov, out=out,
                                                      name='deploy_stderr',
                                                      long=True)
        self.assertEqual(
            u'''\
  deploy_stderr: |
    1
    2
    3
    4
    5
    6
    7
    8
    9
    10
    11
''', out.getvalue())
