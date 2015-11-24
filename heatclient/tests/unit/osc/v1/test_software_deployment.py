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

import mock

from openstackclient.common import exceptions as exc

from heatclient import exc as heat_exc
from heatclient.osc.v1 import software_deployment
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes


class TestDeployment(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestDeployment, self).setUp()
        sd_client = self.app.client_manager.orchestration.software_deployments
        self.mock_client = sd_client
        sc_client = self.app.client_manager.orchestration.software_configs
        self.mock_config_client = sc_client


class TestDeploymentDelete(TestDeployment):

    def setUp(self):
        super(TestDeploymentDelete, self).setUp()
        self.cmd = software_deployment.DeleteDeployment(self.app, None)

    def test_deployment_delete_success(self):
        arglist = ['test_deployment']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.mock_client.get = mock.Mock()
        self.mock_client.delete = mock.Mock()
        self.cmd.take_action(parsed_args)
        self.mock_client.delete.assert_called_with(
            deployment_id='test_deployment')

    def test_deployment_delete_multiple(self):
        arglist = ['test_deployment', 'test_deployment2']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.mock_client.get = mock.Mock()
        self.mock_client.delete = mock.Mock()
        self.cmd.take_action(parsed_args)
        self.mock_client.delete.assert_has_calls(
            [mock.call(deployment_id='test_deployment'),
             mock.call(deployment_id='test_deployment2')])

    def test_deployment_delete_not_found(self):
        arglist = ['test_deployment', 'test_deployment2']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.mock_client.delete = mock.Mock()
        self.mock_client.delete.side_effect = heat_exc.HTTPNotFound()
        error = self.assertRaises(
            exc.CommandError, self.cmd.take_action, parsed_args)
        self.assertIn("Unable to delete 2 of the 2 deployments.", str(error))

    def test_deployment_config_delete_failed(self):
        arglist = ['test_deployment']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.mock_config_client.delete = mock.Mock()
        self.mock_config_client.delete.side_effect = heat_exc.HTTPNotFound()
        error = self.assertRaises(
            exc.CommandError, self.cmd.take_action, parsed_args)
        self.assertEqual("Unable to delete 1 of the 1 deployments.",
                         str(error))


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
        self.mock_client.list = mock.MagicMock(return_value=[self.data])

    def test_deployment_list(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        self.mock_client.list.assert_called_with()
        self.assertEqual(self.columns, columns)

    def test_deployment_list_server(self):
        kwargs = {}
        kwargs['server_id'] = 'ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5'
        arglist = ['--server', 'ec14c864-096e-4e27-bb8a-2c2b4dc6f3f5']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        self.mock_client.list.assert_called_with(**kwargs)
        self.assertEqual(self.columns, columns)

    def test_deployment_list_long(self):
        kwargs = {}
        cols = ['id', 'config_id', 'server_id', 'action', 'status',
                'creation_time', 'status_reason']
        arglist = ['--long']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.mock_client.list.assert_called_with(**kwargs)
        self.assertEqual(cols, columns)
