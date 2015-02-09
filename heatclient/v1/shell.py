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

import logging
import six
from six.moves.urllib import request
import yaml

from oslo.serialization import jsonutils
from oslo.utils import strutils

from heatclient.common import template_format
from heatclient.common import template_utils
from heatclient.common import utils

from heatclient.openstack.common._i18n import _
from heatclient.openstack.common._i18n import _LW

import heatclient.exc as exc

logger = logging.getLogger(__name__)


def _authenticated_fetcher(hc):
    """A wrapper around the heat client object to fetch a template.
    """
    def _do(*args, **kwargs):
        return hc.http_client.raw_request(*args, **kwargs).content

    return _do


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help=_('URL of template.'))
@utils.arg('-o', '--template-object', metavar='<URL>',
           help=_('URL to retrieve template object (e.g. from swift).'))
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes.'
           ' DEPRECATED use %(arg)s instead.')
           % {'arg': '--timeout'})
@utils.arg('-t', '--timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('Enable rollback on create/update failure.'))
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by a semicolon.'),
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help=_('Name of the stack to create.'))
def do_create(hc, args):
    '''DEPRECATED! Use stack-create instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'stack-create'})
    do_stack_create(hc, args)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help=_('URL of template.'))
@utils.arg('-o', '--template-object', metavar='<URL>',
           help=_('URL to retrieve template object (e.g. from swift).'))
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes.'
           '  DEPRECATED use %(arg)s instead.')
           % {'arg': '--timeout'})
@utils.arg('-t', '--timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('Enable rollback on create/update failure.'))
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by a semicolon.'),
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help=_('Name of the stack to create.'))
def do_stack_create(hc, args):
    '''Create the stack.'''
    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        _authenticated_fetcher(hc))
    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file)

    if args.create_timeout:
        logger.warning(_LW('%(arg1)s is deprecated, '
                           'please use %(arg2)s instead'),
                       {
                           'arg1': '-c/--create-timeout',
                           'arg2': '-t/--timeout'
                       })

    fields = {
        'stack_name': args.name,
        'disable_rollback': not(args.enable_rollback),
        'parameters': utils.format_parameters(args.parameters),
        'template': template,
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env
    }

    timeout = args.timeout or args.create_timeout
    if timeout:
        fields['timeout_mins'] = timeout

    hc.stacks.create(**fields)
    do_stack_list(hc)


@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes.'
           '  DEPRECATED use %(arg)s instead.')
           % {'arg': '--timeout'})
@utils.arg('-t', '--timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes.'))
@utils.arg('-a', '--adopt-file', metavar='<FILE or URL>',
           help=_('Path to adopt stack data file.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('Enable rollback on create/update failure.'))
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by a semicolon.'),
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help=_('Name of the stack to adopt.'))
def do_stack_adopt(hc, args):
    '''Adopt a stack.'''
    env_files, env = template_utils.process_environment_and_files(
        env_path=args.environment_file)

    if not args.adopt_file:
        raise exc.CommandError(_('Need to specify %(arg)s') %
                               {'arg': '--adopt-file'})

    adopt_url = template_utils.normalise_file_path_to_url(args.adopt_file)
    adopt_data = request.urlopen(adopt_url).read()

    if args.create_timeout:
        logger.warning(_LW('%(arg1)s is deprecated, '
                           'please use %(arg2)s instead'),
                       {
                           'arg1': '-c/--create-timeout',
                           'arg2': '-t/--timeout'
                       })

    fields = {
        'stack_name': args.name,
        'disable_rollback': not(args.enable_rollback),
        'adopt_stack_data': adopt_data,
        'parameters': utils.format_parameters(args.parameters),
        'files': dict(list(env_files.items())),
        'environment': env
    }

    timeout = args.timeout or args.create_timeout
    if timeout:
        fields['timeout_mins'] = timeout

    hc.stacks.create(**fields)
    do_stack_list(hc)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help=_('URL of template.'))
@utils.arg('-o', '--template-object', metavar='<URL>',
           help=_('URL to retrieve template object (e.g. from swift)'))
@utils.arg('-t', '--timeout', metavar='<TIMEOUT>', type=int,
           help=_('Stack creation timeout in minutes. This is only used during'
           'validation in preview.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('Enable rollback on failure. This option is not used during'
           'preview and exists only for symmetry with %(cmd)s.')
           % {'cmd': 'stack-create'})
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to preview the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by semicolon.'),
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help=_('Name of the stack to preview.'))
def do_stack_preview(hc, args):
    '''Preview the stack.'''
    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        _authenticated_fetcher(hc))
    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file)

    fields = {
        'stack_name': args.name,
        'disable_rollback': not(args.enable_rollback),
        'timeout_mins': args.timeout,
        'parameters': utils.format_parameters(args.parameters),
        'template': template,
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env
    }

    stack = hc.stacks.preview(**fields)
    formatters = {
        'description': utils.text_wrap_formatter,
        'template_description': utils.text_wrap_formatter,
        'stack_status_reason': utils.text_wrap_formatter,
        'parameters': utils.json_formatter,
        'outputs': utils.json_formatter,
        'resources': utils.json_formatter,
        'links': utils.link_formatter,
    }
    utils.print_dict(stack.to_dict(), formatters=formatters)


@utils.arg('id', metavar='<NAME or ID>', nargs='+',
           help=_('Name or ID of stack(s) to delete.'))
def do_delete(hc, args):
    '''DEPRECATED! Use stack-delete instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'stack-delete '})
    do_stack_delete(hc, args)


