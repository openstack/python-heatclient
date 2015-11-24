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
#   Copyright 2015 IBM Corp.

import logging

from cliff import lister
from openstackclient.common import utils

from heatclient import exc
from heatclient.openstack.common._i18n import _


class VersionList(lister.Lister):
    """List the available template versions."""

    log = logging.getLogger(__name__ + '.VersionList')

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        versions = client.template_versions.list()
        fields = ['version', 'type']

        return (
            fields,
            (utils.get_item_properties(s, fields) for s in versions)
        )


class FunctionList(lister.Lister):
    """List the available functions."""

    log = logging.getLogger(__name__ + '.FunctionList')

    def get_parser(self, prog_name):
        parser = super(FunctionList, self).get_parser(prog_name)
        parser.add_argument(
            'template_version',
            metavar='<TEMPLATE_VERSION>',
            help=_('Template version to get the functions for')
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        version = parsed_args.template_version
        try:
            functions = client.template_versions.get(version)
        except exc.HTTPNotFound:
            msg = _('Template version not found: %s') % version
            raise exc.CommandError(msg)

        fields = ['functions', 'description']
        return (
            fields,
            (utils.get_item_properties(s, fields) for s in functions)
        )
