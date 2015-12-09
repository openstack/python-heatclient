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
from heatclient.osc.v1 import resources
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes


class TestResource(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestResource, self).setUp()
        self.mock_client = self.app.client_manager.orchestration


class TestResourceMetadata(TestResource):

    def setUp(self):
        super(TestResourceMetadata, self).setUp()
        self.cmd = resources.ResourceMetadata(self.app, None)
        self.mock_client.resources.metadata = mock.Mock(
            return_value={})

    def test_resource_metadata(self):
        arglist = ['my_stack', 'my_resource']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resources.metadata.assert_called_with(**{
            'stack_id': 'my_stack',
            'resource_name': 'my_resource'
        })

    def test_resource_metadata_yaml(self):
        arglist = ['my_stack', 'my_resource', '--format', 'yaml']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resources.metadata.assert_called_with(**{
            'stack_id': 'my_stack',
            'resource_name': 'my_resource'
        })

    def test_resource_metadata_error(self):
        arglist = ['my_stack', 'my_resource']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.mock_client.resources.metadata = mock.Mock(
            side_effect=heat_exc.HTTPNotFound)
        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)