@utils.arg('id', metavar='<NAME or ID>', nargs='+',
           help=_('Name or ID of stack(s) to delete.'))
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
        raise exc.CommandError(_("Unable to delete any of the specified "
                               "stacks."))
    do_stack_list(hc)


@utils.arg('-O', '--output-file', metavar='<FILE>',
           help=_('file to output abandon result. '
           'If the option is specified, the result will be'
           ' output into <FILE>.'))
@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to abandon.'))
def do_stack_abandon(hc, args):
    '''Abandon the stack.

    This will delete the record of the stack from Heat, but will not delete
    any of the underlying resources. Prints an adoptable JSON representation
    of the stack to stdout or a file on success.
    '''
    fields = {'stack_id': args.id}
    try:
        stack = hc.stacks.abandon(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        result = jsonutils.dumps(stack, indent=2)
        if args.output_file is not None:
            try:
                with open(args.output_file, "w") as f:
                    f.write(result)
            except IOError as err:
                print(result)
                raise exc.CommandError(str(err))
        else:
            print(result)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to suspend.'))
def do_action_suspend(hc, args):
    '''Suspend the stack.'''
    fields = {'stack_id': args.id}
    try:
        hc.actions.suspend(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to resume.'))
def do_action_resume(hc, args):
    '''Resume the stack.'''
    fields = {'stack_id': args.id}
    try:
        hc.actions.resume(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to check.'))
def do_action_check(hc, args):
    '''Check that stack resources are in expected states.'''
    fields = {'stack_id': args.id}
    try:
        hc.actions.check(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to describe.'))
def do_describe(hc, args):
    '''DEPRECATED! Use stack-show instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'stack-show'})
    do_stack_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to describe.'))
def do_stack_show(hc, args):
    '''Describe the stack.'''
    fields = {'stack_id': args.id}
    try:
        stack = hc.stacks.get(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
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
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help=_('URL of template.'))
@utils.arg('-o', '--template-object', metavar='<URL>',
           help=_('URL to retrieve template object (e.g. from swift).'))
@utils.arg('-t', '--timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack update timeout in minutes.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('DEPRECATED! Use %(arg)s argument instead. '
                  'Enable rollback on stack update failure. '
                  'NOTE: default behavior is now to use the rollback value '
                  'of existing stack.') % {'arg': '--rollback'})
@utils.arg('--rollback', default=None, metavar='<VALUE>',
           help=_('Set rollback on update failure. '
           'Values %(true)s  set rollback to enabled. '
           'Values %(false)s set rollback to disabled. '
           'Default is to use the value of existing stack to be updated.')
           % {'true': strutils.TRUE_STRINGS, 'false': strutils.FALSE_STRINGS})
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by a semicolon.'),
           action='append')
@utils.arg('-x', '--existing', default=False, action="store_true",
           help=_('Re-use the set of parameters of the current stack. '
           'Parameters specified in %(arg)s will patch over the existing '
           'values in the current stack. Parameters omitted will keep '
           'the existing values.')
           % {'arg': '--parameters'})
@utils.arg('-c', '--clear-parameter', metavar='<PARAMETER>',
           help=_('Remove the parameters from the set of parameters of '
           'current stack for the stack-update. The default value in the '
           'template will be used. This can be specified multiple times.'),
           action='append')
@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to update.'))
def do_update(hc, args):
    '''DEPRECATED! Use stack-update instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'stack-update'})
    do_stack_update(hc, args)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-u', '--template-url', metavar='<URL>',
           help=_('URL of template.'))
@utils.arg('-o', '--template-object', metavar='<URL>',
           help=_('URL to retrieve template object (e.g. from swift).'))
@utils.arg('-t', '--timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack update timeout in minutes.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('DEPRECATED! Use %(arg)s argument instead. '
           'Enable rollback on stack update failure. '
           'NOTE: default behavior is now to use the rollback value '
           'of existing stack.')
           % {'arg': '--rollback'})
