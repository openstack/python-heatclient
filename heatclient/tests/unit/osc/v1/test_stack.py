#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

import copy
import io

import mock
from osc_lib import exceptions as exc
from osc_lib import utils
import six
import testscenarios
import yaml

from heatclient.common import template_format
from heatclient import exc as heat_exc
from heatclient.osc.v1 import stack
from heatclient.tests import inline_templates
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes
from heatclient.v1 import events
from heatclient.v1 import resources
from heatclient.v1 import stacks

load_tests = testscenarios.load_tests_apply_scenarios


class TestStack(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestStack, self).setUp()
        self.mock_client = self.app.client_manager.orchestration
        self.stack_client = self.app.client_manager.orchestration.stacks


class TestStackCreate(TestStack):

    template_path = 'heatclient/tests/test_templates/empty.yaml'
    env_path = 'heatclient/tests/unit/var/environment.json'

    defaults = {
        'stack_name': 'my_stack',
        'disable_rollback': True,
        'parameters': {},
        'template': {'heat_template_version': '2013-05-23'},
        'files': {},
        'environment': {}
    }

    def setUp(self):
        super(TestStackCreate, self).setUp()
        self.cmd = stack.CreateStack(self.app, None)
        self.stack_client.create.return_value = {'stack': {'id': '1234'}}
        self.stack_client.get.return_value = {
            'stack_status': 'create_complete'}
        self.stack_client.preview.return_value = stacks.Stack(
            None, {'stack': {'id', '1234'}})
        stack._authenticated_fetcher = mock.MagicMock()

    def test_stack_create_defaults(self):
        arglist = ['my_stack', '-t', self.template_path]
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**self.defaults)

    def test_stack_create_with_env(self):
        arglist = ['my_stack', '-t', self.template_path, '-e', self.env_path]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.assertEqual(1, self.stack_client.create.call_count)
        args = self.stack_client.create.call_args[1]
        self.assertEqual({'parameters': {}}, args.get('environment'))
        self.assertIn(self.env_path, args.get('environment_files')[0])

    def test_stack_create_rollback(self):
        arglist = ['my_stack', '-t', self.template_path, '--enable-rollback']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['disable_rollback'] = False
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**kwargs)

    def test_stack_create_parameters(self):
        template_path = ('/'.join(self.template_path.split('/')[:-1]) +
                         '/parameters.yaml')
        arglist = ['my_stack', '-t', template_path, '--parameter', 'p1=a',
                   '--parameter', 'p2=6']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['parameters'] = {'p1': 'a', 'p2': '6'}
        kwargs['template']['parameters'] = {'p1': {'type': 'string'},
                                            'p2': {'type': 'number'}}
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**kwargs)

    def test_stack_create_tags(self):
        arglist = ['my_stack', '-t', self.template_path, '--tags', 'tag1,tag2']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['tags'] = 'tag1,tag2'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**kwargs)

    def test_stack_create_timeout(self):
        arglist = ['my_stack', '-t', self.template_path, '--timeout', '60']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['timeout_mins'] = 60
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**kwargs)

    def test_stack_create_pre_create(self):
        arglist = ['my_stack', '-t', self.template_path, '--pre-create', 'a']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['environment'] = {
            'resource_registry': {'resources': {'a': {'hooks': 'pre-create'}}}
        }
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**kwargs)

    @mock.patch('heatclient.common.event_utils.poll_for_events',
                return_value=('CREATE_COMPLETE',
                              'Stack my_stack CREATE_COMPLETE'))
    def test_stack_create_wait(self, mock_poll):
        arglist = ['my_stack', '-t', self.template_path, '--wait']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**self.defaults)
        self.stack_client.get.assert_called_with(**{'stack_id': '1234',
                                                    'resolve_outputs': False})

    @mock.patch('heatclient.common.event_utils.poll_for_events',
                return_value=('CREATE_FAILED',
                              'Stack my_stack CREATE_FAILED'))
    def test_stack_create_wait_fail(self, mock_wait):
        arglist = ['my_stack', '-t', self.template_path, '--wait']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_stack_create_dry_run(self):
        arglist = ['my_stack', '-t', self.template_path, '--dry-run']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.preview.assert_called_with(**self.defaults)
        self.stack_client.create.assert_not_called()


