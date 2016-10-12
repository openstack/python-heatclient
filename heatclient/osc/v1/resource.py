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

"""Orchestration v1 Stack action implementations"""

import logging

from osc_lib.command import command
from osc_lib import exceptions as exc
from osc_lib.i18n import _
from osc_lib import utils
from oslo_serialization import jsonutils
import six
from six.moves.urllib import request

from heatclient.common import format_utils
from heatclient.common import utils as heat_utils
from heatclient import exc as heat_exc


class ResourceShow(command.ShowOne):
    """Display stack resource."""

    log = logging.getLogger(__name__ + '.ResourceShowStack')

    def get_parser(self, prog_name):
        parser = super(ResourceShow, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack to query')
        )
        parser.add_argument(
            'resource',
            metavar='<resource>',
            help=_('Name of resource')
        )
        parser.add_argument(
            '--with-attr',
            metavar='<attribute>',
            action='append',
            help=_('Attribute to show, can be specified multiple times')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        try:
            resource = client.resources.get(parsed_args.stack,
                                            parsed_args.resource,
                                            with_attr=parsed_args.with_attr)
        except heat_exc.HTTPNotFound:
            msg = (_('Stack or resource not found: %(stack)s %(resource)s') %
                   {'stack': parsed_args.stack,
                    'resource': parsed_args.resource})
            raise exc.CommandError(msg)

        return self.dict2columns(resource.to_dict())


class ResourceList(command.Lister):
    """List stack resources."""

    log = logging.getLogger(__name__ + '.ResourceListStack')

    @property
    def formatter_namespace(self):
        return 'heatclient.resource.formatter.list'

    def get_parser(self, prog_name):
        parser = super(ResourceList, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack to query')
        )
        parser.add_argument(
            '--long',
            action='store_true',
            help=_('Enable detailed information presented for each resource '
                   'in resource list')
        )
        parser.add_argument(
            '-n', '--nested-depth',
            metavar='<nested-depth>',
            type=int,
            help=_('Depth of nested stacks from which to display resources')
        )

        parser.add_argument(
            '--filter',
            metavar='<key=value>',
            action='append',
            help=_('Filter parameters to apply on returned resources based on '
                   'their name, status, type, action, id and '
                   'physical_resource_id')
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        fields = {
            'nested_depth': parsed_args.nested_depth,
            'with_detail': parsed_args.long,
            'filters': heat_utils.format_parameters(parsed_args.filter),
        }

        try:
            resources = client.resources.list(parsed_args.stack, **fields)
        except heat_exc.HTTPNotFound:
            msg = _('Stack not found: %s') % parsed_args.stack
            raise exc.CommandError(msg)

        if parsed_args.formatter == 'dot':
            return [], resources

        columns = ['physical_resource_id', 'resource_type', 'resource_status',
                   'updated_time']

        if len(resources) >= 1 and not hasattr(resources[0], 'resource_name'):
            columns.insert(0, 'logical_resource_id')
        else:
            columns.insert(0, 'resource_name')

        if parsed_args.nested_depth or parsed_args.long:
            columns.append('stack_name')

        return (
            columns,
            (utils.get_item_properties(r, columns) for r in resources)
        )


class ResourceMetadata(format_utils.JsonFormat):
    """Show resource metadata"""

    log = logging.getLogger(__name__ + ".ResourceMetadata")

    def get_parser(self, prog_name):
        parser = super(ResourceMetadata, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Stack to display (name or ID)'),
        )
        parser.add_argument(
            'resource',
            metavar='<resource>',
            help=_('Name of the resource to show the metadata for'))
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _resource_metadata(heat_client, parsed_args)


def _resource_metadata(heat_client, args):
    fields = {'stack_id': args.stack,
              'resource_name': args.resource}
    try:
        metadata = heat_client.resources.metadata(**fields)
    except heat_exc.HTTPNotFound:
        raise exc.CommandError(_('Stack %(stack)s or resource %(resource)s '
                                 'not found.') %
                               {'stack': args.stack,
                                'resource': args.resource})

    data = list(six.itervalues(metadata))
    columns = list(six.iterkeys(metadata))
    return columns, data


class ResourceSignal(command.Command):
    """Signal a resource with optional data."""

    log = logging.getLogger(__name__ + ".ResourceSignal")

    def get_parser(self, prog_name):
        parser = super(ResourceSignal, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack the resource belongs to'),
        )
        parser.add_argument(
            'resource',
            metavar='<resource>',
            help=_('Name of the resoure to signal'),
        )
        parser.add_argument(
            '--data',
            metavar='<data>',
            help=_('JSON Data to send to the signal handler')
        )
        parser.add_argument(
            '--data-file',
            metavar='<data-file>',
            help=_('File containing JSON data to send to the signal handler')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _resource_signal(heat_client, parsed_args)


def _resource_signal(heat_client, args):
    fields = {'stack_id': args.stack,
              'resource_name': args.resource}
    data = args.data
    data_file = args.data_file
    if data and data_file:
        raise exc.CommandError(_('Should only specify one of data or '
                                 'data-file'))

    if data_file:
        data_url = heat_utils.normalise_file_path_to_url(data_file)
        data = request.urlopen(data_url).read()

    if data:
        try:
            data = jsonutils.loads(data)
        except ValueError as ex:
            raise exc.CommandError(_('Data should be in JSON format: %s') % ex)
        if not isinstance(data, dict):
            raise exc.CommandError(_('Data should be a JSON dict'))

        fields['data'] = data
    try:
        heat_client.resources.signal(**fields)
    except heat_exc.HTTPNotFound:
        raise exc.CommandError(_('Stack %(stack)s or resource %(resource)s '
                                 'not found.') %
                               {'stack': args.stack,
                                'resource': args.resource})


class ResourceMarkUnhealthy(command.Command):
    """Set resource's health."""

    log = logging.getLogger(__name__ + ".ResourceMarkUnhealthy")

    def get_parser(self, prog_name):
        parser = super(ResourceMarkUnhealthy, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack the resource belongs to')
        )
        parser.add_argument(
            'resource',
            metavar='<resource>',
            help=_('Name of the resource')
        )
        parser.add_argument(
            'reason',
            default="",
            nargs='?',
            help=_('Reason for state change')
        )
        parser.add_argument(
            '--reset',
            default=False,
            action="store_true",
            help=_('Set the resource as healthy')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        fields = {'stack_id': parsed_args.stack,
                  'resource_name': parsed_args.resource,
                  'mark_unhealthy': not parsed_args.reset,
                  'resource_status_reason': parsed_args.reason}
        try:
            heat_client.resources.mark_unhealthy(**fields)
        except heat_exc.HTTPNotFound:
            raise exc.CommandError(_('Stack or resource not found: '
                                     '%(id)s %(resource)s') %
                                   {'id': parsed_args.stack,
                                    'resource': parsed_args.resource})
