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

from osc_lib.command import command
from osc_lib import exceptions as exc
from osc_lib.i18n import _
import six

from heatclient.common import format_utils
from heatclient.common import utils as heat_utils
from heatclient import exc as heat_exc


class ResourceTypeShow(format_utils.YamlFormat):
    """Show details and optionally generate a template for a resource type."""

    log = logging.getLogger(__name__ + ".ResourceTypeShow")

    def get_parser(self, prog_name):
        parser = super(ResourceTypeShow,
                       self).get_parser(prog_name)
        parser.add_argument(
            'resource_type',
            metavar='<resource-type>',
            help=_('Resource type to show details for'),
        )
        parser.add_argument(
            '--template-type',
            metavar='<template-type>',
            help=_('Optional template type to generate, hot or cfn')
        )
        parser.add_argument(
            '--long',
            default=False,
            action='store_true',
            help=_('Show resource type with corresponding description.')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        if parsed_args.template_type is not None and parsed_args.long:
            msg = _('Cannot use --template-type and --long in one time.')
            raise exc.CommandError(msg)

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
            data = heat_client.resource_types.get(parsed_args.resource_type,
                                                  parsed_args.long)
    except heat_exc.HTTPNotFound:
        raise exc.CommandError(
            _('Resource type not found: %s') % parsed_args.resource_type)

    rows = list(six.itervalues(data))
    columns = list(six.iterkeys(data))
    return columns, rows


class ResourceTypeList(command.Lister):
    """List resource types."""

    log = logging.getLogger(__name__ + '.ResourceTypeList')

    def get_parser(self, prog_name):
        parser = super(ResourceTypeList,
                       self).get_parser(prog_name)
        parser.add_argument(
            '--filter',
            dest='filter',
            metavar='<key=value>',
            help=_('Filter parameters to apply on returned resource types. '
                   'This can be specified multiple times. It can be any of '
                   'name, version or support_status'),
            action='append'
        )
        parser.add_argument(
            '--long',
            default=False,
            action='store_true',
            help=_('Show resource types with corresponding description of '
                   'each resource type.')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _list_resourcetypes(heat_client, parsed_args)


def _list_resourcetypes(heat_client, parsed_args):
    resource_types = heat_client.resource_types.list(
        filters=heat_utils.format_parameters(parsed_args.filter),
        with_description=parsed_args.long
    )
    if parsed_args.long:
        columns = ['Resource Type', 'Description']
        rows = sorted([r.resource_type, r.description] for r in resource_types)
    else:
        columns = ['Resource Type']
        rows = sorted([r.resource_type] for r in resource_types)
    return columns, rows
