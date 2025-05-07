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
#

from cliff import columns

from heatclient.common import utils as heat_utils


class LinkColumn(columns.FormattableColumn):
    def human_readable(self):
        return heat_utils.link_formatter(self._value)


class JsonColumn(columns.FormattableColumn):
    def human_readable(self):
        return heat_utils.json_formatter(self._value)


class YamlColumn(columns.FormattableColumn):
    def human_readable(self):
        return heat_utils.yaml_formatter(self._value)


class TextWrapColumn(columns.FormattableColumn):
    def human_readable(self):
        return heat_utils.text_wrap_formatter(self._value)


class NewlineListColumn(columns.FormattableColumn):
    def human_readable(self):
        return heat_utils.newline_list_formatter(self._value)
