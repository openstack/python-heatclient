# Copyright 2012 OpenStack LLC.
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

import json
import urllib2
import yaml

from heatclient.common import utils
import heatclient.exc as exc


def _set_template_fields(hc, args, fields):
    if args.template_file:
        tpl = open(args.template_file).read()
        if tpl.startswith('{'):
            fields['template'] = json.loads(tpl)
        else:
            fields['template'] = tpl
    elif args.template_url:
        fields['template_url'] = args.template_url
    elif args.template_object:
        template_body = hc.raw_request('GET', args.template_object)
        if template_body:
            fields['template'] = json.loads(template_body)
        else:
            raise exc.CommandError('Could not fetch template from %s'
                                   % args.template_object)
    else:
        raise exc.CommandError('Need to specify exactly one of '
                               '--template-file, --template-url '
                               'or --template-object')


def _get_file_contents(resource_registry, fields, base_url=''):
    base_url = resource_registry.get('base_url', base_url)
    for key, value in iter(resource_registry.items()):
        if key == 'base_url':
            continue

        if isinstance(value, dict):
            _get_file_contents(value, fields, base_url)
            continue

        facade = key
        provider = value
        if '::' in provider:
            # Built in providers like: "X::Compute::Server"
            # don't need downloading.
            continue

        str_url = base_url + provider
        name = str_url[len(base_url):]
        try:
            fields['files'][name] = urllib2.urlopen(str_url).read()
        except urllib2.URLError:
            raise exc.CommandError('Could not fetch %s from the environment'
                                   % str_url)
        resource_registry[facade] = name


def _process_environment_and_files(hc, args, fields):
    """go through the env/resource_registry
    look for base_url, urls and file
    get them all and put them in the files section
    modify the environment to just include the relative path as a name
    """
    if not args.environment_file:
        return

    raw_env = open(args.environment_file).read()
    env = yaml.safe_load(raw_env)
    fields['environment'] = env
    fields['files'] = {}

    rr = env.get('resource_registry')
    if rr:
        _get_file_contents(rr, fields)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE>',
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
           help='Parameter values used to create the stack.')
@utils.arg('name', metavar='<STACK_NAME>',
           help='Name of the stack to create.')
def do_create(hc, args):
    '''DEPRECATED! Use stack-create instead.'''
    do_stack_create(hc, args)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE>',
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
           help='Parameter values used to create the stack.')
@utils.arg('name', metavar='<STACK_NAME>',
           help='Name of the stack to create.')
def do_stack_create(hc, args):
    '''Create the stack.'''
    fields = {'stack_name': args.name,
              'timeout_mins': args.create_timeout,
              'disable_rollback': not(args.enable_rollback),
              'parameters': utils.format_parameters(args.parameters)}
    _set_template_fields(hc, args, fields)
    _process_environment_and_files(hc, args, fields)

    hc.stacks.create(**fields)
    do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>', help='Name or ID of stack to delete.')
def do_delete(hc, args):
    '''DEPRECATED! Use stack-delete instead.'''
    do_stack_delete(hc, args)


@utils.arg('id', metavar='<NAME or ID>', help='Name or ID of stack to delete.')
def do_stack_delete(hc, args):
    '''Delete the stack.'''
    fields = {'stack_id': args.id}
    try:
        hc.stacks.delete(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        do_stack_list(hc)


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
@utils.arg('-e', '--environment-file', metavar='<FILE>',
           help='Path to the environment.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack.')
@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to update.')
def do_update(hc, args):
    '''DEPRECATED! Use stack-update instead.'''
    do_stack_update(hc, args)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE>',
           help='Path to the environment.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack.')
@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to update.')
def do_stack_update(hc, args):
    '''Update the stack.'''
    fields = {'stack_id': args.id,
              'parameters': utils.format_parameters(args.parameters)}
    _set_template_fields(hc, args, fields)
    _process_environment_and_files(hc, args, fields)

    hc.stacks.update(**fields)
    do_list(hc)


def do_list(hc, args={}):
    '''DEPRECATED! Use stack-list instead.'''
    do_stack_list(hc, args)


def do_stack_list(hc, args={}):
    '''List the user's stacks.'''
    kwargs = {}
    stacks = hc.stacks.list(**kwargs)
    fields = ['id', 'stack_name', 'stack_status', 'creation_time']
    utils.print_list(stacks, fields, sortby=3)


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
            print yaml.safe_dump(template, indent=2)
        else:
            print json.dumps(template, indent=2)


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE>',
           help='Path to the environment.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values to validate.')
def do_validate(hc, args):
    '''DEPRECATED! Use template-validate instead.'''
    do_template_validate(hc, args)


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-e', '--environment-file', metavar='<FILE>',
           help='Path to the environment.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values to validate.')
def do_template_validate(hc, args):
    '''Validate a template with parameters.'''
    fields = {'parameters': utils.format_parameters(args.parameters)}
    _set_template_fields(hc, args, fields)
    _process_environment_and_files(hc, args, fields)

    validation = hc.stacks.validate(**fields)
    print json.dumps(validation, indent=2)


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
        fields = ['logical_resource_id', 'resource_type',
                  'resource_status', 'updated_time']
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
           help="The template output format. %s" % utils.supported_formats)
def do_resource_template(hc, args):
    '''Generate a template based on a resource.'''
    fields = {'resource_name': args.resource}
    try:
        template = hc.resources.generate_template(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Resource %s not found.' % args.resource)
    else:
        if args.format:
            print utils.format_output(template, format=args.format)
        else:
            print utils.format_output(template)


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
        print json.dumps(metadata, indent=2)


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
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        fields = ['logical_resource_id', 'id', 'resource_status_reason',
                  'resource_status', 'event_time']
        utils.print_list(events, fields, sortby=4)


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
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        formatters = {
            'links': utils.link_formatter,
            'resource_properties': utils.json_formatter
        }
        utils.print_dict(event.to_dict(), formatters=formatters)
