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

import base64
import logging
import os
import textwrap
import uuid

from oslo_serialization import jsonutils
from oslo_utils import encodeutils
import prettytable
import six
from six.moves.urllib import error
from six.moves.urllib import parse
from six.moves.urllib import request
import yaml

from heatclient._i18n import _
from heatclient import exc

LOG = logging.getLogger(__name__)


supported_formats = {
    "json": lambda x: jsonutils.dumps(x, indent=2),
    "yaml": yaml.safe_dump
}


def arg(*args, **kwargs):
    """Decorator for CLI args.

    Example:

    >>> @arg("name", help="Name of the new entity")
    ... def entity_create(args):
    ...     pass
    """
    def _decorator(func):
        add_arg(func, *args, **kwargs)
        return func
    return _decorator


def env(*args, **kwargs):
    """Returns the first environment variable set.

    If all are empty, defaults to '' or keyword arg `default`.
    """
    for arg in args:
        value = os.environ.get(arg)
        if value:
            return value
    return kwargs.get('default', '')


def add_arg(func, *args, **kwargs):
    """Bind CLI arguments to a shell.py `do_foo` function."""

    if not hasattr(func, 'arguments'):
        func.arguments = []

    # NOTE(sirp): avoid dups that can occur when the module is shared across
    # tests.
    if (args, kwargs) not in func.arguments:
        # Because of the semantics of decorator composition if we just append
        # to the options list positional options will appear to be backwards.
        func.arguments.insert(0, (args, kwargs))


def print_list(objs, fields, formatters=None, sortby_index=0,
               mixed_case_fields=None, field_labels=None):
    """Print a list of objects as a table, one row per object.

    :param objs: iterable of :class:`Resource`
    :param fields: attributes that correspond to columns, in order
    :param formatters: `dict` of callables for field formatting
    :param sortby_index: index of the field for sorting table rows
    :param mixed_case_fields: fields corresponding to object attributes that
        have mixed case names (e.g., 'serverId')
    :param field_labels: Labels to use in the heading of the table, default to
        fields.
    """
    formatters = formatters or {}
    mixed_case_fields = mixed_case_fields or []
    field_labels = field_labels or fields
    if len(field_labels) != len(fields):
        raise ValueError(_("Field labels list %(labels)s has different number "
                           "of elements than fields list %(fields)s"),
                         {'labels': field_labels, 'fields': fields})

    if sortby_index is None:
        kwargs = {}
    else:
        kwargs = {'sortby': field_labels[sortby_index]}
    pt = prettytable.PrettyTable(field_labels)
    pt.align = 'l'

    for o in objs:
        row = []
        for field in fields:
            if field in formatters:
                row.append(formatters[field](o))
            else:
                if field in mixed_case_fields:
                    field_name = field.replace(' ', '_')
                else:
                    field_name = field.lower().replace(' ', '_')
                data = getattr(o, field_name, '')
                row.append(data)
        pt.add_row(row)

    if six.PY3:
        print(encodeutils.safe_encode(pt.get_string(**kwargs)).decode())
    else:
        print(encodeutils.safe_encode(pt.get_string(**kwargs)))


def link_formatter(links):
    def format_link(l):
        if 'rel' in l:
            return "%s (%s)" % (l.get('href', ''), l.get('rel', ''))
        else:
            return "%s" % (l.get('href', ''))
    return '\n'.join(format_link(l) for l in links or [])


def resource_nested_identifier(rsrc):
    nested_link = [l for l in rsrc.links or []
                   if l.get('rel') == 'nested']
    if nested_link:
        nested_href = nested_link[0].get('href')
        nested_identifier = nested_href.split("/")[-2:]
        return "/".join(nested_identifier)


def json_formatter(js):
    return jsonutils.dumps(js, indent=2, ensure_ascii=False,
                           separators=(', ', ': '))


def yaml_formatter(js):
    return yaml.safe_dump(js, default_flow_style=False)


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


class EventLogContext(object):

    def __init__(self):
        # key is a stack id or the name of the nested stack, value is a tuple
        # of the parent stack id, and the name of the resource in the parent
        # stack
        self.id_to_res_info = {}

    def prepend_paths(self, resource_path, stack_id):
        if stack_id not in self.id_to_res_info:
            return
        stack_id, res_name = self.id_to_res_info.get(stack_id)
        if res_name in self.id_to_res_info:
            # do a double lookup to skip the ugly stack name that doesn't
            # correspond to an actual resource name
            n_stack_id, res_name = self.id_to_res_info.get(res_name)
            resource_path.insert(0, res_name)
            self.prepend_paths(resource_path, n_stack_id)
        elif res_name:
            resource_path.insert(0, res_name)

    def build_resource_name(self, event):
        res_name = getattr(event, 'resource_name')

        # Contribute this event to self.id_to_res_info to assist with
        # future calls to build_resource_name

        def get_stack_id():
            if getattr(event, 'stack_id', None) is not None:
                return event.stack_id
            for l in getattr(event, 'links', []):
                if l.get('rel') == 'stack':
                    if 'href' not in l:
                        return None
                    stack_link = l['href']
                    return stack_link.split('/')[-1]

        stack_id = get_stack_id()
        if not stack_id:
            return res_name
        phys_id = getattr(event, 'physical_resource_id', None)
        status = getattr(event, 'resource_status', None)

        is_stack_event = stack_id == phys_id
        if is_stack_event:
            # this is an event for a stack
            self.id_to_res_info[stack_id] = (stack_id, res_name)
        elif phys_id and status == 'CREATE_IN_PROGRESS':
            # this might be an event for a resource which creates a stack
            self.id_to_res_info[phys_id] = (stack_id, res_name)

        # Now build this resource path based on previous calls to
        # build_resource_name
        resource_path = []
        if res_name and not is_stack_event:
            resource_path.append(res_name)
        self.prepend_paths(resource_path, stack_id)

        return '.'.join(resource_path)


