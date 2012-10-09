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

import argparse
import copy
import os
import sys

from heatclient.common import utils


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           default=60, type=int,
           help='Stack creation timeout in minutes. Default: 60')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack.')
@utils.arg('name', metavar='<STACK_NAME>',
           help='Name of the stack to create.')
def do_create(hc, args):
    '''Create the stack'''
    # Filter out None values
    fields = dict(filter(lambda x: x[1] is not None, vars(args).items()))
    print fields
    stack = hc.stacks.create(**fields)
    utils.print_dict(stack)


@utils.arg('id', metavar='<STACK_ID>', help='ID of stack to delete.')
def do_delete(hc, args):
    '''Delete the stack'''
    pass


@utils.arg('id', metavar='<STACK_ID>', help='ID of stack to describe.')
def do_describe(hc, args):
    '''Describe the stack'''
    pass


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help='Parameter values used to create the stack.')
def do_update(hc, args):
    '''Update the stack'''
    pass


def do_list(hc, args):
    '''List the user's stacks'''
    kwargs = {}
    stacks = hc.stacks.list(**kwargs)
    columns = ['ID', 'Name', 'Status']
    utils.print_list(stacks, columns)


@utils.arg('id', metavar='<STACK_ID>',
           help='ID of stack to get the template for.')
def do_gettemplate(hc, args):
    '''Get the template'''
    pass


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
def do_estimate_template_cost(hc, args):
    '''Returns the estimated monthly cost of a template'''
    pass


@utils.arg('-u', '--template-url', metavar='<URL>',
           help='URL of template.')
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help='Path to the template.')
def do_validate(hc, args):
    '''Validate a template'''
    pass


@utils.arg('id', metavar='<STACK_ID>',
           help='ID of stack to show the events for.')
def do_event_list(hc, args):
    '''List events for a stack'''
    pass


@utils.arg('-r', '--resource', metavar='<RESOURCE_ID>',
           help='ID of the resource to show the details for.')
@utils.arg('id', metavar='<STACK_ID>',
           help='ID of stack to show the resource for.')
def do_resource(hc, args):
    '''Describe the resource'''
    pass


@utils.arg('id', metavar='<STACK_ID>',
           help='ID of stack to show the resources for.')
def do_resource_list(hc, args):
    '''Show list of resources belonging to a stack'''
    pass


@utils.arg('id', metavar='<STACK_ID>',
           help='ID of stack to show the resource details for.')
def do_resource_list_details(hc, args):
    '''Detailed view of resources belonging to a stack'''
    pass
