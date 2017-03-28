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
import time

from cliff.formatters import base
from osc_lib.command import command
from osc_lib import utils

from heatclient._i18n import _
from heatclient.common import event_utils
from heatclient.common import utils as heat_utils
from heatclient import exc


class ShowEvent(command.ShowOne):
    """Show event details."""

    log = logging.getLogger(__name__ + '.ShowEvent')

    def get_parser(self, prog_name):
        parser = super(ShowEvent, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack to show events for')
        )
        parser.add_argument(
            'resource',
            metavar='<resource>',
            help=_('Name of the resource event belongs to')
        )
        parser.add_argument(
            'event',
            metavar='<event>',
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


class ListEvent(command.Lister):
    """List events."""

    log = logging.getLogger(__name__ + '.ListEvent')

    @property
    def formatter_default(self):
        return 'log'

    @property
    def formatter_namespace(self):
        return 'heatclient.event.formatter.list'

    def get_parser(self, prog_name):
        parser = super(ListEvent, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack to show events for')
        )
        parser.add_argument(
            '--resource',
            metavar='<resource>',
            help=_('Name of resource to show events for. Note: this cannot '
                   'be specified with --nested-depth')
        )
        parser.add_argument(
            '--filter',
            metavar='<key=value>',
            action='append',
            help=_('Filter parameters to apply on returned events')
        )
        parser.add_argument(
            '--limit',
            metavar='<limit>',
            type=int,
            help=_('Limit the number of events returned')
        )
        parser.add_argument(
            '--marker',
            metavar='<id>',
            help=_('Only return events that appear after the given ID')
        )
        parser.add_argument(
            '--nested-depth',
            metavar='<depth>',
            type=int,
            help=_('Depth of nested stacks from which to display events. '
                   'Note: this cannot be specified with --resource')
        )
        parser.add_argument(
            '--sort',
            metavar='<key>[:<direction>]',
            action='append',
            help=_('Sort output by selected keys and directions (asc or desc) '
                   '(default: asc). Specify multiple times to sort on '
                   'multiple keys. Sort key can be: '
                   '"event_time" (default), "resource_name", "links", '
                   '"logical_resource_id", "resource_status", '
                   '"resource_status_reason", "physical_resource_id", or '
                   '"id". You can leave the key empty and specify ":desc" '
                   'for sorting by reverse time.')
        )
        parser.add_argument(
            '--follow',
            action='store_true',
            help=_('Print events until process is halted')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        columns = ['id', 'resource_status', 'resource_status_reason',
                   'event_time', 'physical_resource_id']

        kwargs = {
            'resource_name': parsed_args.resource,
            'filters': heat_utils.format_parameters(parsed_args.filter),
            'sort_dir': 'asc'
        }

        if parsed_args.resource and parsed_args.nested_depth:
            msg = _('--nested-depth cannot be specified with --resource')
            raise exc.CommandError(msg)

        if parsed_args.nested_depth:
            columns.append('stack_name')
            nested_depth = parsed_args.nested_depth
        else:
            nested_depth = 0

        if parsed_args.sort:
            sorts = []
            sort_keys = []
            for sort in parsed_args.sort:
                if sort.startswith(":"):
                    sorts.append(":".join(["event_time", sort.lstrip(":")]))
                else:
                    sorts.append(sort)
                    sort_keys.append(sort.split(":")[0])
            kwargs['sort_keys'] = sort_keys

            if ":" in parsed_args.sort[0]:
                kwargs['sort_dir'] = parsed_args.sort[0].split(":")[1]

        if parsed_args.follow:
            if parsed_args.formatter != 'log':
                msg = _('--follow can only be specified with --format log')
                raise exc.CommandError(msg)

            marker = parsed_args.marker
            try:
                event_log_context = heat_utils.EventLogContext()
                while True:
                    events = event_utils.get_events(
                        client,
                        stack_id=parsed_args.stack,
                        event_args=kwargs,
                        nested_depth=nested_depth,
                        marker=marker)
                    if events:
                        marker = getattr(events[-1], 'id', None)
                        events_log = heat_utils.event_log_formatter(
                            events, event_log_context)
                        self.app.stdout.write(events_log)
                        self.app.stdout.write('\n')
                    time.sleep(5)
                    # this loop never exits
            except (KeyboardInterrupt, EOFError):  # ctrl-c, ctrl-d
                return [], []

        events = event_utils.get_events(
            client, stack_id=parsed_args.stack, event_args=kwargs,
            nested_depth=nested_depth, marker=parsed_args.marker,
            limit=parsed_args.limit)

        if parsed_args.sort:
            events = utils.sort_items(events, ','.join(sorts))

        if parsed_args.formatter == 'log':
            return [], events

        if len(events):
            if hasattr(events[0], 'resource_name'):
                columns.insert(0, 'resource_name')
                columns.append('logical_resource_id')
            else:
                columns.insert(0, 'logical_resource_id')

        return (
            columns,
            (utils.get_item_properties(s, columns) for s in events)
        )


class LogFormatter(base.ListFormatter):
    """A formatter which prints event objects in a log style"""

    def add_argument_group(self, parser):
        pass

    def emit_list(self, column_names, data, stdout, parsed_args):
        stdout.write(heat_utils.event_log_formatter(data))
        stdout.write('\n')
