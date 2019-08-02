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

from six.moves.urllib import parse

from heatclient._i18n import _
from heatclient.common import base
from heatclient.common import utils
from heatclient import exc


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

    def output_list(self):
        return self.manager.output_list(self.identifier)

    def output_show(self, output_key):
        return self.manager.output_show(self.identifier, output_key)

    def environment(self):
        return self.manager.environment(self.identifier)

    def files(self):
        return self.manager.files(self.identifier)

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
        # redirected stacks:show, so pass redirect=False
        resp = self.client.get('/stacks/%s' % stack_id, redirect=False)
        location = resp.headers.get('location')
        if not location:
            message = _("Location not returned with redirect")
            raise exc.InvalidEndpoint(message=message)
        return location.split('/stacks/', 1)[1]


class StackManager(StackChildManager):
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

        for key, value in kwargs.items():
            if value:
                params[key] = value

        return paginate(params)

    def preview(self, **kwargs):
        """Preview a stack."""
        headers = self.client.credentials_headers()
        resp = self.client.post('/stacks/preview',
                                data=kwargs, headers=headers)
        body = utils.get_response_body(resp)
        return Stack(self, body.get('stack'))

    def create(self, **kwargs):
        """Create a stack."""
        headers = self.client.credentials_headers()
        resp = self.client.post('/stacks',
                                data=kwargs, headers=headers)
        body = utils.get_response_body(resp)
        return body

    def update(self, stack_id, **kwargs):
        """Update a stack.

        :param stack_id: Stack name or ID to identifies the stack
        """
        headers = self.client.credentials_headers()
        if kwargs.pop('existing', None):
            self.client.patch('/stacks/%s' % stack_id, data=kwargs,
                              headers=headers)
        else:
            self.client.put('/stacks/%s' % stack_id, data=kwargs,
                            headers=headers)

    def preview_update(self, stack_id, **kwargs):
        """Preview a stack update.

        :param stack_id: Stack name or ID to identifies the stack
        """
        stack_identifier = self._resolve_stack_id(stack_id)
        headers = self.client.credentials_headers()
        path = '/stacks/%s/preview' % stack_identifier
        if kwargs.pop('show_nested', False):
            path += '?show_nested=True'
        if kwargs.pop('existing', None):
            resp = self.client.patch(path, data=kwargs, headers=headers)
        else:
            resp = self.client.put(path, data=kwargs, headers=headers)
        body = utils.get_response_body(resp)
        return body

    def delete(self, stack_id):
        """Delete a stack.

        :param stack_id: Stack name or ID to identifies the stack
        """
        self._delete("/stacks/%s" % stack_id)

    def abandon(self, stack_id):
        """Abandon a stack.

        :param stack_id: Stack name or ID to identifies the stack
        """
        stack_identifier = self._resolve_stack_id(stack_id)
        resp = self.client.delete('/stacks/%s/abandon' % stack_identifier)
        body = utils.get_response_body(resp)
        return body

    def export(self, stack_id):
        """Export data of a stack.

        :param stack_id: Stack name or ID to identifies the stack
        """
        stack_identifier = self._resolve_stack_id(stack_id)
        resp = self.client.get('/stacks/%s/export' % stack_identifier)
        body = utils.get_response_body(resp)
        return body

    def snapshot(self, stack_id, name=None):
        """Snapshot a stack.

        :param stack_id: Stack name or ID to identifies the stack
        """
        stack_identifier = self._resolve_stack_id(stack_id)
        data = {}
        if name:
            data['name'] = name
        resp = self.client.post('/stacks/%s/snapshots' % stack_identifier,
                                data=data)
        body = utils.get_response_body(resp)
        return body

    def snapshot_show(self, stack_id, snapshot_id):
        stack_identifier = self._resolve_stack_id(stack_id)
        resp = self.client.get('/stacks/%s/snapshots/%s' % (stack_identifier,
                                                            snapshot_id))
        body = utils.get_response_body(resp)
        return body

    def snapshot_delete(self, stack_id, snapshot_id):
        stack_identifier = self._resolve_stack_id(stack_id)
        resp = self.client.delete('/stacks/%s/snapshots/%s' %
                                  (stack_identifier, snapshot_id))
        body = utils.get_response_body(resp)
        return body

    def restore(self, stack_id, snapshot_id):
        stack_identifier = self._resolve_stack_id(stack_id)
        resp = self.client.post('/stacks/%s/snapshots/%s/restore' %
                                (stack_identifier, snapshot_id))
        body = utils.get_response_body(resp)
        return body

    def snapshot_list(self, stack_id):
        stack_identifier = self._resolve_stack_id(stack_id)
        resp = self.client.get('/stacks/%s/snapshots' % stack_identifier)
        body = utils.get_response_body(resp)
        return body

    def output_list(self, stack_id):
        stack_identifier = self._resolve_stack_id(stack_id)
        resp = self.client.get('/stacks/%s/outputs' % stack_identifier)
        body = utils.get_response_body(resp)
        return body

    def output_show(self, stack_id, output_key):
        stack_identifier = self._resolve_stack_id(stack_id)
        resp = self.client.get('/stacks/%(id)s/outputs/%(key)s' % {
            'id': stack_identifier,
            'key': output_key
        })
        body = utils.get_response_body(resp)
        return body

    def get(self, stack_id, resolve_outputs=True):
        """Get the metadata for a specific stack.

        :param stack_id: Stack ID or name to lookup
        :param resolve_outputs: If True, then outputs for this
               stack will be resolved
        """
        kwargs = {}
        if not resolve_outputs:
            kwargs['params'] = {"resolve_outputs": False}
        resp = self.client.get('/stacks/%s' % stack_id, **kwargs)
        body = utils.get_response_body(resp)
        return Stack(self, body.get('stack'), loaded=True)

    def template(self, stack_id):
        """Get template content for a specific stack as a parsed JSON object.

        :param stack_id: Stack ID or name to get the template for
        """
        resp = self.client.get('/stacks/%s/template' % stack_id)
        body = utils.get_response_body(resp)
        return body

    def environment(self, stack_id):
        """Returns the environment for an existing stack.

        :param stack_id: Stack name or ID to identifies the stack
        :return:
        """
        resp = self.client.get('/stacks/%s/environment' % stack_id)
        body = utils.get_response_body(resp)
        return body

    def files(self, stack_id):
        """Returns the files for an existing stack.

        :param stack_id: Stack name or ID to identifies the stack.
        :return:
        """
        resp = self.client.get('/stacks/%s/files' % stack_id)
        body = utils.get_response_body(resp)
        return body

    def validate(self, **kwargs):
        """Validate a stack template."""

        url = '/validate'

        params = {}
        if kwargs.pop('show_nested', False):
            params['show_nested'] = True

        ignore_errors = kwargs.pop('ignore_errors', None)
        if ignore_errors:
            params['ignore_errors'] = ignore_errors

        args = {}
        if kwargs:
            args['data'] = kwargs
        if params:
            args['params'] = params

        resp = self.client.post(url, **args)
        body = utils.get_response_body(resp)
        return body
