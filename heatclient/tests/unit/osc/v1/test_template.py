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
#   Copyright 2015 IBM Corp.

import mock

from heatclient import exc
from heatclient.osc.v1 import template
from heatclient.tests.unit.osc.v1 import fakes
from heatclient.v1 import template_versions


class TestTemplate(fakes.TestOrchestrationv1):
    def setUp(self):
        super(TestTemplate, self).setUp()
        self.mock_client = self.app.client_manager.orchestration
        self.template_versions = self.mock_client.template_versions


class TestTemplateVersionList(TestTemplate):

    defaults = [
        {'version': 'HOT123', 'type': 'hot'},
        {'version': 'CFN456', 'type': 'cfn'}
    ]

    def setUp(self):
        super(TestTemplateVersionList, self).setUp()
        tv1 = template_versions.TemplateVersion(None, self.defaults[0])
        tv2 = template_versions.TemplateVersion(None, self.defaults[1])
        self.template_versions.list.return_value = [tv1, tv2]
        self.cmd = template.VersionList(self.app, None)

    def test_version_list(self):
        parsed_args = self.check_parser(self.cmd, [], [])

        columns, data = self.cmd.take_action(parsed_args)

        self.assertEqual(['version', 'type'], columns)
        self.assertEqual([('HOT123', 'hot'), ('CFN456', 'cfn')], list(data))


class TestTemplateFunctionList(TestTemplate):

    defaults = [
        {'functions': 'func1', 'description': 'Function 1'},
        {'functions': 'func2', 'description': 'Function 2'}
    ]

    def setUp(self):
        super(TestTemplateFunctionList, self).setUp()
        tv1 = template_versions.TemplateVersion(None, self.defaults[0])
        tv2 = template_versions.TemplateVersion(None, self.defaults[1])
        self.template_versions.get.return_value = [tv1, tv2]
        self.cmd = template.FunctionList(self.app, None)

    def test_function_list(self):
        arglist = ['version1']
        parsed_args = self.check_parser(self.cmd, arglist, [])

        columns, data = self.cmd.take_action(parsed_args)

        self.assertEqual(['functions', 'description'], columns)
        self.assertEqual([('func1', 'Function 1'), ('func2', 'Function 2')],
                         list(data))

    def test_function_list_not_found(self):
        arglist = ['bad_version']
        self.template_versions.get.side_effect = exc.HTTPNotFound
        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.assertRaises(exc.CommandError, self.cmd.take_action, parsed_args)


class TestTemplateValidate(TestTemplate):

    template_path = 'heatclient/tests/test_templates/empty.yaml'
    env_path = 'heatclient/tests/unit/var/environment.json'

    defaults = {
        'environment': {},
        'files': {},
        'parameters': {},
        'template': {'heat_template_version': '2013-05-23'}
    }

    def setUp(self):
        super(TestTemplateValidate, self).setUp()
        self.stack_client = self.app.client_manager.orchestration.stacks
        self.stack_client.validate = mock.MagicMock(return_value={})
        self.cmd = template.Validate(self.app, None)

    def test_validate(self):
        arglist = ['-t', self.template_path]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)

        self.stack_client.validate.assert_called_once_with(**self.defaults)
        self.assertEqual([], columns)
        self.assertEqual([], data)

    def test_validate_env(self):
        arglist = ['-t', self.template_path, '-e', self.env_path]
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)

        self.assertEqual(1, self.stack_client.validate.call_count)
        args = self.stack_client.validate.call_args[1]
        self.assertEqual(args.get('environment'), {'parameters': {}})
        self.assertTrue(self.env_path in args.get('environment_files')[0])
        self.assertEqual([], columns)
        self.assertEqual([], data)

    def test_validate_nested(self):
        arglist = ['-t', self.template_path, '--show-nested']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        args = dict(self.defaults)
        args['show_nested'] = True
        self.stack_client.validate.assert_called_once_with(**args)
        self.assertEqual([], columns)
        self.assertEqual([], data)

    def test_validate_parameter(self):
        arglist = ['-t', self.template_path,
                   '--parameter', 'key1=value1',
                   '--parameter', 'key2=value2']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        args = dict(self.defaults)
        args['parameters'] = {'key1': 'value1', 'key2': 'value2'}
        self.stack_client.validate.assert_called_once_with(**args)
        self.assertEqual([], columns)
        self.assertEqual([], data)

    def test_validate_ignore_errors(self):
        arglist = ['-t', self.template_path,
                   '--ignore-errors', 'err1,err2']
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        args = dict(self.defaults)
        args['ignore_errors'] = 'err1,err2'
        self.stack_client.validate.assert_called_once_with(**args)
        self.assertEqual([], columns)
        self.assertEqual([], data)
