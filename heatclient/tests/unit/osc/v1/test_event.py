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
#   Copyright 2015 IBM Corp.

import mock
import testscenarios

from heatclient import exc
from heatclient.osc.v1 import event
from heatclient.tests.unit.osc.v1 import fakes
from heatclient.v1 import events

load_tests = testscenarios.load_tests_apply_scenarios


class TestEvent(fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestEvent, self).setUp()
        self.mock_client = self.app.client_manager.orchestration
        self.event_client = self.app.client_manager.orchestration.events
        self.stack_client = self.app.client_manager.orchestration.stacks
        self.resource_client = self.app.client_manager.orchestration.resources


class TestEventShow(TestEvent):

    scenarios = [
        ('table', dict(format='table')),
        ('shell', dict(format='shell')),
        ('value', dict(format='value')),
    ]

    response = {
        'event': {
            "resource_name": "my_resource",
            "event_time": "2015-11-11T15:23:47Z",
            "links": [],
            "logical_resource_id": "my_resource",
            "resource_status": "CREATE_FAILED",
            "resource_status_reason": "NotFound",
            "physical_resource_id": "null",
            "id": "474bfdf0-a450-46ec-a78a-0c7faa404073"
        }
    }

    def setUp(self):
        super(TestEventShow, self).setUp()
        self.cmd = event.ShowEvent(self.app, None)

    def test_event_show(self):
        arglist = ['--format', self.format, 'my_stack', 'my_resource', '1234']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.get = mock.MagicMock()
        self.resource_client.get = mock.MagicMock()
        self.event_client.get = mock.MagicMock(
            return_value=events.Event(None, self.response))

        self.cmd.take_action(parsed_args)

        self.event_client.get.assert_called_with(**{
            'stack_id': 'my_stack',
            'resource_name': 'my_resource',
            'event_id': '1234'
        })

    def _test_not_found(self, error):
        arglist = ['my_stack', 'my_resource', '1234']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        ex = self.assertRaises(exc.CommandError, self.cmd.take_action,
                               parsed_args)
        self.assertIn(error, str(ex))

    def test_event_show_stack_not_found(self):
        error = 'Stack not found'
        self.stack_client.get = mock.MagicMock(
            side_effect=exc.HTTPNotFound(error))
        self._test_not_found(error)

    def test_event_show_resource_not_found(self):
        error = 'Resource not found'
        self.stack_client.get = mock.MagicMock()
        self.resource_client.get = mock.MagicMock(
            side_effect=exc.HTTPNotFound(error))
        self._test_not_found(error)

    def test_event_show_event_not_found(self):
        error = 'Event not found'
        self.stack_client.get = mock.MagicMock()
        self.resource_client.get = mock.MagicMock()
        self.event_client.get = mock.MagicMock(
            side_effect=exc.HTTPNotFound(error))
        self._test_not_found(error)
