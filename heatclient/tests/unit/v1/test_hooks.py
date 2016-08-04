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

import mock
import testtools

from heatclient.common import hook_utils
import heatclient.v1.shell as shell


class TestHooks(testtools.TestCase):
    def setUp(self):
        super(TestHooks, self).setUp()
        self.client = mock.Mock()
        nested_stack = mock.Mock()
        self.client.resources.get = mock.Mock(name='thingy',
                                              return_value=nested_stack)
        type(nested_stack).physical_resource_id = mock.PropertyMock(
            return_value='nested_id')
        self.args = mock.Mock()
        stack_name_p = mock.PropertyMock(return_value="mystack")
        type(self.args).name = stack_name_p
        type(self.args).id = stack_name_p
        shell.template_utils.get_template_contents = mock.Mock(
            return_value=({}, ""))
        shell.template_utils.process_multiple_environments_and_files = (
            mock.Mock(return_value=({}, {})))
        shell.utils.format_all_parameters = mock.Mock(return_value=[])
        shell.do_stack_list = mock.Mock()
        shell.logger = mock.Mock()
        type(self.args).clear_parameter = mock.PropertyMock(return_value=[])
        type(self.args).rollback = mock.PropertyMock(return_value=None)
        type(self.args).pre_create = mock.PropertyMock(return_value=False)
        type(self.args).pre_update = mock.PropertyMock(return_value=False)
        type(self.args).poll = mock.PropertyMock(return_value=None)

    def test_create_hooks_in_args(self):
        type(self.args).pre_create = mock.PropertyMock(
            return_value=['bp', 'another_bp'])

        shell.do_stack_create(self.client, self.args)
        self.assertEqual(1, self.client.stacks.create.call_count)
        expected_hooks = {
            'bp': {'hooks': 'pre-create'},
            'another_bp': {'hooks': 'pre-create'}
        }
        actual_hooks = self.client.stacks.create.call_args[1][
            'environment']['resource_registry']['resources']
        self.assertEqual(expected_hooks, actual_hooks)

    def test_create_nested_hooks_in_args(self):
        type(self.args).pre_create = mock.PropertyMock(
            return_value=['nested/bp', 'super/nested/bp'])

        shell.do_stack_create(self.client, self.args)
        self.assertEqual(1, self.client.stacks.create.call_count)
        expected_hooks = {
            'nested': {
                'bp': {'hooks': 'pre-create'},
            },
            'super': {
                'nested': {
                    'bp': {'hooks': 'pre-create'},
                }
            }
        }
        actual_hooks = self.client.stacks.create.call_args[1][
            'environment']['resource_registry']['resources']
        self.assertEqual(expected_hooks, actual_hooks)

    def test_create_hooks_in_env_and_args(self):
        type(self.args).pre_create = mock.PropertyMock(return_value=[
            'nested_a/bp',
            'bp_a',
            'another_bp_a',
            'super_a/nested/bp',
        ])
        env = {
            'resource_registry': {
                'resources': {
                    'bp_e': {'hooks': 'pre-create'},
                    'another_bp_e': {'hooks': 'pre-create'},
                    'nested_e': {
                        'bp': {'hooks': 'pre-create'}
                    },
                    'super_e': {
                        'nested': {
                            'bp': {'hooks': 'pre-create'}
                        }
                    }
                }
            }
        }
        shell.template_utils.process_multiple_environments_and_files = (
            mock.Mock(return_value=({}, env)))

        shell.do_stack_create(self.client, self.args)
        self.assertEqual(1, self.client.stacks.create.call_count)
        actual_hooks = self.client.stacks.create.call_args[1][
            'environment']['resource_registry']['resources']
        expected_hooks = {
            'bp_e': {'hooks': 'pre-create'},
            'another_bp_e': {'hooks': 'pre-create'},
            'nested_e': {
                'bp': {'hooks': 'pre-create'}
            },
            'super_e': {
                'nested': {
                    'bp': {'hooks': 'pre-create'}
                }
            },
            'bp_a': {'hooks': 'pre-create'},
            'another_bp_a': {'hooks': 'pre-create'},
            'nested_a': {
                'bp': {'hooks': 'pre-create'}
            },
            'super_a': {
                'nested': {
                    'bp': {'hooks': 'pre-create'}
                }
            },
        }
        self.assertEqual(expected_hooks, actual_hooks)

    def test_update_hooks_in_args(self):
        type(self.args).pre_update = mock.PropertyMock(
            return_value=['bp', 'another_bp'])

        shell.do_stack_update(self.client, self.args)
        self.assertEqual(1, self.client.stacks.update.call_count)
        expected_hooks = {
            'bp': {'hooks': 'pre-update'},
            'another_bp': {'hooks': 'pre-update'},
        }
        actual_hooks = self.client.stacks.update.call_args[1][
            'environment']['resource_registry']['resources']
        self.assertEqual(expected_hooks, actual_hooks)

    def test_update_nested_hooks_in_args(self):
        type(self.args).pre_update = mock.PropertyMock(
            return_value=['nested/bp', 'super/nested/bp'])

        shell.do_stack_update(self.client, self.args)
        self.assertEqual(1, self.client.stacks.update.call_count)
        expected_hooks = {
            'nested': {
                'bp': {'hooks': 'pre-update'}
            },
            'super': {
                'nested': {
                    'bp': {'hooks': 'pre-update'}
                }
            }
        }
        actual_hooks = self.client.stacks.update.call_args[1][
            'environment']['resource_registry']['resources']
        self.assertEqual(expected_hooks, actual_hooks)

    def test_update_hooks_in_env_and_args(self):
        type(self.args).pre_update = mock.PropertyMock(return_value=[
            'nested_a/bp',
            'bp_a',
            'another_bp_a',
            'super_a/nested/bp',
        ])
        env = {
            'resource_registry': {
                'resources': {
                    'bp_e': {'hooks': 'pre-update'},
                    'another_bp_e': {'hooks': 'pre-update'},
                    'nested_e': {
                        'bp': {'hooks': 'pre-update'}
                    },
                    'super_e': {
                        'nested': {
                            'bp': {'hooks': 'pre-update'}
                        }
                    }
                }
            }
        }
        shell.template_utils.process_multiple_environments_and_files = (
            mock.Mock(return_value=({}, env)))

        shell.do_stack_update(self.client, self.args)
        self.assertEqual(1, self.client.stacks.update.call_count)
        actual_hooks = self.client.stacks.update.call_args[1][
            'environment']['resource_registry']['resources']
        expected_hooks = {
            'bp_e': {'hooks': 'pre-update'},
            'another_bp_e': {'hooks': 'pre-update'},
            'nested_e': {
                'bp': {'hooks': 'pre-update'}
            },
            'super_e': {
                'nested': {
                    'bp': {'hooks': 'pre-update'}
                }
            },
            'bp_a': {'hooks': 'pre-update'},
            'another_bp_a': {'hooks': 'pre-update'},
            'nested_a': {
                'bp': {'hooks': 'pre-update'}
            },
            'super_a': {
                'nested': {
                    'bp': {'hooks': 'pre-update'}
                }
            },
        }
        self.assertEqual(expected_hooks, actual_hooks)

    def test_clear_all_hooks(self):
        hook_utils.get_hook_type_via_status = mock.Mock(
            return_value='pre-create')
        type(self.args).hook = mock.PropertyMock(
            return_value=['bp'])
        type(self.args).pre_create = mock.PropertyMock(return_value=True)
        bp = mock.Mock()
        type(bp).resource_name = 'bp'
        self.client.resources.list = mock.Mock(return_value=[bp])

        shell.do_hook_clear(self.client, self.args)
        self.assertEqual(1, self.client.resources.signal.call_count)
        payload_pre_create = self.client.resources.signal.call_args_list[0][1]
        self.assertEqual({'unset_hook': 'pre-create'},
                         payload_pre_create['data'])
        self.assertEqual('bp', payload_pre_create['resource_name'])
        self.assertEqual('mystack', payload_pre_create['stack_id'])

    def test_clear_pre_create_hooks(self):
        type(self.args).hook = mock.PropertyMock(
            return_value=['bp'])
        type(self.args).pre_create = mock.PropertyMock(return_value=True)
        bp = mock.Mock()
        type(bp).resource_name = 'bp'
        self.client.resources.list = mock.Mock(return_value=[bp])

        shell.do_hook_clear(self.client, self.args)
        self.assertEqual(1, self.client.resources.signal.call_count)
        payload = self.client.resources.signal.call_args_list[0][1]
        self.assertEqual({'unset_hook': 'pre-create'}, payload['data'])
        self.assertEqual('bp', payload['resource_name'])
        self.assertEqual('mystack', payload['stack_id'])

    def test_clear_pre_update_hooks(self):
        type(self.args).hook = mock.PropertyMock(
            return_value=['bp'])
        type(self.args).pre_update = mock.PropertyMock(return_value=True)
        bp = mock.Mock()
        type(bp).resource_name = 'bp'
        self.client.resources.list = mock.Mock(return_value=[bp])

        shell.do_hook_clear(self.client, self.args)
        self.assertEqual(1, self.client.resources.signal.call_count)
        payload = self.client.resources.signal.call_args_list[0][1]
        self.assertEqual({'unset_hook': 'pre-update'}, payload['data'])
        self.assertEqual('bp', payload['resource_name'])
        self.assertEqual('mystack', payload['stack_id'])

    def test_clear_pre_delete_hooks(self):
        type(self.args).hook = mock.PropertyMock(
            return_value=['bp'])
        type(self.args).pre_delete = mock.PropertyMock(return_value=True)
        bp = mock.Mock()
        type(bp).resource_name = 'bp'
        self.client.resources.list = mock.Mock(return_value=[bp])

        shell.do_hook_clear(self.client, self.args)
        self.assertEqual(1, self.client.resources.signal.call_count)
        payload = self.client.resources.signal.call_args_list[0][1]
        self.assertEqual({'unset_hook': 'pre-delete'}, payload['data'])
        self.assertEqual('bp', payload['resource_name'])
        self.assertEqual('mystack', payload['stack_id'])

    def test_clear_nested_hook(self):
        type(self.args).hook = mock.PropertyMock(
            return_value=['a/b/bp'])
        type(self.args).pre_create = mock.PropertyMock(return_value=True)

        a = mock.Mock()
        type(a).resource_name = 'a'
        b = mock.Mock()
        type(b).resource_name = 'b'
        bp = mock.Mock()
        type(bp).resource_name = 'bp'
        self.client.resources.list = mock.Mock(
            side_effect=[[a], [b], [bp]])
        m1 = mock.Mock()
        m2 = mock.Mock()
        type(m2).physical_resource_id = 'nested_id'
        self.client.resources.get = mock.Mock(
            side_effect=[m1, m2])

        shell.do_hook_clear(self.client, self.args)
        payload = self.client.resources.signal.call_args_list[0][1]
        self.assertEqual({'unset_hook': 'pre-create'}, payload['data'])
        self.assertEqual('bp', payload['resource_name'])
        self.assertEqual('nested_id', payload['stack_id'])

    def test_clear_wildcard_hooks(self):
        type(self.args).hook = mock.PropertyMock(
            return_value=['a/*b/bp*'])
        type(self.args).pre_create = mock.PropertyMock(return_value=True)
        a = mock.Mock()
        type(a).resource_name = 'a'
        b = mock.Mock()
        type(b).resource_name = 'matcthis_b'
        bp = mock.Mock()
        type(bp).resource_name = 'bp_matchthis'
        self.client.resources.list = mock.Mock(
            side_effect=[[a], [b], [bp]])
        m1 = mock.Mock()
        m2 = mock.Mock()
        type(m2).physical_resource_id = 'nested_id'
        self.client.resources.get = mock.Mock(
            side_effect=[m1, m2])

        shell.do_hook_clear(self.client, self.args)
        payload = self.client.resources.signal.call_args_list[0][1]
        self.assertEqual({'unset_hook': 'pre-create'},
                         payload['data'])
        self.assertEqual('bp_matchthis', payload['resource_name'])
        self.assertEqual('nested_id', payload['stack_id'])
