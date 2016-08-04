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
from osc_lib import exceptions as exc

from heatclient import exc as heat_exc
from heatclient.osc.v1 import resource
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes
from heatclient.v1 import resources as v1_resources


class TestResource(orchestration_fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestResource, self).setUp()
        self.resource_client = self.app.client_manager.orchestration.resources


class TestStackResourceShow(TestResource):

    response = {
        'attributes': {},
        'creation_time': '2016-02-01T20:20:53',
        'description': 'a resource',
        'links': [
            {'rel': 'stack',
             "href": "http://heat.example.com:8004/my_stack/12"}
        ],
        'logical_resource_id': 'my_resource',
        'physical_resource_id': '1234',
        'required_by': [],
        'resource_name': 'my_resource',
        'resource_status': 'CREATE_COMPLETE',
        'resource_status_reason': 'state changed',
        'resource_type': 'OS::Heat::None',
        'updated_time': '2016-02-01T20:20:53',
    }

    def setUp(self):
        super(TestStackResourceShow, self).setUp()
        self.cmd = resource.ResourceShow(self.app, None)
        self.resource_client.get.return_value = v1_resources.Resource(
            None, self.response)

    def test_resource_show(self):
        arglist = ['my_stack', 'my_resource']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.resource_client.get.assert_called_with('my_stack', 'my_resource',
                                                    with_attr=None)
        for key in self.response:
            self.assertIn(key, columns)
            self.assertIn(self.response[key], data)

    def test_resource_show_with_attr(self):
        arglist = ['my_stack', 'my_resource',
                   '--with-attr', 'foo', '--with-attr', 'bar']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.resource_client.get.assert_called_with('my_stack', 'my_resource',
                                                    with_attr=['foo', 'bar'])
        for key in self.response:
            self.assertIn(key, columns)
            self.assertIn(self.response[key], data)

    def test_resource_show_not_found(self):
        arglist = ['my_stack', 'bad_resource']
        self.resource_client.get.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Stack or resource not found: my_stack bad_resource',
                         str(error))


class TestStackResourceList(TestResource):

    response = {
        'attributes': {},
        'creation_time': '2016-02-01T20:20:53',
        'description': 'a resource',
        'links': [
            {'rel': 'stack',
             "href": "http://heat.example.com:8004/my_stack/12"}
        ],
        'logical_resource_id': '1234',
        'physical_resource_id': '1234',
        'required_by': [],
        'resource_name': 'my_resource',
        'resource_status': 'CREATE_COMPLETE',
        'resource_status_reason': 'state changed',
        'resource_type': 'OS::Heat::None',
        'updated_time': '2016-02-01T20:20:53',
    }

    columns = ['resource_name', 'physical_resource_id', 'resource_type',
               'resource_status', 'updated_time']

    data = ['my_resource', '1234', 'OS::Heat::None',
            'CREATE_COMPLETE', '2016-02-01T20:20:53']

    def setUp(self):
        super(TestStackResourceList, self).setUp()
        self.cmd = resource.ResourceList(self.app, None)
        self.resource_client.list.return_value = [
            v1_resources.Resource(None, self.response)]

    def test_resource_list(self):
        arglist = ['my_stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.resource_client.list.assert_called_with(
            'my_stack',
            filters={},
            with_detail=False,
            nested_depth=None)
        self.assertEqual(self.columns, columns)
        self.assertEqual(tuple(self.data), list(data)[0])

    def test_resource_list_not_found(self):
        arglist = ['bad_stack']
        self.resource_client.list.side_effect = heat_exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)

    def test_resource_list_with_detail(self):
        arglist = ['my_stack', '--long']
        cols = copy.deepcopy(self.columns)
        cols.append('stack_name')
        out = copy.deepcopy(self.data)
        out.append('my_stack')
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.resource_client.list.assert_called_with(
            'my_stack',
            filters={},
            with_detail=True,
            nested_depth=None)
        self.assertEqual(cols, columns)
        self.assertEqual(tuple(out), list(data)[0])

    def test_resource_list_nested_depth(self):
        arglist = ['my_stack', '--nested-depth', '3']
        cols = copy.deepcopy(self.columns)
        cols.append('stack_name')
        out = copy.deepcopy(self.data)
        out.append('my_stack')
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.resource_client.list.assert_called_with(
            'my_stack',
            filters={},
            with_detail=False,
            nested_depth=3)
        self.assertEqual(cols, columns)
        self.assertEqual(tuple(out), list(data)[0])

    def test_resource_list_no_resource_name(self):
        arglist = ['my_stack']
        resp = copy.deepcopy(self.response)
        del resp['resource_name']
        cols = copy.deepcopy(self.columns)
        cols[0] = 'logical_resource_id'
        out = copy.deepcopy(self.data)
        out[1] = '1234'
        self.resource_client.list.return_value = [
            v1_resources.Resource(None, resp)]
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.resource_client.list.assert_called_with(
            'my_stack',
            filters={},
            with_detail=False,
            nested_depth=None)
        self.assertEqual(cols, columns)

    def test_resource_list_filter(self):
        arglist = ['my_stack', '--filter', 'name=my_resource']
        out = copy.deepcopy(self.data)
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.resource_client.list.assert_called_with(
            'my_stack',
            filters=dict(name='my_resource'),
            with_detail=False,
            nested_depth=None)
        self.assertEqual(tuple(out), list(data)[0])


