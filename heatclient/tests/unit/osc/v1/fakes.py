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

import mock

from heatclient.tests.unit.osc import fakes
from heatclient.tests.unit.osc import utils


class FakeOrchestrationv1Client(object):
    def __init__(self, **kwargs):
        self.http_client = mock.Mock()
        self.http_client.auth_token = kwargs['token']
        self.http_client.management_url = kwargs['endpoint']
        self.stacks = mock.Mock()
        self.stacks.list = mock.Mock(return_value=[])
        self.resources = fakes.FakeResource(None, {})
        self.resource_types = fakes.FakeResource(None, {})
        self.events = fakes.FakeResource(None, {})
        self.actions = fakes.FakeResource(None, {})
        self.build_info = fakes.FakeResource(None, {})
        self.software_deployments = fakes.FakeResource(None, {})
        self.software_configs = fakes.FakeResource(None, {})
        self.template_versions = fakes.FakeResource(None, {})


class TestOrchestrationv1(utils.TestCommand):
    def setUp(self):
        super(TestOrchestrationv1, self).setUp()

        self.app.client_manager.orchestration = FakeOrchestrationv1Client(
            endpoint=fakes.AUTH_URL,
            token=fakes.AUTH_TOKEN,
        )
