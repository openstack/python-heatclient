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
import sys

from osc_lib.command import command
from osc_lib import exceptions as exc
from osc_lib.i18n import _
from osc_lib import utils

from heatclient.common import format_utils
from heatclient import exc as heat_exc


class ListSnapshot(command.Lister):
    """List stack snapshots."""

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
        self.log.debug('take_action(%s)', parsed_args)
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
        self.log.debug('take_action(%s)', parsed_args)
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

        rows = list(data.values())
        columns = list(data.keys())
        return columns, rows


class RestoreSnapshot(command.Command):
    """Restore stack snapshot"""

    log = logging.getLogger(__name__ + ".RestoreSnapshot")

    def get_parser(self, prog_name):
        parser = super(RestoreSnapshot, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack containing the snapshot')
        )
        parser.add_argument(
            'snapshot',
            metavar='<snapshot>',
            help=_('ID of the snapshot to restore')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)
        heat_client = self.app.client_manager.orchestration
        return self._restore_snapshot(heat_client, parsed_args)

    def _restore_snapshot(self, heat_client, parsed_args):
        fields = {'stack_id': parsed_args.stack,
                  'snapshot_id': parsed_args.snapshot}
        try:
            heat_client.stacks.restore(**fields)
        except heat_exc.HTTPNotFound:
            raise exc.CommandError(_('Stack %(stack)s or '
                                     'snapshot %(snapshot)s not found.') %
                                   {'stack': parsed_args.stack,
                                    'snapshot': parsed_args.snapshot})


class CreateSnapshot(command.ShowOne):
    """Create stack snapshot."""

    log = logging.getLogger(__name__ + ".CreateSnapshot")

    def get_parser(self, prog_name):
        parser = super(CreateSnapshot, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack')
        )
        parser.add_argument(
            '--name',
            metavar='<name>',
            help=_('Name of snapshot')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)
        heat_client = self.app.client_manager.orchestration

        try:
            data = heat_client.stacks.snapshot(parsed_args.stack,
                                               parsed_args.name)
        except heat_exc.HTTPNotFound:
            raise exc.CommandError(_('Stack not found: %s')
                                   % parsed_args.stack)

        columns = [
            'ID',
            'name',
            'status',
            'status_reason',
            'data',
            'creation_time'
        ]
        return (columns, utils.get_dict_properties(data, columns))


class DeleteSnapshot(command.Command):
    """Delete stack snapshot."""
    log = logging.getLogger(__name__ + ".DeleteSnapshot")

    def get_parser(self, prog_name):
        parser = super(DeleteSnapshot, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help=_('Name or ID of stack')
        )
        parser.add_argument(
            'snapshot',
            metavar='<snapshot>',
            help=_('ID of stack snapshot')
        )
        parser.add_argument(
            '-y', '--yes',
            action='store_true',
            help=_('Skip yes/no prompt (assume yes)')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)
        heat_client = self.app.client_manager.orchestration
        msg = ('User did not confirm snapshot delete '
               '%sso taking no action.')
        try:
            if not parsed_args.yes and sys.stdin.isatty():
                sys.stdout.write(
                    _('Are you sure you want to delete the snapshot of this '
                      'stack [Y/N]?'))
                prompt_response = sys.stdin.readline().lower()
                if not prompt_response.startswith('y'):
                    self.log.info(msg, '')
                    return
        except KeyboardInterrupt:  # ctrl-c
            self.log.info(msg, '(ctrl-c) ')
            return
        except EOFError:  # ctrl-d
            self.log.info(msg, '(ctrl-d) ')
            return

        try:
            heat_client.stacks.snapshot_delete(parsed_args.stack,
                                               parsed_args.snapshot)
        except heat_exc.HTTPNotFound:
            raise exc.CommandError(_('Snapshot ID <%(snapshot_id)s> not found '
                                     'for stack <%(stack_id)s>')
                                   % {'snapshot_id': parsed_args.snapshot,
                                      'stack_id': parsed_args.stack})
