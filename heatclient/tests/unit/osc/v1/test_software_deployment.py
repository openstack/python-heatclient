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