class TestStackUpdate(TestStack):

    template_path = 'heatclient/tests/test_templates/empty.yaml'
    env_path = 'heatclient/tests/unit/var/environment.json'

    defaults = {
        'stack_id': 'my_stack',
        'environment': {},
        'existing': False,
        'files': {},
        'template': {'heat_template_version': '2013-05-23'},
        'parameters': {},
    }

    def setUp(self):
        super(TestStackUpdate, self).setUp()
        self.cmd = stack.UpdateStack(self.app, None)
        self.stack_client.update.return_value = {'stack': {'id': '1234'}}
        self.stack_client.preview_update.return_value = {
            'resource_changes': {'added': [],
                                 'deleted': [],
                                 'replaced': [],
                                 'unchanged': [],
                                 'updated': []}}
        self.stack_client.get.return_value = {
            'stack_status': 'create_complete'}

    def test_stack_update_defaults(self):
        arglist = ['my_stack', '-t', self.template_path]
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**self.defaults)

    def test_stack_update_with_env(self):
        arglist = ['my_stack', '-t', self.template_path, '-e', self.env_path]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.assertEqual(1, self.stack_client.update.call_count)
        args = self.stack_client.update.call_args[1]
        self.assertEqual({'parameters': {}}, args.get('environment'))
        self.assertIn(self.env_path, args.get('environment_files')[0])

    def test_stack_update_rollback_enabled(self):
        arglist = ['my_stack', '-t', self.template_path, '--rollback',
                   'enabled']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['disable_rollback'] = False
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_rollback_disabled(self):
        arglist = ['my_stack', '-t', self.template_path, '--rollback',
                   'disabled']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['disable_rollback'] = True
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_rollback_keep(self):
        arglist = ['my_stack', '-t', self.template_path, '--rollback',
                   'keep']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.assertNotIn('disable_rollback', self.defaults)
        self.stack_client.update.assert_called_with(**self.defaults)

    def test_stack_update_rollback_invalid(self):
        arglist = ['my_stack', '-t', self.template_path, '--rollback', 'foo']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['disable_rollback'] = False
        parsed_args = self.check_parser(self.cmd, arglist, [])

        ex = self.assertRaises(exc.CommandError, self.cmd.take_action,
                               parsed_args)
        self.assertEqual("--rollback invalid value: foo", six.text_type(ex))

    def test_stack_update_parameters(self):
        template_path = ('/'.join(self.template_path.split('/')[:-1]) +
                         '/parameters.yaml')
        arglist = ['my_stack', '-t', template_path, '--parameter', 'p1=a',
                   '--parameter', 'p2=6']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['parameters'] = {'p1': 'a', 'p2': '6'}
        kwargs['template']['parameters'] = {'p1': {'type': 'string'},
                                            'p2': {'type': 'number'}}
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_clear_parameters(self):
        arglist = ['my_stack', '-t', self.template_path, '--clear-parameter',
                   'a']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['clear_parameters'] = ['a']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_tags(self):
        arglist = ['my_stack', '-t', self.template_path, '--tags', 'tag1,tag2']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['tags'] = 'tag1,tag2'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_timeout(self):
        arglist = ['my_stack', '-t', self.template_path, '--timeout', '60']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['timeout_mins'] = 60
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_converge(self):
        arglist = ['my_stack', '-t', self.template_path, '--converge']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['converge'] = True
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_pre_update(self):
        arglist = ['my_stack', '-t', self.template_path, '--pre-update', 'a']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['environment'] = {
            'resource_registry': {'resources': {'a': {'hooks': 'pre-update'}}}
        }
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_existing(self):
        arglist = ['my_stack', '-t', self.template_path, '--existing']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['existing'] = True
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**kwargs)

    def test_stack_update_dry_run(self):
        arglist = ['my_stack', '-t', self.template_path, '--dry-run']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.preview_update.assert_called_with(**self.defaults)
        self.stack_client.update.assert_not_called()

    def test_stack_update_dry_run_show_nested(self):
        arglist = ['my_stack', '-t', self.template_path, '--dry-run',
                   '--show-nested']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.preview_update.assert_called_with(
            show_nested=True, **self.defaults)
        self.stack_client.update.assert_not_called()

    @mock.patch('heatclient.common.event_utils.poll_for_events',
                return_value=('UPDATE_COMPLETE',
                              'Stack my_stack UPDATE_COMPLETE'))
    @mock.patch('heatclient.common.event_utils.get_events', return_value=[])
    def test_stack_update_wait(self, ge, mock_poll):
        arglist = ['my_stack', '-t', self.template_path, '--wait']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.get.return_value = mock.MagicMock(
            stack_name='my_stack')

        self.cmd.take_action(parsed_args)

        self.stack_client.update.assert_called_with(**self.defaults)
        self.stack_client.get.assert_called_with(**{'stack_id': 'my_stack',
                                                    'resolve_outputs': False})

    @mock.patch('heatclient.common.event_utils.poll_for_events',
                return_value=('UPDATE_FAILED',
                              'Stack my_stack UPDATE_FAILED'))
    @mock.patch('heatclient.common.event_utils.get_events', return_value=[])
    def test_stack_update_wait_fail(self, ge, mock_poll):
        arglist = ['my_stack', '-t', self.template_path, '--wait']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.stack_client.get.return_value = mock.MagicMock(
            stack_name='my_stack')

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)


class TestStackShow(TestStack):

    scenarios = [
        ('table', dict(
            format='table')),
        ('shell', dict(
            format='shell')),
        ('value', dict(
            format='value')),
    ]

    get_response = {"stack": {
        "disable_rollback": True,
        "description": "This is a\ndescription\n",
        "parent": None,
        "tags": None,
        "stack_name": "a",
        "stack_user_project_id": "02ad9bd403d44ff9ba128cf9ce77f989",
        "stack_status_reason": "Stack UPDATE completed successfully",
        "creation_time": "2015-08-04T04:46:10",
        "links": [{
            "href": "http://192.0.2.1:8004/v1/5dcd28/stacks/a/4af43781",
            "rel": "self"
        }],
        "capabilities": [],
        "notification_topics": [],
        "updated_time": "2015-08-05T21:33:28",
        "timeout_mins": None,
        "stack_status": "UPDATE_COMPLETE",
        "stack_owner": None,
        "parameters": {
            "OS::project_id": "e0e5e140c5854c259a852621b65dcd28",
            "OS::stack_id": "4af43781",
            "OS::stack_name": "a"
        },
        "id": "4af43781",
        "outputs": [],
        "template_description": "This is a\ndescription\n"}
    }

    def setUp(self):
        super(TestStackShow, self).setUp()
        self.cmd = stack.ShowStack(self.app, None)
        self.stack_client.get.return_value = stacks.Stack(
            None, self.get_response)

    def test_stack_show(self):
        arglist = ['--format', self.format, 'my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.stack_client.get.assert_called_with(**{
            'stack_id': 'my_stack',
            'resolve_outputs': True,
        })

    def test_stack_show_explicit_no_resolve(self):
        arglist = ['--no-resolve-outputs', '--format', self.format, 'my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.stack_client.get.assert_called_with(**{
            'stack_id': 'my_stack',
            'resolve_outputs': False,
        })

    def test_stack_show_short(self):
        expected = ['id', 'stack_name', 'description', 'creation_time',
                    'updated_time', 'stack_status', 'stack_status_reason']

        columns, data = stack._show_stack(self.mock_client, 'my_stack',
                                          short=True)

        self.assertEqual(expected, columns)


