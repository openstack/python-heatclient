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

from osc_lib.command import command
from osc_lib import exceptions as exc
from osc_lib import utils
from oslo_serialization import jsonutils

from heatclient._i18n import _
from heatclient.common import deployment_utils
from heatclient.common import format_utils
from heatclient.common import utils as heat_utils
from heatclient import exc as heat_exc


class CreateDeployment(format_utils.YamlFormat):
    """Create a software deployment."""

    log = logging.getLogger(__name__ + '.CreateDeployment')

    def get_parser(self, prog_name):
        parser = super(CreateDeployment, self).get_parser(prog_name)
        parser.add_argument(
            'name',
            metavar='<deployment-name>',
            help=_('Name of the derived config associated with this '
                   'deployment. This is used to apply a sort order to the '
                   'list of configurations currently deployed to the server.')
        )
        parser.add_argument(
            '--input-value',
            metavar='<key=value>',
            action='append',
            help=_('Input value to set on the deployment. This can be '
                   'specified multiple times.')
        )
        parser.add_argument(
            '--action',
            metavar='<action>',
            default='UPDATE',
            help=_('Name of an action for this deployment. This can be a '
                   'custom action, or one of CREATE, UPDATE, DELETE, SUSPEND, '
                   'RESUME. Default is UPDATE')
        )
        parser.add_argument(
            '--config',
            metavar='<config>',
            help=_('ID of the configuration to deploy')
        )
        parser.add_argument(
            '--signal-transport',
            metavar='<signal-transport>',
            default='TEMP_URL_SIGNAL',
            help=_('How the server should signal to heat with the deployment '
                   'output values. TEMP_URL_SIGNAL will create a Swift '
                   'TempURL to be signaled via HTTP PUT. ZAQAR_SIGNAL will '
                   'create a dedicated zaqar queue to be signaled using the '
                   'provided keystone credentials.NO_SIGNAL will result in '
                   'the resource going to the COMPLETE state without waiting '
                   'for any signal')
        )
        parser.add_argument(
            '--container',
            metavar='<container>',
            help=_('Optional name of container to store TEMP_URL_SIGNAL '
                   'objects in. If not specified a container will be created '
                   'with a name derived from the DEPLOY_NAME')
        )
        parser.add_argument(
            '--timeout',
            metavar='<timeout>',
            type=int,
            default=60,
            help=_('Deployment timeout in minutes')
        )
        parser.add_argument(
            '--server',
            metavar='<server>',
            required=True,
            help=_('ID of the server being deployed to')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        config = {}
        if parsed_args.config:
            try:
                config = client.software_configs.get(parsed_args.config)
            except heat_exc.HTTPNotFound:
                msg = (_('Software configuration not found: %s') %
                       parsed_args.config)
                raise exc.CommandError(msg)

        derived_params = deployment_utils.build_derived_config_params(
            parsed_args.action,
            config,
            parsed_args.name,
            heat_utils.format_parameters(parsed_args.input_value, False),
            parsed_args.server,
            parsed_args.signal_transport,
            signal_id=deployment_utils.build_signal_id(client, parsed_args)
        )
        derived_config = client.software_configs.create(**derived_params)

        sd = client.software_deployments.create(
            config_id=derived_config.id,
            server_id=parsed_args.server,
            action=parsed_args.action,
            status='IN_PROGRESS'
        )

        return zip(*sorted(sd.to_dict().items()))


class DeleteDeployment(command.Command):
    """Delete software deployment(s) and correlative config(s)."""

    log = logging.getLogger(__name__ + '.DeleteDeployment')

    def get_parser(self, prog_name):
        parser = super(DeleteDeployment, self).get_parser(prog_name)
        parser.add_argument(
            'deployment',
            metavar='<deployment>',
            nargs='+',
            help=_('ID of the deployment(s) to delete.')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)
        hc = self.app.client_manager.orchestration
        failure_count = 0

        for deploy_id in parsed_args.deployment:
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
                                   'total': len(parsed_args.deployment)})


