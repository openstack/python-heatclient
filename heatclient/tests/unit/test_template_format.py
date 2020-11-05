#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

import six
import testscenarios
import testtools
import yaml

from heatclient.common import template_format


load_tests = testscenarios.load_tests_apply_scenarios


class YamlParseExceptions(testtools.TestCase):

    scenarios = [
        ('scanner', dict(raised_exception=yaml.scanner.ScannerError())),
        ('parser', dict(raised_exception=yaml.parser.ParserError())),
        ('reader',
         dict(raised_exception=yaml.reader.ReaderError('', '', '', '', ''))),
    ]

    def test_parse_to_value_exception(self):
        """
        Parse a yaml document.

        Args:
            self: (todo): write your description
        """
        text = 'not important'

        with mock.patch.object(yaml, 'load') as yaml_loader:
            yaml_loader.side_effect = self.raised_exception

            self.assertRaises(ValueError,
                              template_format.parse, text)

    def test_parse_no_version_format(self):
        """
        : param yaml format : py : func : test_parse.

        Args:
            self: (todo): write your description
        """
        yaml = ''
        self.assertRaises(ValueError, template_format.parse, yaml)
        yaml2 = '''Parameters: {}
Mappings: {}
Resources: {}
Outputs: {}
'''
        self.assertRaises(ValueError, template_format.parse, yaml2)


class DetailedYAMLParseExceptions(testtools.TestCase):

    def test_parse_to_value_exception(self):
        """
        Convert the test value to the test.

        Args:
            self: (todo): write your description
        """
        yaml = """not important
but very:
  - incorrect
"""
        ex = self.assertRaises(ValueError, template_format.parse, yaml)
        self.assertIn('but very:\n            ^', six.text_type(ex))