class TestStackList(TestStack):

    defaults = {
        'limit': None,
        'marker': None,
        'filters': {},
        'tags': None,
        'tags_any': None,
        'not_tags': None,
        'not_tags_any': None,
        'global_tenant': False,
        'show_deleted': False,
        'show_hidden': False,
    }

    columns = ['ID', 'Stack Name', 'Stack Status', 'Creation Time',
               'Updated Time']

    data = {
        'id': '1234',
        'stack_name': 'my_stack',
        'stack_status': 'CREATE_COMPLETE',
        'creation_time': '2015-10-21T07:28:00Z',
        'update_time': '2015-10-21T07:30:00Z',
        'deletion_time': '2015-10-21T07:50:00Z',
    }

    data_with_project = copy.deepcopy(data)
    data_with_project['project'] = 'test_project'

    def setUp(self):
        super(TestStackList, self).setUp()
        self.cmd = stack.ListStack(self.app, None)
        self.stack_client.list.return_value = [stacks.Stack(None, self.data)]
        utils.get_dict_properties = mock.MagicMock(return_value='')

    def test_stack_list_defaults(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**self.defaults)
        self.assertEqual(self.columns, columns)

    def test_stack_list_nested(self):
        kwargs = copy.deepcopy(self.defaults)
        kwargs['show_nested'] = True
        cols = copy.deepcopy(self.columns)
        cols.append('Parent')
        arglist = ['--nested']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**kwargs)
        self.assertEqual(cols, columns)

    def test_stack_list_deleted(self):
        kwargs = copy.deepcopy(self.defaults)
        kwargs['show_deleted'] = True
        cols = copy.deepcopy(self.columns)
        cols.append('Deletion Time')
        arglist = ['--deleted']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**kwargs)
        self.assertEqual(cols, columns)

    def test_stack_list_all_projects(self):
        self.stack_client.list.return_value = [
            stacks.Stack(None, self.data_with_project)]
        kwargs = copy.deepcopy(self.defaults)
        kwargs['global_tenant'] = True
        cols = copy.deepcopy(self.columns)
        cols.insert(2, 'Project')
        arglist = ['--all-projects']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**kwargs)
        self.assertEqual(cols, columns)

    def test_stack_list_with_project(self):
        self.stack_client.list.return_value = [
            stacks.Stack(None, self.data_with_project)]
        kwargs = copy.deepcopy(self.defaults)
        cols = copy.deepcopy(self.columns)
        cols.insert(2, 'Project')
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**kwargs)
        self.assertEqual(cols, columns)

    def test_stack_list_long(self):
        self.stack_client.list.return_value = [
            stacks.Stack(None, self.data_with_project)]
        kwargs = copy.deepcopy(self.defaults)
        kwargs['global_tenant'] = True
        cols = copy.deepcopy(self.columns)
        cols.insert(2, 'Stack Owner')
        cols.insert(2, 'Project')
        arglist = ['--long']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**kwargs)
        self.assertEqual(cols, columns)

    def test_stack_list_short(self):
        cols = ['ID', 'Stack Name', 'Stack Status']
        arglist = ['--short']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**self.defaults)
        self.assertEqual(cols, columns)

    def test_stack_list_sort(self):
        arglist = ['--sort', 'stack_name:desc,id']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**self.defaults)
        self.assertEqual(self.columns, columns)

    def test_stack_list_sort_invalid_key(self):
        arglist = ['--sort', 'bad_key']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_stack_list_tags(self):
        kwargs = copy.deepcopy(self.defaults)
        kwargs['tags'] = 'tag1,tag2'
        arglist = ['--tags', 'tag1,tag2']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**kwargs)
        self.assertEqual(self.columns, columns)

    def test_stack_list_tags_mode(self):
        kwargs = copy.deepcopy(self.defaults)
        kwargs['not_tags'] = 'tag1,tag2'
        arglist = ['--tags', 'tag1,tag2', '--tag-mode', 'not']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**kwargs)
        self.assertEqual(self.columns, columns)

    def test_stack_list_tags_bad_mode(self):
        arglist = ['--tags', 'tag1,tag2', '--tag-mode', 'bad_mode']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)


