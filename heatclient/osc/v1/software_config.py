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

from osc_lib.command import command
from osc_lib import exceptions as exc
from osc_lib import utils
import six
from six.moves.urllib import request
import yaml

from heatclient._i18n import _
from heatclient.common import format_utils
from heatclient.common import template_format
from heatclient.common import utils as heat_utils
from heatclient import exc as heat_exc


class DeleteConfig(command.Command):
    """Delete software configs"""

    log = logging.getLogger(__name__ + ".DeleteConfig")

    def get_parser(self, prog_name):
        parser = super(DeleteConfig, self).get_parser(prog_name)
        parser.add_argument(
            'config',
            metavar='<config>',
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

    for config_id in args.config:
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
                                'total': len(args.config)})


class ListConfig(command.Lister):
    """List software configs"""

    log = logging.getLogger(__name__ + ".ListConfig")

    def get_parser(self, prog_name):
        parser = super(ListConfig, self).get_parser(prog_name)
        parser.add_argument(
            '--limit',
            metavar='<limit>',
            help=_('Limit the number of configs returned')
        )
        parser.add_argument(
            '--marker',
            metavar='<id>',
            help=_('Return configs that appear after the given config ID')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)
        heat_client = self.app.client_manager.orchestration
        return _list_config(heat_client, parsed_args)


def _list_config(heat_client, args):
    kwargs = {}
    if args.limit:
        kwargs['limit'] = args.limit
    if args.marker:
        kwargs['marker'] = args.marker
    scs = heat_client.software_configs.list(**kwargs)

    columns = ['id', 'name', 'group', 'creation_time']
    return (columns, (utils.get_item_properties(s, columns) for s in scs))


class CreateConfig(format_utils.JsonFormat):
    """Create software config"""

    log = logging.getLogger(__name__ + ".CreateConfig")

    def get_parser(self, prog_name):
        parser = super(CreateConfig, self).get_parser(prog_name)
        parser.add_argument(
            'name',
            metavar='<config-name>',
            help=_('Name of the software config to create')
        )
        parser.add_argument(
            '--config-file',
            metavar='<config-file>',
            help=_('Path to JSON/YAML containing map defining '
                   '<inputs>, <outputs>, and <options>')
        )
        parser.add_argument(
            '--definition-file',
            metavar='<destination-file>',
            help=_('Path to software config script/data')
        )
        parser.add_argument(
            '--group',
            metavar='<group>',
            default='Heat::Ungrouped',
            help=_('Group name of tool expected by the software config')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)
        heat_client = self.app.client_manager.orchestration
        return _create_config(heat_client, parsed_args)


def _create_config(heat_client, args):
    config = {
        'group': args.group,
        'config': ''
    }

    defn = {}
    if args.definition_file:
        defn_url = heat_utils.normalise_file_path_to_url(
            args.definition_file)
        defn_raw = request.urlopen(defn_url).read() or '{}'
        defn = yaml.load(defn_raw, Loader=template_format.yaml_loader)

    config['inputs'] = defn.get('inputs', [])
    config['outputs'] = defn.get('outputs', [])
    config['options'] = defn.get('options', {})

    if args.config_file:
        config_url = heat_utils.normalise_file_path_to_url(
            args.config_file)
        config['config'] = request.urlopen(config_url).read()

    # build a mini-template with a config resource and validate it
    validate_template = {
        'heat_template_version': '2013-05-23',
        'resources': {
            args.name: {
                'type': 'OS::Heat::SoftwareConfig',
                'properties': config
            }
        }
    }
    heat_client.stacks.validate(template=validate_template)

    config['name'] = args.name
    sc = heat_client.software_configs.create(**config).to_dict()
    rows = list(six.itervalues(sc))
    columns = list(six.iterkeys(sc))
    return columns, rows


class ShowConfig(format_utils.YamlFormat):
    """Show software config details"""

    log = logging.getLogger(__name__ + ".ShowConfig")

    def get_parser(self, prog_name):
        parser = super(ShowConfig, self).get_parser(prog_name)
        parser.add_argument(
            'config',
            metavar='<config>',
            help=_('ID of the config')
        )
        parser.add_argument(
            '--config-only',
            default=False,
            action="store_true",
            help=_('Only display the value of the <config> property.')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)
        heat_client = self.app.client_manager.orchestration
        return _show_config(heat_client, config_id=parsed_args.config,
                            config_only=parsed_args.config_only)


def _show_config(heat_client, config_id, config_only):
    try:
        sc = heat_client.software_configs.get(config_id=config_id)
    except heat_exc.HTTPNotFound:
        raise exc.CommandError(_('Configuration not found: %s') % config_id)

    columns = None
    rows = None

    if config_only:
        print(sc.config)
    else:
        columns = (
            'id',
            'name',
            'group',
            'config',
            'inputs',
            'outputs',
            'options',
            'creation_time',
        )
        rows = utils.get_dict_properties(sc.to_dict(), columns)

    return columns, rows
