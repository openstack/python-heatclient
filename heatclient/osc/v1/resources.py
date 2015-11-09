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
import six

from cliff import lister
from cliff import show
from openstackclient.common import exceptions as exc
from openstackclient.common import utils
from openstackclient.i18n import _

from heatclient.common import format_utils
from heatclient import exc as heat_exc


class ResourceShow(show.ShowOne):
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
            help=_('Name or ID of resource')
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


class ResourceList(lister.Lister):
    """List stack resources."""

    log = logging.getLogger(__name__ + '.ResourceListStack')

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
            metavar='<DEPTH>',
            type=int,
            help=_('Depth of nested stacks from which to display resources')
        )
        # TODO(jonesbr):
        # Add --filter once https://review.openstack.org/#/c/257864/ is merged
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        fields = {
            'nested_depth': parsed_args.nested_depth,
            'with_detail': parsed_args.long,
        }

        try:
            resources = client.resources.list(parsed_args.stack, **fields)
        except heat_exc.HTTPNotFound:
            msg = _('Stack not found: %s') % parsed_args.stack
            raise exc.CommandError(msg)

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
            metavar='<STACK>',
            help=_('Stack to display (name or ID)'),
        )
        parser.add_argument(
            'resource',
            metavar='<RESOURCE>',
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
        raise exc.CommandError(_('Stack or resource not found: '
                                 '%(stack)s %(resource)s') %
                               {'stack': args.stack,
                                'resource': args.resource})
    data = list(six.itervalues(metadata))
    columns = list(six.iterkeys(metadata))
    return columns, data
