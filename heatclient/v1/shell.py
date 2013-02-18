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
import textwrap

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


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           default=60, type=int,
           help='Stack creation timeout in minutes. Default: 60')
@utils.arg('-D', '--disable-rollback', default=False, action="store_true",
           help='Disable rollback on create/update failure')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack.')
@utils.arg('name', metavar='<STACK_NAME>',
           help='Name of the stack to create.')
def do_create(hc, args):
    '''DEPRECATED! Use stack-create instead'''
    do_stack_create(hc, args)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           default=60, type=int,
           help='Stack creation timeout in minutes. Default: 60')
@utils.arg('-D', '--disable-rollback', default=False, action="store_true",
           help='Disable rollback on create/update failure')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack.')
@utils.arg('name', metavar='<STACK_NAME>',
           help='Name of the stack to create.')
def do_stack_create(hc, args):
    '''Create the stack'''
    fields = {'stack_name': args.name,
              'timeout_mins': args.create_timeout,
              'disable_rollback': args.disable_rollback,
              'parameters': utils.format_parameters(args.parameters)}
    _set_template_fields(hc, args, fields)

    hc.stacks.create(**fields)
    do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>', help='Name or ID of stack to delete.')
def do_delete(hc, args):
    '''DEPRECATED! Use stack-delete instead'''
    do_stack_delete(hc, args)


@utils.arg('id', metavar='<NAME or ID>', help='Name or ID of stack to delete.')
def do_stack_delete(hc, args):
    '''Delete the stack'''
    fields = {'stack_id': args.id}
    try:
        hc.stacks.delete(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
    help='Name or ID of stack to describe.')
def do_describe(hc, args):
    '''DEPRECATED! Use stack-show instead'''
    do_stack_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
    help='Name or ID of stack to describe.')
def do_stack_show(hc, args):
    '''Describe the stack'''
    fields = {'stack_id': args.id}
    try:
        stack = hc.stacks.get(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        text_wrap = lambda d: '\n'.join(textwrap.wrap(d, 55))
        link_format = lambda links: '\n'.join([l['href'] for l in links])
        json_format = lambda js: json.dumps(js, indent=2)
        formatters = {
            'description': text_wrap,
            'template_description': text_wrap,
            'stack_status_reason': text_wrap,
            'parameters': json_format,
            'outputs': json_format,
            'links': link_format
        }
        utils.print_dict(stack.to_dict(), formatters=formatters)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack.')
@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to update.')
def do_update(hc, args):
    '''DEPRECATED! Use stack-update instead'''
    do_stack_update(hc, args)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack.')
@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to update.')
def do_stack_update(hc, args):
    '''Update the stack'''
    fields = {'stack_id': args.id,
              'parameters': utils.format_parameters(args.parameters)}
    _set_template_fields(hc, args, fields)

    hc.stacks.update(**fields)
    do_list(hc)


def do_list(hc, args={}):
    '''DEPRECATED! Use stack-list instead'''
    do_stack_list(hc, args)


def do_stack_list(hc, args={}):
    '''List the user's stacks'''
    kwargs = {}
    stacks = hc.stacks.list(**kwargs)
    field_labels = ['ID', 'Name', 'Status', 'Created']
    fields = ['id', 'stack_name', 'stack_status', 'creation_time']
    utils.print_list(stacks, fields, field_labels, sortby=3)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to get the template for.')
def do_gettemplate(hc, args):
    '''DEPRECATED! Use template-show instead'''
    do_template_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to get the template for.')
def do_template_show(hc, args):
    '''Get the template for the specified stack'''
    fields = {'stack_id': args.id}
    try:
        template = hc.stacks.template(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        print json.dumps(template, indent=2)


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values to validate.')
def do_validate(hc, args):
    '''DEPRECATED! Use template-validate instead'''
    do_template_validate(hc, args)


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help='URL to retrieve template object (e.g from swift)')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values to validate.')
def do_template_validate(hc, args):
    '''Validate a template with parameters'''
    fields = {'parameters': utils.format_parameters(args.parameters)}
    _set_template_fields(hc, args, fields)

    validation = hc.stacks.validate(**fields)
    print json.dumps(validation, indent=2)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the resources for.')
def do_resource_list(hc, args):
    '''Show list of resources belonging to a stack'''
    fields = {'stack_id': args.id}
    try:
        resources = hc.resources.list(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        field_labels = ['Name', 'Type',
                        'Status', 'Updated']
        fields = ['logical_resource_id', 'resource_type',
                  'resource_status', 'updated_time']
        utils.print_list(resources, fields, field_labels, sortby=3)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the resource for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource to show the details for.')
def do_resource(hc, args):
    '''DEPRECATED! Use resource-show instead'''
    do_resource_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the resource for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource to show the details for.')
def do_resource_show(hc, args):
    '''Describe the resource'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    try:
        resource = hc.resources.get(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack or resource not found: %s %s' %
            (args.id, args.resource))
    else:
        link_format = lambda links: '\n'.join([l['href'] for l in links])
        json_format = lambda js: json.dumps(js, indent=2)
        formatters = {
            'links': link_format
        }
        utils.print_dict(resource.to_dict(), formatters=formatters)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the resource metadata for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource to show the metadata for.')
def do_resource_metadata(hc, args):
    '''List resource metadata'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    try:
        resource = hc.resources.metadata(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack or resource not found: %s %s' %
            (args.id, args.resource))
    else:
        formatters = {}
        utils.print_dict(resource.to_dict(), formatters=formatters)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the events for.')
@utils.arg('-r', '--resource', metavar='<RESOURCE>',
           help='Name of the resource to filter events by')
def do_event_list(hc, args):
    '''List events for a stack'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    try:
        events = hc.events.list(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        field_labels = ['Resource', 'ID', 'Reason',
                        'Status', 'Event time']
        fields = ['logical_resource_id', 'id', 'resource_status_reason',
                  'resource_status', 'event_time']
        utils.print_list(events, fields, field_labels, sortby=4)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the events for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource the event belongs to.')
@utils.arg('event', metavar='<EVENT>',
           help='ID of event to display details for')
def do_event(hc, args):
    '''DEPRECATED! Use event-show instead'''
    do_event_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help='Name or ID of stack to show the events for.')
@utils.arg('resource', metavar='<RESOURCE>',
           help='Name of the resource the event belongs to.')
@utils.arg('event', metavar='<EVENT>',
           help='ID of event to display details for')
def do_event_show(hc, args):
    '''Describe the event'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource,
              'event_id': args.event}
    try:
        event = hc.events.get(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError('Stack not found: %s' % args.id)
    else:
        link_format = lambda links: '\n'.join([l['href'] for l in links])
        json_format = lambda js: json.dumps(js, indent=2)
        formatters = {
            'links': link_format,
            'resource_properties': json_format
        }
        utils.print_dict(event.to_dict(), formatters=formatters)
