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
from heatclient.osc.v1 import snapshot
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes


class TestStack(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestStack, self).setUp()
        self.mock_client = self.app.client_manager.orchestration
        self.stack_client = self.app.client_manager.orchestration.stacks


class TestListSnapshot(TestStack):
    def setUp(self):
        super(TestListSnapshot, self).setUp()
        self.cmd = snapshot.ListSnapshot(self.app, None)
        self.stack_client.snapshot_list = mock.Mock(
            return_value={'snapshots': []}
        )

    def test_snapshot_list(self):
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.stack_client.snapshot_list.assert_called_with(
            stack_id='my_stack')

    def test_snapshot_list_error(self):
        self.stack_client.snapshot_list.side_effect = heat_exc.HTTPNotFound()
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)
        self.assertEqual('Stack not found: my_stack',
                         str(error))


class TestSnapshotShow(TestStack):
    def setUp(self):
        super(TestSnapshotShow, self).setUp()
        self.cmd = snapshot.ShowSnapshot(self.app, None)

    def test_snapshot_show(self):
        arglist = ['my_stack', 'snapshot_id']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.snapshot_show = mock.Mock(
            return_value={})
        self.cmd.take_action(parsed_args)
        self.stack_client.snapshot_show.assert_called_with(
            'my_stack', 'snapshot_id')

    def test_snapshot_not_found(self):
        arglist = ['my_stack', 'snapshot_id']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.snapshot_show = mock.Mock(
            side_effect=heat_exc.HTTPNotFound())
        self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)
