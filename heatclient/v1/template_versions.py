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

    def get(self, template_version, **kwargs):
        """Get a list of functions for a specific resource_type.

        :param template_version: template version to get the functions for
        """
        url_str = '/template_versions/%s/functions' % (
                  parse.quote(encodeutils.safe_encode(template_version)))

        params = {}
        if 'with_condition_func' in kwargs:
            with_condition_func = kwargs.pop('with_condition_func')
            params.update({'with_condition_func': with_condition_func})
        if params:
            url_str += '?%s' % parse.urlencode(params, True)

        return self._list(url_str, 'template_functions')
