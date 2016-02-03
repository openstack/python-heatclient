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

"""Orchestration v1 Stack Snapshot implementations"""

import logging

from cliff import lister
from openstackclient.common import exceptions as exc
from openstackclient.common import utils

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
