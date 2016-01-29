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

from tempest_lib import exceptions

from heatclient.tests.functional import base


class SimpleReadOnlyOpenStackClientTest(base.ClientTestBase):
    """Basic, read-only tests for Openstack CLI client heat plugin.

    Basic smoke test for the openstack CLI commands which do not require
    creating or modifying stacks.
    """

    def test_openstack_fake_action(self):
        self.assertRaises(exceptions.CommandFailed,
                          self.openstack,
                          'this-does-not-exist')

    def test_openstack_stack_list(self):
        self.openstack('stack list')

    def test_openstack_stack_list_debug(self):
        self.openstack('stack list', flags='--debug')

    def test_openstack_help_cmd(self):
        self.openstack('help stack')

    def test_openstack_version(self):
        self.openstack('', flags='--version')