class TestStackDelete(TestStack):

    def setUp(self):
        super(TestStackDelete, self).setUp()
        self.cmd = stack.DeleteStack(self.app, None)
        self.stack_client.get.side_effect = heat_exc.HTTPNotFound

    def test_stack_delete(self):
        arglist = ['stack1', 'stack2', 'stack3']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.delete.assert_any_call('stack1')
        self.stack_client.delete.assert_any_call('stack2')
        self.stack_client.delete.assert_any_call('stack3')

    def test_stack_delete_not_found(self):
        arglist = ['my_stack']
        self.stack_client.delete.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_stack_delete_forbidden(self):
        arglist = ['my_stack']
        self.stack_client.delete.side_effect = heat_exc.Forbidden
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_stack_delete_one_found_one_not_found(self):
        arglist = ['stack1', 'stack2']
        self.stack_client.delete.side_effect = [None, heat_exc.HTTPNotFound]
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)

        self.stack_client.delete.assert_any_call('stack1')
        self.stack_client.delete.assert_any_call('stack2')
        self.assertEqual('Unable to delete 1 of the 2 stacks.', str(error))

    @mock.patch('heatclient.common.event_utils.poll_for_events',
                return_value=('DELETE_COMPLETE',
                              'Stack my_stack DELETE_COMPLETE'))
    @mock.patch('heatclient.common.event_utils.get_events', return_value=[])
    def test_stack_delete_wait(self, mock_get_event, mock_poll, ):
        arglist = ['stack1', 'stack2', 'stack3', '--wait']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.stack_client.delete.assert_any_call('stack1')
        self.stack_client.delete.assert_any_call('stack2')
        self.stack_client.delete.assert_any_call('stack3')

    @mock.patch('heatclient.common.event_utils.poll_for_events')
    @mock.patch('heatclient.common.event_utils.get_events', return_value=[])
    def test_stack_delete_wait_fail(self, mock_get_event, mock_poll):
        mock_poll.side_effect = [['DELETE_COMPLETE',
                                  'Stack my_stack DELETE_COMPLETE'],
                                 ['DELETE_FAILED',
                                  'Stack my_stack DELETE_FAILED'],
                                 ['DELETE_COMPLETE',
                                  'Stack my_stack DELETE_COMPLETE']]
        arglist = ['stack1', 'stack2', 'stack3', '--wait']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.stack_client.delete.assert_any_call('stack1')
        self.stack_client.delete.assert_any_call('stack2')
        self.stack_client.delete.assert_any_call('stack3')
        self.assertEqual('Unable to delete 1 of the 3 stacks.', str(error))

    @mock.patch('sys.stdin', spec=six.StringIO)
    def test_stack_delete_prompt(self, mock_stdin):
        arglist = ['my_stack']
        mock_stdin.isatty.return_value = True
        mock_stdin.readline.return_value = 'y'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        mock_stdin.readline.assert_called_with()
        self.stack_client.delete.assert_called_with('my_stack')

    @mock.patch('sys.stdin', spec=six.StringIO)
    def test_stack_delete_prompt_no(self, mock_stdin):
        arglist = ['my_stack']
        mock_stdin.isatty.return_value = True
        mock_stdin.readline.return_value = 'n'
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        mock_stdin.readline.assert_called_with()
        self.stack_client.delete.assert_not_called()


class TestStackAdopt(TestStack):

    adopt_file = 'heatclient/tests/test_templates/adopt.json'
    adopt_with_files = ('heatclient/tests/test_templates/adopt_with_file.json')

    with open(adopt_file, 'r') as f:
        adopt_data = f.read()
    with open(adopt_with_files, 'r') as f:
        adopt_with_files_data = f.read()

    defaults = {
        'stack_name': 'my_stack',
        'disable_rollback': True,
        'adopt_stack_data': adopt_data,
        'parameters': {},
        'files': {},
        'environment': {},
        'timeout': None
    }

    child_stack_yaml = "{\"heat_template_version\": \"2015-10-15\"}"

    expected_with_files = {
        'stack_name': 'my_stack',
        'disable_rollback': True,
        'adopt_stack_data': adopt_with_files_data,
        'parameters': {},
        'files': {'file://empty.yaml': child_stack_yaml},
        'environment': {},
        'timeout': None
    }

    def setUp(self):
        super(TestStackAdopt, self).setUp()
        self.cmd = stack.AdoptStack(self.app, None)
        self.stack_client.create.return_value = {'stack': {'id': '1234'}}

    def test_stack_adopt_defaults(self):
        arglist = ['my_stack', '--adopt-file', self.adopt_file]
        cols = ['id', 'stack_name', 'description', 'creation_time',
                'updated_time', 'stack_status', 'stack_status_reason']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**self.defaults)
        self.assertEqual(cols, columns)

    def test_stack_adopt_enable_rollback(self):
        arglist = ['my_stack', '--adopt-file', self.adopt_file,
                   '--enable-rollback']
        kwargs = copy.deepcopy(self.defaults)
        kwargs['disable_rollback'] = False
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**kwargs)

    @mock.patch('heatclient.common.event_utils.poll_for_events',
                return_value=('ADOPT_COMPLETE',
                              'Stack my_stack ADOPT_COMPLETE'))
    def test_stack_adopt_wait(self, mock_poll):
        arglist = ['my_stack', '--adopt-file', self.adopt_file, '--wait']
        self.stack_client.get.return_value = stacks.Stack(
            None, {'stack_status': 'ADOPT_COMPLETE'})
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**self.defaults)
        self.stack_client.get.assert_called_with(**{'stack_id': '1234',
                                                    'resolve_outputs': False})

    @mock.patch('heatclient.common.event_utils.poll_for_events',
                return_value=('ADOPT_FAILED',
                              'Stack my_stack ADOPT_FAILED'))
    def test_stack_adopt_wait_fail(self, mock_poll):
        arglist = ['my_stack', '--adopt-file', self.adopt_file, '--wait']
        self.stack_client.get.return_value = stacks.Stack(
            None, {'stack_status': 'ADOPT_FAILED'})
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_stack_adopt_with_adopt_files(self):
        # Make sure when we adopt with files in adopt script, we will load
        # those files as part of input when calling adopt.
        arglist = ['my_stack', '--adopt-file', self.adopt_with_files]
        cols = ['id', 'stack_name', 'description', 'creation_time',
                'updated_time', 'stack_status', 'stack_status_reason']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**self.expected_with_files)
        self.assertEqual(cols, columns)


