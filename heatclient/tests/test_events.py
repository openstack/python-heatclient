# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from heatclient.v1.events import EventManager

from mock import MagicMock
from mock import patch
import mox
import testtools


class EventManagerTest(testtools.TestCase):

    def setUp(self):
        super(EventManagerTest, self).setUp()
        self.m = mox.Mox()
        self.addCleanup(self.m.UnsetStubs)
        self.addCleanup(self.m.ResetAll)

    def test_list_event(self):
        stack_id = 'teststack',
        resource_name = 'testresource'
        manager = EventManager(None)
        self.m.StubOutWithMock(manager, '_resolve_stack_id')
        manager._resolve_stack_id(stack_id).AndReturn('teststack/abcd1234')
        self.m.ReplayAll()
        manager._list = MagicMock()
        manager.list(stack_id, resource_name)
        # Make sure url is correct.
        manager._list.assert_called_once_with('/stacks/teststack%2Fabcd1234/'
                                              'resources/testresource/events',
                                              "events")

    def test_list_event_with_unicode_resource_name(self):
        stack_id = 'teststack',
        resource_name = u'\u5de5\u4f5c'
        manager = EventManager(None)
        self.m.StubOutWithMock(manager, '_resolve_stack_id')
        manager._resolve_stack_id(stack_id).AndReturn('teststack/abcd1234')
        self.m.ReplayAll()
        manager._list = MagicMock()
        manager.list(stack_id, resource_name)
        # Make sure url is correct.
        manager._list.assert_called_once_with('/stacks/teststack%2Fabcd1234/'
                                              'resources/%E5%B7%A5%E4%BD%9C/'
                                              'events', "events")

    def test_list_event_with_none_resource_name(self):
        stack_id = 'teststack',
        manager = EventManager(None)
        manager._list = MagicMock()
        manager.list(stack_id)
        # Make sure url is correct.
        manager._list.assert_called_once_with('/stacks/teststack/'
                                              'events', "events")

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

        manager = EventManager(FakeAPI())
        with patch('heatclient.v1.events.Event'):
            self.m.StubOutWithMock(manager, '_resolve_stack_id')
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

        manager = EventManager(FakeAPI())
        with patch('heatclient.v1.events.Event'):
            self.m.StubOutWithMock(manager, '_resolve_stack_id')
            manager._resolve_stack_id('teststack').AndReturn(
                'teststack/abcd1234')
            self.m.ReplayAll()
            manager.get(**fields)
