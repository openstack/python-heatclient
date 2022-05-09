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

from unittest import mock

import io
from osc_lib import exceptions as exc

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
        self.stack_client.snapshot_list.return_value = {'snapshots': []}

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
        self.stack_client.snapshot_show.return_value = {}
        self.cmd.take_action(parsed_args)
        self.stack_client.snapshot_show.assert_called_with(
            'my_stack', 'snapshot_id')

    def test_snapshot_not_found(self):
        arglist = ['my_stack', 'snapshot_id']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.snapshot_show.side_effect = heat_exc.HTTPNotFound()
        self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)


class TestRestoreSnapshot(TestStack):
    def setUp(self):
        super(TestRestoreSnapshot, self).setUp()
        self.cmd = snapshot.RestoreSnapshot(self.app, None)

    def test_snapshot_restore(self):
        arglist = ['my_stack', 'my_snapshot']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.stack_client.restore.assert_called_with(
            snapshot_id='my_snapshot', stack_id='my_stack')

    def test_snapshot_restore_error(self):
        self.stack_client.restore.side_effect = heat_exc.HTTPNotFound()
        arglist = ['my_stack', 'my_snapshot']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)
        self.assertEqual('Stack my_stack or snapshot my_snapshot not found.',
                         str(error))


class TestSnapshotCreate(TestStack):
    get_response = {
        "status": "IN_PROGRESS",
        "name": "test_snapshot",
        "status_reason": None,
        "creation_time": "2015-11-09T04:35:38.534130",
        "data": None,
        "id": "108604fe-6d13-41b7-aa3a-79b6cf60c4ff"
    }

    def setUp(self):
        super(TestSnapshotCreate, self).setUp()
        self.cmd = snapshot.CreateSnapshot(self.app, None)

    def test_snapshot_create(self):
        arglist = ['my_stack', '--name', 'test_snapshot']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.snapshot.return_value = self.get_response
        self.cmd.take_action(parsed_args)
        self.stack_client.snapshot.assert_called_with(
            'my_stack', 'test_snapshot')

    def test_snapshot_create_no_name(self):
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.snapshot.return_value = self.get_response
        self.cmd.take_action(parsed_args)
        self.stack_client.snapshot.assert_called_with(
            'my_stack', None)

    def test_snapshot_create_error(self):
        arglist = ['my_stack', '--name', 'test_snapshot']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.snapshot.side_effect = heat_exc.HTTPNotFound
        self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)


class TestSnapshotDelete(TestStack):
    def setUp(self):
        super(TestSnapshotDelete, self).setUp()
        self.cmd = snapshot.DeleteSnapshot(self.app, None)

    def test_snapshot_delete(self):
        arglist = ['my_stack', 'snapshot_id']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.stack_client.snapshot_delete.assert_called_with(
            'my_stack', 'snapshot_id')

    def test_snapshot_delete_not_found(self):
        arglist = ['my_stack', 'snapshot_id']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.snapshot_delete.side_effect = heat_exc.HTTPNotFound()
        self.assertRaises(
            exc.CommandError,
            self.cmd.take_action,
            parsed_args)

    @mock.patch('sys.stdin', spec=io.StringIO)
    def test_snapshot_delete_prompt(self, mock_stdin):
        arglist = ['my_stack', 'snapshot_id']
        mock_stdin.isatty.return_value = True
        mock_stdin.readline.return_value = 'y'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        mock_stdin.readline.assert_called_with()
        self.stack_client.snapshot_delete.assert_called_with('my_stack',
                                                             'snapshot_id')

    @mock.patch('sys.stdin', spec=io.StringIO)
    def test_snapshot_delete_prompt_no(self, mock_stdin):
        arglist = ['my_stack', 'snapshot_id']
        mock_stdin.isatty.return_value = True
        mock_stdin.readline.return_value = 'n'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        mock_stdin.readline.assert_called_with()
        self.stack_client.snapshot_delete.assert_not_called()
