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
import testscenarios

from heatclient.osc.v1 import stack
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes
from heatclient.v1 import stacks

load_tests = testscenarios.load_tests_apply_scenarios


class TestStack(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestStack, self).setUp()
        self.mock_client = self.app.client_manager.orchestration
        self.stack_client = self.app.client_manager.orchestration.stacks


class TestStackShow(TestStack):

    scenarios = [
        ('table', dict(
            format='table')),
        ('shell', dict(
            format='shell')),
        ('value', dict(
            format='value')),
    ]

    get_response = {"stack": {
        "disable_rollback": True,
        "description": "This is a\ndescription\n",
        "parent": None,
        "tags": None,
        "stack_name": "a",
        "stack_user_project_id": "02ad9bd403d44ff9ba128cf9ce77f989",
        "stack_status_reason": "Stack UPDATE completed successfully",
        "creation_time": "2015-08-04T04:46:10",
        "links": [{
            "href": "http://192.0.2.1:8004/v1/5dcd28/stacks/a/4af43781",
            "rel": "self"
        }],
        "capabilities": [],
        "notification_topics": [],
        "updated_time": "2015-08-05T21:33:28",
        "timeout_mins": None,
        "stack_status": "UPDATE_COMPLETE",
        "stack_owner": None,
        "parameters": {
            "OS::project_id": "e0e5e140c5854c259a852621b65dcd28",
            "OS::stack_id": "4af43781",
            "OS::stack_name": "a"
        },
        "id": "4af43781",
        "outputs": [],
        "template_description": "This is a\ndescription\n"}
    }

    def setUp(self):
        super(TestStackShow, self).setUp()
        self.cmd = stack.ShowStack(self.app, None)

    def test_stack_show(self):
        arglist = ['--format', self.format, 'my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.get = mock.Mock(
            return_value=stacks.Stack(None, self.get_response))
        self.cmd.take_action(parsed_args)
        self.stack_client.get.assert_called_with(**{
            'stack_id': 'my_stack',
        })
