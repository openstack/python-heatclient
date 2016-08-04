# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
from oslo_serialization import jsonutils
import testtools

from heatclient.tests.unit import fakes
from heatclient.v1 import build_info


class BuildInfoManagerTest(testtools.TestCase):
    def setUp(self):
        super(BuildInfoManagerTest, self).setUp()
        self.client = mock.Mock()
        self.client.get.return_value = fakes.FakeHTTPResponse(
            200,
            None,
            {'content-type': 'application/json'},
            jsonutils.dumps('body')
        )
        self.manager = build_info.BuildInfoManager(self.client)

    def test_build_info_makes_a_call_to_the_api(self):
        self.manager.build_info()
        self.client.get.assert_called_once_with('/build_info')

    def test_build_info_returns_the_response_body(self):
        response = self.manager.build_info()
        self.assertEqual('body', response)
