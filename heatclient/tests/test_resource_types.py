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

import testtools

from heatclient.v1 import resource_types


class ResourceTypeManagerTest(testtools.TestCase):

    def _base_test(self, expect, key):

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def get(self, *args, **kwargs):
                assert ('GET', args[0]) == expect

            def json_request(self, *args, **kwargs):
                assert args == expect
                ret = key and {key: []} or {}
                return {}, {key: ret}

        manager = resource_types.ResourceTypeManager(FakeAPI())
        return manager

    def test_list_types(self):
        key = 'resource_types'
        expect = ('GET', '/resource_types')

        class FakeResponse(object):
            def json(self):
                return {key: {}}

        class FakeClient(object):
            def get(self, *args, **kwargs):
                assert ('GET', args[0]) == expect
                return FakeResponse()

        manager = resource_types.ResourceTypeManager(FakeClient())
        manager.list()

    def test_get(self):
        key = 'resource_types'
        resource_type = 'OS::Nova::KeyPair'
        expect = ('GET', '/resource_types/OS%3A%3ANova%3A%3AKeyPair')
        manager = self._base_test(expect, key)
        manager.get(resource_type)

    def test_generate_template(self):
        key = 'resource_types'
        resource_type = 'OS::Nova::KeyPair'
        expect = ('GET', '/resource_types/OS%3A%3ANova%3A%3AKeyPair/template')
        manager = self._base_test(expect, key)
        manager.generate_template(resource_type)
