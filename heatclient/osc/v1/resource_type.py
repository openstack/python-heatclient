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

"""Orchestration v1 resource type implementations"""

import logging
import six

from cliff import lister
from heatclient.common import format_utils
from heatclient.common import utils as heat_utils
from heatclient import exc as heat_exc
from openstackclient.common import exceptions as exc
from openstackclient.i18n import _


class ResourceTypeShow(format_utils.YamlFormat):
    """Show details and optionally generate a template for a resource type."""

    log = logging.getLogger(__name__ + ".ResourceTypeShow")

    def get_parser(self, prog_name):
        parser = super(ResourceTypeShow,
                       self).get_parser(prog_name)
        parser.add_argument(
            'resource_type',
            metavar='<RESOURCE_TYPE>',
            help=_('Resource type to show details for'),
        )
        parser.add_argument(
            '--template-type',
            metavar='<TEMPLATE_TYPE>',
            help=_('Optional template type to generate, hot or cfn')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _show_resourcetype(heat_client, parsed_args)


def _show_resourcetype(heat_client, parsed_args):
    try:
        if parsed_args.template_type:
            template_type = parsed_args.template_type.lower()
            if template_type not in ('hot', 'cfn'):
                raise exc.CommandError(
                    _('Template type invalid: %s') % parsed_args.template_type)

            fields = {'resource_type': parsed_args.resource_type,
                      'template_type': template_type}
            data = heat_client.resource_types.generate_template(**fields)
        else:
            data = heat_client.resource_types.get(parsed_args.resource_type)
    except heat_exc.HTTPNotFound:
        raise exc.CommandError(
            _('Resource type not found: %s') % parsed_args.resource_type)

    rows = list(six.itervalues(data))
    columns = list(six.iterkeys(data))
    return columns, rows


class ResourceTypeList(lister.Lister):
    """List resource types."""

    log = logging.getLogger(__name__ + '.ResourceTypeList')

    def get_parser(self, prog_name):
        parser = super(ResourceTypeList,
                       self).get_parser(prog_name)
        parser.add_argument(
            '--filter',
            dest='filter',
            metavar='<KEY=VALUE>',
            help=_('Filter parameters to apply on returned resource types. '
                   'This can be specified multiple times. It can be any of '
                   'name, version or support_status'),
            action='append'
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _list_resourcetypes(heat_client, parsed_args)


def _list_resourcetypes(heat_client, parsed_args):
    resource_types = heat_client.resource_types.list(
        filters=heat_utils.format_parameters(parsed_args.filter))
    columns = ['Resource Type']
    rows = sorted([r.resource_type] for r in resource_types)
    return (columns, rows)
