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

from heatclient.v1 import actions

import testtools


class ActionManagerTest(testtools.TestCase):

    def setUp(self):
        super(ActionManagerTest, self).setUp()

    def _base_test(self, expect_args, expect_kwargs):

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def json_request(self, *args, **kwargs):
                assert expect_args == args
                assert expect_kwargs['data'] == kwargs['data']
                return {}, {}

        manager = actions.ActionManager(FakeAPI())
        return manager

    def test_suspend(self):
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'suspend': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.suspend(**fields)

    def test_resume(self):
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'resume': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.resume(**fields)

    def test_cancel_update(self):
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'cancel_update': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.cancel_update(**fields)

    def test_check(self):
        fields = {'stack_id': 'teststack%2Fabcd1234'}
        expect_args = ('POST',
                       '/stacks/teststack%2Fabcd1234/actions')
        expect_kwargs = {'data': {'check': None}}

        manager = self._base_test(expect_args, expect_kwargs)
        manager.check(**fields)
