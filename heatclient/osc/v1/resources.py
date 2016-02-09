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
import six

from openstackclient.common import exceptions as exc
from openstackclient.i18n import _

from heatclient.common import format_utils
from heatclient import exc as heat_exc


class ResourceMetadata(format_utils.JsonFormat):
    """Show resource metadata"""

    log = logging.getLogger(__name__ + ".ResourceMetadata")

    def get_parser(self, prog_name):
        parser = super(ResourceMetadata, self).get_parser(prog_name)
        parser.add_argument(
            'stack',
            metavar='<STACK>',
            help=_('Stack to display (name or ID)'),
        )
        parser.add_argument(
            'resource',
            metavar='<RESOURCE>',
            help=_('Name of the resource to show the metadata for'))
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _resource_metadata(heat_client, parsed_args)


def _resource_metadata(heat_client, args):
    fields = {'stack_id': args.stack,
              'resource_name': args.resource}
    try:
        metadata = heat_client.resources.metadata(**fields)
    except heat_exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or resource not found: '
                                 '%(stack)s %(resource)s') %
                               {'stack': args.stack,
                                'resource': args.resource})
    data = list(six.itervalues(metadata))
    columns = list(six.iterkeys(metadata))
    return columns, data