class TestResourceMetadata(TestResource):

    def setUp(self):
        super(TestResourceMetadata, self).setUp()
        self.cmd = resource.ResourceMetadata(self.app, None)
        self.resource_client.metadata.return_value = {}

    def test_resource_metadata(self):
        arglist = ['my_stack', 'my_resource']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.resource_client.metadata.assert_called_with(**{
            'stack_id': 'my_stack',
            'resource_name': 'my_resource'
        })

    def test_resource_metadata_yaml(self):
        arglist = ['my_stack', 'my_resource', '--format', 'yaml']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.resource_client.metadata.assert_called_with(**{
            'stack_id': 'my_stack',
            'resource_name': 'my_resource'
        })

    def test_resource_metadata_error(self):
        arglist = ['my_stack', 'my_resource']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.resource_client.metadata.side_effect = heat_exc.HTTPNotFound
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action,
                                  parsed_args)
        self.assertEqual('Stack my_stack or resource my_resource not found.',
                         str(error))


class TestResourceSignal(TestResource):

    def setUp(self):
        super(TestResourceSignal, self).setUp()
        self.cmd = resource.ResourceSignal(self.app, None)

    def test_resource_signal(self):
        arglist = ['my_stack', 'my_resource']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.resource_client.signal.assert_called_with(**{
            'stack_id': 'my_stack',
            'resource_name': 'my_resource'
        })

    def test_resource_signal_error(self):
        arglist = ['my_stack', 'my_resource']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.resource_client.signal.side_effect = heat_exc.HTTPNotFound
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action,
                                  parsed_args)
        self.assertEqual('Stack my_stack or resource my_resource not found.',
                         str(error))

    def test_resource_signal_data(self):
        arglist = ['my_stack', 'my_resource',
                   '--data', '{"message":"Content"}']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.resource_client.signal.assert_called_with(**{
            'data': {u'message': u'Content'},
            'stack_id': 'my_stack',
            'resource_name': 'my_resource'
        })

    def test_resource_signal_data_not_json(self):
        arglist = ['my_stack', 'my_resource', '--data', '{']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action,
                                  parsed_args)
        self.assertIn('Data should be in JSON format', str(error))

    def test_resource_signal_data_and_file_error(self):
        arglist = ['my_stack', 'my_resource',
                   '--data', '{}', '--data-file', 'file']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action,
                                  parsed_args)
        self.assertEqual('Should only specify one of data or data-file',
                         str(error))

    @mock.patch('six.moves.urllib.request.urlopen')
    def test_resource_signal_file(self, urlopen):
        data = mock.Mock()
        data.read.side_effect = ['{"message":"Content"}']
        urlopen.return_value = data

        arglist = ['my_stack', 'my_resource', '--data-file', 'test_file']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.resource_client.signal.assert_called_with(**{
            'data': {u'message': u'Content'},
            'stack_id': 'my_stack',
            'resource_name': 'my_resource'
        })


class TestResourceMarkUnhealthy(TestResource):
    def setUp(self):
        super(TestResourceMarkUnhealthy, self).setUp()
        self.cmd = resource.ResourceMarkUnhealthy(self.app, None)
        self.resource_client.mark_unhealthy = mock.Mock()

    def test_resource_mark_unhealthy(self):
        arglist = ['my_stack', 'my_resource', 'reason']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.resource_client.mark_unhealthy.assert_called_with(**{
            "stack_id": "my_stack",
            "resource_name": "my_resource",
            "mark_unhealthy": True,
            "resource_status_reason": "reason"
        })

    def test_resource_mark_unhealthy_reset(self):
        arglist = ['my_stack', 'my_resource', '--reset']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)
        self.resource_client.mark_unhealthy.assert_called_with(**{
            "stack_id": "my_stack",
            "resource_name": "my_resource",
            "mark_unhealthy": False,
            "resource_status_reason": ""
        })

    def test_resource_mark_unhealthy_not_found(self):
        arglist = ['my_stack', 'my_resource', '--reset']
        self.resource_client.mark_unhealthy.side_effect = (
            heat_exc.HTTPNotFound)
        parsed_args = self.check_parser(self.cmd, arglist, [])

        error = self.assertRaises(exc.CommandError,
                                  self.cmd.take_action, parsed_args)
        self.assertEqual('Stack or resource not found: my_stack my_resource',
                         str(error))
