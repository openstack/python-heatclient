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

from unittest import mock

from heatclient.osc.v1 import build_info as osc_build_info
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes


class TestBuildInfo(orchestration_fakes.TestOrchestrationv1):
    response = {"api": {
        "revision": "{api_build_revision}"
        },
        "engine": {
            "revision": "{engine_build_revision}"
        }
    }

    def setUp(self):
        super(TestBuildInfo, self).setUp()
        self.cmd = osc_build_info.BuildInfo(self.app, None)
        self.mock_client = self.app.client_manager.orchestration
        self.mock_client.build_info.build_info = mock.Mock(
            return_value=self.response)

    def test_build_info(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        self.mock_client.build_info.build_info.assert_called_with()
        self.assertEqual(['api', 'engine'], columns)
        self.assertEqual(['{\n  "revision": "{api_build_revision}"\n}',
                          '{\n  "revision": "{engine_build_revision}"\n}'],
                         list(data))