@utils.arg('--rollback', default=None, metavar='<VALUE>',
           help=_('Set rollback on update failure. '
           'Values %(true)s  set rollback to enabled. '
           'Values %(false)s set rollback to disabled. '
           'Default is to use the value of existing stack to be updated.')
           % {'true': strutils.TRUE_STRINGS, 'false': strutils.FALSE_STRINGS})
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to create the stack. '
           'This can be specified multiple times, or once with parameters '
           'separated by a semicolon.'),
           action='append')
@utils.arg('-x', '--existing', default=False, action="store_true",
           help=_('Re-use the set of parameters of the current stack. '
           'Parameters specified in %(arg)s will patch over the existing '
           'values in the current stack. Parameters omitted will keep '
           'the existing values.')
           % {'arg': '--parameters'})
@utils.arg('-c', '--clear-parameter', metavar='<PARAMETER>',
           help=_('Remove the parameters from the set of parameters of '
           'current stack for the %(cmd)s. The default value in the '
           'template will be used. This can be specified multiple times.')
           % {'cmd': 'stack-update'},
           action='append')
@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to update.'))
def do_stack_update(hc, args):
    '''Update the stack.'''

    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        _authenticated_fetcher(hc))

    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file)

    fields = {
        'stack_id': args.id,
        'parameters': utils.format_parameters(args.parameters),
        'existing': args.existing,
        'template': template,
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env
    }

    if args.timeout:
        fields['timeout_mins'] = args.timeout
    if args.clear_parameter:
        fields['clear_parameters'] = list(args.clear_parameter)

    if args.rollback is not None:
        try:
            rollback = strutils.bool_from_string(args.rollback, strict=True)
        except ValueError as ex:
            raise exc.CommandError(six.text_type(ex))
        else:
            fields['disable_rollback'] = not(rollback)
    # TODO(pshchelo): remove the following 'else' clause after deprecation
    # period of --enable-rollback switch and assign -r shortcut to --rollback
    else:
        if args.enable_rollback:
            fields['disable_rollback'] = False

    hc.stacks.update(**fields)
    do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to cancel update for.'))
