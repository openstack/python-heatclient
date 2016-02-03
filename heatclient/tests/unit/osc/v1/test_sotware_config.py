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
from heatclient.osc.v1 import software_config
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes


class TestConfig(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestConfig, self).setUp()
        self.mock_client = self.app.client_manager.orchestration


class TestDeleteConfig(TestConfig):

    def setUp(self):
        super(TestDeleteConfig, self).setUp()
        self.cmd = software_config.DeleteConfig(self.app, None)
        self.mock_delete = mock.Mock()
        self.mock_client.software_configs.delete = self.mock_delete

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
