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

"""Orchestration v1 Software Deployment action implementations"""

import logging

from cliff import command
from cliff import lister

from openstackclient.common import exceptions as exc
from openstackclient.common import utils

from heatclient import exc as heat_exc
from heatclient.openstack.common._i18n import _


class DeleteDeployment(command.Command):
    """Delete software deployment(s) and correlative config(s)."""

    log = logging.getLogger(__name__ + '.DeleteDeployment')

    def get_parser(self, prog_name):
        parser = super(DeleteDeployment, self).get_parser(prog_name)
        parser.add_argument(
            'id',
            metavar='<ID>',
            nargs='+',
            help=_('ID of the deployment(s) to delete.')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)
        hc = self.app.client_manager.orchestration
        failure_count = 0

        for deploy_id in parsed_args.id:
            try:
                sd = hc.software_deployments.get(deployment_id=deploy_id)
                hc.software_deployments.delete(
                    deployment_id=deploy_id)
            except Exception as e:
                if isinstance(e, heat_exc.HTTPNotFound):
                    print(_('Deployment with ID %s not found') % deploy_id)
                else:
                    print(_('Deployment with ID %s failed to delete')
                          % deploy_id)
                failure_count += 1
                continue
            # just try best to delete the corresponding config
            try:
                config_id = getattr(sd, 'config_id')
                hc.software_configs.delete(config_id=config_id)
            except Exception:
                print(_('Failed to delete the correlative config'
                        ' %(config_id)s of deployment %(deploy_id)s') %
                      {'config_id': config_id, 'deploy_id': deploy_id})

        if failure_count:
            raise exc.CommandError(_('Unable to delete %(count)s of the '
                                     '%(total)s deployments.') %
                                   {'count': failure_count,
                                   'total': len(parsed_args.id)})


class ListDeployment(lister.Lister):
    """List software deployments."""

    log = logging.getLogger(__name__ + '.ListDeployment')

    def get_parser(self, prog_name):
        parser = super(ListDeployment, self).get_parser(prog_name)
        parser.add_argument(
            '--server',
            metavar='<SERVER>',
            help=_('ID of the server to fetch deployments for')
        )
        parser.add_argument(
            '--long',
            action='store_true',
            help=_('List more fields in output')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _list_deployment(heat_client, args=parsed_args)


def _list_deployment(heat_client, args=None):
    kwargs = {'server_id': args.server} if args.server else {}
    columns = ['id', 'config_id', 'server_id', 'action', 'status']
    if args.long:
        columns.append('creation_time')
        columns.append('status_reason')

    deployments = heat_client.software_deployments.list(**kwargs)
    return (
        columns,
        (utils.get_item_properties(s, columns) for s in deployments)
    )
