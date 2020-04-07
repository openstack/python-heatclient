#
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

import collections

from unittest import mock

from heatclient import exc
from heatclient.osc.v1 import stack_failures
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes


class ListStackFailuresTest(orchestration_fakes.TestOrchestrationv1):

    def setUp(self):
        super(ListStackFailuresTest, self).setUp()
        self.cmd = stack_failures.ListStackFailures(self.app, None)
        self.cmd.heat_client = self.app.client_manager.orchestration
        self.stack_client = self.app.client_manager.orchestration.stacks
        self.resource_client = self.app.client_manager.orchestration.resources
        self.software_deployments_client = \
            self.app.client_manager.orchestration.software_deployments

        self.stack = mock.MagicMock(id='123', status='FAILED',
                                    stack_name='stack')
        self.stack_client.get.return_value = self.stack
        self.failed_template_resource = mock.MagicMock(
            physical_resource_id='aaaa',
            resource_type='My::TemplateResource',
            resource_status='CREATE_FAILED',
            links=[{'rel': 'nested'}],
            resource_name='my_templateresource',
            resource_status_reason='All gone Pete Tong',
            logical_resource_id='my_templateresource',
        )
        self.failed_resource = mock.MagicMock(
            physical_resource_id='cccc',
            resource_type='OS::Nova::Server',
            resource_status='CREATE_FAILED',
            links=[],
            resource_name='my_server',
            resource_status_reason='All gone Pete Tong',
            logical_resource_id='my_server',
        )
        self.other_failed_template_resource = mock.MagicMock(
            physical_resource_id='dddd',
            resource_type='My::OtherTemplateResource',
            resource_status='CREATE_FAILED',
            links=[{'rel': 'nested'}],
            resource_name='my_othertemplateresource',
            resource_status_reason='RPC timeout',
            logical_resource_id='my_othertemplateresource',
        )
        self.working_resource = mock.MagicMock(
            physical_resource_id='bbbb',
            resource_type='OS::Nova::Server',
            resource_status='CREATE_COMPLETE',
            resource_name='my_server',
        )
        self.failed_deployment_resource = mock.MagicMock(
            physical_resource_id='eeee',
            resource_type='OS::Heat::SoftwareDeployment',
            resource_status='CREATE_FAILED',
            links=[],
            resource_name='my_deployment',
            resource_status_reason='Returned deploy_statuscode 1',
            logical_resource_id='my_deployment',
        )
        self.failed_deployment = mock.MagicMock(
            id='eeee',
            output_values={
                'deploy_statuscode': '1',
                'deploy_stderr': 'It broke',
                'deploy_stdout': ('1\n2\n3\n4\n5\n6\n7\n8\n9\n10'
                                  '\n11\n12')
            },
        )
        self.software_deployments_client.get.return_value = (
            self.failed_deployment)

    def test_build_failed_none(self):
        self.stack = mock.MagicMock(id='123', status='COMPLETE',
                                    stack_name='stack')
        failures = self.cmd._build_failed_resources('stack')
        expected = collections.OrderedDict()
        self.assertEqual(expected, failures)

    def test_build_failed_resources(self):
        self.resource_client.list.side_effect = [[
            # resource-list stack
            self.failed_template_resource,
            self.other_failed_template_resource,
            self.working_resource,
        ], [  # resource-list aaaa
            self.failed_resource
        ], [  # resource-list dddd
        ]]
        failures = self.cmd._build_failed_resources('stack')
        expected = collections.OrderedDict()
        expected['stack.my_templateresource.my_server'] = self.failed_resource
        expected['stack.my_othertemplateresource'] = (
            self.other_failed_template_resource)
        self.assertEqual(expected, failures)

    def test_build_failed_resources_not_found(self):
        self.resource_client.list.side_effect = [[
            # resource-list stack
            self.failed_template_resource,
            self.other_failed_template_resource,
            self.working_resource,
        ], exc.HTTPNotFound(), [  # resource-list dddd
        ]]

        failures = self.cmd._build_failed_resources('stack')
        expected = collections.OrderedDict()
        expected['stack.my_templateresource'] = self.failed_template_resource
        expected['stack.my_othertemplateresource'] = (
            self.other_failed_template_resource)
        self.assertEqual(expected, failures)

    def test_build_software_deployments(self):
        resources = {
            'stack.my_server': self.working_resource,
            'stack.my_deployment': self.failed_deployment_resource
        }
        deployments = self.cmd._build_software_deployments(resources)
        self.assertEqual({
            'eeee': self.failed_deployment
        }, deployments)

    def test_build_software_deployments_not_found(self):
        resources = {
            'stack.my_server': self.working_resource,
            'stack.my_deployment': self.failed_deployment_resource
        }
        self.software_deployments_client.get.side_effect = exc.HTTPNotFound()
        deployments = self.cmd._build_software_deployments(resources)
        self.assertEqual({}, deployments)

    def test_build_software_deployments_no_resources(self):
        resources = {}
        self.software_deployments_client.get.side_effect = exc.HTTPNotFound()
        deployments = self.cmd._build_software_deployments(resources)
        self.assertEqual({}, deployments)

    def test_list_stack_failures(self):
        self.resource_client.list.side_effect = [[
            # resource-list stack
            self.failed_template_resource,
            self.other_failed_template_resource,
            self.working_resource,
            self.failed_deployment_resource
        ], [  # resource-list aaaa
            self.failed_resource
        ], [  # resource-list dddd
        ]]

        arglist = ['stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.assertEqual(
            self.app.stdout.make_string(),
            '''stack.my_templateresource.my_server:
  resource_type: OS::Nova::Server
  physical_resource_id: cccc
  status: CREATE_FAILED
  status_reason: |
    All gone Pete Tong
stack.my_othertemplateresource:
  resource_type: My::OtherTemplateResource
  physical_resource_id: dddd
  status: CREATE_FAILED
  status_reason: |
    RPC timeout
stack.my_deployment:
  resource_type: OS::Heat::SoftwareDeployment
  physical_resource_id: eeee
  status: CREATE_FAILED
  status_reason: |
    Returned deploy_statuscode 1
  deploy_stdout: |
    ...
    3
    4
    5
    6
    7
    8
    9
    10
    11
    12
    (truncated, view all with --long)
  deploy_stderr: |
    It broke
''')

    def test_list_stack_failures_long(self):
        self.resource_client.list.side_effect = [[
            # resource-list stack
            self.failed_template_resource,
            self.other_failed_template_resource,
            self.working_resource,
            self.failed_deployment_resource
        ], [  # resource-list aaaa
            self.failed_resource
        ], [  # resource-list dddd
        ]]

        arglist = ['--long', 'stack']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        self.cmd.take_action(parsed_args)

        self.assertEqual(
            self.app.stdout.make_string(),
            '''stack.my_templateresource.my_server:
  resource_type: OS::Nova::Server
  physical_resource_id: cccc
  status: CREATE_FAILED
  status_reason: |
    All gone Pete Tong
stack.my_othertemplateresource:
  resource_type: My::OtherTemplateResource
  physical_resource_id: dddd
  status: CREATE_FAILED
  status_reason: |
    RPC timeout
stack.my_deployment:
  resource_type: OS::Heat::SoftwareDeployment
  physical_resource_id: eeee
  status: CREATE_FAILED
  status_reason: |
    Returned deploy_statuscode 1
  deploy_stdout: |
    1
    2
    3
    4
    5
    6
    7
    8
    9
    10
    11
    12
  deploy_stderr: |
    It broke
''')
