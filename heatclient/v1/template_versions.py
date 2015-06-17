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

from heatclient.openstack.common.apiclient import base


class TemplateVersion(base.Resource):
    def __repr__(self):
        return "<TemplateVersion %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class TemplateVersionManager(base.BaseManager):
    resource_class = TemplateVersion

    def list(self):
        """Get a list of template versions.
        :rtype: list of :class:`TemplateVersion`
        """
        return self._list('/template_versions', 'template_versions')
