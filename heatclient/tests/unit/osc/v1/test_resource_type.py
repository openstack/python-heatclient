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

from osc_lib import exceptions as exc

from heatclient import exc as heat_exc
from heatclient.osc.v1 import resource_type
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes
from heatclient.v1 import resource_types


class TestResourceType(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        """
        Sets the application s client.

        Args:
            self: (todo): write your description
        """
        super(TestResourceType, self).setUp()
        self.mock_client = self.app.client_manager.orchestration


class TestResourceTypeShow(TestResourceType):

    def setUp(self):
        """
        Set the resource type for this resource.

        Args:
            self: (todo): write your description
        """
        super(TestResourceTypeShow, self).setUp()
        self.cmd = resource_type.ResourceTypeShow(self.app, None)
        self.mock_client.resource_types.get.return_value = {}
        self.mock_client.resource_types.generate_template.return_value = {}

    def test_resourcetype_show(self):
        """
        Resourcetype

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resource_types.get.assert_called_once_with(
            'OS::Heat::None', False)

    def test_resourcetype_show_json(self):
        """
        Show a resource json resource

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None',
                   '--format', 'json']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resource_types.get.assert_called_once_with(
            'OS::Heat::None', False)

    def test_resourcetype_show_error_get(self):
        """
        Show an unspecetypepe.

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.mock_client.resource_types.get.side_effect = heat_exc.HTTPNotFound
        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_resourcetype_show_error_template(self):
        """
        Resourcetype command.

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None',
                   '--template-type', 'hot']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.mock_client.resource_types.generate_template.side_effect = \
            heat_exc.HTTPNotFound
        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_resourcetype_show_template_hot(self):
        """
        Resourcetype template.

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None',
                   '--template-type', 'Hot']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resource_types.generate_template.assert_called_with(
            **{'resource_type': 'OS::Heat::None',
               'template_type': 'hot'})

    def test_resourcetype_show_template_cfn(self):
        """
        Show cfg template template template.

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None',
                   '--template-type', 'cfn']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resource_types.generate_template.assert_called_with(
            **{'resource_type': 'OS::Heat::None',
               'template_type': 'cfn'})

    def test_resourcetype_show_template_cfn_yaml(self):
        """
        Show template yaml template yaml template.

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None',
                   '--template-type', 'Cfn',
                   '--format', 'yaml']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resource_types.generate_template.assert_called_with(
            **{'resource_type': 'OS::Heat::None',
               'template_type': 'cfn'})

    def test_resourcetype_show_invalid_template_type(self):
        """
        Check that the template template command.

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None',
                   '--template-type', 'abc']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_resourcetype_show_with_description(self):
        """
        Resourcetype command.

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None', '--long']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resource_types.get.assert_called_with(
            'OS::Heat::None', True)

    def test_resourcetype_show_long_and_template_type_error(self):
        """
        Show a resourcetype command.

        Args:
            self: (todo): write your description
        """
        arglist = ['OS::Heat::None',
                   '--template-type', 'cfn',
                   '--long']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)


class TestTypeList(TestResourceType):

    expected_columns = ['Resource Type']
    list_response = [
        resource_types.ResourceType(None, {'resource_type': 'BBB',
                                           'description': 'This is BBB'}),
        resource_types.ResourceType(None, {'resource_type': 'AAA',
                                           'description': 'Well done'}),
        resource_types.ResourceType(None,
                                    {'resource_type': 'CCC',
                                     'description': 'No description given'})
    ]
    expected_rows = [
        ['AAA'],
        ['BBB'],
        ['CCC']
    ]

    def setUp(self):
        """
        Set a list of resource types.

        Args:
            self: (todo): write your description
        """
        super(TestTypeList, self).setUp()
        self.cmd = resource_type.ResourceTypeList(self.app, None)
        self.mock_client.resource_types.list.return_value = self.list_response

    def test_resourcetype_list(self):
        """
        Resourcetype argument.

        Args:
            self: (todo): write your description
        """
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)

        self.mock_client.resource_types.list.assert_called_with(
            filters={}, with_description=False)
        self.assertEqual(self.expected_columns, columns)
        self.assertEqual(self.expected_rows, rows)

    def test_resourcetype_list_filter(self):
        """
        Resourcetype devices.

        Args:
            self: (todo): write your description
        """
        arglist = ['--filter', 'name=B']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)

        self.mock_client.resource_types.list.assert_called_once_with(
            filters={'name': 'B'}, with_description=False)
        self.assertEqual(self.expected_columns, columns)
        self.assertEqual(self.expected_rows, rows)

    def test_resourcetype_list_filters(self):
        """
        Resour filters have_resour.

        Args:
            self: (todo): write your description
        """
        arglist = ['--filter', 'name=B', '--filter', 'version=123']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)

        self.mock_client.resource_types.list.assert_called_once_with(
            filters={'name': 'B', 'version': '123'}, with_description=False)
        self.assertEqual(self.expected_columns, columns)
        self.assertEqual(self.expected_rows, rows)

    def test_resourcetype_list_with_description(self):
        """
        Resourcetype command.

        Args:
            self: (todo): write your description
        """
        arglist = ['--long']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)

        self.mock_client.resource_types.list.assert_called_once_with(
            filters={}, with_description=True)
        self.assertEqual(['Resource Type', 'Description'], columns)
        self.assertEqual([['AAA', 'Well done'],
                          ['BBB', 'This is BBB'],
                          ['CCC', 'No description given']],
                         rows)
