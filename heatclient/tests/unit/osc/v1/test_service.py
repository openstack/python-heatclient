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

from heatclient.osc.v1 import service as osc_service
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes


class TestServiceList(orchestration_fakes.TestOrchestrationv1):
    response = {"services": [
        {
            "status": "up",
            "binary": "heat-engine",
            "report_interval": 60,
            "engine_id": "9d9242c3-4b9e-45e1-9e74-7615fbf20e5d",
            "created_at": "2015-02-03T05:55:59.000000",
            "hostname": "mrkanag",
            "updated_at": "2015-02-03T05:57:59.000000",
            "topic": "engine",
            "host": "engine-1",
            "deleted_at": 'null',
            "id": "e1908f44-42f9-483f-b778-bc814072c33d"
        },
        {
            "status": "down",
            "binary": "heat-engine",
            "report_interval": 60,
            "engine_id": "2d2434bf-adb6-4453-9c6b-b22fb8bd2306",
            "created_at": "2015-02-03T06:03:14.000000",
            "hostname": "mrkanag",
            "updated_at": "2015-02-03T06:09:55.000000",
            "topic": "engine",
            "host": "engine",
            "deleted_at": 'null',
            "id": "582b5657-6db7-48ad-8483-0096350faa21"
        }
    ]}

    columns = ['Hostname', 'Binary', 'Engine ID', 'Host',
               'Topic', 'Updated At', 'Status']

    def setUp(self):
        super(TestServiceList, self).setUp()
        self.cmd = osc_service.ListService(self.app, None)
        self.mock_client = self.app.client_manager.orchestration
        self.mock_client.services.list.return_value = self.response

    def test_service_list(self):
        arglist = []
        parsed_args = self.check_parser(self.cmd, arglist, [])
        columns, data = self.cmd.take_action(parsed_args)
        self.mock_client.services.list.assert_called_with()
        self.assertEqual(self.columns, columns)
