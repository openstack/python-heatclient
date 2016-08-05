# Copyright 2013 IBM Corp.
#
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

import mock
import mox
import testtools

from heatclient.common import utils
from heatclient.v1 import events


class EventManagerTest(testtools.TestCase):

    def setUp(self):
        super(EventManagerTest, self).setUp()
        self.m = mox.Mox()
        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def test_list_event(self):
        stack_id = 'teststack',
        resource_name = 'testresource'
        manager = events.EventManager(None)
        self.m.StubOutWithMock(manager, '_resolve_stack_id')
        manager._resolve_stack_id(stack_id).AndReturn('teststack/abcd1234')
        self.m.ReplayAll()
        manager._list = mock.MagicMock()
        manager.list(stack_id, resource_name)
        # Make sure url is correct.
        manager._list.assert_called_once_with('/stacks/teststack%2Fabcd1234/'
                                              'resources/testresource/events',
                                              "events")

    def test_list_event_with_unicode_resource_name(self):
        stack_id = 'teststack',
        resource_name = u'\u5de5\u4f5c'
        manager = events.EventManager(None)
        self.m.StubOutWithMock(manager, '_resolve_stack_id')
        manager._resolve_stack_id(stack_id).AndReturn('teststack/abcd1234')
        self.m.ReplayAll()
        manager._list = mock.MagicMock()
        manager.list(stack_id, resource_name)
        # Make sure url is correct.
        manager._list.assert_called_once_with('/stacks/teststack%2Fabcd1234/'
                                              'resources/%E5%B7%A5%E4%BD%9C/'
                                              'events', "events")

    def test_list_event_with_none_resource_name(self):
        stack_id = 'teststack',
        manager = events.EventManager(None)
        manager._list = mock.MagicMock()
        manager.list(stack_id)
        # Make sure url is correct.
        manager._list.assert_called_once_with('/stacks/teststack/'
                                              'events', "events")

    def test_list_event_with_kwargs(self):
        stack_id = 'teststack',
        resource_name = 'testresource'
        kwargs = {'limit': 2,
                  'marker': '6d6935f4-0ae5',
                  'filters': {
                      'resource_action': 'CREATE',
                      'resource_status': 'COMPLETE'
                  }}
        manager = events.EventManager(None)
        self.m.StubOutWithMock(manager, '_resolve_stack_id')
        manager._resolve_stack_id(stack_id).AndReturn('teststack/abcd1234')
        self.m.ReplayAll()
        manager._list = mock.MagicMock()
        manager.list(stack_id, resource_name, **kwargs)
        # Make sure url is correct.
        self.assertEqual(1, manager._list.call_count)
        args = manager._list.call_args
        self.assertEqual(2, len(args[0]))
        url, param = args[0]
        self.assertEqual("events", param)
        base_url, query_params = utils.parse_query_url(url)
        expected_base_url = ('/stacks/teststack%2Fabcd1234/'
                             'resources/testresource/events')
        self.assertEqual(expected_base_url, base_url)
        expected_query_dict = {'marker': ['6d6935f4-0ae5'],
                               'limit': ['2'],
                               'resource_action': ['CREATE'],
                               'resource_status': ['COMPLETE']}
        self.assertEqual(expected_query_dict, query_params)

    def test_get_event(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': 'testresource',
                  'event_id': '1'}

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def json_request(self, *args, **kwargs):
                expect = ('GET',
                          '/stacks/teststack%2Fabcd1234/resources'
                          '/testresource/events/1')
                assert args == expect
                return {}, {'event': []}

            def get(self, *args, **kwargs):
                pass

        manager = events.EventManager(FakeAPI())
        with mock.patch('heatclient.v1.events.Event'):
            self.m.StubOutWithMock(manager, '_resolve_stack_id')
            self.m.StubOutWithMock(utils, 'get_response_body')
            utils.get_response_body(mox.IgnoreArg()).AndReturn({'event': []})
            manager._resolve_stack_id('teststack').AndReturn(
                'teststack/abcd1234')
            self.m.ReplayAll()
            manager.get(**fields)

    def test_get_event_with_unicode_resource_name(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': u'\u5de5\u4f5c',
                  'event_id': '1'}

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def json_request(self, *args, **kwargs):
                expect = ('GET',
                          '/stacks/teststack%2Fabcd1234/resources'
                          '/%E5%B7%A5%E4%BD%9C/events/1')
                assert args == expect
                return {}, {'event': []}

            def get(self, *args, **kwargs):
                pass

        manager = events.EventManager(FakeAPI())
        with mock.patch('heatclient.v1.events.Event'):
            self.m.StubOutWithMock(manager, '_resolve_stack_id')
            self.m.StubOutWithMock(utils, 'get_response_body')
            utils.get_response_body(mox.IgnoreArg()).AndReturn({'event': []})
            manager._resolve_stack_id('teststack').AndReturn(
                'teststack/abcd1234')
            self.m.ReplayAll()
            manager.get(**fields)
