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
import testtools

from heatclient.v1.resource_types import ResourceTypeManager


class ResourceTypeManagerTest(testtools.TestCase):

    def test_list_types(self):
        manager = ResourceTypeManager(None)
        manager._list = mock.MagicMock()
        manager.list()
        manager._list.assert_called_once_with('/resource_types',
                                              'resource_types')

    def test_get(self):
        resource_type = u'OS::Nova::KeyPair'

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""
            def __init__(self, *args, **kwargs):
                self.requests = []

            def json_request(self, *args, **kwargs):
                self.requests.append(args)
                return {}, {'attributes': [], 'properties': []}

        test_api = FakeAPI()
        manager = ResourceTypeManager(test_api)
        manager.get(resource_type)
        expect = ('GET', '/resource_types/OS%3A%3ANova%3A%3AKeyPair')
        self.assertIn(expect, test_api.requests)
