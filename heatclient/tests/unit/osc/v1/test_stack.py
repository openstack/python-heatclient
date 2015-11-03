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
import mock
import testscenarios

from openstackclient.common import exceptions as exc
from openstackclient.common import utils

from heatclient.osc.v1 import stack
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes
from heatclient.v1 import stacks

load_tests = testscenarios.load_tests_apply_scenarios


class TestStack(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestStack, self).setUp()
        self.mock_client = self.app.client_manager.orchestration
        self.stack_client = self.app.client_manager.orchestration.stacks


class TestStackCreate(TestStack):

    template_path = 'heatclient/tests/test_templates/empty.yaml'

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
        self.stack_client.create = mock.MagicMock(
            return_value={'stack': {'id': '1234'}})
        self.stack_client.get = mock.MagicMock(
            return_value={'stack_status': 'create_complete'})
        stack._authenticated_fetcher = mock.MagicMock()

    def test_stack_create_defaults(self):
        arglist = ['my_stack', '-t', self.template_path]
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**self.defaults)

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

    def test_stack_create_wait(self):
        arglist = ['my_stack', '-t', self.template_path, '--wait']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.stack_client.create.assert_called_with(**self.defaults)
        self.stack_client.get.assert_called_with(**{'stack_id': '1234'})

    @mock.patch('openstackclient.common.utils.wait_for_status',
                return_value=False)
    def test_stack_create_wait_fail(self, mock_wait):
        arglist = ['my_stack', '-t', self.template_path, '--wait']
        parsed_args = self.check_parser(self.cmd, arglist, [])

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
        self.stack_client.get = mock.Mock(
            return_value=stacks.Stack(None, self.get_response))

    def test_stack_show(self):
        arglist = ['--format', self.format, 'my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.stack_client.get.assert_called_with(**{
            'stack_id': 'my_stack',
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
        'update_time': '2015-10-21T07:30:00Z'
    }

    def setUp(self):
        super(TestStackList, self).setUp()
        self.cmd = stack.ListStack(self.app, None)
        self.stack_client.list = mock.MagicMock(
            return_value=[stacks.Stack(None, self.data)])
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

    def test_stack_list_all_projects(self):
        kwargs = copy.deepcopy(self.defaults)
        kwargs['global_tenant'] = True
        cols = copy.deepcopy(self.columns)
        cols.insert(2, 'Project')
        arglist = ['--all-projects']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.list.assert_called_with(**kwargs)
        self.assertEqual(cols, columns)

    def test_stack_list_long(self):
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
