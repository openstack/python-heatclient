# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import print_function

import prettytable
from six.moves.urllib import parse
import sys
import textwrap
import uuid
import yaml

from oslo.serialization import jsonutils
from oslo.utils import importutils

from heatclient import exc
from heatclient.openstack.common._i18n import _
from heatclient.openstack.common import cliutils

supported_formats = {
    "json": lambda x: jsonutils.dumps(x, indent=2),
    "yaml": yaml.safe_dump
}

# Using common methods from oslo cliutils
arg = cliutils.arg
env = cliutils.env
print_list = cliutils.print_list


def link_formatter(links):
    def format_link(l):
        if 'rel' in l:
            return "%s (%s)" % (l.get('href', ''), l.get('rel', ''))
        else:
            return "%s" % (l.get('href', ''))
    return '\n'.join(format_link(l) for l in links or [])


def json_formatter(js):
    return jsonutils.dumps(js, indent=2, ensure_ascii=False,
                           separators=(', ', ': '))


def text_wrap_formatter(d):
    return '\n'.join(textwrap.wrap(d or '', 55))


def newline_list_formatter(r):
    return '\n'.join(r or [])


def print_dict(d, formatters=None):
    formatters = formatters or {}
    pt = prettytable.PrettyTable(['Property', 'Value'],
                                 caching=False, print_empty=False)
    pt.align = 'l'

    for field in d.keys():
        if field in formatters:
            pt.add_row([field, formatters[field](d[field])])
        else:
            pt.add_row([field, d[field]])
    print(pt.get_string(sortby='Property'))


def find_resource(manager, name_or_id):
    """Helper for the _find_* methods."""
    # first try to get entity as integer id
    try:
        if isinstance(name_or_id, int) or name_or_id.isdigit():
            return manager.get(int(name_or_id))
    except exc.NotFound:
        pass

    # now try to get entity as uuid
    try:
        uuid.UUID(str(name_or_id))
        return manager.get(name_or_id)
    except (ValueError, exc.NotFound):
        pass

    # finally try to find entity by name
    try:
        return manager.find(name=name_or_id)
    except exc.NotFound:
        msg = _("No %(name)s with a name or ID of "
                "'%(name_or_id)s' exists.") % \
            {
                'name': manager.resource_class.__name__.lower(),
                'name_or_id': name_or_id
            }
        raise exc.CommandError(msg)


def import_versioned_module(version, submodule=None):
    module = 'heatclient.v%s' % version
    if submodule:
        module = '.'.join((module, submodule))
    return importutils.import_module(module)


def exit(msg=''):
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(1)


def format_parameters(params):
    '''Reformat parameters into dict of format expected by the API.'''

    if not params:
        return {}

    # expect multiple invocations of --parameters but fall back
    # to ; delimited if only one --parameters is specified
    if len(params) == 1:
        params = params[0].split(';')

    parameters = {}
    for p in params:
        try:
            (n, v) = p.split(('='), 1)
        except ValueError:
            msg = _('Malformed parameter(%s). Use the key=value format.') % p
            raise exc.CommandError(msg)

        if n not in parameters:
            parameters[n] = v
        else:
            if not isinstance(parameters[n], list):
                parameters[n] = [parameters[n]]
            parameters[n].append(v)

    return parameters


def format_output(output, format='yaml'):
    """Format the supplied dict as specified."""
    output_format = format.lower()
    try:
        return supported_formats[output_format](output)
    except KeyError:
        raise exc.HTTPUnsupported(_("The format(%s) is unsupported.")
                                  % output_format)


def parse_query_url(url):
    base_url, query_params = url.split('?')
    return base_url, parse.parse_qs(query_params)
