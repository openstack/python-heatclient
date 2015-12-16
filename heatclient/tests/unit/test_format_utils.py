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
