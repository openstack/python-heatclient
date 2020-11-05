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

from unittest import mock

import testtools

from heatclient.common import utils
from heatclient.v1 import resource_types


class ResourceTypeManagerTest(testtools.TestCase):

    def _base_test(self, expect, key):

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def get(self, *args, **kwargs):
                """
                Return the first argument.

                Args:
                    self: (todo): write your description
                """
                assert ('GET', args[0]) == expect

            def json_request(self, *args, **kwargs):
                """
                Return json data

                Args:
                    self: (todo): write your description
                """
                assert args == expect
                ret = key and {key: []} or {}
                return {}, {key: ret}

            def raw_request(self, *args, **kwargs):
                """
                Convenience method.

                Args:
                    self: (todo): write your description
                """
                assert args == expect
                return {}

            def head(self, url, **kwargs):
                """
                Make a head request.

                Args:
                    self: (todo): write your description
                    url: (str): write your description
                """
                return self.json_request("HEAD", url, **kwargs)

            def post(self, url, **kwargs):
                """
                Make a post request.

                Args:
                    self: (todo): write your description
                    url: (todo): write your description
                """
                return self.json_request("POST", url, **kwargs)

            def put(self, url, **kwargs):
                """
                Make a put request.

                Args:
                    self: (todo): write your description
                    url: (todo): write your description
                """
                return self.json_request("PUT", url, **kwargs)

            def delete(self, url, **kwargs):
                """
                Make a delete request.

                Args:
                    self: (todo): write your description
                    url: (str): write your description
                """
                return self.raw_request("DELETE", url, **kwargs)

            def patch(self, url, **kwargs):
                """
                Sends a patch request.

                Args:
                    self: (todo): write your description
                    url: (str): write your description
                """
                return self.json_request("PATCH", url, **kwargs)

        manager = resource_types.ResourceTypeManager(FakeAPI())
        return manager

    def test_list_types(self):
        """
        Return a dictionary of the resource types.

        Args:
            self: (todo): write your description
        """
        key = 'resource_types'
        expect = ('GET', '/resource_types')

        class FakeResponse(object):
            def json(self):
                """
                Return a json - serialization.

                Args:
                    self: (todo): write your description
                """
                return {key: {}}

        class FakeClient(object):
            def get(self, *args, **kwargs):
                """
                See : class instance.

                Args:
                    self: (todo): write your description
                """
                assert ('GET', args[0]) == expect
                return FakeResponse()

        manager = resource_types.ResourceTypeManager(FakeClient())
        manager.list()

    def test_list_types_with_filters(self):
        """
        Return a list of the mock types.

        Args:
            self: (todo): write your description
        """
        filters = {'name': 'OS::Keystone::*',
                   'version': '5.0.0',
                   'support_status': 'SUPPORTED'}

        manager = resource_types.ResourceTypeManager(None)
        with mock.patch.object(manager, '_list') as mock_list:
            mock_list.return_value = None
            manager.list(filters=filters)
            self.assertEqual(1, mock_list.call_count)
            url, param = mock_list.call_args[0]
            self.assertEqual("resource_types", param)
            base_url, query_params = utils.parse_query_url(url)
            self.assertEqual('/%s' % manager.KEY, base_url)
            # parameters in query_params is in list format, so filter params
            # are made to be inline with it
            filters_params = {}
            for item in filters:
                filters_params[item] = [filters[item]]

            self.assertEqual(filters_params, query_params)

    @mock.patch.object(utils, 'get_response_body')
    def test_get(self, mock_utils):
        """
        Gets the test.

        Args:
            self: (todo): write your description
            mock_utils: (todo): write your description
        """
        key = 'resource_types'
        resource_type = 'OS::Nova::KeyPair'
        expect = ('GET', '/resource_types/OS%3A%3ANova%3A%3AKeyPair')
        manager = self._base_test(expect, key)
        mock_utils.return_value = None
        manager.get(resource_type)

    @mock.patch.object(utils, 'get_response_body')
    def test_generate_template(self, mock_utils):
        """
        Generate a test template.

        Args:
            self: (todo): write your description
            mock_utils: (todo): write your description
        """
        key = 'resource_types'
        resource_type = 'OS::Nova::KeyPair'
        template_type = 'cfn'
        expect = ('GET', '/resource_types/OS%3A%3ANova%3A%3AKeyPair/template'
                         '?template_type=cfn')
        manager = self._base_test(expect, key)
        mock_utils.return_value = None
        manager.generate_template(resource_type, template_type)