class TestStackExport(TestStack):

    columns = ['stack_name', 'stack_status', 'id']
    data = ['my_stack', 'ABANDONED', '1234']

    response = dict(zip(columns, data))

    def setUp(self):
        super(TestStackExport, self).setUp()
        self.cmd = stack.ExportStack(self.app, None)
        self.stack_client.export.return_value = self.response

    def test_stack_export(self):
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        for column in self.columns:
            self.assertIn(column, columns)
        for datum in self.data:
            self.assertIn(datum, data)

    @mock.patch('heatclient.osc.v1.stack.open', create=True)
    def test_stack_export_output_file(self, mock_open):
        arglist = ['my_stack', '--output-file', 'file.json']
        mock_open.return_value = mock.MagicMock(spec=io.IOBase)
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        mock_open.assert_called_once_with('file.json', 'w')
        self.assertEqual([], columns)
        self.assertIsNone(data)


class TestStackAbandon(TestStack):

    columns = ['stack_name', 'stack_status', 'id']
    data = ['my_stack', 'ABANDONED', '1234']

    response = dict(zip(columns, data))

    def setUp(self):
        super(TestStackAbandon, self).setUp()
        self.cmd = stack.AbandonStack(self.app, None)
        self.stack_client.abandon.return_value = self.response

    def test_stack_abandon(self):
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        for column in self.columns:
            self.assertIn(column, columns)
        for datum in self.data:
            self.assertIn(datum, data)

    def test_stack_abandon_not_found(self):
        arglist = ['my_stack']
        self.stack_client.abandon.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    @mock.patch('heatclient.osc.v1.stack.open', create=True)
    def test_stack_abandon_output_file(self, mock_open):
        arglist = ['my_stack', '--output-file', 'file.json']
        mock_open.return_value = mock.MagicMock(spec=io.IOBase)
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        mock_open.assert_called_once_with('file.json', 'w')
        self.assertEqual([], columns)
        self.assertIsNone(data)

    @mock.patch('heatclient.osc.v1.stack.open', create=True,
                side_effect=IOError)
    def test_stack_abandon_output_file_error(self, mock_open):
        arglist = ['my_stack', '--output-file', 'file.json']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)


class TestStackOutputShow(TestStack):

    outputs = [
        {'output_key': 'output1', 'output_value': 'value1'},
        {'output_key': 'output2', 'output_value': 'value2',
         'output_error': 'error'}
    ]

    response = {
        'outputs': outputs,
        'stack_name': 'my_stack'
    }

    def setUp(self):
        super(TestStackOutputShow, self).setUp()
        self.cmd = stack.OutputShowStack(self.app, None)
        self.stack_client.get.return_value = stacks.Stack(None, self.response)

    def test_stack_output_show_no_output(self):
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Either <OUTPUT NAME> or --all must be specified.',
                         str(error))

    def test_stack_output_show_output_and_all(self):
        arglist = ['my_stack', 'output1', '--all']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Cannot specify both <OUTPUT NAME> and --all.',
                         str(error))

    def test_stack_output_show_all(self):
        arglist = ['my_stack', '--all']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, outputs = self.cmd.take_action(parsed_args)

        self.stack_client.get.assert_called_with('my_stack')
        self.assertEqual(['output1', 'output2'], columns)

    def test_stack_output_show_output(self):
        arglist = ['my_stack', 'output1']
        self.stack_client.output_show.return_value = {
            'output': self.outputs[0]}
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, outputs = self.cmd.take_action(parsed_args)

        self.stack_client.output_show.assert_called_with('my_stack', 'output1')
        self.assertEqual(('output_key', 'output_value'), columns)
        self.assertEqual(('output1', 'value1'), outputs)

    def test_stack_output_show_not_found(self):
        arglist = ['my_stack', '--all']
        self.stack_client.get.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Stack not found: my_stack', str(error))

    def test_stack_output_show_output_error(self):
        arglist = ['my_stack', 'output2']
        self.stack_client.output_show.return_value = {
            'output': self.outputs[1]}
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Output error: error', str(error))
        self.stack_client.output_show.assert_called_with('my_stack', 'output2')

    def test_stack_output_show_bad_output(self):
        arglist = ['my_stack', 'output3']
        self.stack_client.output_show.side_effect = heat_exc.HTTPNotFound
        self.stack_client.get.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Stack my_stack or output output3 not found.',
                         str(error))
        self.stack_client.output_show.assert_called_with('my_stack', 'output3')

    def test_stack_output_show_old_api(self):
        arglist = ['my_stack', 'output1']
        self.stack_client.output_show.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, outputs = self.cmd.take_action(parsed_args)

        self.stack_client.get.assert_called_with('my_stack')
        self.assertEqual(('output_key', 'output_value'), columns)
        self.assertEqual(('output1', 'value1'), outputs)


