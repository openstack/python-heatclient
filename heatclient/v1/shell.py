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

import yaml

from heatclient.common import template_utils
from heatclient.common import utils
from heatclient.openstack.common import jsonutils
from heatclient.openstack.common.py3kcompat import urlutils

import heatclient.exc as exc


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help='Path to the environment.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           default=60, type=int,
           help='Stack creation timeout in minutes. Default: 60')
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help='Enable rollback on create/update failure')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.',
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help='Name of the stack to create.')
def do_create(hc, args):
    '''DEPRECATED! Use stack-create instead.'''
    do_stack_create(hc, args)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help='Path to the environment.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           default=60, type=int,
           help='Stack creation timeout in minutes. Default: 60')
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help='Enable rollback on create/update failure')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.',
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help='Name of the stack to create.')
def do_stack_create(hc, args):
    '''Create the stack.'''
    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        hc.http_client.raw_request)
    env_files, env = template_utils.process_environment_and_files(
        env_path=args.environment_file)

    fields = {
        'stack_name': args.name,
        'timeout_mins': args.create_timeout,
        'disable_rollback': not(args.enable_rollback),
        'parameters': utils.format_parameters(args.parameters),
        'template': template,
        'files': dict(tpl_files.items() + env_files.items()),
        'environment': env
    }

    hc.stacks.create(**fields)
    do_stack_list(hc)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help='Path to the environment.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           default=60, type=int,
           help='Stack creation timeout in minutes. Default: 60')
@utils.arg('-a', '--adopt-file', metavar='<FILE or URL>',
           help='Path to adopt stack data file.')
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help='Enable rollback on create/update failure')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.',
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help='Name of the stack to adopt.')
def do_stack_adopt(hc, args):
    '''Adopt a stack.'''
    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        hc.http_client.raw_request)
    env_files, env = template_utils.process_environment_and_files(
        env_path=args.environment_file)

    if not args.adopt_file:
        raise exc.CommandError('Need to specify --adopt-file')

    adopt_url = template_utils.normalise_file_path_to_url(args.adopt_file)
    adopt_data = urlutils.urlopen(adopt_url).read()

    fields = {
        'stack_name': args.name,
        'timeout_mins': args.create_timeout,
        'disable_rollback': not(args.enable_rollback),
        'adopt_stack_data': adopt_data,
        'parameters': utils.format_parameters(args.parameters),
        'template': template,
        'files': dict(tpl_files.items() + env_files.items()),
        'environment': env
    }

    hc.stacks.create(**fields)
    do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>', nargs='+',
           help='Name or ID of stack(s) to delete.')
def do_delete(hc, args):
    '''DEPRECATED! Use stack-delete instead.'''
    do_stack_delete(hc, args)


@utils.arg('id', metavar='<NAME or ID>', nargs='+',
           help='Name or ID of stack(s) to delete.')
def do_stack_delete(hc, args):
    '''Delete the stack(s).'''
    failure_count = 0

    for sid in args.id:
        fields = {'stack_id': sid}
        try:
            hc.stacks.delete(**fields)
        except exc.HTTPNotFound as e:
            failure_count += 1
            print(e)
    if failure_count == len(args.id):
        raise exc.CommandError("Unable to delete any of the specified "
                               "stacks.")
    do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to abandon.')
def do_stack_abandon(hc, args):
    '''Abandon the stack.'''
    fields = {'stack_id': args.id}
    try:
        stack = hc.stacks.abandon(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        print(jsonutils.dumps(stack, indent=2))


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to suspend.')
def do_action_suspend(hc, args):
    '''Suspend the stack.'''
    fields = {'stack_id': args.id}
    try:
        hc.actions.suspend(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>', help='Name or ID of stack to resume.')
def do_action_resume(hc, args):
    '''Resume the stack.'''
    fields = {'stack_id': args.id}
    try:
        hc.actions.resume(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to describe.')
def do_describe(hc, args):
    '''DEPRECATED! Use stack-show instead.'''
    do_stack_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to describe.')
def do_stack_show(hc, args):
    '''Describe the stack.'''
    fields = {'stack_id': args.id}
    try:
        stack = hc.stacks.get(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        formatters = {
            'description': utils.text_wrap_formatter,
            'template_description': utils.text_wrap_formatter,
            'stack_status_reason': utils.text_wrap_formatter,
            'parameters': utils.json_formatter,
            'outputs': utils.json_formatter,
            'links': utils.link_formatter
        }
        utils.print_dict(stack.to_dict(), formatters=formatters)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help='Path to the environment.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.',
           action='append')
@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to update.')
def do_update(hc, args):
    '''DEPRECATED! Use stack-update instead.'''
    do_stack_update(hc, args)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help='Path to the environment.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.',
           action='append')
@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to update.')
def do_stack_update(hc, args):
    '''Update the stack.'''

    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        hc.http_client.raw_request)

    env_files, env = template_utils.process_environment_and_files(
        env_path=args.environment_file)

    fields = {
        'stack_id': args.id,
        'parameters': utils.format_parameters(args.parameters),
        'template': template,
        'files': dict(tpl_files.items() + env_files.items()),
        'environment': env
    }

    hc.stacks.update(**fields)
    do_stack_list(hc)


def do_list(hc):
    '''DEPRECATED! Use stack-list instead.'''
    do_stack_list(hc)


@utils.arg('-f', '--filters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Filter parameters to apply on returned stacks. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.',
           action='append')
@utils.arg('-l', '--limit', metavar='<LIMIT>',
           help='Limit the number of stacks returned')
@utils.arg('-m', '--marker', metavar='<ID>',
           help='Only return stacks that appear after the given stack ID')
def do_stack_list(hc, args=None):
    '''List the user's stacks.'''
    kwargs = {}
    if args:
        kwargs = {'limit': args.limit,
                  'marker': args.marker,
                  'filters': utils.format_parameters(args.filters)}

    stacks = hc.stacks.list(**kwargs)
    fields = ['id', 'stack_name', 'stack_status', 'creation_time']
    utils.print_list(stacks, fields, sortby=3)


def do_resource_type_list(hc, args={}):
    '''List the available resource types.'''
    kwargs = {}
    types = hc.resource_types.list(**kwargs)
    utils.print_list(types, ['resource_type'], sortby=0)


@utils.arg('resource_type', metavar='<RESOURCE_TYPE>',
           help='Resource Type to get the details for.')
def do_resource_type_show(hc, args={}):
    '''Show the resource type.'''
    try:
        resource_type = hc.resource_types.get(args.resource_type)
    except exc.HTTPNotFound:
        raise exc.CommandError(
            'Resource Type not found: %s' % args.resource_type)
    else:
        print(jsonutils.dumps(resource_type, indent=2))


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to get the template for.')
def do_gettemplate(hc, args):
    '''DEPRECATED! Use template-show instead.'''
    do_template_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to get the template for.')
def do_template_show(hc, args):
    '''Get the template for the specified stack.'''
    fields = {'stack_id': args.id}
    try:
        template = hc.stacks.template(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        if 'heat_template_version' in template:
            print(yaml.safe_dump(template, indent=2))
        else:
            print(jsonutils.dumps(template, indent=2))


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help='Path to the environment.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values to validate. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.',
           action='append')
def do_validate(hc, args):
    '''DEPRECATED! Use template-validate instead.'''
    do_template_validate(hc, args)


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help='Path to the environment.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values to validate. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.',
           action='append')
