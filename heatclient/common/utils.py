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

import os
import prettytable
import sys
import textwrap
import uuid
import yaml

from heatclient import exc
from heatclient.openstack.common import importutils
from heatclient.openstack.common import jsonutils

supported_formats = {
    "json": lambda x: jsonutils.dumps(x, indent=2),
    "yaml": yaml.safe_dump
}


# Decorator for cli-args
def arg(*args, **kwargs):
    def _decorator(func):
        # Because of the semantics of decorator composition if we just append
        # to the options list positional options will appear to be backwards.
        func.__dict__.setdefault('arguments', []).insert(0, (args, kwargs))
        return func
    return _decorator


def link_formatter(links):
    return '\n'.join([l.get('href', '') for l in links or []])


def json_formatter(js):
    return jsonutils.dumps(js, indent=2)


def text_wrap_formatter(d):
    return '\n'.join(textwrap.wrap(d or '', 55))


def newline_list_formatter(r):
    return '\n'.join(r or [])


def print_list(objs, fields, field_labels=None, formatters={}, sortby=None):
    field_labels = field_labels or fields
    pt = prettytable.PrettyTable([f for f in field_labels],
                                 caching=False, print_empty=False)
    pt.align = 'l'

    for o in objs:
        row = []
        for field in fields:
            if field in formatters:
                row.append(formatters[field](o))
            else:
                data = getattr(o, field, None) or ''
                row.append(data)
        pt.add_row(row)
    if sortby is None:
        print(pt.get_string())
    else:
        print(pt.get_string(sortby=field_labels[sortby]))


def print_dict(d, formatters={}):
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
        msg = "No %s with a name or ID of '%s' exists." % \
              (manager.resource_class.__name__.lower(), name_or_id)
        raise exc.CommandError(msg)


def string_to_bool(arg):
    return arg.strip().lower() in ('t', 'true', 'yes', '1')


def env(*vars, **kwargs):
    """Search for the first defined of possibly many env vars

    Returns the first environment variable defined in vars, or
    returns the default defined in kwargs.
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


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
            msg = '%s(%s). %s.' % ('Malformed parameter', p,
                                   'Use the key=value format')
            raise exc.CommandError(msg)

        parameters[n] = v
    return parameters


def format_output(output, format='yaml'):
    """Format the supplied dict as specified."""
    output_format = format.lower()
    try:
        return supported_formats[output_format](output)
    except KeyError:
        raise exc.HTTPUnsupported("The format(%s) is unsupported."
                                  % output_format)
