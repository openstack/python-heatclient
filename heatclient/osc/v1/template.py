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

from osc_lib.command import command
from osc_lib import utils
import six

from heatclient._i18n import _
from heatclient.common import format_utils
from heatclient.common import http
from heatclient.common import template_utils
from heatclient.common import utils as heat_utils
from heatclient import exc


class VersionList(command.Lister):
    """List the available template versions."""

    log = logging.getLogger(__name__ + '.VersionList')

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        versions = client.template_versions.list()
        try:
            versions[1].aliases

            def format_alias(aliases):
                return ','.join(aliases)

            fields = ['Version', 'Type', 'Aliases']
            formatters = {'Aliases': format_alias}
        except AttributeError:
            fields = ['Version', 'Type']
            formatters = None

        items = (utils.get_item_properties(s, fields,
                                           formatters=formatters)
                 for s in versions)

        return (fields, items)


class FunctionList(command.Lister):
    """List the available functions."""

    log = logging.getLogger(__name__ + '.FunctionList')

    def get_parser(self, prog_name):
        parser = super(FunctionList, self).get_parser(prog_name)
        parser.add_argument(
            'template_version',
            metavar='<template-version>',
            help=_('Template version to get the functions for')
        )
        parser.add_argument(
            '--with_conditions',
            default=False,
            action='store_true',
            help=_('Show condition functions for template.')
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)', parsed_args)

        client = self.app.client_manager.orchestration

        version = parsed_args.template_version
        try:
            functions = client.template_versions.get(
                version, with_condition_func=parsed_args.with_conditions)
        except exc.HTTPNotFound:
            msg = _('Template version not found: %s') % version
            raise exc.CommandError(msg)

        fields = ['Functions', 'Description']
        return (
            fields,
            (utils.get_item_properties(s, fields) for s in functions)
        )


class Validate(format_utils.YamlFormat):
    """Validate a template"""

    log = logging.getLogger(__name__ + ".Validate")

    def get_parser(self, prog_name):
        parser = super(Validate, self).get_parser(prog_name)
        parser.add_argument(
            '-e', '--environment',
            metavar='<environment>',
            action='append',
            help=_('Path to the environment. Can be specified multiple times')
        )
        parser.add_argument(
            '--show-nested',
            action='store_true',
            help=_('Resolve parameters from nested templates as well')
        )
        parser.add_argument(
            '--parameter',
            metavar='<key=value>',
            action='append',
            help=_('Parameter values used to create the stack. This can be '
                   'specified multiple times')
        )
        parser.add_argument(
            '--ignore-errors',
            metavar='<error1,error2,...>',
            help=_('List of heat errors to ignore')
        )
        parser.add_argument(
            '-t', '--template',
            metavar='<template>',
            required=True,
            help=_('Path to the template')
        )
        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action(%s)", parsed_args)

        heat_client = self.app.client_manager.orchestration
        return _validate(heat_client, parsed_args)


def _validate(heat_client, args):
    tpl_files, template = template_utils.process_template_path(
        args.template,
        object_request=http.authenticated_fetcher(heat_client))

    env_files_list = []
    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment, env_list_tracker=env_files_list)

    fields = {
        'template': template,
        'parameters': heat_utils.format_parameters(args.parameter),
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env,
    }

    if args.ignore_errors:
        fields['ignore_errors'] = args.ignore_errors

    # If one or more environments is found, pass the listing to the server
    if env_files_list:
        fields['environment_files'] = env_files_list

    if args.show_nested:
        fields['show_nested'] = args.show_nested

    validation = heat_client.stacks.validate(**fields)
    data = list(six.itervalues(validation))
    columns = list(six.iterkeys(validation))
    return columns, data
