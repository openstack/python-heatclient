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

from heatclient.openstack.common.py3kcompat import urlutils

from heatclient.common import base


class Stack(base.Resource):
    def __repr__(self):
        return "<Stack %s>" % self._info

    def create(self, **fields):
        return self.manager.create(self.identifier, **fields)

    def update(self, **fields):
        self.manager.update(self.identifier, **fields)

    def delete(self):
        return self.manager.delete(self.identifier)

    def get(self):
        # set_loaded() first ... so if we have to bail, we know we tried.
        self.set_loaded(True)
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


class StackManager(base.Manager):
    resource_class = Stack

    def list(self, **kwargs):
        """Get a list of stacks.

        :param page_size: number of items to request in each paginated request
        :param limit: maximum number of stacks to return
        :param marker: begin returning stacks that appear later in the stack
                       list than that represented by this stack id
        :param filters: dict of direct comparison filters that mimics the
                        structure of a stack object
        :rtype: list of :class:`Stack`
        """
        absolute_limit = kwargs.get('limit')

        def paginate(qp, seen=0):
            sort_qp = sorted(qp.items(), key=lambda x: x[0])
            url = '/stacks?%s' % urlutils.urlencode(sort_qp)

            stacks = self._list(url, "stacks")
            for stack in stacks:
                seen += 1
                if absolute_limit is not None and seen > absolute_limit:
                    return
                yield stack

            page_size = qp.get('limit')
            if (page_size and len(stacks) == page_size and
                    (absolute_limit is None or 0 < seen < absolute_limit)):
                qp['marker'] = stack.id
                for stack in paginate(qp, seen):
                    yield stack

        params = {}
        if 'page_size' in kwargs:
            params['limit'] = kwargs['page_size']

        if 'marker' in kwargs:
            params['marker'] = kwargs['marker']

        filters = kwargs.get('filters', {})
        properties = filters.pop('properties', {})
        for key, value in properties.items():
            params['property-%s' % key] = value
        params.update(filters)

        return paginate(params)

    def create(self, **kwargs):
        """Create a stack."""
        headers = self.api.credentials_headers()
        resp, body = self.api.json_request('POST', '/stacks',
                                           body=kwargs, headers=headers)
        return body

    def update(self, stack_id, **kwargs):
        """Update a stack."""
        headers = self.api.credentials_headers()
        resp, body = self.api.json_request('PUT', '/stacks/%s' % stack_id,
                                           body=kwargs, headers=headers)

    def delete(self, stack_id):
        """Delete a stack."""
        self._delete("/stacks/%s" % stack_id)

    def get(self, stack_id):
        """Get the metadata for a specific stack.

        :param stack_id: Stack ID to lookup
        """
        resp, body = self.api.json_request('GET', '/stacks/%s' % stack_id)
        return Stack(self, body['stack'])

    def template(self, stack_id):
        """Get the template content for a specific stack as a parsed JSON
        object.

        :param stack_id: Stack ID to get the template for
        """
        resp, body = self.api.json_request(
            'GET', '/stacks/%s/template' % stack_id)
        return body

    def validate(self, **kwargs):
        """Validate a stack template."""
        resp, body = self.api.json_request('POST', '/validate', body=kwargs)
        return body


class StackChildManager(base.Manager):

    def _resolve_stack_id(self, stack_id):
        # if the id already has a slash in it,
        # then it is already {stack_name}/{stack_id}
        if stack_id.find('/') > 0:
            return stack_id
        resp, body = self.api.json_request('GET',
                                           '/stacks/%s' % stack_id)
        stack = body['stack']
        return '%s/%s' % (stack['stack_name'], stack['id'])
