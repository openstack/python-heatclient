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

from cliff import show
from openstackclient.common import exceptions as exc
from openstackclient.common import utils

from heatclient.common import utils as heat_utils
from heatclient import exc as heat_exc


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
