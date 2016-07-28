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

import testtools

from heatclient import exc
from heatclient.v1 import services


class ManageServiceTest(testtools.TestCase):
    def setUp(self):
        super(ManageServiceTest, self).setUp()

    def test_service_list(self):
        class FakeResponse(object):
            def json(self):
                return {'services': []}

        class FakeClient(object):
            def get(self, *args, **kwargs):
                assert args[0] == ('/services')
                return FakeResponse()

        manager = services.ServiceManager(FakeClient())
        self.assertEqual([], manager.list())

    def test_service_list_403(self):
        class FakeClient403(object):

            def get(self, *args, **kwargs):
                assert args[0] == ('/services')
                raise exc.HTTPForbidden()

        manager = services.ServiceManager(FakeClient403())
        self.assertRaises(exc.HTTPForbidden,
                          manager.list)

    def test_service_list_503(self):
        class FakeClient503(object):
            def get(self, *args, **kwargs):
                assert args[0] == ('/services')
                raise exc.HTTPServiceUnavailable()

        manager = services.ServiceManager(FakeClient503())
        self.assertRaises(exc.HTTPServiceUnavailable,
                          manager.list)
