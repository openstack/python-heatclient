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
import six
from six.moves.urllib import parse

from heatclient.common import base
from heatclient.common import utils


class ResourceType(base.Resource):
    def __repr__(self):
        """
        Return a repr representation of - repr representation of this object.

        Args:
            self: (todo): write your description
        """
        if isinstance(self._info, six.string_types):
            return "<ResourceType %s>" % self._info
        else:
            return "<ResourceType %s>" % self._info.get('resource_type')

    def data(self, **kwargs):
        """
        The data for the : class.

        Args:
            self: (todo): write your description
        """
        return self.manager.data(self, **kwargs)

    def _add_details(self, info):
        """
        Add details to the resource

        Args:
            self: (todo): write your description
            info: (dict): write your description
        """
        if isinstance(info, six.string_types):
            self.resource_type = info
        elif isinstance(info, dict):
            self.resource_type = info.get('resource_type')
            self.description = info.get('description')


class ResourceTypeManager(base.BaseManager):
    resource_class = ResourceType
    KEY = 'resource_types'

    def list(self, **kwargs):
        """Get a list of resource types.

        :rtype: list of :class:`ResourceType`
        """

        url = '/%s' % self.KEY
        params = {}
        if 'filters' in kwargs:
            filters = kwargs.pop('filters')
            params.update(filters)
        if 'with_description' in kwargs:
            with_description = kwargs.pop('with_description')
            params.update({'with_description': with_description})
        if params:
            url += '?%s' % parse.urlencode(params, True)

        return self._list(url, self.KEY)

    def get(self, resource_type, with_description=False):
        """Get the details for a specific resource_type.

        :param resource_type: name of the resource type to get the details for
        :param with_description: return result with description or not
        """
        url_str = '/%s/%s' % (
                  self.KEY,
                  parse.quote(encodeutils.safe_encode(resource_type)))
        resp = self.client.get(url_str,
                               params={'with_description': with_description})
        body = utils.get_response_body(resp)
        return body

    def generate_template(self, resource_type, template_type='cfn'):
        """
        Generate a template.

        Args:
            self: (todo): write your description
            resource_type: (str): write your description
            template_type: (str): write your description
        """
        url_str = '/%s/%s/template' % (
                  self.KEY,
                  parse.quote(encodeutils.safe_encode(resource_type)))
        if template_type:
            url_str += '?%s' % parse.urlencode(
                {'template_type': template_type}, True)
        resp = self.client.get(url_str)
        body = utils.get_response_body(resp)
        return body
