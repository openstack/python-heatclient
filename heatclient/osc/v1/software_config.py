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

"""Orchestration v1 software config action implementations"""

import logging

from cliff import command
from openstackclient.common import exceptions as exc

from heatclient import exc as heat_exc
from heatclient.openstack.common._i18n import _


class DeleteConfig(command.Command):
    """Delete software configs"""

    log = logging.getLogger(__name__ + ".DeleteConfig")

    def get_parser(self, prog_name):
        parser = super(DeleteConfig, self).get_parser(prog_name)
        parser.add_argument(
            'id',
            metavar='<ID>',
            nargs='+',
            help=_('IDs of the software configs to delete')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _delete_config(heat_client, parsed_args)


def _delete_config(heat_client, args):
    failure_count = 0

    for config_id in args.id:
        try:
            heat_client.software_configs.delete(
                config_id=config_id)
        except Exception as e:
            if isinstance(e, heat_exc.HTTPNotFound):
                print(_('Software config with ID %s not found') % config_id)
            failure_count += 1
            continue

    if failure_count:
        raise exc.CommandError(_('Unable to delete %(count)s of the '
                                 '%(total)s software configs.') %
                               {'count': failure_count,
                                'total': len(args.id)})
