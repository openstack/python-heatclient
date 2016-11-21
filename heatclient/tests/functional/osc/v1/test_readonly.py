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

import yaml

from tempest.lib import exceptions

from heatclient.tests.functional.osc.v1 import base


class SimpleReadOnlyOpenStackClientTest(base.OpenStackClientTestBase):
    """Basic, read-only tests for Openstack CLI client heat plugin.

    Basic smoke test for the openstack CLI commands which do not require
    creating or modifying stacks.
    """

    def test_openstack_fake_action(self):
        self.assertRaises(exceptions.CommandFailed,
                          self.openstack,
                          'this-does-not-exist')

    # Empty list commands
    def test_openstack_empty_lists(self):
        cmds = [
            'software config',
            'software deployment',
            'stack',
        ]
        for cmd in cmds:
            self.openstack(cmd + ' list')

    # Stack not found commands
    def test_openstack_stack_not_found(self):
        cmds = [
            'stack abandon',
            'stack check',
            'stack output list',
            'stack resume',
            'stack show',
            'stack snapshot list',
            'stack suspend',
            'stack template show',
            'stack cancel'
        ]
        for cmd in cmds:
            err = self.assertRaises(exceptions.CommandFailed,
                                    self.openstack,
                                    cmd + ' I-AM-NOT-FOUND')
            self.assertIn('Stack not found: I-AM-NOT-FOUND', str(err))

    def test_openstack_stack_list_debug(self):
        self.openstack('stack list', flags='--debug')

    def test_openstack_stack_list_property(self):
        self.openstack('stack list --property id=123')

    def test_openstack_help_cmd(self):
        help_text = self.openstack('help stack list')
        lines = help_text.split('\n')
        self.assertFirstLineStartsWith(lines, 'usage: openstack stack list')

    def test_openstack_version(self):
        self.openstack('', flags='--version')

    def test_openstack_template_version_list(self):
        ret = self.openstack('orchestration template version list')
        tmpl_types = self.parser.listing(ret)
        self.assertTableStruct(tmpl_types, ['Version', 'Type'])

    def test_openstack_template_function_list(self):
        ret = self.openstack('orchestration template function list '
                             'heat_template_version.2015-10-15')
        tmpl_functions = self.parser.listing(ret)
        self.assertTableStruct(tmpl_functions, ['Functions', 'Description'])

    def test_openstack_resource_type_list(self):
        ret = self.openstack('orchestration resource type list')
        rsrc_types = self.parser.listing(ret)
        self.assertTableStruct(rsrc_types, ['Resource Type'])

    def test_openstack_resource_type_show(self):
        rsrc_schema = self.openstack('orchestration resource type show '
                                     'OS::Heat::RandomString')
        self.assertIsInstance(yaml.load(rsrc_schema), dict)

    def _template_validate(self, templ_name, parms):
        heat_template_path = self.get_template_path(templ_name)
        cmd = 'stack create test-stack --dry-run --template %s'\
              % heat_template_path
        for parm in parms:
            cmd += ' --parameter ' + parm
        ret = self.openstack(cmd)
        self.assertRegex(ret, r'stack_name.*|.*test_stack')

    def test_heat_template_validate_yaml(self):
        self._template_validate(
            'heat_minimal.yaml',
            ['ClientName=ClientName', 'WaitSecs=123']
        )

    def test_heat_template_validate_hot(self):
        self._template_validate(
            'heat_minimal_hot.yaml',
            ['test_client_name=test_client_name', 'test_wait_secs=123']
        )

    def _orchestration_template_validate(self, templ_name, parms):
        template_path = self.get_template_path(templ_name)
        cmd = 'orchestration template validate --template %s' % template_path
        for parm in parms:
            cmd += ' --parameter ' + parm
        ret = self.openstack(cmd)
        self.assertRegex(ret, r'Value:.*123')

    def test_orchestration_template_validate_yaml(self):
        self._orchestration_template_validate(
            'heat_minimal.yaml',
            ['ClientName=ClientName', 'WaitSecs=123']
        )

    def test_orchestration_template_validate_hot(self):
        self._orchestration_template_validate(
            'heat_minimal_hot.yaml',
            ['test_client_name=test_client_name', 'test_wait_secs=123']
        )
