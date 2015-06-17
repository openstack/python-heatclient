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

from heatclient.v1 import template_versions


class TemplateVersionManagerTest(testtools.TestCase):

    def setUp(self):
        super(TemplateVersionManagerTest, self).setUp()

    def test_list_versions(self):
        expect = ('GET', '/template_versions')

        class FakeResponse(object):
            def json(self):
                return {'template_versions': [{'version': '2013-05-23',
                                               'type': 'hot'}]}

        class FakeClient(object):
            def get(self, *args, **kwargs):
                assert ('GET', args[0]) == expect
                return FakeResponse()

        manager = template_versions.TemplateVersionManager(FakeClient())
        versions = manager.list()
        self.assertEqual('2013-05-23', getattr(versions[0], 'version'))
        self.assertEqual('hot', getattr(versions[0], 'type'))
