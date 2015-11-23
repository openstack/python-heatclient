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
        self.template_versions.list = mock.MagicMock(return_value=[tv1, tv2])
        self.cmd = template.VersionList(self.app, None)

    def test_version_list(self):
        parsed_args = self.check_parser(self.cmd, [], [])

        columns, data = self.cmd.take_action(parsed_args)

        self.assertEqual(['version', 'type'], columns)
        self.assertEqual([('HOT123', 'hot'), ('CFN456', 'cfn')], list(data))
