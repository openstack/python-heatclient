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

from heatclient.common import base
from heatclient.common import utils


class SoftwareConfig(base.Resource):
    def __repr__(self):
        return "<SoftwareConfig %s>" % self._info

    def delete(self):
        return self.manager.delete(config_id=self.id)

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class SoftwareConfigManager(base.BaseManager):
    resource_class = SoftwareConfig

    def list(self, **kwargs):
        """Get a list of software configs.

        :rtype: list of :class:`SoftwareConfig`
        """
        qparams = {}

        for opt, val in kwargs.items():
            if val:
                qparams[opt] = val

        # Transform the dict to a sequence of two-element tuples in fixed
        # order, then the encoded string will be consistent in Python 2&3.
        if qparams:
            new_qparams = sorted(qparams.items(), key=lambda x: x[0])
            query_string = "?%s" % parse.urlencode(new_qparams)
        else:
            query_string = ""
        url = '/software_configs%s' % query_string
        return self._list(url, "software_configs")

    def get(self, config_id):
        """Get the details for a specific software config.

        :param config_id: ID of the software config
        """
        resp = self.client.get('/software_configs/%s' % config_id)
        body = utils.get_response_body(resp)
        return SoftwareConfig(self, body.get('software_config'))

    def create(self, **kwargs):
        """Create a software config."""
        resp = self.client.post('/software_configs',
                                data=kwargs)
        body = utils.get_response_body(resp)
        return SoftwareConfig(self, body.get('software_config'))

    def delete(self, config_id):
        """Delete a software config."""
        self._delete("/software_configs/%s" % config_id)
