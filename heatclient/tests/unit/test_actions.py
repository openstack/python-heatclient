# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import testtools

from heatclient.tests.unit import fakes
from heatclient.v1 import actions


class ActionManagerTest(testtools.TestCase):

    def setUp(self):
        """
        Sets the safe to set the inputed action.

        Args:
            self: (todo): write your description
        """
        super(ActionManagerTest, self).setUp()

    def _base_test(self, expect_args, expect_kwargs):

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def json_request(self, *args, **kwargs):
                """
                A json request

                Args:
                    self: (todo): write your description
                """
                assert expect_args == args
                assert expect_kwargs['data'] == kwargs['data']
                return fakes.FakeHTTPResponse(
                    '200',
                    '',
                    {'content-type': 'application/json'},
                    {}), {}

            def raw_request(self, *args, **kwargs):
                """
                Make a raw request.

                Args:
                    self: (todo): write your description
                """
                assert expect_args == args
                return fakes.FakeHTTPResponse(
                    '200',
                    '',
                    {},
                    {})

            def head(self, url, **kwargs):
                """
                Make a head request.

                Args:
                    self: (todo): write your description
                    url: (str): write your description
                """
                resp, body = self.json_request("HEAD", url, **kwargs)
                return resp

            def get(self, url, **kwargs):
                """
                Make a get request.

                Args:
                    self: (todo): write your description
                    url: (todo): write your description
                """
                resp, body = self.json_request("GET", url, **kwargs)
                return resp

            def post(self, url, **kwargs):
                """
                Make a post request.

                Args:
                    self: (todo): write your description
                    url: (todo): write your description
                """
                resp, body = self.json_request("POST", url, **kwargs)
                return resp

            def put(self, url, **kwargs):
                """
                Make a put request.

                Args:
                    self: (todo): write your description
                    url: (todo): write your description
                """
                resp, body = self.json_request("PUT", url, **kwargs)
                return resp

            def delete(self, url, **kwargs):
                """
                Make a delete request.

                Args:
                    self: (todo): write your description
                    url: (str): write your description
                """
                resp, body = self.raw_request("DELETE", url, **kwargs)
                return resp

            def patch(self, url, **kwargs):
                """
                Sends a patch request.

                Args:
                    self: (todo): write your description
                    url: (str): write your description
                """
                resp, body = self.json_request("PATCH", url, **kwargs)
                return resp

        manager = actions.ActionManager(FakeAPI())
        return manager

    def test_suspend(self):
        """
        Synchronously run the manager

        Args:
            self: (todo): write your description
        """
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'suspend': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.suspend(**fields)

    def test_resume(self):
        """
        Resume the test.

        Args:
            self: (todo): write your description
        """
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'resume': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.resume(**fields)

    def test_cancel_update(self):
        """
        Cancel the test.

        Args:
            self: (todo): write your description
        """
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'cancel_update': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.cancel_update(**fields)

    def test_cancel_without_rollback(self):
        """
        Cancel the rollback

        Args:
            self: (todo): write your description
        """
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'cancel_without_rollback': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.cancel_without_rollback(**fields)

    def test_check(self):
        """
        Perform test check

        Args:
            self: (todo): write your description
        """
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'check': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.check(**fields)