class TestStackOutputList(TestStack):

    response = {'outputs': [{'output_key': 'key1', 'description': 'desc1'},
                            {'output_key': 'key2', 'description': 'desc2'}]}
    stack_response = {
        'stack_name': 'my_stack',
        'outputs': response['outputs']
    }

    def setUp(self):
        super(TestStackOutputList, self).setUp()
        self.cmd = stack.OutputListStack(self.app, None)
        self.stack_client.get = mock.MagicMock(
            return_value=stacks.Stack(None, self.response))

    def test_stack_output_list(self):
        arglist = ['my_stack']
        self.stack_client.output_list.return_value = self.response
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.assertEqual(['output_key', 'description'], columns)
        self.stack_client.output_list.assert_called_with('my_stack')

    def test_stack_output_list_not_found(self):
        arglist = ['my_stack']
        self.stack_client.output_list.side_effect = heat_exc.HTTPNotFound
        self.stack_client.get.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Stack not found: my_stack', str(error))

    def test_stack_output_list_old_api(self):
        arglist = ['my_stack']
        self.stack_client.output_list.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, outputs = self.cmd.take_action(parsed_args)

        self.stack_client.get.assert_called_with('my_stack')
        self.assertEqual(['output_key', 'description'], columns)


class TestStackTemplateShow(TestStack):

    fields = ['heat_template_version', 'description', 'parameter_groups',
              'parameters', 'resources', 'outputs']

    def setUp(self):
        super(TestStackTemplateShow, self).setUp()
        self.cmd = stack.TemplateShowStack(self.app, None)

    def test_stack_template_show_full_template(self):
        arglist = ['my_stack']
        self.stack_client.template.return_value = yaml.load(
            inline_templates.FULL_TEMPLATE,
            Loader=template_format.yaml_loader)
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, outputs = self.cmd.take_action(parsed_args)

        for f in self.fields:
            self.assertIn(f, columns)

    def test_stack_template_show_short_template(self):
        arglist = ['my_stack']
        self.stack_client.template.return_value = yaml.load(
            inline_templates.SHORT_TEMPLATE,
            Loader=template_format.yaml_loader)
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, outputs = self.cmd.take_action(parsed_args)

        for f in ['heat_template_version', 'resources']:
            self.assertIn(f, columns)

    def test_stack_template_show_not_found(self):
        arglist = ['my_stack']
        self.stack_client.template.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)


class _TestStackCheckBase(object):

    stack = stacks.Stack(None, {
        "id": '1234',
        "stack_name": 'my_stack',
        "creation_time": "2013-08-04T20:57:55Z",
        "updated_time": "2013-08-04T20:57:55Z",
        "stack_status": "CREATE_COMPLETE"
    })

    columns = ['ID', 'Stack Name', 'Stack Status', 'Creation Time',
               'Updated Time']

    def _setUp(self, cmd, action, action_name=None):
        self.cmd = cmd
        self.action = action
        self.action_name = action_name
        self.mock_client.stacks.get.return_value = self.stack

    def _test_stack_action(self, get_call_count=1):
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.action.assert_called_once_with('my_stack')
        self.mock_client.stacks.get.assert_called_with('my_stack')
        self.assertEqual(get_call_count,
                         self.mock_client.stacks.get.call_count)
        self.assertEqual(self.columns, columns)
        self.assertEqual(1, len(rows))

    def _test_stack_action_multi(self, get_call_count=2):
        arglist = ['my_stack1', 'my_stack2']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.assertEqual(2, self.action.call_count)
        self.assertEqual(get_call_count,
                         self.mock_client.stacks.get.call_count)
        self.action.assert_called_with('my_stack2')
        self.mock_client.stacks.get.assert_called_with('my_stack2')
        self.assertEqual(self.columns, columns)
        self.assertEqual(2, len(rows))

    @mock.patch('heatclient.common.event_utils.poll_for_events')
    @mock.patch('heatclient.common.event_utils.get_events', return_value=[])
    def _test_stack_action_wait(self, ge, mock_poll):
        arglist = ['my_stack', '--wait']
        mock_poll.return_value = (
            '%s_COMPLETE' % self.action_name,
            'Stack my_stack %s_COMPLETE' % self.action_name
        )
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.action.assert_called_with('my_stack')
        self.mock_client.stacks.get.assert_called_with('my_stack')
        self.assertEqual(self.columns, columns)
        self.assertEqual(1, len(rows))

    @mock.patch('heatclient.common.event_utils.poll_for_events')
    @mock.patch('heatclient.common.event_utils.get_events', return_value=[])
    def _test_stack_action_wait_error(self, ge, mock_poll):
        arglist = ['my_stack', '--wait']
        mock_poll.return_value = (
            '%s_FAILED' % self.action_name,
            'Error waiting for status from stack my_stack'
        )
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action,
                                  parsed_args)
        self.assertEqual('Error waiting for status from stack my_stack',
                         str(error))

    def _test_stack_action_exception(self):
        self.action.side_effect = heat_exc.HTTPNotFound
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action,
                                  parsed_args)
        self.assertEqual('Stack not found: my_stack',
                         str(error))


class TestStackSuspend(_TestStackCheckBase, TestStack):

    def setUp(self):
        super(TestStackSuspend, self).setUp()
        self._setUp(
            stack.SuspendStack(self.app, None),
            self.mock_client.actions.suspend,
            'SUSPEND'
        )

    def test_stack_suspend(self):
        self._test_stack_action()

    def test_stack_suspend_multi(self):
        self._test_stack_action_multi()

    def test_stack_suspend_wait(self):
        self._test_stack_action_wait()

    def test_stack_suspend_wait_error(self):
        self._test_stack_action_wait_error()

    def test_stack_suspend_exception(self):
        self._test_stack_action_exception()


