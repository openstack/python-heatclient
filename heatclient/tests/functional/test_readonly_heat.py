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

import json
import os

from tempest.lib import exceptions
import yaml

from heatclient.tests.functional import base


class SimpleReadOnlyHeatClientTest(base.ClientTestBase):
    """Basic, read-only tests for Heat CLI client.

    Basic smoke test for the heat CLI commands which do not require
    creating or modifying stacks.
    """

    def test_heat_fake_action(self):
        """
        Test if the test test for test mode.

        Args:
            self: (todo): write your description
        """
        self.assertRaises(exceptions.CommandFailed,
                          self.heat,
                          'this-does-not-exist')

    def test_heat_stack_list(self):
        """
        Test if the heatmap is heatmap.

        Args:
            self: (todo): write your description
        """
        self.heat('stack-list')

    def test_heat_stack_list_debug(self):
        """
        Test if the heatmap

        Args:
            self: (todo): write your description
        """
        self.heat('stack-list', flags='--debug')

    def test_heat_resource_template_fmt_default(self):
        """
        Evaluates template heat template

        Args:
            self: (todo): write your description
        """
        ret = self.heat('resource-template OS::Nova::Server')
        self.assertIn('Type: OS::Nova::Server', ret)

    def test_heat_resource_template_fmt_arg_short_yaml(self):
        """
        Test for heat template file exists ini format template

        Args:
            self: (todo): write your description
        """
        ret = self.heat('resource-template -F yaml OS::Nova::Server')
        self.assertIn('Type: OS::Nova::Server', ret)
        self.assertIsInstance(yaml.safe_load(ret), dict)

    def test_heat_resource_template_fmt_arg_long_json(self):
        """
        Evaluate template template template template conversion

        Args:
            self: (todo): write your description
        """
        ret = self.heat('resource-template --format json OS::Nova::Server')
        self.assertIn('"Type": "OS::Nova::Server"', ret)
        self.assertIsInstance(json.loads(ret), dict)

    def test_heat_resource_type_list(self):
        """
        Test if the resource type type_heat type

        Args:
            self: (todo): write your description
        """
        ret = self.heat('resource-type-list')
        rsrc_types = self.parser.listing(ret)
        self.assertTableStruct(rsrc_types, ['resource_type'])

    def test_heat_resource_type_show(self):
        """
        Show the heat type is supported heat type

        Args:
            self: (todo): write your description
        """
        rsrc_schema = self.heat('resource-type-show OS::Heat::RandomString')
        # resource-type-show returns a json resource schema
        self.assertIsInstance(json.loads(rsrc_schema), dict)

    def _template_validate(self, templ_name):
        """
        Validate template.

        Args:
            self: (todo): write your description
            templ_name: (str): write your description
        """
        heat_template_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'templates/%s' % templ_name)
        ret = self.heat('template-validate -f %s' % heat_template_path)
        # On success template-validate returns a json representation
        # of the template parameters
        self.assertIsInstance(json.loads(ret), dict)

    def test_heat_template_validate_yaml(self):
        """
        Determine template template is valid

        Args:
            self: (todo): write your description
        """
        self._template_validate('heat_minimal.yaml')

    def test_heat_template_validate_hot(self):
        """
        Determine whether the template is valid

        Args:
            self: (todo): write your description
        """
        self._template_validate('heat_minimal_hot.yaml')

    def test_heat_help(self):
        """
        Emit help for help.

        Args:
            self: (todo): write your description
        """
        self.heat('help')

    def test_heat_bash_completion(self):
        """
        Test if the bash bash

        Args:
            self: (todo): write your description
        """
        self.heat('bash-completion')

    def test_heat_help_cmd(self):
        """
        Test for help text.

        Args:
            self: (todo): write your description
        """
        # Check requesting help for a specific command works
        help_text = self.heat('help resource-template')
        lines = help_text.split('\n')
        self.assertFirstLineStartsWith(lines, 'usage: heat resource-template')

    def test_heat_version(self):
        """
        Test the heat version.

        Args:
            self: (todo): write your description
        """
        self.heat('', flags='--version')

    def test_heat_template_version_list(self):
        """
        : return the heat template template

        Args:
            self: (todo): write your description
        """
        ret = self.heat('template-version-list')
        tmpl_types = self.parser.listing(ret)
        self.assertTableStruct(tmpl_types, ['version', 'type'])

    def test_heat_template_function_list(self):
        """
        Determine template template template function.

        Args:
            self: (todo): write your description
        """
        ret = self.heat('template-function-list '
                        'heat_template_version.2013-05-23')
        tmpl_functions = self.parser.listing(ret)
        self.assertTableStruct(tmpl_functions, ['functions', 'description'])
