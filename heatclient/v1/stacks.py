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

import six
from six.moves.urllib import parse

from heatclient.openstack.common.apiclient import base


class Stack(base.Resource):
    def __repr__(self):
        return "<Stack %s>" % self._info

    def preview(self, **fields):
        return self.manager.preview(**fields)

    def create(self, **fields):
        return self.manager.create(self.identifier, **fields)

    def update(self, **fields):
        self.manager.update(self.identifier, **fields)

    def delete(self):
        return self.manager.delete(self.identifier)

    def abandon(self):
        return self.manager.abandon(self.identifier)

    def snapshot(self, name=None):
        return self.manager.snapshot(self.identifier, name)

    def snapshot_show(self, snapshot_id):
        return self.manager.snapshot_show(self.identifier, snapshot_id)

    def snapshot_delete(self, snapshot_id):
        return self.manager.snapshot_delete(self.identifier, snapshot_id)

    def restore(self, snapshot_id):
        return self.manager.restore(self.identifier, snapshot_id)

    def snapshot_list(self):
        return self.manager.snapshot_list(self.identifier)

    def get(self):
        # set_loaded() first ... so if we have to bail, we know we tried.
        self._loaded = True
        if not hasattr(self.manager, 'get'):
            return

        new = self.manager.get(self.identifier)
        if new:
            self._add_details(new._info)

    @property
    def action(self):
        s = self.stack_status
        # Return everything before the first underscore
        return s[:s.index('_')]

    @property
    def status(self):
        s = self.stack_status
        # Return everything after the first underscore
        return s[s.index('_') + 1:]

    @property
    def identifier(self):
        return '%s/%s' % (self.stack_name, self.id)


class StackManager(base.BaseManager):
    resource_class = Stack

    def list(self, **kwargs):
        """Get a list of stacks.

        :param limit: maximum number of stacks to return
        :param marker: begin returning stacks that appear later in the stack
                       list than that represented by this stack id
        :param filters: dict of direct comparison filters that mimics the
                        structure of a stack object
        :rtype: list of :class:`Stack`
        """
        def paginate(params):
            '''Paginate stacks, even if more than API limit.'''
            current_limit = int(params.get('limit') or 0)
            url = '/stacks?%s' % parse.urlencode(params, True)
            stacks = self._list(url, 'stacks')
            for stack in stacks:
                yield stack

            num_stacks = len(stacks)
            remaining_limit = current_limit - num_stacks
            if remaining_limit > 0 and num_stacks > 0:
                params['limit'] = remaining_limit
                params['marker'] = stack.id
                for stack in paginate(params):
                    yield stack

        params = {}
        if 'filters' in kwargs:
            filters = kwargs.pop('filters')
            params.update(filters)

        for key, value in six.iteritems(kwargs):
            if value:
                params[key] = value

        return paginate(params)

    def preview(self, **kwargs):
        """Preview a stack."""
        headers = self.client.credentials_headers()
        resp, body = self.client.json_request('POST', '/stacks/preview',
                                              data=kwargs, headers=headers)
        return Stack(self, body['stack'])

    def create(self, **kwargs):
        """Create a stack."""
        headers = self.client.credentials_headers()
        resp, body = self.client.json_request('POST', '/stacks',
                                              data=kwargs, headers=headers)
        return body

    def update(self, stack_id, **kwargs):
        """Update a stack."""
        headers = self.client.credentials_headers()
        method = 'PATCH' if kwargs.pop('existing', None) else 'PUT'
        resp, body = self.client.json_request(method, '/stacks/%s' % stack_id,
                                              data=kwargs, headers=headers)

    def delete(self, stack_id):
        """Delete a stack."""
        self._delete("/stacks/%s" % stack_id)

    def abandon(self, stack_id):
        """Abandon a stack."""
        stack = self.get(stack_id)
        resp, body = self.client.json_request(
            'DELETE',
            '/stacks/%s/abandon' % stack.identifier)
        return body

    def snapshot(self, stack_id, name=None):
        """Snapshot a stack."""
        stack = self.get(stack_id)
        data = {}
        if name:
            data['name'] = name
        resp, body = self.client.json_request(
            'POST',
            '/stacks/%s/snapshots' % stack.identifier,
            data=data)
        return body

    def snapshot_show(self, stack_id, snapshot_id):
        stack = self.get(stack_id)
        resp, body = self.client.json_request(
            'GET',
            '/stacks/%s/snapshots/%s' % (stack.identifier, snapshot_id))
        return body

    def snapshot_delete(self, stack_id, snapshot_id):
        stack = self.get(stack_id)
        resp, body = self.client.json_request(
            'DELETE',
            '/stacks/%s/snapshots/%s' % (stack.identifier, snapshot_id))
        return body

    def restore(self, stack_id, snapshot_id):
        stack = self.get(stack_id)
        resp, body = self.client.json_request(
            'POST',
            '/stacks/%s/snapshots/%s/restore' % (stack.identifier,
                                                 snapshot_id))
        return body

    def snapshot_list(self, stack_id):
        stack = self.get(stack_id)
        resp, body = self.client.json_request(
            'GET',
            '/stacks/%s/snapshots' % stack.identifier)
        return body

    def get(self, stack_id):
        """Get the metadata for a specific stack.

        :param stack_id: Stack ID to lookup
        """
        resp, body = self.client.json_request('GET', '/stacks/%s' % stack_id)
        return Stack(self, body['stack'])

    def template(self, stack_id):
        """Get the template content for a specific stack as a parsed JSON
        object.

        :param stack_id: Stack ID to get the template for
        """
        resp, body = self.client.json_request(
            'GET', '/stacks/%s/template' % stack_id)
        return body

    def validate(self, **kwargs):
        """Validate a stack template."""
        resp, body = self.client.json_request('POST', '/validate', data=kwargs)
        return body


class StackChildManager(base.BaseManager):
    @property
    def api(self):
        return self.client

    def _resolve_stack_id(self, stack_id):
        # if the id already has a slash in it,
        # then it is already {stack_name}/{stack_id}
        if stack_id.find('/') > 0:
            return stack_id
        # We want to capture the redirect, not actually get the stack,
        # since all we want is the stacks:lookup response to get the
        # fully qualified ID, and not all users are allowed to do the
        # redirected stacks:show, so pass follow_redirects=False
        resp, body = self.client.json_request('GET',
                                              '/stacks/%s' % stack_id,
                                              follow_redirects=False)
        location = resp.headers.get('location')
        path = self.client.strip_endpoint(location)
        return path[len('/stacks/'):]