class TestStackResume(_TestStackCheckBase, TestStack):

    def setUp(self):
        super(TestStackResume, self).setUp()
        self._setUp(
            stack.ResumeStack(self.app, None),
            self.mock_client.actions.resume,
            'RESUME'
        )

    def test_stack_resume(self):
        self._test_stack_action()

    def test_stack_resume_multi(self):
        self._test_stack_action_multi()

    def test_stack_resume_wait(self):
        self._test_stack_action_wait()

    def test_stack_resume_wait_error(self):
        self._test_stack_action_wait_error()

    def test_stack_resume_exception(self):
        self._test_stack_action_exception()


class TestStackCancel(_TestStackCheckBase, TestStack):

    stack_update_in_progress = stacks.Stack(None, {
        "id": '1234',
        "stack_name": 'my_stack',
        "creation_time": "2013-08-04T20:57:55Z",
        "updated_time": "2013-08-04T20:57:55Z",
        "stack_status": "UPDATE_IN_PROGRESS"
    })

    def setUp(self):
        super(TestStackCancel, self).setUp()
        self._setUp(
            stack.CancelStack(self.app, None),
            self.mock_client.actions.cancel_update,
            'ROLLBACK'
        )
        self.mock_client.stacks.get.return_value = (
            self.stack_update_in_progress)

    def test_stack_cancel(self):
        self._test_stack_action(2)

    def _test_stack_cancel_no_rollback(self, call_count):
        self.action = self.mock_client.actions.cancel_without_rollback
        arglist = ['my_stack', '--no-rollback']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.action.assert_called_once_with('my_stack')
        self.mock_client.stacks.get.assert_called_with('my_stack')
        self.assertEqual(call_count,
                         self.mock_client.stacks.get.call_count)
        self.assertEqual(self.columns, columns)
        self.assertEqual(1, len(rows))

    def test_stack_cancel_no_rollback(self):
        self._test_stack_cancel_no_rollback(2)

    def test_stack_cancel_multi(self):
        self._test_stack_action_multi(4)

    def test_stack_cancel_wait(self):
        self._test_stack_action_wait()

    def test_stack_cancel_wait_error(self):
        self._test_stack_action_wait_error()

    def test_stack_cancel_exception(self):
        self._test_stack_action_exception()

    def test_stack_cancel_unsupported_state(self):
        self.stack.stack_status = "CREATE_COMPLETE"
        self.mock_client.stacks.get.return_value = self.stack
        error = self.assertRaises(exc.CommandError,
                                  self._test_stack_action,
                                  2)
        self.assertEqual('Stack my_stack with status \'create_complete\' '
                         'not in cancelable state',
                         str(error))

    def test_stack_cancel_create_in_progress(self):
        self.stack.stack_status = "CREATE_IN_PROGRESS"
        self.mock_client.stacks.get.return_value = self.stack
        error = self.assertRaises(exc.CommandError,
                                  self._test_stack_action,
                                  2)
        self.assertEqual('Stack my_stack with status \'create_in_progress\' '
                         'not in cancelable state',
                         str(error))
        self._test_stack_cancel_no_rollback(3)


class TestStackCheck(_TestStackCheckBase, TestStack):

    def setUp(self):
        super(TestStackCheck, self).setUp()
        self._setUp(
            stack.CheckStack(self.app, None),
            self.mock_client.actions.check,
            'CHECK'
        )

    def test_stack_check(self):
        self._test_stack_action()

    def test_stack_check_multi(self):
        self._test_stack_action_multi()

    def test_stack_check_wait(self):
        self._test_stack_action_wait()

    def test_stack_check_wait_error(self):
        self._test_stack_action_wait_error()

    def test_stack_check_exception(self):
        self._test_stack_action_exception()


class TestStackHookPoll(TestStack):

    stack = stacks.Stack(None, {
        "id": '1234',
        "stack_name": 'my_stack',
        "creation_time": "2013-08-04T20:57:55Z",
        "updated_time": "2013-08-04T20:57:55Z",
        "stack_status": "CREATE_IN_PROGRESS"
    })
    resource = resources.Resource(None, {
        'resource_name': 'resource1',
        'links': [{'href': 'http://heat.example.com:8004/resource1',
                   'rel': 'self'},
                  {'href': 'http://192.168.27.100:8004/my_stack',
                   'rel': 'stack'}],
        'logical_resource_id': 'random_group',
        'creation_time': '2015-12-03T16:50:56',
        'resource_status': 'INIT_COMPLETE',
        'updated_time': '2015-12-03T16:50:56',
        'required_by': [],
        'resource_status_reason': '',
        'physical_resource_id': '',
        'resource_type': 'OS::Heat::ResourceGroup',
        'id': '1111'
    })
    columns = ['ID', 'Resource Status Reason', 'Resource Status',
               'Event Time']
    event0 = events.Event(manager=None, info={
        'resource_name': 'my_stack',
        'event_time': '2015-12-02T16:50:56',
        'logical_resource_id': 'my_stack',
        'resource_status': 'CREATE_IN_PROGRESS',
        'resource_status_reason': 'Stack CREATE started',
        'id': '1234'
    })
    event1 = events.Event(manager=None, info={
        'resource_name': 'resource1',
        'event_time': '2015-12-03T19:59:58',
        'logical_resource_id': 'resource1',
        'resource_status': 'INIT_COMPLETE',
        'resource_status_reason':
            'CREATE paused until Hook pre-create is cleared',
        'id': '1111'
    })
    row1 = ('resource1',
            '1111',
            'CREATE paused until Hook pre-create is cleared',
            'INIT_COMPLETE',
            '2015-12-03T19:59:58'
            )

    def setUp(self):
        super(TestStackHookPoll, self).setUp()
        self.cmd = stack.StackHookPoll(self.app, None)
        self.mock_client.stacks.get.return_value = self.stack
        self.mock_client.events.list.return_value = [self.event0, self.event1]
        self.mock_client.resources.list.return_value = [self.resource]

    def test_hook_poll(self):
        expected_columns = ['Resource Name'] + self.columns
        expected_rows = [self.row1]
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.assertEqual(expected_rows, list(rows))
        self.assertEqual(expected_columns, columns)

    def test_hook_poll_nested(self):
        expected_columns = ['Resource Name'] + self.columns + ['Stack Name']
        expected_rows = [self.row1 + ('my_stack',)]
        arglist = ['my_stack', '--nested-depth=10']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, rows = self.cmd.take_action(parsed_args)
        self.assertEqual(expected_rows, list(rows))
        self.assertEqual(expected_columns, columns)

    def test_hook_poll_nested_invalid(self):
        arglist = ['my_stack', '--nested-depth=ugly']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)