def event_log_formatter(events, event_log_context=None):
    """Return the events in log format."""
    event_log = []
    log_format = ("%(event_time)s "
                  "[%(rsrc_name)s]: %(rsrc_status)s  %(rsrc_status_reason)s")

    # It is preferable for a context to be passed in, but there might be enough
    # events in this call to build a better resource name, so create a context
    # anyway
    if event_log_context is None:
        event_log_context = EventLogContext()

    for event in events:
        rsrc_name = event_log_context.build_resource_name(event)

        event_time = getattr(event, 'event_time', '')
        log = log_format % {
            'event_time': event_time.replace('T', ' '),
            'rsrc_name': rsrc_name,
            'rsrc_status': getattr(event, 'resource_status', ''),
            'rsrc_status_reason': getattr(event, 'resource_status_reason', '')
        }
        event_log.append(log)

    return "\n".join(event_log)


def print_update_list(lst, fields, formatters=None):
    """Print the stack-update --dry-run output as a table.

    This function is necessary to print the stack-update --dry-run
    output, which contains additional information about the update.
    """
    formatters = formatters or {}
    pt = prettytable.PrettyTable(fields, caching=False, print_empty=False)
    pt.align = 'l'

    for change in lst:
        row = []
        for field in fields:
            if field in formatters:
                row.append(formatters[field](change.get(field, None)))
            else:
                row.append(change.get(field, None))

        pt.add_row(row)

    if six.PY3:
        print(encodeutils.safe_encode(pt.get_string()).decode())
    else:
        print(encodeutils.safe_encode(pt.get_string()))


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
        msg = (
            _("No %(name)s with a name or ID of "
              "'%(name_or_id)s' exists.")
            % {
                'name': manager.resource_class.__name__.lower(),
                'name_or_id': name_or_id
            })
        raise exc.CommandError(msg)


def format_parameters(params, parse_semicolon=True):
    '''Reformat parameters into dict of format expected by the API.'''

    if not params:
        return {}

    if parse_semicolon:
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


def format_all_parameters(params, param_files,
                          template_file=None, template_url=None):
    parameters = {}
    parameters.update(format_parameters(params))
    parameters.update(format_parameter_file(
        param_files,
        template_file,
        template_url))
    return parameters


def format_parameter_file(param_files, template_file=None,
                          template_url=None):
    '''Reformat file parameters into dict of format expected by the API.'''
    if not param_files:
        return {}
    params = format_parameters(param_files, False)

    template_base_url = None
    if template_file or template_url:
        template_base_url = base_url_for_url(get_template_url(
            template_file, template_url))

    param_file = {}
    for key, value in params.items():
                param_file[key] = resolve_param_get_file(value,
                                                         template_base_url)
    return param_file


def resolve_param_get_file(file, base_url):
    if base_url and not base_url.endswith('/'):
        base_url = base_url + '/'
    str_url = parse.urljoin(base_url, file)
    return read_url_content(str_url)


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


def get_template_url(template_file=None, template_url=None):
    if template_file:
        template_url = normalise_file_path_to_url(template_file)
    return template_url


def read_url_content(url):
    try:
        content = request.urlopen(url).read()
    except error.URLError:
        raise exc.CommandError(_('Could not fetch contents for %s') % url)

    if content:
        try:
            content.decode('utf-8')
        except ValueError:
            content = base64.encodestring(content)
    return content


def base_url_for_url(url):
    parsed = parse.urlparse(url)
    parsed_dir = os.path.dirname(parsed.path)
    return parse.urljoin(url, parsed_dir)


def normalise_file_path_to_url(path):
    if parse.urlparse(path).scheme:
        return path
    path = os.path.abspath(path)
    return parse.urljoin('file:', request.pathname2url(path))


def get_response_body(resp):
    body = resp.content
    if 'application/json' in resp.headers.get('content-type', ''):
        try:
            body = resp.json()
        except ValueError:
            LOG.error('Could not decode response body as JSON')
    else:
        body = None
    return body
