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

from oslo.utils import encodeutils

from heatclient.openstack.common.apiclient import base


class ResourceType(base.Resource):
    def __repr__(self):
        return "<ResourceType %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)

    def _add_details(self, info):
        self.resource_type = info


class ResourceTypeManager(base.BaseManager):
    resource_class = ResourceType

    def list(self):
        """Get a list of resource types.
        :rtype: list of :class:`ResourceType`
        """
        return self._list('/resource_types', 'resource_types')

    def get(self, resource_type):
        """Get the details for a specific resource_type.

        :param resource_type: name of the resource type to get the details for
        """
        url_str = '/resource_types/%s' % (
                  parse.quote(encodeutils.safe_encode(resource_type), ''))
        resp, body = self.client.json_request('GET', url_str)
        return body

    def generate_template(self, resource_type):
        url_str = '/resource_types/%s/template' % (
                  parse.quote(encodeutils.safe_encode(resource_type), ''))
        resp, body = self.client.json_request('GET', url_str)
        return body
