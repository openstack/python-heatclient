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

import os

import six
from tempest.lib.cli import base
from tempest.lib.cli import output_parser


class OpenStackClientTestBase(base.ClientTestBase):
    """Command line client base functions."""

    def setUp(self):
        super(OpenStackClientTestBase, self).setUp()
        self.parser = output_parser

    def _get_clients(self):
        cli_dir = os.environ.get(
            'OS_HEATCLIENT_EXEC_DIR',
            os.path.join(os.path.abspath('.'), '.tox/functional/bin'))

        return base.CLIClient(
            username=os.environ.get('OS_USERNAME'),
            password=os.environ.get('OS_PASSWORD'),
            tenant_name=os.environ.get('OS_TENANT_NAME'),
            uri=os.environ.get('OS_AUTH_URL'),
            cli_dir=cli_dir)

    def openstack(self, *args, **kwargs):
        return self.clients.openstack(*args, **kwargs)

    def get_template_path(self, templ_name):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            '../../templates/%s' % templ_name)

    def show_to_dict(self, output):
        obj = {}
        items = self.parser.listing(output)
        for item in items:
            obj[item['Field']] = six.text_type(item['Value'])
        return dict((self._key_name(k), v) for k, v in obj.items())

    def _key_name(self, key):
        return key.lower().replace(' ', '_')

    def list_to_dict(self, output, id):
        obj = {}
        items = self.parser.listing(output)
        for item in items:
            if item['ID'] == id:
                obj = item
                break
        return dict((self._key_name(k), v) for k, v in obj.items())

    def _stack_create(self, name, template, parameters=[], wait=True):
        cmd = 'stack create ' + name
        if template:
            cmd += ' -t ' + template
        if wait:
            cmd += ' --wait'

        for parameter in parameters:
            cmd += ' --parameter ' + parameter
        stack_raw = self.openstack(cmd)
        stack = self.show_to_dict(stack_raw)
        self.addCleanup(self._stack_delete, stack['id'])
        return stack

    def _stack_delete(self, id, wait=False):
        cmd = 'stack delete ' + id + ' --yes'
        if wait:
            cmd += ' --wait'
        if id in self.openstack('stack list --short'):
            self.openstack(cmd)

    def _stack_suspend(self, id, wait=True):
        cmd = 'stack suspend ' + id
        if wait:
            cmd += ' --wait'
        stack_raw = self.openstack(cmd)
        stack = self.list_to_dict(stack_raw, id)
        return stack

    def _stack_resume(self, id, wait=True):
        cmd = 'stack resume ' + id
        if wait:
            cmd += ' --wait'
        stack_raw = self.openstack(cmd)
        stack = self.list_to_dict(stack_raw, id)
        return stack

    def _stack_snapshot_create(self, id, name):
        cmd = 'stack snapshot create ' + id + ' --name ' + name
        snapshot_raw = self.openstack(cmd)
        snapshot = self.show_to_dict(snapshot_raw)
        self.addCleanup(self._stack_snapshot_delete, id, snapshot['id'])
        return snapshot

    def _stack_snapshot_delete(self, id, snapshot_id):
        cmd = 'stack snapshot delete ' + id + ' ' + snapshot_id
        if snapshot_id in self.openstack('stack snapshot list ' + id):
            self.openstack(cmd)

    def _stack_snapshot_restore(self, id, snapshot_id):
        cmd = 'stack snapshot restore ' + id + ' ' + snapshot_id
        self.openstack(cmd)
