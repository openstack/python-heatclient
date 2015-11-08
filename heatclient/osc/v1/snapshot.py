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

"""Orchestration v1 Stack Snapshot implementations."""

import logging
import six

from cliff import lister
from openstackclient.common import exceptions as exc
from openstackclient.common import utils

from heatclient.common import format_utils
from heatclient import exc as heat_exc
from openstackclient.i18n import _


class ListSnapshot(lister.Lister):
    """List stack snapshots"""

    log = logging.getLogger(__name__ + ".ListSnapshot")

    def get_parser(self, prog_name):
        parser = super(ListSnapshot, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack containing the snapshots')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        heat_client = self.app.client_manager.orchestration
        return self._list_snapshot(heat_client, parsed_args)

    def _list_snapshot(self, heat_client, parsed_args):
        fields = {'stack_id': parsed_args.stack}
        try:
            snapshots = heat_client.stacks.snapshot_list(**fields)
        except heat_exc.HTTPNotFound:
            raise exc.CommandError(_('Stack not found: %s') %
                                   parsed_args.stack)

        columns = ['id', 'name', 'status', 'status_reason', 'creation_time']
        return (
            columns,
            (utils.get_dict_properties(s, columns)
             for s in snapshots['snapshots'])
        )


class ShowSnapshot(format_utils.YamlFormat):
    """Show stack snapshot."""

    log = logging.getLogger(__name__ + ".ShowSnapshot")

    def get_parser(self, prog_name):
        parser = super(ShowSnapshot, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack containing the snapshot')
        )
        parser.add_argument(
            'snapshot',
            metavar='<snapshot>',
            help=_('ID of the snapshot to show')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        heat_client = self.app.client_manager.orchestration
        return self._show_snapshot(heat_client, parsed_args.stack,
                                   parsed_args.snapshot)

    def _show_snapshot(self, heat_client, stack_id, snapshot_id):
        try:
            data = heat_client.stacks.snapshot_show(stack_id, snapshot_id)
        except heat_exc.HTTPNotFound:
            raise exc.CommandError(_('Snapshot ID <%(snapshot_id)s> not found '
                                     'for stack <%(stack_id)s>')
                                   % {'snapshot_id': snapshot_id,
                                      'stack_id': stack_id})

        rows = list(six.itervalues(data))
        columns = list(six.iterkeys(data))
        return columns, rows