def do_stack_cancel_update(hc, args):
    '''Cancel currently running update of the stack.'''
    fields = {'stack_id': args.id}
    try:
        hc.actions.cancel_update(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        do_stack_list(hc)


def do_list(hc, args):
    '''DEPRECATED! Use stack-list instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'stack-list'})
    do_stack_list(hc)


@utils.arg('-s', '--show-deleted', default=False, action="store_true",
           help=_('Include soft-deleted stacks in the stack listing.'))
@utils.arg('-n', '--show-nested', default=False, action="store_true",
           help=_('Include nested stacks in the stack listing.'))
@utils.arg('-f', '--filters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Filter parameters to apply on returned stacks. '
           'This can be specified multiple times, or once with parameters '
           'separated by a semicolon.'),
           action='append')
@utils.arg('-l', '--limit', metavar='<LIMIT>',
           help=_('Limit the number of stacks returned.'))
@utils.arg('-m', '--marker', metavar='<ID>',
           help=_('Only return stacks that appear after the given stack ID.'))
@utils.arg('-g', '--global-tenant', action='store_true', default=False,
           help=_('Display stacks from all tenants. Operation only authorized '
                  'for users who match the policy in heat\'s policy.json.'))
@utils.arg('-o', '--show-owner', action='store_true', default=False,
           help=_('Display stack owner information. This is automatically '
                  'enabled when using %(arg)s.') % {'arg': '--global-tenant'})
def do_stack_list(hc, args=None):
    '''List the user's stacks.'''
    kwargs = {}
    fields = ['id', 'stack_name', 'stack_status', 'creation_time']
    if args:
        kwargs = {'limit': args.limit,
                  'marker': args.marker,
                  'filters': utils.format_parameters(args.filters),
                  'global_tenant': args.global_tenant,
                  'show_deleted': args.show_deleted}
        if args.show_nested:
            fields.append('parent')
            kwargs['show_nested'] = True

        if args.global_tenant or args.show_owner:
            fields.insert(2, 'stack_owner')
        if args.global_tenant:
            fields.insert(2, 'project')

    stacks = hc.stacks.list(**kwargs)
    utils.print_list(stacks, fields, sortby_index=3)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to query.'))
def do_output_list(hc, args):
    '''Show available outputs.'''
    try:
        stack = hc.stacks.get(stack_id=args.id)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        outputs = stack.to_dict()['outputs']
        fields = ['output_key', 'description']
        formatters = {
            'output_key': lambda x: x['output_key'],
            'description': lambda x: x['description'],
        }

        utils.print_list(outputs, fields, formatters=formatters)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to query.'))
@utils.arg('output', metavar='<OUTPUT NAME>', nargs='?', default=None,
           help=_('Name of an output to display.'))
@utils.arg('-a', '--all', default=False, action='store_true',
           help=_('Display all stack outputs.'))
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help=_('The output value format, one of: json, raw'),
           default='json')
def do_output_show(hc, args):
    '''Show a specific stack output.'''
    if (not args.all and args.output is None or
            args.all and args.output is not None):
        raise exc.CommandError(
            _('Error: either %(output)s or %(all)s argument is needed.')
            % {'output': '<OUTPUT NAME>', 'all': '--all'})
    try:
        stack = hc.stacks.get(stack_id=args.id)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        if args.all:
            print(utils.json_formatter(stack.to_dict().get('outputs', [])))
        else:
            for output in stack.to_dict().get('outputs', []):
                if output['output_key'] == args.output:
                    if 'output_error' in output:
                        msg = _("Error: %s") % output['output_error']
                        raise exc.CommandError(msg)
                    else:
                        value = output['output_value']
                    break
            else:
                return

            if (args.format == 'json'
                    or isinstance(value, dict)
                    or isinstance(value, list)):
                print(utils.json_formatter(value))
            else:
                print(value)


def do_resource_type_list(hc, args):
    '''List the available resource types.'''
    types = hc.resource_types.list()
    utils.print_list(types, ['resource_type'], sortby_index=0)


@utils.arg('resource_type', metavar='<RESOURCE_TYPE>',
           help=_('Resource type to get the details for.'))
def do_resource_type_show(hc, args):
    '''Show the resource type.'''
    try:
        resource_type = hc.resource_types.get(args.resource_type)
    except exc.HTTPNotFound:
        raise exc.CommandError(
            _('Resource Type not found: %s') % args.resource_type)
    else:
        print(jsonutils.dumps(resource_type, indent=2))


@utils.arg('resource_type', metavar='<RESOURCE_TYPE>',
           help=_('Resource type to generate a template for.'))
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help=_("The template output format, one of: %s.")
                 % ', '.join(utils.supported_formats.keys()))
def do_resource_type_template(hc, args):
    '''Generate a template based on a resource type.'''
    fields = {'resource_type': args.resource_type}
    try:
        template = hc.resource_types.generate_template(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(
            _('Resource Type %s not found.') % args.resource_type)
    else:
        if args.format:
            print(utils.format_output(template, format=args.format))
        else:
            print(utils.format_output(template))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to get the template for.'))
def do_gettemplate(hc, args):
    '''DEPRECATED! Use template-show instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'template-show'})
    do_template_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to get the template for.'))
def do_template_show(hc, args):
    '''Get the template for the specified stack.'''
    fields = {'stack_id': args.id}
    try:
        template = hc.stacks.template(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        if 'heat_template_version' in template:
            print(yaml.safe_dump(template, indent=2))
        else:
            print(jsonutils.dumps(template, indent=2, ensure_ascii=False))


@utils.arg('-u', '--template-url', metavar='<URL>',
           help=_('URL of template.'))
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help=_('URL to retrieve template object (e.g. from swift).'))
def do_validate(hc, args):
    '''DEPRECATED! Use template-validate instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'template-validate'})
    do_template_validate(hc, args)


