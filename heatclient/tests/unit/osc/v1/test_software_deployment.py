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

import copy

import mock
from osc_lib import exceptions as exc

from heatclient import exc as heat_exc
from heatclient.osc.v1 import software_deployment
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes
from heatclient.v1 import software_configs
from heatclient.v1 import software_deployments


class TestDeployment(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestDeployment, self).setUp()
        self.mock_client = self.app.client_manager.orchestration
        self.config_client = self.mock_client.software_configs
        self.sd_client = self.mock_client.software_deployments


class TestDeploymentCreate(TestDeployment):

    server_id = '1234'
    config_id = '5678'
    deploy_id = '910'

    config = {
        'name': 'my_deploy',
        'group': 'strict',
        'config': '#!/bin/bash',
        'inputs': [],
        'outputs': [],
        'options': [],
        'id': config_id,
    }

    deployment = {
        'server_id': server_id,
        'input_values': {},
        'action': 'UPDATE',
        'status': 'IN_PROGRESS',
        'status_reason': None,
        'signal_id': 'signal_id',
        'config_id': config_id,
        'id': deploy_id,
    }

    config_defaults = {
        'group': 'Heat::Ungrouped',
        'config': '',
        'options': {},
        'inputs': [
            {
                'name': 'deploy_server_id',
                'description': 'ID of the server being deployed to',
                'type': 'String',
                'value': server_id,
            },
            {
                'name': 'deploy_action',
                'description': 'Name of the current action being deployed',
                'type': 'String',
                'value': 'UPDATE',
            },
            {
                'name': 'deploy_signal_transport',
                'description': 'How the server should signal to heat with the '
                               'deployment output values.',
                'type': 'String',
                'value': 'TEMP_URL_SIGNAL',
            },
            {
                'name': 'deploy_signal_id',
                'description': 'ID of signal to use for signaling output '
                               'values',
                'type': 'String',
                'value': 'signal_id',
            },
            {
                'name': 'deploy_signal_verb',
                'description': 'HTTP verb to use for signaling output values',
                'type': 'String',
                'value': 'PUT',
            },
        ],
        'outputs': [],
        'name': 'my_deploy',
    }

    deploy_defaults = {
        'config_id': config_id,
        'server_id': server_id,
        'action': 'UPDATE',
        'status': 'IN_PROGRESS',
    }

    def setUp(self):
        super(TestDeploymentCreate, self).setUp()
        self.cmd = software_deployment.CreateDeployment(self.app, None)
        self.config_client.create.return_value = \
            software_configs.SoftwareConfig(None, self.config)
        self.config_client.get.return_value = \
            software_configs.SoftwareConfig(None, self.config)
        self.sd_client.create.return_value = \
            software_deployments.SoftwareDeployment(None, self.deployment)

    @mock.patch('heatclient.common.deployment_utils.build_signal_id',
                return_value='signal_id')
    def test_deployment_create(self, mock_build):
        arglist = ['my_deploy', '--server', self.server_id]
        expected_cols = ('action', 'config_id', 'id',  'input_values',
                         'server_id', 'signal_id', 'status', 'status_reason')
        expected_data = ('UPDATE', self.config_id, self.deploy_id, {},
                         self.server_id, 'signal_id', 'IN_PROGRESS', None)
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.config_client.create.assert_called_with(**self.config_defaults)
        self.sd_client.create.assert_called_with(
            **self.deploy_defaults)
        self.assertEqual(expected_cols, columns)
        self.assertEqual(expected_data, data)

    @mock.patch('heatclient.common.deployment_utils.build_signal_id',
                return_value='signal_id')
    def test_deployment_create_with_config(self, mock_build):
        arglist = ['my_deploy', '--server', self.server_id,
                   '--config', self.config_id]
        config = copy.deepcopy(self.config_defaults)
        config['config'] = '#!/bin/bash'
        config['group'] = 'strict'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.config_client.get.assert_called_with(self.config_id)
        self.config_client.create.assert_called_with(**config)
        self.sd_client.create.assert_called_with(
            **self.deploy_defaults)

    def test_deployment_create_config_not_found(self):
        arglist = ['my_deploy', '--server', self.server_id,
                   '--config', 'bad_id']
        self.config_client.get.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_deployment_create_no_signal(self):
        arglist = ['my_deploy', '--server', self.server_id,
                   '--signal-transport', 'NO_SIGNAL']
        config = copy.deepcopy(self.config_defaults)
        config['inputs'] = config['inputs'][:-2]
        config['inputs'][2]['value'] = 'NO_SIGNAL'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.config_client.create.assert_called_with(**config)
        self.sd_client.create.assert_called_with(
            **self.deploy_defaults)

    @mock.patch('heatclient.common.deployment_utils.build_signal_id',
                return_value='signal_id')
    def test_deployment_create_invalid_signal_transport(self, mock_build):
        arglist = ['my_deploy', '--server', self.server_id,
                   '--signal-transport', 'A']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(heat_exc.CommandError,
                          self.cmd.take_action, parsed_args)

    @mock.patch('heatclient.common.deployment_utils.build_signal_id',
                return_value='signal_id')
    def test_deployment_create_input_value(self, mock_build):
        arglist = ['my_deploy', '--server', self.server_id,
                   '--input-value', 'foo=bar']
        config = copy.deepcopy(self.config_defaults)
        config['inputs'].insert(
            0, {'name': 'foo', 'type': 'String', 'value': 'bar'})
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.config_client.create.assert_called_with(**config)
        self.sd_client.create.assert_called_with(
            **self.deploy_defaults)

    @mock.patch('heatclient.common.deployment_utils.build_signal_id',
                return_value='signal_id')
    def test_deployment_create_action(self, mock_build):
        arglist = ['my_deploy', '--server', self.server_id,
                   '--action', 'DELETE']
        config = copy.deepcopy(self.config_defaults)
        config['inputs'][1]['value'] = 'DELETE'
        deploy = copy.deepcopy(self.deploy_defaults)
        deploy['action'] = 'DELETE'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.config_client.create.assert_called_with(**config)
        self.sd_client.create.assert_called_with(**deploy)


