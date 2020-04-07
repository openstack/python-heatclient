#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

import testtools

from heatclient.common import event_utils
from heatclient.v1 import events as hc_ev
from heatclient.v1 import resources as hc_res


class FakeWebSocket(object):

    def __init__(self, events):
        self.events = events

    def recv(self):
        return self.events.pop(0)


class ShellTestEventUtils(testtools.TestCase):
    @staticmethod
    def _mock_resource(resource_id, nested_id=None):
        res_info = {"links": [{"href": "http://heat/foo", "rel": "self"},
                              {"href": "http://heat/foo2", "rel": "resource"}],
                    "logical_resource_id": resource_id,
                    "physical_resource_id": resource_id,
                    "resource_status": "CREATE_COMPLETE",
                    "resource_status_reason": "state changed",
                    "resource_type": "OS::Nested::Server",
                    "updated_time": "2014-01-06T16:14:26Z"}
        if nested_id:
            nested_link = {"href": "http://heat/%s" % nested_id,
                           "rel": "nested"}
            res_info["links"].append(nested_link)
        return hc_res.Resource(manager=None, info=res_info)

    @staticmethod
    def _mock_event(event_id, resource_id,
                    resource_status='CREATE_COMPLETE'):
        ev_info = {"links": [
                   {"href": "http://heat/foo", "rel": "self"},
                   {"href": "http://heat/stacks/astack", "rel": "stack"}],
                   "logical_resource_id": resource_id,
                   "physical_resource_id": resource_id,
                   "resource_name": resource_id,
                   "resource_status": resource_status,
                   "resource_status_reason": "state changed",
                   "event_time": "2014-12-05T14:14:30Z",
                   "id": event_id}
        return hc_ev.Event(manager=None, info=ev_info)

    @staticmethod
    def _mock_stack_event(event_id, stack_name,
                          stack_status='CREATE_COMPLETE'):
        stack_id = 'abcdef'
        ev_info = {"links": [{"href": "http://heat/foo", "rel": "self"},
                             {"href": "http://heat/stacks/%s/%s" % (stack_name,
                                                                    stack_id),
                              "rel": "stack"}],
                   "logical_resource_id": stack_name,
                   "physical_resource_id": stack_id,
                   "resource_name": stack_name,
                   "resource_status": stack_status,
                   "resource_status_reason": "state changed",
                   "event_time": "2014-12-05T14:14:30Z",
                   "id": event_id}
        return hc_ev.Event(manager=None, info=ev_info)

    def test_get_nested_ids(self):
        def list_stub(stack_id):
            return [self._mock_resource('aresource', 'foo3/3id')]
        mock_client = mock.MagicMock()
        mock_client.resources.list.side_effect = list_stub
        ids = event_utils._get_nested_ids(hc=mock_client,
                                          stack_id='astack/123')
        mock_client.resources.list.assert_called_once_with(
            stack_id='astack/123')
        self.assertEqual(['foo3/3id'], ids)

    def test_get_stack_events(self):
        def event_stub(stack_id, argfoo):
            return [self._mock_event('event1', 'aresource')]
        mock_client = mock.MagicMock()
        mock_client.events.list.side_effect = event_stub
        ev_args = {'argfoo': 123}
        evs = event_utils._get_stack_events(hc=mock_client,
                                            stack_id='astack/123',
                                            event_args=ev_args)
        mock_client.events.list.assert_called_once_with(
            stack_id='astack/123', argfoo=123)
        self.assertEqual(1, len(evs))
        self.assertEqual('event1', evs[0].id)
        self.assertEqual('astack', evs[0].stack_name)

    def test_get_nested_events(self):
        resources = {'parent': self._mock_resource('resource1', 'foo/child1'),
                     'foo/child1': self._mock_resource('res_child1',
                                                       'foo/child2'),
                     'foo/child2': self._mock_resource('res_child2',
                                                       'foo/child3'),
                     'foo/child3': self._mock_resource('res_child3',
                                                       'foo/END')}

        def resource_list_stub(stack_id):
            return [resources[stack_id]]
        mock_client = mock.MagicMock()
        mock_client.resources.list.side_effect = resource_list_stub

        events = {'foo/child1': self._mock_event('event1', 'res_child1'),
                  'foo/child2': self._mock_event('event2', 'res_child2'),
                  'foo/child3': self._mock_event('event3', 'res_child3')}

        def event_list_stub(stack_id, argfoo):
            return [events[stack_id]]
        mock_client.events.list.side_effect = event_list_stub

        ev_args = {'argfoo': 123}
        # Check nested_depth=1 (non recursive)..
        evs = event_utils._get_nested_events(hc=mock_client,
                                             nested_depth=1,
                                             stack_id='parent',
                                             event_args=ev_args)

        rsrc_calls = [mock.call(stack_id='parent')]
        mock_client.resources.list.assert_has_calls(rsrc_calls)
        ev_calls = [mock.call(stack_id='foo/child1', argfoo=123)]
        mock_client.events.list.assert_has_calls(ev_calls)
        self.assertEqual(1, len(evs))
        self.assertEqual('event1', evs[0].id)

        # ..and the recursive case via nested_depth=3
        mock_client.resources.list.reset_mock()
        mock_client.events.list.reset_mock()
        evs = event_utils._get_nested_events(hc=mock_client,
                                             nested_depth=3,
                                             stack_id='parent',
                                             event_args=ev_args)

        rsrc_calls = [mock.call(stack_id='parent'),
                      mock.call(stack_id='foo/child1'),
                      mock.call(stack_id='foo/child2')]
        mock_client.resources.list.assert_has_calls(rsrc_calls)
        ev_calls = [mock.call(stack_id='foo/child1', argfoo=123),
                    mock.call(stack_id='foo/child2', argfoo=123),
                    mock.call(stack_id='foo/child3', argfoo=123)]
        mock_client.events.list.assert_has_calls(ev_calls)
        self.assertEqual(3, len(evs))
        self.assertEqual('event1', evs[0].id)
        self.assertEqual('event2', evs[1].id)
        self.assertEqual('event3', evs[2].id)

    @mock.patch('heatclient.common.event_utils.get_events')
    def test_poll_for_events(self, ge):
        ge.side_effect = [[
            self._mock_stack_event('1', 'astack', 'CREATE_IN_PROGRESS'),
            self._mock_event('2', 'res_child1', 'CREATE_IN_PROGRESS'),
            self._mock_event('3', 'res_child2', 'CREATE_IN_PROGRESS'),
            self._mock_event('4', 'res_child3', 'CREATE_IN_PROGRESS')
        ], [
            self._mock_event('5', 'res_child1', 'CREATE_COMPLETE'),
            self._mock_event('6', 'res_child2', 'CREATE_COMPLETE'),
            self._mock_event('7', 'res_child3', 'CREATE_COMPLETE'),
            self._mock_stack_event('8', 'astack', 'CREATE_COMPLETE')
        ]]

        stack_status, msg = event_utils.poll_for_events(
            None, 'astack', action='CREATE', poll_period=0)
        self.assertEqual('CREATE_COMPLETE', stack_status)
        self.assertEqual('\n Stack astack CREATE_COMPLETE \n', msg)
        ge.assert_has_calls([
            mock.call(None, stack_id='astack', nested_depth=0, event_args={
                'sort_dir': 'asc', 'marker': None
            }),
            mock.call(None, stack_id='astack', nested_depth=0, event_args={
                'sort_dir': 'asc', 'marker': '4'
            })
        ])

    @mock.patch('heatclient.common.event_utils.get_events')
    def test_poll_for_events_same_name(self, ge):
        ge.side_effect = [[
            self._mock_stack_event('1', 'mything', 'CREATE_IN_PROGRESS'),
            self._mock_event('2', 'res_child1', 'CREATE_IN_PROGRESS'),
            self._mock_event('3', 'mything', 'CREATE_IN_PROGRESS'),
        ], [
            self._mock_event('4', 'mything', 'CREATE_COMPLETE'),
        ], [
            self._mock_event('5', 'res_child1', 'CREATE_COMPLETE'),
            self._mock_stack_event('6', 'mything', 'CREATE_COMPLETE'),
        ]]

        stack_status, msg = event_utils.poll_for_events(
            None, 'mything', action='CREATE', poll_period=0)
        self.assertEqual('CREATE_COMPLETE', stack_status)
        self.assertEqual('\n Stack mything CREATE_COMPLETE \n', msg)
        ge.assert_has_calls([
            mock.call(None, stack_id='mything', nested_depth=0, event_args={
                'sort_dir': 'asc', 'marker': None
            }),
            mock.call(None, stack_id='mything', nested_depth=0, event_args={
                'sort_dir': 'asc', 'marker': '3'
            }),
            mock.call(None, stack_id='mything', nested_depth=0, event_args={
                'sort_dir': 'asc', 'marker': '4'
            })
        ])

    @mock.patch('heatclient.common.event_utils.get_events')
    def test_poll_for_events_with_marker(self, ge):
        ge.side_effect = [[
            self._mock_event('5', 'res_child1', 'CREATE_COMPLETE'),
            self._mock_event('6', 'res_child2', 'CREATE_COMPLETE'),
            self._mock_event('7', 'res_child3', 'CREATE_COMPLETE'),
            self._mock_stack_event('8', 'astack', 'CREATE_COMPLETE')
        ]]

        stack_status, msg = event_utils.poll_for_events(
            None, 'astack', action='CREATE', poll_period=0, marker='4',
            nested_depth=0)
        self.assertEqual('CREATE_COMPLETE', stack_status)
        self.assertEqual('\n Stack astack CREATE_COMPLETE \n', msg)
        ge.assert_has_calls([
            mock.call(None, stack_id='astack', nested_depth=0, event_args={
                'sort_dir': 'asc', 'marker': '4'
            })
        ])

    @mock.patch('heatclient.common.event_utils.get_events')
    def test_poll_for_events_in_progress_resource(self, ge):
        ge.side_effect = [[
            self._mock_stack_event('1', 'astack', 'CREATE_IN_PROGRESS'),
            self._mock_event('2', 'res_child1', 'CREATE_IN_PROGRESS'),
            self._mock_stack_event('3', 'astack', 'CREATE_COMPLETE')
        ]]

        stack_status, msg = event_utils.poll_for_events(
            None, 'astack', action='CREATE', poll_period=0)
        self.assertEqual('CREATE_COMPLETE', stack_status)
        self.assertEqual('\n Stack astack CREATE_COMPLETE \n', msg)

    @mock.patch('heatclient.common.event_utils.get_events')
    def test_poll_for_events_failed(self, ge):
        ge.side_effect = [[
            self._mock_stack_event('1', 'astack', 'CREATE_IN_PROGRESS'),
            self._mock_event('2', 'res_child1', 'CREATE_IN_PROGRESS'),
            self._mock_event('3', 'res_child2', 'CREATE_IN_PROGRESS'),
            self._mock_event('4', 'res_child3', 'CREATE_IN_PROGRESS')
        ], [
            self._mock_event('5', 'res_child1', 'CREATE_COMPLETE'),
            self._mock_event('6', 'res_child2', 'CREATE_FAILED'),
            self._mock_event('7', 'res_child3', 'CREATE_COMPLETE'),
            self._mock_stack_event('8', 'astack', 'CREATE_FAILED')
        ]]

        stack_status, msg = event_utils.poll_for_events(
            None, 'astack', action='CREATE', poll_period=0)
        self.assertEqual('CREATE_FAILED', stack_status)
        self.assertEqual('\n Stack astack CREATE_FAILED \n', msg)

    @mock.patch('heatclient.common.event_utils.get_events')
    def test_poll_for_events_no_action(self, ge):
        ge.side_effect = [[
            self._mock_stack_event('1', 'astack', 'CREATE_IN_PROGRESS'),
            self._mock_event('2', 'res_child1', 'CREATE_IN_PROGRESS'),
            self._mock_event('3', 'res_child2', 'CREATE_IN_PROGRESS'),
            self._mock_event('4', 'res_child3', 'CREATE_IN_PROGRESS')
        ], [
            self._mock_event('5', 'res_child1', 'CREATE_COMPLETE'),
            self._mock_event('6', 'res_child2', 'CREATE_FAILED'),
            self._mock_event('7', 'res_child3', 'CREATE_COMPLETE'),
            self._mock_stack_event('8', 'astack', 'FOO_FAILED')
        ]]

        stack_status, msg = event_utils.poll_for_events(
            None, 'astack', action=None, poll_period=0)
        self.assertEqual('FOO_FAILED', stack_status)
        self.assertEqual('\n Stack astack FOO_FAILED \n', msg)

    @mock.patch('heatclient.common.event_utils.get_events')
    def test_poll_for_events_stack_get(self, ge):
        mock_client = mock.MagicMock()
        mock_client.stacks.get.return_value.stack_status = 'CREATE_FAILED'

        ge.side_effect = [[
            self._mock_stack_event('1', 'astack', 'CREATE_IN_PROGRESS'),
            self._mock_event('2', 'res_child1', 'CREATE_IN_PROGRESS'),
            self._mock_event('3', 'res_child2', 'CREATE_IN_PROGRESS'),
            self._mock_event('4', 'res_child3', 'CREATE_IN_PROGRESS')
        ], [], []]

        stack_status, msg = event_utils.poll_for_events(
            mock_client, 'astack', action='CREATE', poll_period=0)
        self.assertEqual('CREATE_FAILED', stack_status)
        self.assertEqual('\n Stack astack CREATE_FAILED \n', msg)

    def test_wait_for_events(self):
        ws = FakeWebSocket([
            {'body': {
                'timestamp': '2014-01-06T16:14:26Z',
                'payload': {'resource_action': 'CREATE',
                            'resource_status': 'COMPLETE',
                            'resource_name': 'mystack',
                            'physical_resource_id': 'stackid1',
                            'stack_id': 'stackid1'}}}])
        stack_status, msg = event_utils.wait_for_events(ws, 'mystack')
        self.assertEqual('CREATE_COMPLETE', stack_status)
        self.assertEqual('\n Stack mystack CREATE_COMPLETE \n', msg)

    def test_wait_for_events_failed(self):
        ws = FakeWebSocket([
            {'body': {
                'timestamp': '2014-01-06T16:14:23Z',
                'payload': {'resource_action': 'CREATE',
                            'resource_status': 'IN_PROGRESS',
                            'resource_name': 'mystack',
                            'physical_resource_id': 'stackid1',
                            'stack_id': 'stackid1'}}},
            {'body': {
                'timestamp': '2014-01-06T16:14:26Z',
                'payload': {'resource_action': 'CREATE',
                            'resource_status': 'FAILED',
                            'resource_name': 'mystack',
                            'physical_resource_id': 'stackid1',
                            'stack_id': 'stackid1'}}}])
        stack_status, msg = event_utils.wait_for_events(ws, 'mystack')
        self.assertEqual('CREATE_FAILED', stack_status)
        self.assertEqual('\n Stack mystack CREATE_FAILED \n', msg)
