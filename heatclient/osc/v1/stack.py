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

from cliff import lister
from cliff import show
from openstackclient.common import exceptions as exc
from openstackclient.common import parseractions
from openstackclient.common import utils

from heatclient.common import utils as heat_utils
from heatclient import exc as heat_exc
from heatclient.openstack.common._i18n import _


class ShowStack(show.ShowOne):
    """Show stack details"""

    log = logging.getLogger(__name__ + ".ShowStack")

    def get_parser(self, prog_name):
        parser = super(ShowStack, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<stack>',
            help='Stack to display (name or ID)',
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _show_stack(heat_client, stack_id=parsed_args.stack,
                           format=parsed_args.formatter)


def _show_stack(heat_client, stack_id, format):
    try:
        data = heat_client.stacks.get(stack_id=stack_id)
    except heat_exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % stack_id)
    else:

        columns = [
            'id',
            'stack_name',
            'description',
            'creation_time',
            'updated_time',
            'stack_status',
            'stack_status_reason',
            'parameters',
            'outputs',
            'links',
        ]
        exclude_columns = ('template_description',)
        for key in data.to_dict():
            # add remaining columns without an explicit order
            if key not in columns and key not in exclude_columns:
                columns.append(key)
        formatters = {}
        complex_formatter = None
        if format in 'table':
            complex_formatter = heat_utils.yaml_formatter
        elif format in ('shell', 'value', 'html'):
            complex_formatter = heat_utils.json_formatter
        if complex_formatter:
            formatters['parameters'] = complex_formatter
            formatters['outputs'] = complex_formatter
            formatters['links'] = complex_formatter

        return columns, utils.get_item_properties(data, columns,
                                                  formatters=formatters)


class ListStack(lister.Lister):
    """List stacks."""

    log = logging.getLogger(__name__ + '.ListStack')

    def get_parser(self, prog_name):
        parser = super(ListStack, self).get_parser(prog_name)
        parser.add_argument(
            '--deleted',
            action='store_true',
            help=_('Include soft-deleted stacks in the stack listing')
        )
        parser.add_argument(
            '--nested',
            action='store_true',
            help=_('Include nested stacks in the stack listing')
        )
        parser.add_argument(
            '--hidden',
            action='store_true',
            help=_('Include hidden stacks in the stack listing')
        )
        parser.add_argument(
            '--property',
            dest='properties',
            metavar='<KEY=VALUE>',
            help=_('Filter properties to apply on returned stacks (repeat to '
                   'filter on multiple properties)'),
            action=parseractions.KeyValueAction
        )
        parser.add_argument(
            '--tags',
            metavar='<TAG1,TAG2...>',
            help=_('List of tags to filter by. Can be combined with '
                   '--tag-mode to specify how to filter tags')
        )
        parser.add_argument(
            '--tag-mode',
            metavar='<MODE>',
            help=_('Method of filtering tags. Must be one of "any", "not", '
                   'or "not-any". If not specified, multiple tags will be '
                   'combined with the boolean AND expression')
        )
        parser.add_argument(
            '--limit',
            metavar='<LIMIT>',
            help=_('The number of stacks returned')
        )
        parser.add_argument(
            '--marker',
            metavar='<ID>',
            help=_('Only return stacks that appear after the given ID')
        )
        parser.add_argument(
            '--sort',
            metavar='<KEY>[:<DIRECTION>]',
            help=_('Sort output by selected keys and directions (asc or desc) '
                   '(default: asc). Specify multiple times to sort on '
                   'multiple properties')
        )
        parser.add_argument(
            '--all-projects',
            action='store_true',
            help=_('Include all projects (admin only)')
        )
        parser.add_argument(
            '--short',
            action='store_true',
            help=_('List fewer fields in output')
        )
        parser.add_argument(
            '--long',
            action='store_true',
            help=_('List additional fields in output, this is implied by '
                   '--all-projects')
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        client = self.app.client_manager.orchestration
        return _list(client, args=parsed_args)


def _list(client, args=None):
    kwargs = {}
    columns = [
        'ID',
        'Stack Name',
        'Stack Status',
        'Creation Time',
        'Updated Time',
    ]

    if args:
        kwargs = {'limit': args.limit,
                  'marker': args.marker,
                  'filters': heat_utils.format_parameters(args.properties),
                  'tags': None,
                  'tags_any': None,
                  'not_tags': None,
                  'not_tags_any': None,
                  'global_tenant': args.all_projects or args.long,
                  'show_deleted': args.deleted,
                  'show_hidden': args.hidden}

        if args.tags:
            if args.tag_mode:
                if args.tag_mode == 'any':
                    kwargs['tags_any'] = args.tags
                elif args.tag_mode == 'not':
                    kwargs['not_tags'] = args.tags
                elif args.tag_mode == 'not-any':
                    kwargs['not_tags_any'] = args.tags
                else:
                    err = _('tag mode must be one of "any", "not", "not-any"')
                    raise exc.CommandError(err)
            else:
                kwargs['tags'] = args.tags

        if args.short:
            columns.pop()
            columns.pop()
        if args.long:
            columns.insert(2, 'Stack Owner')
        if args.long or args.all_projects:
            columns.insert(2, 'Project')

        if args.nested:
            columns.append('Parent')
            kwargs['show_nested'] = True

    data = client.stacks.list(**kwargs)
    data = utils.sort_items(data, args.sort if args else None)

    return (
        columns,
        (utils.get_dict_properties(s, columns) for s in data)
    )
