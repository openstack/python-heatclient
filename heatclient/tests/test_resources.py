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

from heatclient.v1.resources import Resource
from heatclient.v1.resources import ResourceManager

from mock import MagicMock
from mox3 import mox
import testtools


class ResourceManagerTest(testtools.TestCase):

    def setUp(self):
        super(ResourceManagerTest, self).setUp()
        self.m = mox.Mox()
        self.addCleanup(self.m.UnsetStubs)
        self.addCleanup(self.m.ResetAll)

    def test_get_event(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': 'testresource'}

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def json_request(self, *args, **kwargs):
                expect = ('GET',
                          '/stacks/teststack%2Fabcd1234/resources'
                          '/testresource')
                assert args == expect
                return {}, {'resource': []}

        manager = ResourceManager(FakeAPI())
        Resource.__init__ = MagicMock()
        Resource.__init__.return_value = None
        self.m.StubOutWithMock(manager, '_resolve_stack_id')
        manager._resolve_stack_id('teststack').AndReturn('teststack/abcd1234')
        self.m.ReplayAll()
        manager.get(**fields)

    def test_get_event_with_unicode_resource_name(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': u'\u5de5\u4f5c'}

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def json_request(self, *args, **kwargs):
                expect = ('GET',
                          '/stacks/teststack%2Fabcd1234/resources'
                          '/%E5%B7%A5%E4%BD%9C')
                assert args == expect
                return {}, {'resource': []}

        manager = ResourceManager(FakeAPI())
        Resource.__init__ = MagicMock()
        Resource.__init__.return_value = None
        self.m.StubOutWithMock(manager, '_resolve_stack_id')
        manager._resolve_stack_id('teststack').AndReturn('teststack/abcd1234')
        self.m.ReplayAll()
        manager.get(**fields)