def do_template_validate(hc, args):
    '''Validate a template with parameters.'''

    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        hc.http_client.raw_request)

    env_files, env = template_utils.process_environment_and_files(
        env_path=args.environment_file)
    fields = {
        'parameters': utils.format_parameters(args.parameters),
        'template': template,
        'files': dict(tpl_files.items() + env_files.items()),
        'environment': env
    }

    validation = hc.stacks.validate(**fields)
    print(jsonutils.dumps(validation, indent=2))


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the resources for.')
def do_resource_list(hc, args):
    '''Show list of resources belonging to a stack.'''
    fields = {'stack_id': args.id}
    try:
        resources = hc.resources.list(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        fields = ['resource_type', 'resource_status', 'updated_time']
        if len(resources) >= 1:
            if hasattr(resources[0], 'resource_name'):
                fields.insert(0, 'resource_name')
            else:
                fields.insert(0, 'logical_resource_id')

        utils.print_list(resources, fields, sortby=3)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the resource for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource to show the details for.')
def do_resource(hc, args):
    '''DEPRECATED! Use resource-show instead.'''
    do_resource_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the resource for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource to show the details for.')
def do_resource_show(hc, args):
    '''Describe the resource.'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    try:
        resource = hc.resources.get(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack or resource not found: %s %s' %
                               (args.id, args.resource))
    else:
        formatters = {
            'links': utils.link_formatter,
            'required_by': utils.newline_list_formatter
        }
        utils.print_dict(resource.to_dict(), formatters=formatters)


@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource to generate a template for.')
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help="The template output format, one of: %s"
                % ', '.join(utils.supported_formats.keys()))
def do_resource_template(hc, args):
    '''Generate a template based on a resource.'''
    fields = {'resource_name': args.resource}
    try:
        template = hc.resources.generate_template(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Resource %s not found.' % args.resource)
    else:
        if args.format:
            print(utils.format_output(template, format=args.format))
        else:
            print(utils.format_output(template))


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the resource metadata for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource to show the metadata for.')
def do_resource_metadata(hc, args):
    '''List resource metadata.'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    try:
        metadata = hc.resources.metadata(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack or resource not found: %s %s' %
                               (args.id, args.resource))
    else:
        print(jsonutils.dumps(metadata, indent=2))


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the events for.')
@utils.arg('-r', '--resource', metavar='<RESOURCE>',
           help='Name of the resource to filter events by')
def do_event_list(hc, args):
    '''List events for a stack.'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    try:
        events = hc.events.list(**fields)
    except exc.HTTPNotFound as ex:
        # it could be the stack or resource that is not found
        # just use the message that the server sent us.
        raise exc.CommandError(str(ex))
    else:
        fields = ['id', 'resource_status_reason',
                  'resource_status', 'event_time']
        if len(events) >= 1:
            if hasattr(events[0], 'resource_name'):
                fields.insert(0, 'resource_name')
            else:
                fields.insert(0, 'logical_resource_id')
        utils.print_list(events, fields)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the events for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource the event belongs to.')
@utils.arg('event', metavar='<EVENT>',
           help='ID of event to display details for')
def do_event(hc, args):
    '''DEPRECATED! Use event-show instead.'''
    do_event_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the events for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource the event belongs to.')
@utils.arg('event', metavar='<EVENT>',
           help='ID of event to display details for')
def do_event_show(hc, args):
    '''Describe the event.'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource,
              'event_id': args.event}
    try:
        event = hc.events.get(**fields)
    except exc.HTTPNotFound as ex:
        # it could be the stack/resource/or event that is not found
        # just use the message that the server sent us.
        raise exc.CommandError(str(ex))
    else:
        formatters = {
            'links': utils.link_formatter,
            'resource_properties': utils.json_formatter
        }
        utils.print_dict(event.to_dict(), formatters=formatters)


def do_build_info(hc, args):
    '''Retrieve build information.'''
    result = hc.build_info.build_info()
    formatters = {
        'api': utils.json_formatter,
        'engine': utils.json_formatter,
    }
    utils.print_dict(result, formatters=formatters)
