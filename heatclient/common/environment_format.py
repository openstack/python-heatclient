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

from heatclient.common import template_format
from heatclient.openstack.common._i18n import _

import yaml


SECTIONS = (
    PARAMETER_DEFAULTS, PARAMETERS, RESOURCE_REGISTRY, EVENT_SINKS
) = (
    'parameter_defaults', 'parameters', 'resource_registry', 'event_sinks'
)


def parse(env_str):
    """Takes a string and returns a dict containing the parsed structure.

    This includes determination of whether the string is using the
    YAML format.
    """
    try:
        env = yaml.load(env_str, Loader=template_format.yaml_loader)
    except yaml.YAMLError:
        # NOTE(prazumovsky): we need to return more informative error for
        # user, so use SafeLoader, which return error message with template
        # snippet where error has been occurred.
        try:
            env = yaml.load(env_str, Loader=yaml.SafeLoader)
        except yaml.YAMLError as yea:
            raise ValueError(yea)
    else:
        if env is None:
            env = {}
        elif not isinstance(env, dict):
            raise ValueError(_('The environment is not a valid '
                             'YAML mapping data type.'))

    for param in env:
        if param not in SECTIONS:
            raise ValueError(_('environment has wrong section "%s"') % param)

    return env


def default_for_missing(env):
    """Checks a parsed environment for missing sections."""

    for param in SECTIONS:
        if param not in env:
            env[param] = {}
