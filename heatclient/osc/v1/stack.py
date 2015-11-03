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

from heatclient.common import http
from heatclient.common import template_utils
from heatclient.common import utils as heat_utils
from heatclient import exc as heat_exc
from heatclient.openstack.common._i18n import _


def _authenticated_fetcher(client):
    def _do(*args, **kwargs):
        if isinstance(client.http_client, http.SessionClient):
            method, url = args
            return client.http_client.request(url, method, **kwargs).content
        else:
            return client.http_client.raw_request(*args, **kwargs).content

    return _do


class CreateStack(show.ShowOne):
    """Create a stack."""

    log = logging.getLogger(__name__ + '.CreateStack')

    def get_parser(self, prog_name):
        parser = super(CreateStack, self).get_parser(prog_name)
        parser.add_argument(
            '-t', '--template',
            metavar='<FILE or URL>',
            required=True,
            help=_('Path to the template')
        )
        parser.add_argument(
            '-e', '--environment',
            metavar='<FILE or URL>',
            action='append',
            help=_('Path to the environment. Can be specified multiple times')
        )
        parser.add_argument(
            '--timeout',
            metavar='<TIMEOUT>',
            type=int,
            help=_('Stack creating timeout in minutes')
        )
        parser.add_argument(
            '--pre-create',
            metavar='<RESOURCE>',
            default=None,
            action='append',
            help=_('Name of a resource to set a pre-create hook to. Resources '
                   'in nested stacks can be set using slash as a separator: '
                   'nested_stack/another/my_resource. You can use wildcards '
                   'to match multiple stacks or resources: '
                   'nested_stack/an*/*_resource. This can be specified '
                   'multiple times')
        )
        parser.add_argument(
            '--enable-rollback',
            action='store_true',
            help=_('Enable rollback on create/update failure')
        )
        parser.add_argument(
            '--parameter',
            metavar='<KEY=VALUE>',
            action='append',
            help=_('Parameter values used to create the stack. This can be '
                   'specified multiple times')
        )
        parser.add_argument(
            '--parameter-file',
            metavar='<KEY=FILE>',
            action='append',
            help=_('Parameter values from file used to create the stack. '
                   'This can be specified multiple times. Parameter values '
                   'would be the content of the file')
        )
        parser.add_argument(
            '--wait',
            action='store_true',
            help=_('Wait until stack completes')
        )
        parser.add_argument(
            '--tags',
            metavar='<TAG1,TAG2...>',
            help=_('A list of tags to associate with the stack')
        )
        parser.add_argument(
            'name',
            metavar='<STACK_NAME>',
            help=_('Name of the stack to create')
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        tpl_files, template = template_utils.process_template_path(
            parsed_args.template,
            object_request=_authenticated_fetcher(client))

        env_files, env = (
            template_utils.process_multiple_environments_and_files(
                env_paths=parsed_args.environment))

        parameters = heat_utils.format_all_parameters(
            parsed_args.parameter,
            parsed_args.parameter_file,
            parsed_args.template)

        if parsed_args.pre_create:
            template_utils.hooks_to_env(env, parsed_args.pre_create,
                                        'pre-create')

        fields = {
            'stack_name': parsed_args.name,
            'disable_rollback': not parsed_args.enable_rollback,
            'parameters': parameters,
            'template': template,
            'files': dict(list(tpl_files.items()) + list(env_files.items())),
            'environment': env
        }

        if parsed_args.tags:
            fields['tags'] = parsed_args.tags
        if parsed_args.timeout:
            fields['timeout_mins'] = parsed_args.timeout

        stack = client.stacks.create(**fields)['stack']
        if parsed_args.wait:
            if not utils.wait_for_status(client.stacks.get, parsed_args.name,
                                         status_field='stack_status',
                                         success_status='create_complete',
                                         error_status='create_failed'):

                msg = _('Stack %s failed to create.') % parsed_args.name
                raise exc.CommandError(msg)

        return _show_stack(client, stack['id'], format='table', short=True)


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


def _show_stack(heat_client, stack_id, format='', short=False):
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
        ]

        if not short:
            columns += [
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
        (utils.get_item_properties(s, columns) for s in data)
    )