class TestDeploymentDelete(TestDeployment):

    def setUp(self):
        super(TestDeploymentDelete, self).setUp()
        self.cmd = software_deployment.DeleteDeployment(self.app, None)

    def test_deployment_delete_success(self):
        arglist = ['test_deployment']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.sd_client.delete.assert_called_with(
            deployment_id='test_deployment')

    def test_deployment_delete_multiple(self):
        arglist = ['test_deployment', 'test_deployment2']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.sd_client.delete.assert_has_calls(
            [mock.call(deployment_id='test_deployment'),
             mock.call(deployment_id='test_deployment2')])

    def test_deployment_delete_not_found(self):
        arglist = ['test_deployment', 'test_deployment2']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.sd_client.delete.side_effect = heat_exc.HTTPNotFound()
        error = self.assertRaises(
            exc.CommandError, self.cmd.take_action, parsed_args)
        self.assertIn("Unable to delete 2 of the 2 deployments.", str(error))

    def test_deployment_config_delete_failed(self):
        arglist = ['test_deployment']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.config_client.delete.side_effect = heat_exc.HTTPNotFound()
        self.assertIsNone(self.cmd.take_action(parsed_args))


class TestDeploymentList(TestDeployment):

    columns = ['id', 'config_id', 'server_id', 'action', 'status']

    data = {"software_deployments": [
        {
            "status": "COMPLETE",
            "server_id": "ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5",
            "config_id": "8da95794-2ad9-4979-8ae5-739ce314c5cd",
            "output_values": {
                "deploy_stdout": "Writing to /tmp/barmy Written to /tmp/barmy",
                "deploy_stderr": "+ echo Writing to /tmp/barmy\n+ echo fu\n+ c"
                                 "at /tmp/barmy\n+ echo -n The file /tmp/barmy"
                                 "contains for server ec14c864-096e-4e27-bb8a-"
                                 "2c2b4dc6f3f5 during CREATE\n+"
                                 "echo Output to stderr\nOutput to stderr\n",
                "deploy_status_code": 0,
                "result": "The file /tmp/barmy contains fu for server "
                          "ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5 during CREATE"
            },
            "input_values": None,
            "action": "CREATE",
            "status_reason": "Outputs received",
            "id": "ef422fa5-719a-419e-a10c-72e3a367b0b8",
            "creation_time": "2015-01-31T15:12:36Z",
            "updated_time": "2015-01-31T15:18:21Z"
        }
    ]
    }

    def setUp(self):
        super(TestDeploymentList, self).setUp()
        self.cmd = software_deployment.ListDeployment(self.app, None)
        self.sd_client.list = mock.MagicMock(return_value=[self.data])

    def test_deployment_list(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        self.sd_client.list.assert_called_with()
        self.assertEqual(self.columns, columns)

    def test_deployment_list_server(self):
        kwargs = {}
        kwargs['server_id'] = 'ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5'
        arglist = ['--server', 'ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        self.sd_client.list.assert_called_with(**kwargs)
        self.assertEqual(self.columns, columns)

    def test_deployment_list_long(self):
        kwargs = {}
        cols = ['id', 'config_id', 'server_id', 'action', 'status',
                'creation_time', 'status_reason']
        arglist = ['--long']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.sd_client.list.assert_called_with(**kwargs)
        self.assertEqual(cols, columns)


class TestDeploymentShow(TestDeployment):
    get_response = {"software_deployment": {
        "status": "IN_PROGRESS",
        "server_id": "ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5",
        "config_id": "3d5ec2a8-7004-43b6-a7f6-542bdbe9d434",
        "output_values": 'null',
        "input_values": 'null',
        "action": "CREATE",
        "status_reason": "Deploy data available",
        "id": "06e87bcc-33a2-4bce-aebd-533e698282d3",
        "creation_time": "2015-01-31T15:12:36Z",
        "updated_time": "2015-01-31T15:18:21Z"
    }}

    def setUp(self):
        super(TestDeploymentShow, self).setUp()
        self.cmd = software_deployment.ShowDeployment(self.app, None)

    def test_deployment_show(self):
        arglist = ['my_deployment']
        cols = ['id', 'server_id', 'config_id', 'creation_time',
                'updated_time', 'status', 'status_reason',
                'input_values', 'action']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.sd_client.get.return_value = \
            software_deployments.SoftwareDeployment(
                None, self.get_response)
        columns, data = self.cmd.take_action(parsed_args)
        self.sd_client.get.assert_called_with(**{
            'deployment_id': 'my_deployment',
        })
        self.assertEqual(cols, columns)

    def test_deployment_show_long(self):
        arglist = ['my_deployment', '--long']
        cols = ['id', 'server_id', 'config_id', 'creation_time',
                'updated_time', 'status', 'status_reason',
                'input_values', 'action', 'output_values']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.sd_client.get.return_value = \
            software_deployments.SoftwareDeployment(
                None, self.get_response)
        columns, data = self.cmd.take_action(parsed_args)
        self.sd_client.get.assert_called_once_with(**{
            'deployment_id': 'my_deployment',
        })
        self.assertEqual(cols, columns)

    def test_deployment_not_found(self):
        arglist = ['my_deployment']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.sd_client.get.side_effect = heat_exc.HTTPNotFound()
        self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)


class TestDeploymentMetadataShow(TestDeployment):

    def setUp(self):
        super(TestDeploymentMetadataShow, self).setUp()
        self.cmd = software_deployment.ShowMetadataDeployment(self.app, None)
        self.sd_client.metadata.return_value = {}

    def test_deployment_show_metadata(self):
        arglist = ['ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.sd_client.metadata.assert_called_with(
            server_id='ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5')


class TestDeploymentOutputShow(TestDeployment):

    get_response = {
        "status": "IN_PROGRESS",
        "server_id": "ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5",
        "config_id": "3d5ec2a8-7004-43b6-a7f6-542bdbe9d434",
        "output_values": None,
        "input_values": None,
        "action": "CREATE",
        "status_reason": "Deploy data available",
        "id": "06e87bcc-33a2-4bce-aebd-533e698282d3",
        "creation_time": "2015-01-31T15:12:36Z",
        "updated_time": "2015-01-31T15:18:21Z"
    }

    def setUp(self):
        super(TestDeploymentOutputShow, self).setUp()
        self.cmd = software_deployment.ShowOutputDeployment(self.app, None)

    def test_deployment_output_show(self):
        arglist = ['85c3a507-351b-4b28-a7d8-531c8d53f4e6', '--all', '--long']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.sd_client.get.return_value = \
            software_deployments.SoftwareDeployment(
                None, self.get_response)
        self.cmd.take_action(parsed_args)
        self.sd_client.get.assert_called_with(**{
            'deployment_id': '85c3a507-351b-4b28-a7d8-531c8d53f4e6'
            })

    def test_deployment_output_show_invalid(self):
        arglist = ['85c3a507-351b-4b28-a7d8-531c8d53f4e6']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)
        self.assertIn('either <output-name> or --all argument is needed',
                      str(error))

    def test_deployment_output_show_not_found(self):
        arglist = ['85c3a507-351b-4b28-a7d8-531c8d53f4e6', '--all']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.sd_client.get.side_effect = heat_exc.HTTPNotFound()
        self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)
