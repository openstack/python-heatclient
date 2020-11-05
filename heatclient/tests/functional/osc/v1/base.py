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
from tempest.lib import exceptions as tempest_exc


class OpenStackClientTestBase(base.ClientTestBase):
    """Command line client base functions."""

    def setUp(self):
        """
        Sets the output of the client.

        Args:
            self: (todo): write your description
        """
        super(OpenStackClientTestBase, self).setUp()
        self.parser = output_parser

    def _get_clients(self):
        """
        Returns cli clients.

        Args:
            self: (todo): write your description
        """
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
        """
        Opens a stack.

        Args:
            self: (todo): write your description
        """
        return self.clients.openstack(*args, **kwargs)

    def get_template_path(self, templ_name):
        """
        Returns the template path to use the template.

        Args:
            self: (todo): write your description
            templ_name: (str): write your description
        """
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            '../../templates/%s' % templ_name)

    def show_to_dict(self, output):
        """
        Convert a dictionary to a dictionary.

        Args:
            self: (todo): write your description
            output: (str): write your description
        """
        obj = {}
        items = self.parser.listing(output)
        for item in items:
            obj[item['Field']] = six.text_type(item['Value'])
        return dict((self._key_name(k), v) for k, v in obj.items())

    def _key_name(self, key):
        """
        Returns the key name for a key name.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        return key.lower().replace(' ', '_')

    def list_to_dict(self, output, id):
        """
        Convert a dict to a dictionary.

        Args:
            self: (todo): write your description
            output: (str): write your description
            id: (str): write your description
        """
        obj = {}
        items = self.parser.listing(output)
        for item in items:
            if item['ID'] == id:
                obj = item
                break
        return dict((self._key_name(k), v) for k, v in obj.items())

    def _stack_create(self, name, template, parameters=[], wait=True):
        """
        Create a stack stack.

        Args:
            self: (todo): write your description
            name: (str): write your description
            template: (str): write your description
            parameters: (todo): write your description
            wait: (str): write your description
        """
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
        """
        Delete a stack stack

        Args:
            self: (todo): write your description
            id: (str): write your description
            wait: (str): write your description
        """
        cmd = 'stack delete ' + id + ' --yes'
        if wait:
            cmd += ' --wait'
        if id in self.openstack('stack list --short'):
            try:
                self.openstack(cmd)
            except tempest_exc.CommandFailed as e:
                msg = "Stack not found: %s" % id
                if msg in six.text_type(e.stdout):
                    return
                raise

    def _stack_suspend(self, id, wait=True):
        """
        Suspendend a stack

        Args:
            self: (todo): write your description
            id: (int): write your description
            wait: (bool): write your description
        """
        cmd = 'stack suspend ' + id
        if wait:
            cmd += ' --wait'
        stack_raw = self.openstack(cmd)
        stack = self.list_to_dict(stack_raw, id)
        return stack

    def _stack_resume(self, id, wait=True):
        """
        Resume a stack.

        Args:
            self: (todo): write your description
            id: (int): write your description
            wait: (bool): write your description
        """
        cmd = 'stack resume ' + id
        if wait:
            cmd += ' --wait'
        stack_raw = self.openstack(cmd)
        stack = self.list_to_dict(stack_raw, id)
        return stack

    def _stack_snapshot_create(self, id, name):
        """
        Create a snapshot snapshot of a snapshot.

        Args:
            self: (todo): write your description
            id: (str): write your description
            name: (str): write your description
        """
        cmd = 'stack snapshot create ' + id + ' --name ' + name
        snapshot_raw = self.openstack(cmd)
        snapshot = self.show_to_dict(snapshot_raw)
        self.addCleanup(self._stack_snapshot_delete, id, snapshot['id'])
        return snapshot

    def _stack_snapshot_delete(self, id, snapshot_id):
        """
        Deletes snapshot

        Args:
            self: (todo): write your description
            id: (str): write your description
            snapshot_id: (str): write your description
        """
        cmd = 'stack snapshot delete ' + id + ' ' + snapshot_id
        if snapshot_id in self.openstack('stack snapshot list ' + id):
            self.openstack(cmd)

    def _stack_snapshot_restore(self, id, snapshot_id):
        """
        Open snapshot of the snapshot

        Args:
            self: (todo): write your description
            id: (int): write your description
            snapshot_id: (str): write your description
        """
        cmd = 'stack snapshot restore ' + id + ' ' + snapshot_id
        self.openstack(cmd)

    def _stack_show(self, stack_id):
        """
        Show the current stack

        Args:
            self: (todo): write your description
            stack_id: (int): write your description
        """
        cmd = 'stack show ' + stack_id
        stack_raw = self.openstack(cmd)
        return self.show_to_dict(stack_raw)
