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

from six.moves.urllib import parse

from heatclient.openstack.common.apiclient import base


class SoftwareDeployment(base.Resource):
    def __repr__(self):
        return "<SoftwareDeployment %s>" % self._info

    def update(self, **fields):
        self.manager.update(deployment_id=self.id, **fields)

    def delete(self):
        return self.manager.delete(deployment_id=self.id)


class SoftwareDeploymentManager(base.BaseManager):
    resource_class = SoftwareDeployment

    def list(self, **kwargs):
        """Get a list of software deployments.
        :rtype: list of :class:`SoftwareDeployment`
        """
        url = '/software_deployments?%s' % parse.urlencode(kwargs)
        return self._list(url, "software_deployments")

    def metadata(self, server_id):
        """Get a grouped collection of software deployment metadata for a
        given server.
        :rtype: list of :class:`SoftwareDeployment`
        """
        url = '/software_deployments/metadata/%s' % parse.quote(
            server_id, '')
        resp, body = self.client.json_request('GET', url)
        return body['metadata']

    def get(self, deployment_id):
        """Get the details for a specific software deployment.

        :param deployment_id: ID of the software deployment
        """
        resp, body = self.client.json_request(
            'GET', '/software_deployments/%s' % deployment_id)

        return SoftwareDeployment(self, body['software_deployment'])

    def create(self, **kwargs):
        """Create a software deployment."""
        resp, body = self.client.json_request(
            'POST', '/software_deployments', data=kwargs)
        return SoftwareDeployment(self, body['software_deployment'])

    def update(self, deployment_id, **kwargs):
        """Update a software deployment."""
        resp, body = self.client.json_request(
            'PUT', '/software_deployments/%s' % deployment_id, data=kwargs)
        return SoftwareDeployment(self, body['software_deployment'])

    def delete(self, deployment_id):
        """Delete a software deployment."""
        self._delete("/software_deployments/%s" % deployment_id)
