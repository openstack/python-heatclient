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
#   Copyright 2015 IBM Corp.

import logging

from cliff import show
from openstackclient.common import utils

from heatclient.common import utils as heat_utils
from heatclient import exc
from heatclient.openstack.common._i18n import _


class ShowEvent(show.ShowOne):
    """Show event details."""

    log = logging.getLogger(__name__ + '.ShowEvent')

    def get_parser(self, prog_name):
        parser = super(ShowEvent, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<NAME or ID>',
            help=_('Name or ID of stack to show events for')
        )
        parser.add_argument(
            'resource',
            metavar='<RESOURCE>',
            help=_('Name of the resource event belongs to')
        )
        parser.add_argument(
            'event',
            metavar='<EVENT>',
            help=_('ID of event to display details for')
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        fields = {
            'stack_id': parsed_args.stack,
            'resource_name': parsed_args.resource,
            'event_id': parsed_args.event
        }

        try:
            client.stacks.get(parsed_args.stack)
            client.resources.get(parsed_args.stack, parsed_args.resource)
            event = client.events.get(**fields)
        except exc.HTTPNotFound as ex:
            raise exc.CommandError(str(ex))

        formatters = {
            'links': heat_utils.link_formatter,
            'resource_properties': heat_utils.json_formatter
        }

        columns = []
        for key in event.to_dict():
            columns.append(key)

        return columns, utils.get_item_properties(event, columns,
                                                  formatters=formatters)
