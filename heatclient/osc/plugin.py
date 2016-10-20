#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

"""OpenStackClient plugin for Orchestration service."""

import logging

from osc_lib import utils

LOG = logging.getLogger(__name__)

DEFAULT_ORCHESTRATION_API_VERSION = '1'
API_VERSION_OPTION = 'os_orchestration_api_version'
API_NAME = 'orchestration'
API_VERSIONS = {
    '1': 'heatclient.v1.client.Client',
}


def make_client(instance):
    """Returns an orchestration service client"""
    heat_client = utils.get_client_class(
        API_NAME,
        instance._api_version[API_NAME],
        API_VERSIONS)
    LOG.debug('Instantiating orchestration client: %s', heat_client)

    kwargs = {'region_name': instance.region_name,
              'interface': instance.interface}

    if instance.session:
        kwargs.update({'session': instance.session,
                       'service_type': API_NAME})
    elif instance.auth_plugin_name == 'token_endpoint':
        kwargs.update({'endpoint': instance.auth.url,
                       'token': instance.auth.token})
    else:
        endpoint = instance.get_endpoint_for_service_type(
            API_NAME,
            region_name=instance.region_name,
            interface=instance.interface,
        )
        kwargs.update({'endpoint': endpoint,
                       'auth_url': instance.auth.auth_url,
                       'username': instance.auth_ref.username,
                       'token': instance.auth_ref.auth_token})

    client = heat_client(**kwargs)

    return client


def build_option_parser(parser):
    """Hook to add global options"""
    parser.add_argument(
        '--os-orchestration-api-version',
        metavar='<orchestration-api-version>',
        default=utils.env(
            'OS_ORCHESTRATION_API_VERSION',
            default=DEFAULT_ORCHESTRATION_API_VERSION),
        help='Orchestration API version, default=' +
             DEFAULT_ORCHESTRATION_API_VERSION +
             ' (Env: OS_ORCHESTRATION_API_VERSION)')
    return parser