@utils.arg('-u', '--template-url', metavar='<URL>',
           help=_('URL of template.'))
@utils.arg('-f', '--template-file', metavar='<FILE>',
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-o', '--template-object', metavar='<URL>',
           help=_('URL to retrieve template object (e.g. from swift).'))
def do_template_validate(hc, args):
    '''Validate a template with parameters.'''

    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        _authenticated_fetcher(hc))

    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file)
    fields = {
        'template': template,
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env
    }

    validation = hc.stacks.validate(**fields)
    print(jsonutils.dumps(validation, indent=2, ensure_ascii=False))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the resources for.'))
@utils.arg('-n', '--nested-depth', metavar='<DEPTH>',
           help=_('Depth of nested stacks from which to display resources.'))
def do_resource_list(hc, args):
    '''Show list of resources belonging to a stack.'''
    fields = {
        'stack_id': args.id,
        'nested_depth': args.nested_depth,
    }
    try:
        resources = hc.resources.list(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        fields = ['physical_resource_id', 'resource_type',
                  'resource_status', 'updated_time']
        if len(resources) >= 1 and not hasattr(resources[0], 'resource_name'):
            fields.insert(0, 'logical_resource_id')
        else:
            fields.insert(0, 'resource_name')

        if args.nested_depth:
            fields.append('parent_resource')

        utils.print_list(resources, fields, sortby_index=4)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the resource for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource to show the details for.'))
def do_resource(hc, args):
    '''DEPRECATED! Use resource-show instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'resource-show'})
    do_resource_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the resource for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource to show the details for.'))
def do_resource_show(hc, args):
    '''Describe the resource.'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    try:
        resource = hc.resources.get(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or resource not found: '
                                 '%(id)s %(resource)s') %
                               {'id': args.id, 'resource': args.resource})
    else:
        formatters = {
            'attributes': utils.json_formatter,
            'links': utils.link_formatter,
            'required_by': utils.newline_list_formatter
        }
        utils.print_dict(resource.to_dict(), formatters=formatters)


@utils.arg('resource_type', metavar='<RESOURCE_TYPE>',
           help=_('Resource type to generate a template for.'))
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help=_("The template output format, one of: %s.")
                 % ', '.join(utils.supported_formats.keys()))
def do_resource_template(hc, args):
    '''DEPRECATED! Use resource-type-template instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'resource-type-template'})
    do_resource_type_template(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the resource metadata for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource to show the metadata for.'))
def do_resource_metadata(hc, args):
    '''List resource metadata.'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    try:
        metadata = hc.resources.metadata(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or resource not found: '
                                 '%(id)s %(resource)s') %
                               {'id': args.id, 'resource': args.resource})
    else:
        print(jsonutils.dumps(metadata, indent=2))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack the resource belongs to.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource to signal.'))
@utils.arg('-D', '--data', metavar='<DATA>',
           help=_('JSON Data to send to the signal handler.'))
@utils.arg('-f', '--data-file', metavar='<FILE>',
           help=_('File containing JSON data to send to the signal handler.'))
