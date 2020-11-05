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
        """
        Sets the service to the given service.

        Args:
            self: (todo): write your description
        """
        super(ManageServiceTest, self).setUp()

    def test_service_list(self):
        """
        Returns a json - rpc request.

        Args:
            self: (todo): write your description
        """
        class FakeResponse(object):
            def json(self):
                """
                Returns the json representation of this : class :.

                Args:
                    self: (todo): write your description
                """
                return {'services': []}

        class FakeClient(object):
            def get(self, *args, **kwargs):
                """
                See : meth : meth : get

                Args:
                    self: (todo): write your description
                """
                assert args[0] == ('/services')
                return FakeResponse()

        manager = services.ServiceManager(FakeClient())
        self.assertEqual([], manager.list())

    def test_service_list_403(self):
        """
        Test if a service service has a service.

        Args:
            self: (todo): write your description
        """
        class FakeClient403(object):

            def get(self, *args, **kwargs):
                """
                Wrapper around get ().

                Args:
                    self: (todo): write your description
                """
                assert args[0] == ('/services')
                raise exc.HTTPForbidden()

        manager = services.ServiceManager(FakeClient403())
        self.assertRaises(exc.HTTPForbidden,
                          manager.list)

    def test_service_list_503(self):
        """
        Test for a list of a service.

        Args:
            self: (todo): write your description
        """
        class FakeClient503(object):
            def get(self, *args, **kwargs):
                """
                Return an item.

                Args:
                    self: (todo): write your description
                """
                assert args[0] == ('/services')
                raise exc.HTTPServiceUnavailable()

        manager = services.ServiceManager(FakeClient503())
        self.assertRaises(exc.HTTPServiceUnavailable,
                          manager.list)
