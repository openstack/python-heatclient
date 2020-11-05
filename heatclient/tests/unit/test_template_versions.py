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
        """
        Sets the version of the application.

        Args:
            self: (todo): write your description
        """
        super(TemplateVersionManagerTest, self).setUp()

    def test_list_versions(self):
        """
        Return the versions of versions of versions.

        Args:
            self: (todo): write your description
        """
        expect = ('GET', '/template_versions')

        class FakeResponse(object):
            def json(self):
                """
                Returns the json representation of the object.

                Args:
                    self: (todo): write your description
                """
                return {'template_versions': [{'version': '2013-05-23',
                                               'type': 'hot'}]}

        class FakeClient(object):
            def get(self, *args, **kwargs):
                """
                See : class instance.

                Args:
                    self: (todo): write your description
                """
                assert ('GET', args[0]) == expect
                return FakeResponse()

        manager = template_versions.TemplateVersionManager(FakeClient())
        versions = manager.list()
        self.assertEqual('2013-05-23', getattr(versions[0], 'version'))
        self.assertEqual('hot', getattr(versions[0], 'type'))

    def test_get(self):
        """
        Handles the test data.

        Args:
            self: (todo): write your description
        """
        expect = ('GET', '/template_versions/heat_template_version.2015-04-30'
                         '/functions')

        class FakeResponse(object):
            def json(self):
                """
                Returns : class : ~.

                Args:
                    self: (todo): write your description
                """
                return {'template_functions': [{'function': 'get_attr'}]}

        class FakeClient(object):
            def get(self, *args, **kwargs):
                """
                See : class instance.

                Args:
                    self: (todo): write your description
                """
                assert ('GET', args[0]) == expect
                return FakeResponse()

        manager = template_versions.TemplateVersionManager(FakeClient())
        functions = manager.get('heat_template_version.2015-04-30')
        self.assertEqual('get_attr', getattr(functions[0], 'function'))
