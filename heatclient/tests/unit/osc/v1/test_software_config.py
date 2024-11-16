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

from unittest import mock

from osc_lib import exceptions as exc
import yaml

from heatclient import exc as heat_exc
from heatclient.osc.v1 import software_config
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes
from heatclient.v1 import software_configs


class TestConfig(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestConfig, self).setUp()
        self.mock_client = self.app.client_manager.orchestration


class TestDeleteConfig(TestConfig):

    def setUp(self):
        super(TestDeleteConfig, self).setUp()
        self.cmd = software_config.DeleteConfig(self.app, None)
        self.mock_delete = self.mock_client.software_configs.delete

    def test_config_delete(self):
        arglist = ['id_123']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_delete.assert_called_with(
            config_id='id_123')

    def test_config_delete_multi(self):
        arglist = ['id_123', 'id_456']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_delete.assert_has_calls(
            [mock.call(config_id='id_123'),
             mock.call(config_id='id_456')])

    def test_config_delete_not_found(self):
        arglist = ['id_123', 'id_456', 'id_789']
        self.mock_client.software_configs.delete.side_effect = [
            None, heat_exc.HTTPNotFound, None]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(exc.CommandError, self.cmd.take_action,
                                  parsed_args)
        self.mock_delete.assert_has_calls(
            [mock.call(config_id='id_123'),
             mock.call(config_id='id_456'),
             mock.call(config_id='id_789')])
        self.assertEqual('Unable to delete 1 of the 3 software configs.',
                         str(error))


class TestListConfig(TestConfig):

    def setUp(self):
        super(TestListConfig, self).setUp()
        self.cmd = software_config.ListConfig(self.app, None)
        self.mock_client.software_configs.list.return_value = [
            software_configs.SoftwareConfig(None, {})]

    def test_config_list(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.software_configs.list.assert_called_once_with()

    def test_config_list_limit(self):
        arglist = ['--limit', '3']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.software_configs.list.assert_called_with(limit=3)

    def test_config_list_marker(self):
        arglist = ['--marker', 'id123']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.software_configs.list.assert_called_with(
            marker='id123')


class TestCreateConfig(TestConfig):

    def setUp(self):
        super(TestCreateConfig, self).setUp()
        self.cmd = software_config.CreateConfig(self.app, None)
        self.mock_client.software_configs.create.return_value = \
            software_configs.SoftwareConfig(None, {})

    def test_config_create(self):
        properties = {
            'config': '',
            'group': 'Heat::Ungrouped',
            'name': 'test',
            'options': {},
            'inputs': [],
            'outputs': []
        }
        arglist = ['test']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.mock_client.stacks.validate.assert_called_with(**{
            'template': {
                'heat_template_version': '2013-05-23',
                'resources': {
                    'test': {
                        'type': 'OS::Heat::SoftwareConfig',
                        'properties': properties}}}})
        self.mock_client.software_configs.create.assert_called_with(
            **properties)

    def test_config_create_group(self):
        properties = {
            'config': '',
            'group': 'group',
            'name': 'test',
            'options': {},
            'inputs': [],
            'outputs': []
        }
        arglist = ['test', '--group', 'group']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.mock_client.stacks.validate.assert_called_with(**{
            'template': {
                'heat_template_version': '2013-05-23',
                'resources': {
                    'test': {
                        'type': 'OS::Heat::SoftwareConfig',
                        'properties': properties}}}})
        self.mock_client.software_configs.create.assert_called_with(
            **properties)

    @mock.patch('urllib.request.urlopen')
    def test_config_create_config_file(self, urlopen):
        properties = {
            'config': 'config',
            'group': 'Heat::Ungrouped',
            'name': 'test',
            'options': {},
            'inputs': [],
            'outputs': []
        }
        data = mock.Mock()
        data.read.side_effect = ['config']
        urlopen.return_value = data

        arglist = ['test', '--config-file', 'config_file']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.mock_client.stacks.validate.assert_called_with(**{
            'template': {
                'heat_template_version': '2013-05-23',
                'resources': {
                    'test': {
                        'type': 'OS::Heat::SoftwareConfig',
                        'properties': properties}}}})
        self.mock_client.software_configs.create.assert_called_with(
            **properties)

    @mock.patch('urllib.request.urlopen')
    def test_config_create_definition_file(self, urlopen):
        definition = {
            'inputs': [
                {'name': 'input'},
            ],
            'outputs': [
                {'name': 'output'}
            ],
            'options': {'option': 'value'}
        }

        properties = {
            'config': '',
            'group': 'Heat::Ungrouped',
            'name': 'test'
        }
        properties.update(definition)

        data = mock.Mock()
        data.read.side_effect = [yaml.safe_dump(definition)]
        urlopen.return_value = data

        arglist = ['test', '--definition-file', 'definition-file']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.mock_client.stacks.validate.assert_called_with(**{
            'template': {
                'heat_template_version': '2013-05-23',
                'resources': {
                    'test': {
                        'type': 'OS::Heat::SoftwareConfig',
                        'properties': properties}}}})
        self.mock_client.software_configs.create.assert_called_with(
            **properties)


class TestConfigShow(TestConfig):
    columns = (
        'id',
        'name',
        'group',
        'config',
        'inputs',
        'outputs',
        'options',
        'creation_time',
    )

    data = (
        '96dfee3f-27b7-42ae-a03e-966226871ae6',
        'test',
        'Heat::Ungrouped',
        '',
        [],
        [],
        {},
        '2015-12-09T11:55:06',
    )

    response = dict(zip(columns, data))

    def setUp(self):
        super(TestConfigShow, self).setUp()
        self.cmd = software_config.ShowConfig(self.app, None)
        self.mock_client.software_configs.get.return_value = \
            software_configs.SoftwareConfig(None, self.response)

    def test_config_show(self):
        arglist = ['96dfee3f-27b7-42ae-a03e-966226871ae6']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        self.mock_client.software_configs.get.assert_called_with(**{
            'config_id': '96dfee3f-27b7-42ae-a03e-966226871ae6',
        })
        self.assertEqual(self.columns, columns)
        self.assertEqual(self.data, data)

    def test_config_show_config_only(self):
        arglist = ['--config-only', '96dfee3f-27b7-42ae-a03e-966226871ae6']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        self.mock_client.software_configs.get.assert_called_with(**{
            'config_id': '96dfee3f-27b7-42ae-a03e-966226871ae6',
        })
        self.assertIsNone(columns)
        self.assertIsNone(data)

    def test_config_show_not_found(self):
        arglist = ['96dfee3f-27b7-42ae-a03e-966226871ae6']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.mock_client.software_configs.get.side_effect = \
            heat_exc.HTTPNotFound()
        self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)