def do_resource_signal(hc, args):
    '''Send a signal to a resource.'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    data = args.data
    data_file = args.data_file
    if data and data_file:
        raise exc.CommandError(_('Can only specify one of data and data-file'))
    if data_file:
        data_url = template_utils.normalise_file_path_to_url(data_file)
        data = request.urlopen(data_url).read()
    if data:
        if isinstance(data, six.binary_type):
            data = data.decode('utf-8')
        try:
            data = jsonutils.loads(data)
        except ValueError as ex:
            raise exc.CommandError(_('Data should be in JSON format: %s') % ex)
        if not isinstance(data, dict):
            raise exc.CommandError(_('Data should be a JSON dict'))
        fields['data'] = data
    try:
        hc.resources.signal(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or resource not found: '
                                 '%(id)s %(resource)s') %
                               {'id': args.id, 'resource': args.resource})


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the events for.'))
@utils.arg('-r', '--resource', metavar='<RESOURCE>',
           help=_('Name of the resource to filter events by.'))
@utils.arg('-f', '--filters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Filter parameters to apply on returned events. '
           'This can be specified multiple times, or once with parameters '
           'separated by a semicolon.'),
           action='append')
@utils.arg('-l', '--limit', metavar='<LIMIT>',
           help=_('Limit the number of events returned.'))
@utils.arg('-m', '--marker', metavar='<ID>',
           help=_('Only return events that appear after the given event ID.'))
def do_event_list(hc, args):
    '''List events for a stack.'''
    fields = {'stack_id': args.id,
              'resource_name': args.resource,
              'limit': args.limit,
              'marker': args.marker,
              'filters': utils.format_parameters(args.filters)}
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
        utils.print_list(events, fields, sortby_index=None)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the events for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource the event belongs to.'))
@utils.arg('event', metavar='<EVENT>',
           help=_('ID of event to display details for.'))
def do_event(hc, args):
    '''DEPRECATED! Use event-show instead.'''
    logger.warning(_LW('DEPRECATED! Use %(cmd)s instead.'),
                   {'cmd': 'event-show'})
    do_event_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the events for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource the event belongs to.'))
@utils.arg('event', metavar='<EVENT>',
           help=_('ID of event to display details for.'))
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


@utils.arg('-f', '--definition-file', metavar='<FILE or URL>',
           help=_('Path to JSON/YAML containing map defining '
           '<inputs>, <outputs>, and <options>.'))
@utils.arg('-c', '--config-file', metavar='<FILE or URL>',
           help=_('Path to configuration script/data.'))
@utils.arg('-g', '--group', metavar='<GROUP_NAME>', default='Heat::Ungrouped',
           help=_('Group name of configuration tool expected by the config.'))
@utils.arg('name', metavar='<CONFIG_NAME>',
           help=_('Name of the configuration to create.'))
def do_config_create(hc, args):
    '''Create a software configuration.'''
    config = {
        'group': args.group,
        'config': ''
    }

    defn = {}
    if args.definition_file:
        defn_url = template_utils.normalise_file_path_to_url(
            args.definition_file)
        defn_raw = request.urlopen(defn_url).read() or '{}'
        defn = yaml.load(defn_raw, Loader=template_format.yaml_loader)

    config['inputs'] = defn.get('inputs', [])
    config['outputs'] = defn.get('outputs', [])
    config['options'] = defn.get('options', {})

    if args.config_file:
        config_url = template_utils.normalise_file_path_to_url(
            args.config_file)
        config['config'] = request.urlopen(config_url).read()

    # build a mini-template with a config resource and validate it
    validate_template = {
        'heat_template_version': '2013-05-23',
        'resources': {
            args.name: {
                'type': 'OS::Heat::SoftwareConfig',
                'properties': config
            }
        }
    }
    hc.stacks.validate(template=validate_template)

    config['name'] = args.name

    sc = hc.software_configs.create(**config)
    print(jsonutils.dumps(sc.to_dict(), indent=2))


@utils.arg('id', metavar='<ID>',
           help=_('ID of the config.'))
@utils.arg('-c', '--config-only', default=False, action="store_true",
           help=_('Only display the value of the <config> property.'))
def do_config_show(hc, args):
    '''View details of a software configuration.'''
    try:
        sc = hc.software_configs.get(config_id=args.id)
    except exc.HTTPNotFound:
        raise exc.CommandError('Configuration not found: %s' % args.id)
    else:
        if args.config_only:
            print(sc.config)
        else:
            print(jsonutils.dumps(sc.to_dict(), indent=2))


@utils.arg('id', metavar='<ID>', nargs='+',
           help=_('IDs of the configurations to delete.'))
def do_config_delete(hc, args):
    '''Delete software configurations.'''
    failure_count = 0

    for config_id in args.id:
        try:
            hc.software_configs.delete(config_id=config_id)
        except exc.HTTPNotFound as e:
            failure_count += 1
            print(e)
    if failure_count == len(args.id):
        raise exc.CommandError(_("Unable to delete any of the specified "
                                 "configs."))


@utils.arg('id', metavar='<ID>',
           help=_('ID of the deployment.'))
def do_deployment_show(hc, args):
    '''Show the details of a software deployment.'''
    try:
        sd = hc.software_deployments.get(deployment_id=args.id)
    except exc.HTTPNotFound:
        raise exc.CommandError('Deployment not found: %s' % args.id)
    else:
        print(jsonutils.dumps(sd.to_dict(), indent=2))


@utils.arg('id', metavar='<ID>',
           help=_('ID of the server to fetch deployments for.'))
def do_deployment_metadata_show(hc, args):
    '''Get deployment configuration metadata for the specified server.'''
    md = hc.software_deployments.metadata(server_id=args.id)
    print(jsonutils.dumps(md, indent=2))


@utils.arg('id', metavar='<ID>', nargs='+',
           help=_('IDs of the deployments to delete.'))
def do_deployment_delete(hc, args):
    '''Delete software deployments.'''
    failure_count = 0

    for deploy_id in args.id:
        try:
            hc.software_deployments.delete(deployment_id=deploy_id)
        except exc.HTTPNotFound as e:
            failure_count += 1
            print(e)
    if failure_count == len(args.id):
        raise exc.CommandError(_("Unable to delete any of the specified "
                                 "deployments."))


def do_build_info(hc, args):
    '''Retrieve build information.'''
    result = hc.build_info.build_info()
    formatters = {
        'api': utils.json_formatter,
        'engine': utils.json_formatter,
    }
    utils.print_dict(result, formatters=formatters)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to snapshot.'))
@utils.arg('-n', '--name', metavar='<NAME>',
           help=_('If specified, the name given to the snapshot.'))
def do_stack_snapshot(hc, args):
    '''Make a snapshot of a stack.'''
    fields = {'stack_id': args.id}
    if args.name:
        fields['name'] = args.name
    try:
        snapshot = hc.stacks.snapshot(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        print(jsonutils.dumps(snapshot, indent=2, ensure_ascii=False))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of the stack containing the snapshot.'))
@utils.arg('snapshot', metavar='<SNAPSHOT>',
           help=_('The ID of the snapshot to show.'))
def do_snapshot_show(hc, args):
    '''Show a snapshot of a stack.'''
    fields = {'stack_id': args.id, 'snapshot_id': args.snapshot}
    try:
        snapshot = hc.stacks.snapshot_show(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or snapshot not found'))
    else:
        print(jsonutils.dumps(snapshot, indent=2, ensure_ascii=False))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of the stack containing the snapshot.'))
@utils.arg('snapshot', metavar='<SNAPSHOT>',
           help=_('The ID of the snapshot to delete.'))
def do_snapshot_delete(hc, args):
    '''Delete a snapshot of a stack.'''
    fields = {'stack_id': args.id, 'snapshot_id': args.snapshot}
    try:
        hc.stacks.snapshot_delete(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or snapshot not found'))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of the stack containing the snapshot.'))
@utils.arg('snapshot', metavar='<SNAPSHOT>',
           help=_('The ID of the snapshot to restore.'))
def do_stack_restore(hc, args):
    '''Restore a snapshot of a stack.'''
    fields = {'stack_id': args.id, 'snapshot_id': args.snapshot}
    try:
        hc.stacks.restore(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or snapshot not found'))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of the stack containing the snapshots.'))
def do_snapshot_list(hc, args):
    '''List the snapshots of a stack.'''
    fields = {'stack_id': args.id}
    try:
        snapshots = hc.stacks.snapshot_list(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        fields = ['id', 'name', 'status', 'status_reason', 'data',
                  'creation_time']
        formatters = {
            'id': lambda x: x['id'],
            'name': lambda x: x['name'],
            'status': lambda x: x['status'],
            'status_reason': lambda x: x['status_reason'],
            'data': lambda x: jsonutils.dumps(x['data'], indent=2,
                                              ensure_ascii=False),
            'creation_time': lambda x: x['creation_time'],
        }
        utils.print_list(snapshots["snapshots"], fields, formatters=formatters)


def do_service_list(hc, args=None):
    '''List the Heat engines.'''
    fields = ['hostname', 'binary', 'engine_id', 'host',
              'topic', 'updated_at', 'status']
    services = hc.services.list()
    utils.print_list(services, fields, sortby_index=1)
