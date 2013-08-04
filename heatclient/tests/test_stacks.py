# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from heatclient.v1.stacks import Stack

from mock import MagicMock
import testscenarios
from testscenarios.scenarios import multiply_scenarios
import testtools


load_tests = testscenarios.load_tests_apply_scenarios


class StackStatusActionTest(testtools.TestCase):

    scenarios = multiply_scenarios([
        ('CREATE', dict(action='CREATE')),
        ('DELETE', dict(action='DELETE')),
        ('UPDATE', dict(action='UPDATE')),
        ('ROLLBACK', dict(action='ROLLBACK')),
        ('SUSPEND', dict(action='SUSPEND')),
        ('RESUME', dict(action='RESUME'))
    ], [
        ('IN_PROGRESS', dict(status='IN_PROGRESS')),
        ('FAILED', dict(status='FAILED')),
        ('COMPLETE', dict(status='COMPLETE'))
    ])

    def test_status_action(self):
        stack_status = '%s_%s' % (self.action, self.status)
        stack = Stack(None, {'stack_status': stack_status})
        self.assertEqual(self.action, stack.action)
        self.assertEqual(self.status, stack.status)


class StackOperationsTest(testtools.TestCase):

    def test_delete_stack(self):
        manager = MagicMock()
        stack = Stack(manager, {'id': 'abcd1234'})
        stack.delete()
        manager.delete.assert_called_once_with('abcd1234')
