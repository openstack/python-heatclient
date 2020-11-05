#   Copyright 2014 OpenStack Foundation
#
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

from heatclient.tests.unit.osc import utils


class TestOrchestrationv1(utils.TestCommand):
    def setUp(self):
        """
        Set the client.

        Args:
            self: (todo): write your description
        """
        super(TestOrchestrationv1, self).setUp()

        self.app.client_manager.orchestration = mock.MagicMock()