class ListDeployment(command.Lister):
    """List software deployments."""

    log = logging.getLogger(__name__ + '.ListDeployment')

    def get_parser(self, prog_name):
        parser = super(ListDeployment, self).get_parser(prog_name)
        parser.add_argument(
            '--server',
            metavar='<server>',
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


class ShowDeployment(command.ShowOne):
    """Show SoftwareDeployment Details."""

    log = logging.getLogger(__name__ + ".ShowSoftwareDeployment")

    def get_parser(self, prog_name):
        parser = super(ShowDeployment, self).get_parser(prog_name)
        parser.add_argument(
            'deployment',
            metavar='<deployment>',
            help=_('ID of the deployment')
        )
        parser.add_argument(
            '--long',
            action='store_true',
            help=_('Show more fields in output')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        try:
            data = heat_client.software_deployments.get(
                deployment_id=parsed_args.deployment)
        except heat_exc.HTTPNotFound:
            raise exc.CommandError(
                _('Software Deployment not found: %s')
                % parsed_args.deployment)
        else:
            columns = [
                'id',
                'server_id',
                'config_id',
                'creation_time',
                'updated_time',
                'status',
                'status_reason',
                'input_values',
                'action',
            ]
            if parsed_args.long:
                columns.append('output_values')
            return columns, utils.get_item_properties(data, columns)


class ShowMetadataDeployment(command.Command):
    """Get deployment configuration metadata for the specified server."""

    log = logging.getLogger(__name__ + '.ShowMetadataDeployment')

    def get_parser(self, prog_name):
        parser = super(ShowMetadataDeployment, self).get_parser(prog_name)
        parser.add_argument(
            'server',
            metavar='<server>',
            help=_('ID of the server to fetch deployments for')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)
        heat_client = self.app.client_manager.orchestration
        md = heat_client.software_deployments.metadata(
            server_id=parsed_args.server)
        print(jsonutils.dumps(md, indent=2))


class ShowOutputDeployment(command.Command):
    """Show a specific deployment output."""

    log = logging.getLogger(__name__ + '.ShowOutputDeployment')

    def get_parser(self, prog_name):
        parser = super(ShowOutputDeployment, self).get_parser(prog_name)
        parser.add_argument(
            'deployment',
            metavar='<deployment>',
            help=_('ID of deployment to show the output for')
        )
        parser.add_argument(
            'output',
            metavar='<output-name>',
            nargs='?',
            default=None,
            help=_('Name of an output to display')
        )
        parser.add_argument(
            '--all',
            default=False,
            action='store_true',
            help=_('Display all deployment outputs')
        )
        parser.add_argument(
            '--long',
            action='store_true',
            default=False,
            help='Show full deployment logs in output',
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        if (not parsed_args.all and parsed_args.output is None or
                parsed_args.all and parsed_args.output is not None):
            raise exc.CommandError(
                _('Error: either %(output)s or %(all)s argument is needed.')
                % {'output': '<output-name>', 'all': '--all'})
        try:
            sd = heat_client.software_deployments.get(
                deployment_id=parsed_args.deployment)
        except heat_exc.HTTPNotFound:
            raise exc.CommandError(_('Deployment not found: %s')
                                   % parsed_args.deployment)
        outputs = sd.output_values
        if outputs:
            if parsed_args.all:
                print('output_values:\n')
                for k in outputs.keys():
                    format_utils.print_software_deployment_output(
                        data=outputs, name=k, long=parsed_args.long)
            else:
                if parsed_args.output not in outputs:
                    msg = (_('Output %(output)s does not exist in deployment'
                             ' %(deployment)s')
                           % {'output': parsed_args.output,
                              'deployment': parsed_args.deployment})
                    raise exc.CommandError(msg)
                else:
                    print('output_value:\n')
                    format_utils.print_software_deployment_output(
                        data=outputs, name=parsed_args.output)
