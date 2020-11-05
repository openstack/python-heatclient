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

import json
import yaml

from heatclient._i18n import _

if hasattr(yaml, 'CSafeLoader'):
    yaml_loader_base = yaml.CSafeLoader
else:
    yaml_loader_base = yaml.SafeLoader

if hasattr(yaml, 'CSafeDumper'):
    yaml_dumper_base = yaml.CSafeDumper
else:
    yaml_dumper_base = yaml.SafeDumper


# We create custom class to not overriden the default yaml behavior
class yaml_loader(yaml_loader_base):
    pass


class yaml_dumper(yaml_dumper_base):
    pass


def _construct_yaml_str(self, node):
    """
    Parse a yaml string.

    Args:
        self: (todo): write your description
        node: (todo): write your description
    """
    # Override the default string handling function
    # to always return unicode objects
    return self.construct_scalar(node)


yaml_loader.add_constructor(u'tag:yaml.org,2002:str', _construct_yaml_str)
# Unquoted dates like 2013-05-23 in yaml files get loaded as objects of type
# datetime.data which causes problems in API layer when being processed by
# openstack.common.jsonutils. Therefore, make unicode string out of timestamps
# until jsonutils can handle dates.
yaml_loader.add_constructor(u'tag:yaml.org,2002:timestamp',
                            _construct_yaml_str)


def parse(tmpl_str):
    """Takes a string and returns a dict containing the parsed structure.

    This includes determination of whether the string is using the
    JSON or YAML format.
    """
    # strip any whitespace before the check
    tmpl_str = tmpl_str.strip()
    if tmpl_str.startswith('{'):
        tpl = json.loads(tmpl_str)
    else:
        try:
            tpl = yaml.load(tmpl_str, Loader=yaml_loader)
        except yaml.YAMLError:
            # NOTE(prazumovsky): we need to return more informative error for
            # user, so use SafeLoader, which return error message with template
            # snippet where error has been occurred.
            try:
                tpl = yaml.load(tmpl_str, Loader=yaml.SafeLoader)
            except yaml.YAMLError as yea:
                raise ValueError(yea)
        else:
            if tpl is None:
                tpl = {}
    # Looking for supported version keys in the loaded template
    if not ('HeatTemplateFormatVersion' in tpl
            or 'heat_template_version' in tpl
            or 'AWSTemplateFormatVersion' in tpl):
        raise ValueError(_("Template format version not found."))
    return tpl
