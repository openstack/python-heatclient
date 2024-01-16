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

from oslo_utils import encodeutils
from urllib import parse

from heatclient.common import base
from heatclient.common import utils
from heatclient.v1 import stacks

DEFAULT_PAGE_SIZE = 20


class Resource(base.Resource):
    def __repr__(self):
        return "<Resource %s>" % self._info

    def update(self, **fields):
        self.manager.update(self, **fields)

    def delete(self):
        return self.manager.delete(self)

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)

    @property
    def stack_name(self):
        if not hasattr(self, 'links'):
            return
        for link in self.links:
            if link['rel'] == 'stack':
                return link['href'].split('/')[-2]


class ResourceManager(stacks.StackChildManager):
    resource_class = Resource

    def list(self, stack_id, **kwargs):
        """Get a list of resources.

        :rtype: list of :class:`Resource`
        """
        params = {}

        if 'filters' in kwargs:
            filters = kwargs.pop('filters')
            params.update(filters)

        for key, value in kwargs.items():
            if value:
                params[key] = value

        url = '/stacks/%s/resources' % stack_id
        if params:
            url += '?%s' % parse.urlencode(params, True)

        return self._list(url, "resources")

    def get(self, stack_id, resource_name, with_attr=None):
        """Get the details for a specific resource.

        :param stack_id: ID or name of stack containing the resource
        :param resource_name: ID of resource to get the details for
        :param with_attr: Attributes to show
        """
        stack_id = self._resolve_stack_id(stack_id)
        url_str = '/stacks/%s/resources/%s' % (
                  parse.quote(stack_id),
                  parse.quote(encodeutils.safe_encode(resource_name)))
        if with_attr:
            params = {'with_attr': with_attr}
            url_str += '?%s' % parse.urlencode(params, True)

        resp = self.client.get(url_str)
        body = utils.get_response_body(resp)
        return Resource(self, body.get('resource'))

    def metadata(self, stack_id, resource_name):
        """Get the metadata for a specific resource.

        :param stack_id: ID or name of stack containing the resource
        :param resource_name: ID of resource to get metadata for
        """
        stack_id = self._resolve_stack_id(stack_id)
        url_str = '/stacks/%s/resources/%s/metadata' % (
                  parse.quote(stack_id),
                  parse.quote(encodeutils.safe_encode(resource_name)))
        resp = self.client.get(url_str)
        body = utils.get_response_body(resp)
        return body.get('metadata')

    def signal(self, stack_id, resource_name, data=None):
        """Signal a specific resource.

        :param stack_id: ID or name of stack containing the resource
        :param resource_name: ID of resource to send signal to
        """
        stack_id = self._resolve_stack_id(stack_id)
        url_str = '/stacks/%s/resources/%s/signal' % (
                  parse.quote(stack_id),
                  parse.quote(encodeutils.safe_encode(resource_name)))
        resp = self.client.post(url_str, data=data)
        body = utils.get_response_body(resp)
        return body

    def mark_unhealthy(self, stack_id, resource_name,
                       mark_unhealthy, resource_status_reason):
        """Mark a resource as healthy or unhealthy.

        :param stack_id: ID or name of stack containing the resource
        :param resource_name: ID of resource
        :param mark_unhealthy: Mark resource unhealthy if set to True
        :param resource_status_reason: Reason for resource status change.
        """
        stack_id = self._resolve_stack_id(stack_id)
        url_str = '/stacks/%s/resources/%s' % (
                  parse.quote(stack_id),
                  parse.quote(encodeutils.safe_encode(resource_name)))
        resp = self.client.patch(
            url_str,
            data={"mark_unhealthy": mark_unhealthy,
                  "resource_status_reason": resource_status_reason})

        body = utils.get_response_body(resp)
        return body

    def generate_template(self, resource_name):
        """Deprecated in favor of generate_template in ResourceTypeManager."""

        url_str = '/resource_types/%s/template' % (
                  parse.quote(encodeutils.safe_encode(resource_name)))
        resp = self.client.get(url_str)
        body = utils.get_response_body(resp)
        return body
