# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from heatclient.openstack.common.apiclient import base


class SoftwareConfig(base.Resource):
    def __repr__(self):
        return "<SoftwareConfig %s>" % self._info

    def delete(self):
        return self.manager.delete(config_id=self.id)

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class SoftwareConfigManager(base.BaseManager):
    resource_class = SoftwareConfig

    def get(self, config_id):
        """Get the details for a specific software config.

        :param config_id: ID of the software config
        """
        resp, body = self.client.json_request(
            'GET', '/software_configs/%s' % config_id)

        return SoftwareConfig(self, body['software_config'])

    def create(self, **kwargs):
        """Create a software config."""
        resp, body = self.client.json_request('POST', '/software_configs',
                                              data=kwargs)

        return SoftwareConfig(self, body['software_config'])

    def delete(self, config_id):
        """Delete a software config."""
        self._delete("/software_configs/%s" % config_id)