class TestStackHookClear(TestStack):

    stack = stacks.Stack(None, {
        "id": '1234',
        "stack_name": 'my_stack',
        "creation_time": "2013-08-04T20:57:55Z",
        "updated_time": "2013-08-04T20:57:55Z",
        "stack_status": "CREATE_IN_PROGRESS"
    })
    resource = resources.Resource(None, {
        'stack_id': 'my_stack',
        'resource_name': 'resource'
    })

    def setUp(self):
        super(TestStackHookClear, self).setUp()
        self.cmd = stack.StackHookClear(self.app, None)
        self.mock_client.stacks.get.return_value = self.stack
        self.mock_client.resources.list.return_value = [self.resource]

    def test_hook_clear(self):
        arglist = ['my_stack', 'resource']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resources.signal.assert_called_once_with(
            data={'unset_hook': 'pre-create'},
            resource_name='resource',
            stack_id='my_stack')

    def test_hook_clear_pre_create(self):
        arglist = ['my_stack', 'resource', '--pre-create']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resources.signal.assert_called_once_with(
            data={'unset_hook': 'pre-create'},
            resource_name='resource',
            stack_id='my_stack')

    def test_hook_clear_pre_update(self):
        arglist = ['my_stack', 'resource', '--pre-update']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resources.signal.assert_called_once_with(
            data={'unset_hook': 'pre-update'},
            resource_name='resource',
            stack_id='my_stack')

    def test_hook_clear_pre_delete(self):
        arglist = ['my_stack', 'resource', '--pre-delete']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.mock_client.resources.signal.assert_called_once_with(
            data={'unset_hook': 'pre-delete'},
            resource_name='resource',
            stack_id='my_stack')


class TestEnvironmentStackShow(TestStack):

    SAMPLE_ENV = {
        'parameters': {'p1': 'v1'},
        'resource_registry': {'resources': {'r1': 't1'}},
        'parameter_defaults': {'p1': 'v_default'}
    }

    def setUp(self):
        super(TestEnvironmentStackShow, self).setUp()
        self.cmd = stack.EnvironmentShowStack(self.app, None)

    def test_stack_environment_show(self):
        # Test
        columns, outputs = self._test_stack_environment_show(self.SAMPLE_ENV)

        # Verify
        self.assertEqual([{'p1': 'v1'}, {'resources': {'r1': 't1'}},
                          {'p1': 'v_default'}], outputs)

    def test_stack_environment_show_no_parameters(self):
        # Setup
        sample_env = copy.deepcopy(self.SAMPLE_ENV)
        sample_env['parameters'] = {}

        # Test
        columns, outputs = self._test_stack_environment_show(sample_env)

        # Verify
        self.assertEqual([{}, {'resources': {'r1': 't1'}},
                          {'p1': 'v_default'}], outputs)

    def test_stack_environment_show_no_registry(self):
        # Setup
        sample_env = copy.deepcopy(self.SAMPLE_ENV)
        sample_env['resource_registry'] = {'resources': {}}

        # Test
        columns, outputs = self._test_stack_environment_show(sample_env)

        # Verify
        self.assertEqual([{'p1': 'v1'}, {'resources': {}},
                          {'p1': 'v_default'}], outputs)

    def test_stack_environment_show_no_param_defaults(self):
        # Setup
        sample_env = copy.deepcopy(self.SAMPLE_ENV)
        sample_env['parameter_defaults'] = {}

        # Test
        columns, outputs = self._test_stack_environment_show(sample_env)

        # Verify
        self.assertEqual([{'p1': 'v1'}, {'resources': {'r1': 't1'}}, {}],
                         outputs)

    def _test_stack_environment_show(self, env):
        self.stack_client.environment = mock.MagicMock(
            return_value=env
        )

        parsed_args = self.check_parser(self.cmd, ['test-stack'], [])
        columns, outputs = self.cmd.take_action(parsed_args)
        self.assertEqual(['parameters', 'resource_registry',
                          'parameter_defaults'], columns)

        return columns, outputs
