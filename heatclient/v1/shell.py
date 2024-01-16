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
import sys

from oslo_serialization import jsonutils
from oslo_utils import strutils
from urllib import request
import yaml

from heatclient._i18n import _
from heatclient.common import deployment_utils
from heatclient.common import event_utils
from heatclient.common import hook_utils
from heatclient.common import http
from heatclient.common import template_format
from heatclient.common import template_utils
from heatclient.common import utils
import heatclient.exc as exc

logger = logging.getLogger(__name__)


def show_deprecated(deprecated, recommended):
    logger.warning('"%(old)s" is deprecated, '
                   'please use "%(new)s" instead',
                   {'old': deprecated,
                    'new': recommended}
                   )


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('--pre-create', metavar='<RESOURCE>',
           default=None, action='append',
           help=_('Name of a resource to set a pre-create hook to. Resources '
                  'in nested stacks can be set using slash as a separator: '
                  'nested_stack/another/my_resource. You can use wildcards '
                  'to match multiple stacks or resources: '
                  'nested_stack/an*/*_resource. This can be specified '
                  'multiple times'))
@utils.arg('-u', '--template-url', metavar='<URL>',
           help=_('URL of template.'))
@utils.arg('-o', '--template-object', metavar='<URL>',
           help=_('URL to retrieve template object (e.g. from swift).'))
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes. '
                  'DEPRECATED use %(arg)s instead.')
           % {'arg': '--timeout'})
@utils.arg('-t', '--timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('Enable rollback on create/update failure.'))
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to create the stack. '
                  'This can be specified multiple times, or once with '
                  'parameters separated by a semicolon.'),
           action='append')
@utils.arg('-Pf', '--parameter-file', metavar='<KEY=FILE>',
           help=_('Parameter values from file used to create the stack. '
                  'This can be specified multiple times. Parameter value '
                  'would be the content of the file'),
           action='append')
@utils.arg('--poll', metavar='SECONDS', type=int, nargs='?', const=5,
           help=_('Poll and report events until stack completes. '
                  'Optional poll interval in seconds can be provided as '
                  'argument, default 5.'))
@utils.arg('name', metavar='<STACK_NAME>',
           help=_('Name of the stack to create.'))
@utils.arg('--tags', metavar='<TAG1,TAG2>',
           help=_('A list of tags to associate with the stack.'))
def do_stack_create(hc, args):
    '''Create the stack.'''
    show_deprecated('heat stack-create', 'openstack stack create')

    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        http.authenticated_fetcher(hc))
    env_files_list = []
    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file, env_list_tracker=env_files_list)

    if args.create_timeout:
        logger.warning('%(arg1)s is deprecated, '
                       'please use %(arg2)s instead',
                       {
                           'arg1': '-c/--create-timeout',
                           'arg2': '-t/--timeout'})

    if args.pre_create:
        template_utils.hooks_to_env(env, args.pre_create, 'pre-create')

    fields = {
        'stack_name': args.name,
        'disable_rollback': not args.enable_rollback,
        'parameters': utils.format_all_parameters(args.parameters,
                                                  args.parameter_file,
                                                  args.template_file,
                                                  args.template_url),
        'template': template,
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env
    }

    # If one or more environments is found, pass the listing to the server
    if env_files_list:
        fields['environment_files'] = env_files_list

    if args.tags:
        fields['tags'] = args.tags
    timeout = args.timeout or args.create_timeout
    if timeout:
        fields['timeout_mins'] = timeout

    hc.stacks.create(**fields)
    do_stack_list(hc)
    if not args.poll:
        return

    show_fields = {'stack_id': args.name}
    _do_stack_show(hc, show_fields)
    stack_status, msg = event_utils.poll_for_events(
        hc, args.name, action='CREATE', poll_period=args.poll)
    _do_stack_show(hc, show_fields)
    if stack_status == 'CREATE_FAILED':
        raise exc.StackFailure(msg)
    print(msg)


@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('-c', '--create-timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes. '
                  'DEPRECATED use %(arg)s instead.')
           % {'arg': '--timeout'})
@utils.arg('-t', '--timeout', metavar='<TIMEOUT>',
           type=int,
           help=_('Stack creation timeout in minutes.'))
@utils.arg('-a', '--adopt-file', metavar='<FILE or URL>',
           help=_('Path to adopt stack data file.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('Enable rollback on create/update failure.'))
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to create the stack. This can be '
                  'specified multiple times, or once with parameters '
                  'separated by a semicolon.'),
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help=_('Name of the stack to adopt.'))
def do_stack_adopt(hc, args):
    '''Adopt a stack.'''
    show_deprecated('heat stack-adopt', 'openstack stack adopt')

    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file)

    if not args.adopt_file:
        raise exc.CommandError(_('Need to specify %(arg)s') %
                               {'arg': '--adopt-file'})

    adopt_url = utils.normalise_file_path_to_url(args.adopt_file)
    adopt_data = request.urlopen(adopt_url).read()
    yaml_adopt_data = yaml.safe_load(adopt_data) or {}

    files = yaml_adopt_data.get('files', {})
    files.update(env_files)

    if not len(adopt_data):
        raise exc.CommandError('Invalid adopt-file, no data!')

    if args.create_timeout:
        logger.warning('%(arg1)s is deprecated, '
                       'please use %(arg2)s instead',
                       {
                           'arg1': '-c/--create-timeout',
                           'arg2': '-t/--timeout'})

    fields = {
        'stack_name': args.name,
        'disable_rollback': not args.enable_rollback,
        'adopt_stack_data': adopt_data,
        'parameters': utils.format_parameters(args.parameters),
        'files': files,
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
           help=_('Stack creation timeout in minutes. This is only used '
                  'during validation in preview.'))
@utils.arg('-r', '--enable-rollback', default=False, action="store_true",
           help=_('Enable rollback on failure. This option is not used during '
                  'preview and exists only for symmetry with %(cmd)s.')
           % {'cmd': 'stack-create'})
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to preview the stack. '
                  'This can be specified multiple times, or once with '
                  'parameters separated by semicolon.'),
           action='append')
@utils.arg('-Pf', '--parameter-file', metavar='<KEY=FILE>',
           help=_('Parameter values from file used to create the stack. '
                  'This can be specified multiple times. Parameter value '
                  'would be the content of the file'),
           action='append')
@utils.arg('name', metavar='<STACK_NAME>',
           help=_('Name of the stack to preview.'))
@utils.arg('--tags', metavar='<TAG1,TAG2>',
           help=_('A list of tags to associate with the stack.'))
def do_stack_preview(hc, args):
    '''Preview the stack.'''
    show_deprecated('heat stack-preview', 'openstack stack create --dry-run')

    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        http.authenticated_fetcher(hc))
    env_files_list = []
    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file, env_list_tracker=env_files_list)

    fields = {
        'stack_name': args.name,
        'disable_rollback': not args.enable_rollback,
        'timeout_mins': args.timeout,
        'parameters': utils.format_all_parameters(args.parameters,
                                                  args.parameter_file,
                                                  args.template_file,
                                                  args.template_url),
        'template': template,
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env
    }

    # If one or more environments is found, pass the listing to the server
    if env_files_list:
        fields['environment_files'] = env_files_list

    if args.tags:
        fields['tags'] = args.tags

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
@utils.arg('-y', '--yes', default=False, action="store_true",
           help=_('Skip yes/no prompt (assume yes).'))
def do_stack_delete(hc, args):
    '''Delete the stack(s).'''
    show_deprecated('heat stack-delete', 'openstack stack delete')

    failure_count = 0

    try:
        if not args.yes and sys.stdin.isatty():
            prompt_response = input(
                _("Are you sure you want to delete this stack(s) [y/N]? ")
            ).lower()
            if not prompt_response.startswith('y'):
                logger.info(
                    'User did not confirm stack delete so taking no action.')
                return
    except KeyboardInterrupt:  # ctrl-c
        logger.info(
            'User did not confirm stack delete (ctrl-c) so taking no action.')
        return
    except EOFError:  # ctrl-d
        logger.info(
            'User did not confirm stack delete (ctrl-d) so taking no action.')
        return

    for sid in args.id:
        fields = {'stack_id': sid}
        try:
            hc.stacks.delete(**fields)
            success_msg = _("Request to delete stack %s has been accepted.")
            print(success_msg % sid)
        except (exc.HTTPNotFound, exc.Forbidden) as e:
            failure_count += 1
            print(e)
    if failure_count:
        raise exc.CommandError(_("Unable to delete %(count)d of the %(total)d "
                               "stacks.") %
                               {'count': failure_count,
                                'total': len(args.id)})


@utils.arg('-O', '--output-file', metavar='<FILE>',
           help=_('file to output abandon result. '
                  'If the option is specified, the result will be '
                  'output into <FILE>.'))
@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to abandon.'))
def do_stack_abandon(hc, args):
    '''Abandon the stack.

    This will delete the record of the stack from Heat, but will not delete
    any of the underlying resources. Prints an adoptable JSON representation
    of the stack to stdout or a file on success.
    '''
    show_deprecated('heat stack-abandon', 'openstack stack abandon')

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
    show_deprecated('heat action-suspend', 'openstack stack suspend')

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
    show_deprecated('heat action-resume', 'openstack stack resume')

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
    show_deprecated('heat action-check', 'openstack stack check')

    fields = {'stack_id': args.id}
    try:
        hc.actions.check(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to describe.'))
@utils.arg('--no-resolve-outputs', action="store_true",
           help=_('Do not resolve outputs of the stack.'))
def do_stack_show(hc, args):
    '''Describe the stack.'''
    show_deprecated('heat stack-show', 'openstack stack show')

    fields = {'stack_id': args.id,
              'resolve_outputs': not args.no_resolve_outputs}
    _do_stack_show(hc, fields)


@utils.arg('-f', '--template-file', metavar='<FILE>',
           help=_('Path to the template.'))
@utils.arg('-e', '--environment-file', metavar='<FILE or URL>',
           help=_('Path to the environment, it can be specified '
                  'multiple times.'),
           action='append')
@utils.arg('--pre-update', metavar='<RESOURCE>',
           default=None, action='append',
           help=_('Name of a resource to set a pre-update hook to. Resources '
                  'in nested stacks can be set using slash as a separator: '
                  'nested_stack/another/my_resource. You can use wildcards '
                  'to match multiple stacks or resources: '
                  'nested_stack/an*/*_resource. This can be specified '
                  'multiple times'))
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
                  'Default is to use the value of existing stack to be '
                  'updated.')
           % {'true': strutils.TRUE_STRINGS, 'false': strutils.FALSE_STRINGS})
@utils.arg('-y', '--dry-run', default=False, action="store_true",
           help=_('Do not actually perform the stack update, but show what '
                  'would be changed'))
@utils.arg('-n', '--show-nested', default=False, action="store_true",
           help=_('Show nested stacks when performing --dry-run'))
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values used to create the stack. '
                  'This can be specified multiple times, or once with '
                  'parameters separated by a semicolon.'),
           action='append')
@utils.arg('-Pf', '--parameter-file', metavar='<KEY=FILE>',
           help=_('Parameter values from file used to create the stack. '
                  'This can be specified multiple times. Parameter value '
                  'would be the content of the file'),
           action='append')
@utils.arg('-x', '--existing', default=False, action="store_true",
           help=_('Re-use the template, parameters and environment of the '
                  'current stack. If the template argument is omitted then '
                  'the existing template is used. If no %(env_arg)s is '
                  'specified then the existing environment is used. '
                  'Parameters specified in %(arg)s will patch over the '
                  'existing values in the current stack. Parameters omitted '
                  'will keep the existing values.')
           % {'arg': '--parameters', 'env_arg': '--environment-file'})
@utils.arg('-c', '--clear-parameter', metavar='<PARAMETER>',
           help=_('Remove the parameters from the set of parameters of '
                  'current stack for the %(cmd)s. The default value in the '
                  'template will be used. This can be specified multiple '
                  'times.')
           % {'cmd': 'stack-update'},
           action='append')
@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to update.'))
@utils.arg('--tags', metavar='<TAG1,TAG2>',
           help=_('An updated list of tags to associate with the stack.'))
def do_stack_update(hc, args):
    '''Update the stack.'''
    show_deprecated('heat stack-update', 'openstack stack update')

    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        http.authenticated_fetcher(hc),
        existing=args.existing)
    env_files_list = []
    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file, env_list_tracker=env_files_list)

    if args.pre_update:
        template_utils.hooks_to_env(env, args.pre_update, 'pre-update')

    fields = {
        'stack_id': args.id,
        'parameters': utils.format_all_parameters(args.parameters,
                                                  args.parameter_file,
                                                  args.template_file,
                                                  args.template_url),
        'existing': args.existing,
        'template': template,
        'files': dict(list(tpl_files.items()) + list(env_files.items())),
        'environment': env
    }

    # If one or more environments is found, pass the listing to the server
    if env_files_list:
        fields['environment_files'] = env_files_list

    if args.tags:
        fields['tags'] = args.tags
    if args.timeout:
        fields['timeout_mins'] = args.timeout
    if args.clear_parameter:
        fields['clear_parameters'] = list(args.clear_parameter)

    if args.rollback is not None:
        try:
            rollback = strutils.bool_from_string(args.rollback, strict=True)
        except ValueError as ex:
            raise exc.CommandError(str(ex))
        else:
            fields['disable_rollback'] = not rollback
    # TODO(pshchelo): remove the following 'else' clause after deprecation
    # period of --enable-rollback switch and assign -r shortcut to --rollback
    else:
        if args.enable_rollback:
            fields['disable_rollback'] = False

    if args.dry_run is True:
        if args.show_nested:
            fields['show_nested'] = args.show_nested

        resource_changes = hc.stacks.preview_update(**fields)

        formatters = {
            'resource_identity': utils.json_formatter
        }

        fields = ['state', 'resource_name', 'resource_type',
                  'resource_identity']

        for k in resource_changes.get("resource_changes", {}):
            for i in range(len(resource_changes["resource_changes"][k])):
                resource_changes["resource_changes"][k][i]['state'] = k

        utils.print_update_list(
            sum(resource_changes["resource_changes"].values(), []),
            fields,
            formatters=formatters
        )
        return

    hc.stacks.update(**fields)
    do_stack_list(hc)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to cancel update for.'))
def do_stack_cancel_update(hc, args):
    '''Cancel currently running update of the stack.'''
    show_deprecated('heat stack-cancel-update', 'openstack stack cancel')

    fields = {'stack_id': args.id}
    try:
        hc.actions.cancel_update(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        do_stack_list(hc)


@utils.arg('-s', '--show-deleted', default=False, action="store_true",
           help=_('Include soft-deleted stacks in the stack listing.'))
@utils.arg('-n', '--show-nested', default=False, action="store_true",
           help=_('Include nested stacks in the stack listing.'))
@utils.arg('-a', '--show-hidden', default=False, action="store_true",
           help=_('Include hidden stacks in the stack listing.'))
@utils.arg('-f', '--filters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Filter parameters to apply on returned stacks. '
                  'This can be specified multiple times, or once with '
                  'parameters separated by a semicolon.'),
           action='append')
@utils.arg('-t', '--tags', metavar='<TAG1,TAG2...>',
           help=_('Show stacks containing these tags. If multiple tags '
                  'are passed, they will be combined using the AND '
                  'boolean expression. '))
@utils.arg('--tags-any', metavar='<TAG1,TAG2...>',
           help=_('Show stacks containing these tags, If multiple tags '
                  'are passed, they will be combined using the OR '
                  'boolean expression. '))
@utils.arg('--not-tags', metavar='<TAG1,TAG2...>',
           help=_('Show stacks not containing these tags, If multiple tags '
                  'are passed, they will be combined using the AND '
                  'boolean expression. '))
@utils.arg('--not-tags-any', metavar='<TAG1,TAG2...>',
           help=_('Show stacks not containing these tags, If multiple tags '
                  'are passed, they will be combined using the OR '
                  'boolean expression. '))
@utils.arg('-l', '--limit', metavar='<LIMIT>',
           help=_('Limit the number of stacks returned.'))
@utils.arg('-m', '--marker', metavar='<ID>',
           help=_('Only return stacks that appear after the given stack ID.'))
@utils.arg('-k', '--sort-keys', metavar='<KEY1;KEY2...>',
           help=_('List of keys for sorting the returned stacks. '
                  'This can be specified multiple times or once with keys '
                  'separated by semicolons. Valid sorting keys include '
                  '"stack_name", "stack_status", "creation_time" and '
                  '"updated_time".'),
           action='append')
@utils.arg('-d', '--sort-dir', metavar='[asc|desc]',
           help=_('Sorting direction (either "asc" or "desc") for the sorting '
                  'keys.'))
@utils.arg('-g', '--global-tenant', action='store_true', default=False,
           help=_('Display stacks from all tenants. Operation only authorized '
                  'for users who match the policy (default or explicitly '
                  'configured in policy.json) in heat.'))
@utils.arg('-o', '--show-owner', action='store_true', default=False,
           help=_('Display stack owner information. This is automatically '
                  'enabled when using %(arg)s.') % {'arg': '--global-tenant'})
def do_stack_list(hc, args=None):
    '''List the user's stacks.'''
    show_deprecated('heat stack-list', 'openstack stack list')

    kwargs = {}
    fields = ['id', 'stack_name', 'stack_status', 'creation_time',
              'updated_time']
    sort_keys = ['stack_name', 'stack_status', 'creation_time',
                 'updated_time']
    sortby_index = 3
    if args:
        kwargs = {'limit': args.limit,
                  'marker': args.marker,
                  'filters': utils.format_parameters(args.filters),
                  'tags': args.tags,
                  'tags_any': args.tags_any,
                  'not_tags': args.not_tags,
                  'not_tags_any': args.not_tags_any,
                  'global_tenant': args.global_tenant,
                  'show_deleted': args.show_deleted,
                  'show_hidden': args.show_hidden}
        if args.show_nested:
            fields.append('parent')
            kwargs['show_nested'] = True

        if args.sort_keys:
            # flatten key list first
            keys = []
            for k in args.sort_keys:
                if ';' in k:
                    keys.extend(k.split(';'))
                else:
                    keys.append(k)
            # validate key list
            for key in keys:
                if key not in sort_keys:
                    err = _("Sorting key '%(key)s' not one of the supported "
                            "keys: %(keys)s") % {'key': key, "keys": sort_keys}
                    raise exc.CommandError(err)
            kwargs['sort_keys'] = keys
            sortby_index = None

        if args.sort_dir:
            if args.sort_dir not in ('asc', 'desc'):
                raise exc.CommandError(_("Sorting direction must be one of "
                                         "'asc' and 'desc'"))
            kwargs['sort_dir'] = args.sort_dir

        if args.global_tenant or args.show_owner:
            fields.append('stack_owner')

        if args.show_deleted:
            fields.append('deletion_time')

    stacks = hc.stacks.list(**kwargs)
    stacks = list(stacks)
    for stk in stacks:
        if hasattr(stk, 'project'):
            fields.append('project')
            break
    utils.print_list(stacks, fields, sortby_index=sortby_index)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to query.'))
def do_output_list(hc, args):
    """Show available outputs."""
    show_deprecated('heat output-list', 'openstack stack output list')

    try:
        outputs = hc.stacks.output_list(args.id)
    except exc.HTTPNotFound:
        try:
            outputs = hc.stacks.get(args.id).to_dict()
        except exc.HTTPNotFound:
            raise exc.CommandError(_('Stack not found: %s') % args.id)

    fields = ['output_key', 'description']
    formatters = {
        'output_key': lambda x: x['output_key'],
        'description': lambda x: x['description'],
    }

    utils.print_list(outputs['outputs'], fields, formatters=formatters)


@utils.arg('id', metavar='<NAME or ID>',  # noqa: C901
           help=_('Name or ID of stack to query.'))
@utils.arg('output', metavar='<OUTPUT NAME>', nargs='?', default=None,
           help=_('Name of an output to display.'))
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help=_('The output value format, one of: json, raw.'),
           default='raw')
@utils.arg('-a', '--all', default=False, action='store_true',
           help=_('Display all stack outputs.'))
@utils.arg('--with-detail', default=False, action="store_true",
           help=_('Enable detail information presented, like '
                  'key and description.'))
def do_output_show(hc, args):  # noqa: C901
    """Show a specific stack output."""
    show_deprecated('heat output-show', 'openstack stack output show')

    def resolve_output(output_key):
        try:
            output = hc.stacks.output_show(args.id, output_key)
        except exc.HTTPNotFound:
            try:
                output = None
                stack = hc.stacks.get(args.id).to_dict()
                for o in stack.get('outputs', []):
                    if o['output_key'] == output_key:
                        output = {'output': o}
                        break
                if output is None:
                    raise exc.CommandError(_('Output %(key)s not found.') % {
                        'key': args.output})
            except exc.HTTPNotFound:
                raise exc.CommandError(
                    _('Stack %(id)s or output %(key)s not found.') % {
                        'id': args.id,
                        'key': args.output})
        return output

    def show_output(output):
        if 'output_error' in output['output']:
            msg = _("Output error: %s") % output['output']['output_error']
            raise exc.CommandError(msg)
        if args.with_detail:
            formatters = {
                'output_value': (lambda x: utils.json_formatter(x)
                                 if args.format == 'json'
                                 else x)
            }
            utils.print_dict(output['output'], formatters=formatters)
        else:
            if args.format == 'json':
                print(utils.json_formatter(output['output']))
            elif (isinstance(output['output']['output_value'], dict)
                  or isinstance(output['output']['output_value'], list)):
                print(utils.json_formatter(output['output']['output_value']))
            else:
                print(output['output']['output_value'])

    if args.all:
        if args.output:
            raise exc.CommandError(
                _("Can't specify an output name and the --all flag"))
        try:
            outputs = hc.stacks.output_list(args.id)
            resolved = False
        except exc.HTTPNotFound:
            try:
                outputs = hc.stacks.get(args.id).to_dict()
                resolved = True
            except exc.HTTPNotFound:
                raise exc.CommandError(_('Stack not found: %s') % args.id)
        for output in outputs['outputs']:
            if resolved:
                show_output({'output': output})
            else:
                show_output(resolve_output(output['output_key']))
    else:
        show_output(resolve_output(args.output))


@utils.arg('-f', '--filters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Filter parameters to apply on returned resource types. '
                  'This can be specified multiple times, or once with '
                  'parameters separated by a semicolon. It can be any of '
                  'name, version and support_status'),
           action='append')
def do_resource_type_list(hc, args):
    '''List the available resource types.'''
    show_deprecated('heat resource-type-list',
                    'openstack orchestration resource type list')

    types = hc.resource_types.list(
        filters=utils.format_parameters(args.filters))
    utils.print_list(types, ['resource_type'], sortby_index=0)


@utils.arg('resource_type', metavar='<RESOURCE_TYPE>',
           help=_('Resource type to get the details for.'))
def do_resource_type_show(hc, args):
    '''Show the resource type.'''
    show_deprecated('heat resource-type-show',
                    'openstack orchestration resource type show')

    try:
        resource_type = hc.resource_types.get(args.resource_type)
    except exc.HTTPNotFound:
        raise exc.CommandError(
            _('Resource Type not found: %s') % args.resource_type)
    else:
        print(jsonutils.dumps(resource_type, indent=2))


@utils.arg('resource_type', metavar='<RESOURCE_TYPE>',
           help=_('Resource type to generate a template for.'))
@utils.arg('-t', '--template-type', metavar='<TEMPLATE_TYPE>',
           default='cfn',
           help=_('Template type to generate, hot or cfn.'))
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help=_("The template output format, one of: %s.")
                 % ', '.join(utils.supported_formats.keys()))
def do_resource_type_template(hc, args):
    '''Generate a template based on a resource type.'''
    show_deprecated('heat resource-type-template',
                    'openstack orchestration resource '
                    'type show --template-type hot')
    fields = {'resource_type': args.resource_type,
              'template_type': args.template_type}
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
def do_template_show(hc, args):
    '''Get the template for the specified stack.'''
    show_deprecated('heat template-show', 'openstack stack template show')

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
@utils.arg('-n', '--show-nested', default=False, action="store_true",
           help=_('Resolve parameters from nested templates as well.'))
@utils.arg('-P', '--parameters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Parameter values for the template. '
                  'This can be specified multiple times, or once with '
                  'parameters separated by a semicolon.'),
           action='append')
@utils.arg('-I', '--ignore-errors', metavar='<ERR1,ERR2...>',
           help=_('List of heat errors to ignore.'))
def do_template_validate(hc, args):
    """Validate a template with parameters."""
    show_deprecated('heat template-validate',
                    'openstack orchestration template validate')

    tpl_files, template = template_utils.get_template_contents(
        args.template_file,
        args.template_url,
        args.template_object,
        http.authenticated_fetcher(hc))

    env_files_list = []
    env_files, env = template_utils.process_multiple_environments_and_files(
        env_paths=args.environment_file, env_list_tracker=env_files_list)

    fields = {
        'template': template,
        'parameters': utils.format_parameters(args.parameters),
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

    validation = hc.stacks.validate(**fields)
    print(jsonutils.dumps(validation, indent=2, ensure_ascii=False))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the resources for.'))
@utils.arg('-n', '--nested-depth', metavar='<DEPTH>',
           help=_('Depth of nested stacks from which to display resources.'))
@utils.arg('--with-detail', default=False, action="store_true",
           help=_('Enable detail information presented for each resource '
                  'in resources list.'))
@utils.arg('-f', '--filter', metavar='<KEY=VALUE>',
           help=_('Filter parameters to apply on returned resources based on'
                  ' their name, status, type, action, id and'
                  ' physical_resource_id. This can be specified multiple'
                  ' times.'),
           action='append')
def do_resource_list(hc, args):
    '''Show list of resources belonging to a stack.'''
    show_deprecated('heat resource-list', 'openstack stack resource list')

    fields = {
        'stack_id': args.id,
        'nested_depth': args.nested_depth,
        'with_detail': args.with_detail,
        'filters': utils.format_parameters(args.filter)
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

        if args.nested_depth or args.with_detail:
            fields.append('stack_name')

        utils.print_list(resources, fields, sortby_index=4)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the resource for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource to show the details for.'))
@utils.arg('-a', '--with-attr', metavar='<ATTRIBUTE>',
           help=_('Attribute to show, it can be specified '
                  'multiple times.'),
           action='append')
def do_resource_show(hc, args):
    '''Describe the resource.'''
    show_deprecated('heat resource-show', 'openstack stack resource show')

    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    if args.with_attr:
        fields['with_attr'] = list(args.with_attr)
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
@utils.arg('-t', '--template-type', metavar='<TEMPLATE_TYPE>',
           default='cfn',
           help=_('Template type to generate, hot or cfn.'))
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help=_("The template output format, one of: %s.")
                 % ', '.join(utils.supported_formats.keys()))
def do_resource_template(hc, args):
    '''DEPRECATED!'''
    do_resource_type_template(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the resource metadata for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource to show the metadata for.'))
def do_resource_metadata(hc, args):
    '''List resource metadata.'''
    show_deprecated('heat resource-metadata',
                    'openstack stack resource metadata')

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
    show_deprecated('heat resource-signal', 'openstack stack resource signal')

    fields = {'stack_id': args.id,
              'resource_name': args.resource}
    data = args.data
    data_file = args.data_file
    if data and data_file:
        raise exc.CommandError(_('Can only specify one of data and data-file'))
    if data_file:
        data_url = utils.normalise_file_path_to_url(data_file)
        data = request.urlopen(data_url).read()
    if data:
        if isinstance(data, bytes):
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
           help=_('Name or ID of stack the resource belongs to.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name or physical ID of the resource.'))
@utils.arg('reason', default="", nargs='?',
           help=_('Reason for state change.'))
@utils.arg('--reset', default=False, action="store_true",
           help=_('Set the resource as healthy.'))
def do_resource_mark_unhealthy(hc, args):
    '''Set resource's health.'''
    show_deprecated('heat resource-mark-unhealthy',
                    'openstack stack resource mark unhealthy')

    fields = {'stack_id': args.id,
              'resource_name': args.resource,
              'mark_unhealthy': not args.reset,
              'resource_status_reason': args.reason}
    try:
        hc.resources.mark_unhealthy(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or resource not found: '
                                 '%(id)s %(resource)s') %
                               {'id': args.id, 'resource': args.resource})


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of the stack these resources belong to.'))
@utils.arg('--pre-create', action='store_true', default=False,
           help=_('Clear the pre-create hooks (optional)'))
@utils.arg('--pre-update', action='store_true', default=False,
           help=_('Clear the pre-update hooks (optional)'))
@utils.arg('--pre-delete', action='store_true', default=False,
           help=_('Clear the pre-delete hooks (optional)'))
@utils.arg('hook', metavar='<RESOURCE>', nargs='+',
           help=_('Resource names with hooks to clear. Resources '
                  'in nested stacks can be set using slash as a separator: '
                  'nested_stack/another/my_resource. You can use wildcards '
                  'to match multiple stacks or resources: '
                  'nested_stack/an*/*_resource'))
def do_hook_clear(hc, args):
    '''Clear hooks on a given stack.'''
    show_deprecated('heat hook-clear', 'openstack stack hook clear')

    if args.pre_create:
        hook_type = 'pre-create'
    elif args.pre_update:
        hook_type = 'pre-update'
    elif args.pre_delete:
        hook_type = 'pre-delete'
    else:
        hook_type = hook_utils.get_hook_type_via_status(hc, args.id)

    for hook_string in args.hook:
        hook = [b for b in hook_string.split('/') if b]
        resource_pattern = hook[-1]
        stack_id = args.id

        hook_utils.clear_wildcard_hooks(hc, stack_id, hook[:-1],
                                        hook_type, resource_pattern)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the events for.'))
@utils.arg('-r', '--resource', metavar='<RESOURCE>',
           help=_('Name of the resource to filter events by.'))
@utils.arg('-f', '--filters', metavar='<KEY1=VALUE1;KEY2=VALUE2...>',
           help=_('Filter parameters to apply on returned events. '
                  'This can be specified multiple times, or once with '
                  'parameters separated by a semicolon.'),
           action='append')
@utils.arg('-l', '--limit', metavar='<LIMIT>',
           help=_('Limit the number of events returned.'))
@utils.arg('-m', '--marker', metavar='<ID>',
           help=_('Only return events that appear after the given event ID.'))
@utils.arg('-n', '--nested-depth', metavar='<DEPTH>',
           help=_('Depth of nested stacks from which to display events. '
                  'Note this cannot be specified with --resource.'))
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help=_('The output value format, one of: log, table'),
           default='table')
def do_event_list(hc, args):
    '''List events for a stack.'''
    show_deprecated('heat event-list', 'openstack stack event list')

    display_fields = ['id', 'resource_status_reason',
                      'resource_status', 'event_time']
    event_args = {'resource_name': args.resource,
                  'limit': args.limit,
                  'marker': args.marker,
                  'filters': utils.format_parameters(args.filters),
                  'sort_dir': 'asc'}

    # Specifying a resource in recursive mode makes no sense..
    if args.nested_depth and args.resource:
        msg = _("--nested-depth cannot be specified with --resource")
        raise exc.CommandError(msg)

    if args.nested_depth:
        try:
            nested_depth = int(args.nested_depth)
        except ValueError:
            msg = _("--nested-depth invalid value %s") % args.nested_depth
            raise exc.CommandError(msg)
        # Until the API supports recursive event listing we'll have to do the
        # marker/limit filtering client-side
        del (event_args['marker'])
        del (event_args['limit'])
        # Nested list adds the stack name to the output
        display_fields.append('stack_name')
    else:
        nested_depth = 0

    events = event_utils.get_events(
        hc, stack_id=args.id, event_args=event_args, nested_depth=nested_depth,
        marker=args.marker, limit=args.limit)

    if len(events) >= 1:
        if hasattr(events[0], 'resource_name'):
            display_fields.insert(0, 'resource_name')
        else:
            display_fields.insert(0, 'logical_resource_id')

    if args.format == 'log':
        print(utils.event_log_formatter(events))
    else:
        utils.print_list(events, display_fields, sortby_index=None)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the pending hooks for.'))
@utils.arg('-n', '--nested-depth', metavar='<DEPTH>',
           help=_('Depth of nested stacks from which to display hooks.'))
def do_hook_poll(hc, args):
    '''List resources with pending hook for a stack.'''
    show_deprecated('heat hook-poll', 'openstack stack hook poll')

    # There are a few steps to determining if a stack has pending hooks
    # 1. The stack is IN_PROGRESS status (otherwise, by definition no hooks
    #    can be pending
    # 2. There is an event for a resource associated with hitting a hook
    # 3. There is not an event associated with clearing the hook in step(2)
    #
    # So, essentially, this ends up being a specially filtered type of event
    # listing, because all hook status is exposed via events.  In future
    # we might consider exposing some more efficient interface via the API
    # to reduce the expense of this brute-force polling approach
    display_fields = ['id', 'resource_status_reason',
                      'resource_status', 'event_time']
    if args.nested_depth:
        try:
            nested_depth = int(args.nested_depth)
        except ValueError:
            msg = _("--nested-depth invalid value %s") % args.nested_depth
            raise exc.CommandError(msg)
        display_fields.append('stack_name')
    else:
        nested_depth = 0

    hook_type = hook_utils.get_hook_type_via_status(hc, args.id)
    event_args = {'sort_dir': 'asc'}
    hook_events = event_utils.get_hook_events(
        hc, stack_id=args.id, event_args=event_args,
        nested_depth=nested_depth, hook_type=hook_type)

    if len(hook_events) >= 1:
        if hasattr(hook_events[0], 'resource_name'):
            display_fields.insert(0, 'resource_name')
        else:
            display_fields.insert(0, 'logical_resource_id')

    utils.print_list(hook_events, display_fields, sortby_index=None)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the events for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource the event belongs to.'))
@utils.arg('event', metavar='<EVENT>',
           help=_('ID of event to display details for.'))
def do_event(hc, args):
    '''DEPRECATED!'''
    do_event_show(hc, args)


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of stack to show the events for.'))
@utils.arg('resource', metavar='<RESOURCE>',
           help=_('Name of the resource the event belongs to.'))
@utils.arg('event', metavar='<EVENT>',
           help=_('ID of event to display details for.'))
def do_event_show(hc, args):
    '''Describe the event.'''
    show_deprecated('heat event-show', 'openstack stack event show')

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
    show_deprecated('heat config-create', 'openstack software config create')

    config = {
        'group': args.group,
        'config': ''
    }

    defn = {}
    if args.definition_file:
        defn_url = utils.normalise_file_path_to_url(
            args.definition_file)
        defn_raw = request.urlopen(defn_url).read() or '{}'
        defn = yaml.load(defn_raw, Loader=template_format.yaml_loader)

    config['inputs'] = defn.get('inputs', [])
    config['outputs'] = defn.get('outputs', [])
    config['options'] = defn.get('options', {})

    if args.config_file:
        config_url = utils.normalise_file_path_to_url(
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

    sc = hc.software_configs.create(name=args.name, **config)
    print(jsonutils.dumps(sc.to_dict(), indent=2))


@utils.arg('-l', '--limit', metavar='<LIMIT>',
           help=_('Limit the number of configs returned.'))
@utils.arg('-m', '--marker', metavar='<ID>',
           help=_('Return configs that appear after the given config ID.'))
def do_config_list(hc, args):
    '''List software configs.'''
    show_deprecated('heat config-list', 'openstack software config list')

    kwargs = {}
    if args.limit:
        kwargs['limit'] = args.limit
    if args.marker:
        kwargs['marker'] = args.marker
    scs = hc.software_configs.list(**kwargs)
    fields = ['id', 'name', 'group', 'creation_time']
    utils.print_list(scs, fields, sortby_index=None)


@utils.arg('id', metavar='<ID>',
           help=_('ID of the config.'))
@utils.arg('-c', '--config-only', default=False, action="store_true",
           help=_('Only display the value of the <config> property.'))
def do_config_show(hc, args):
    '''View details of a software configuration.'''
    show_deprecated('heat config-show', 'openstack software config show')

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
           help=_('ID of the configuration(s) to delete.'))
def do_config_delete(hc, args):
    '''Delete the software configuration(s).'''
    show_deprecated('heat config-delete', 'openstack software config delete')

    failure_count = 0

    for config_id in args.id:
        try:
            hc.software_configs.delete(config_id=config_id)
        except exc.HTTPNotFound:
            failure_count += 1
            print(_('Software config with ID %s not found') % config_id)
    if failure_count:
        raise exc.CommandError(_("Unable to delete %(count)d of the %(total)d "
                               "configs.") %
                               {'count': failure_count,
                                'total': len(args.id)})


@utils.arg('-i', '--input-value', metavar='<KEY=VALUE>',
           help=_('Input value to set on the deployment. '
                  'This can be specified multiple times.'),
           action='append')
@utils.arg('-a', '--action', metavar='<ACTION>', default='UPDATE',
           help=_('Name of action for this deployment. '
                  'Can be a custom action, or one of: '
                  'CREATE, UPDATE, DELETE, SUSPEND, RESUME'))
@utils.arg('-c', '--config', metavar='<CONFIG>',
           help=_('ID of the configuration to deploy.'))
@utils.arg('-s', '--server', metavar='<SERVER>', required=True,
           help=_('ID of the server being deployed to.'))
@utils.arg('-t', '--signal-transport',
           default='TEMP_URL_SIGNAL',
           metavar='<TRANSPORT>',
           help=_('How the server should signal to heat with the deployment '
                  'output values. TEMP_URL_SIGNAL will create a '
                  'Swift TempURL to be signaled via HTTP PUT. NO_SIGNAL will '
                  'result in the resource going to the COMPLETE state '
                  'without waiting for any signal.'))
@utils.arg('--container', metavar='<CONTAINER_NAME>',
           help=_('Optional name of container to store TEMP_URL_SIGNAL '
                  'objects in. If not specified a container will be created '
                  'with a name derived from the DEPLOY_NAME'))
@utils.arg('--timeout', metavar='<TIMEOUT>',
           type=int,
           default=60,
           help=_('Deployment timeout in minutes.'))
@utils.arg('name', metavar='<DEPLOY_NAME>',
           help=_('Name of the derived config associated with this '
                  'deployment. This is used to apply a sort order to the '
                  'list of configurations currently deployed to the server.'))
def do_deployment_create(hc, args):
    '''Create a software deployment.'''
    show_deprecated('heat deployment-create',
                    'openstack software deployment create')

    config = {}
    if args.config:
        try:
            config = hc.software_configs.get(config_id=args.config)
        except exc.HTTPNotFound:
            raise exc.CommandError(
                _('Configuration not found: %s') % args.config)

    derrived_params = deployment_utils.build_derived_config_params(
        action=args.action,
        source=config,
        name=args.name,
        input_values=utils.format_parameters(args.input_value, False),
        server_id=args.server,
        signal_transport=args.signal_transport,
        signal_id=deployment_utils.build_signal_id(hc, args)
    )
    derived_config = hc.software_configs.create(**derrived_params)

    sd = hc.software_deployments.create(
        tenant_id='asdf',
        config_id=derived_config.id,
        server_id=args.server,
        action=args.action,
        status='IN_PROGRESS'
    )
    print(jsonutils.dumps(sd.to_dict(), indent=2))


@utils.arg('-s', '--server', metavar='<SERVER>',
           help=_('ID of the server to fetch deployments for.'))
def do_deployment_list(hc, args):
    '''List software deployments.'''
    show_deprecated('heat deployment-list',
                    'openstack software deployment list')

    kwargs = {'server_id': args.server} if args.server else {}
    deployments = hc.software_deployments.list(**kwargs)
    fields = ['id', 'config_id', 'server_id', 'action', 'status',
              'creation_time', 'status_reason']
    utils.print_list(deployments, fields, sortby_index=5)


@utils.arg('id', metavar='<ID>',
           help=_('ID of the deployment.'))
def do_deployment_show(hc, args):
    '''Show the details of a software deployment.'''
    show_deprecated('heat deployment-show',
                    'openstack software deployment show')

    try:
        sd = hc.software_deployments.get(deployment_id=args.id)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Deployment not found: %s') % args.id)
    else:
        print(jsonutils.dumps(sd.to_dict(), indent=2))


@utils.arg('id', metavar='<ID>',
           help=_('ID of the server to fetch deployments for.'))
def do_deployment_metadata_show(hc, args):
    '''Get deployment configuration metadata for the specified server.'''
    show_deprecated('heat deployment-metadata-show',
                    'openstack software deployment metadata show')

    md = hc.software_deployments.metadata(server_id=args.id)
    print(jsonutils.dumps(md, indent=2))


@utils.arg('id', metavar='<ID>', nargs='+',
           help=_('ID of the deployment(s) to delete.'))
def do_deployment_delete(hc, args):
    '''Delete the software deployment(s).'''
    show_deprecated('heat deployment-delete',
                    'openstack software deployment delete')

    failure_count = 0

    for deploy_id in args.id:
        try:
            sd = hc.software_deployments.get(deployment_id=deploy_id)
            hc.software_deployments.delete(deployment_id=deploy_id)
        except Exception as e:
            if isinstance(e, exc.HTTPNotFound):
                print(_('Deployment with ID %s not found') % deploy_id)
            failure_count += 1
            continue

        # just try best to delete the corresponding config
        try:
            config_id = getattr(sd, 'config_id')
            hc.software_configs.delete(config_id=config_id)
        except Exception:
            print(_('Failed to delete the correlative config '
                    '%(config_id)s of deployment %(deploy_id)s') %
                  {'config_id': config_id, 'deploy_id': deploy_id})

    if failure_count:
        raise exc.CommandError(_("Unable to delete %(count)d of the %(total)d "
                                 "deployments.") %
                               {'count': failure_count, 'total': len(args.id)})


@utils.arg('id', metavar='<ID>',
           help=_('ID deployment to show the output for.'))
@utils.arg('output', metavar='<OUTPUT NAME>', nargs='?', default=None,
           help=_('Name of an output to display.'))
@utils.arg('-a', '--all', default=False, action='store_true',
           help=_('Display all deployment outputs.'))
@utils.arg('-F', '--format', metavar='<FORMAT>',
           help=_('The output value format, one of: raw, json'),
           default='raw')
def do_deployment_output_show(hc, args):
    '''Show a specific deployment output.'''
    show_deprecated('heat deployment-output-show',
                    'openstack software deployment output show')

    if (not args.all and args.output is None or
            args.all and args.output is not None):
        raise exc.CommandError(
            _('Error: either %(output)s or %(all)s argument is needed.')
            % {'output': '<OUTPUT NAME>', 'all': '--all'})
    try:
        sd = hc.software_deployments.get(deployment_id=args.id)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Deployment not found: %s') % args.id)
    outputs = sd.to_dict().get('output_values', {})

    if args.all:
        print(utils.json_formatter(outputs))
    else:
        for output_key, value in outputs.items():
            if output_key == args.output:
                break
        else:
            return

        if (args.format == 'json'
                or isinstance(value, dict)
                or isinstance(value, list)):
            print(utils.json_formatter(value))
        else:
            print(value)


def do_build_info(hc, args):
    '''Retrieve build information.'''
    show_deprecated('heat build-info', 'openstack orchestration build info')

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
    show_deprecated('heat stack-snapshot', 'openstack stack snapshot create')

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
    show_deprecated('heat snapshot-show', 'openstack stack snapshot show')

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
@utils.arg('-y', '--yes', default=False, action="store_true",
           help=_('Skip yes/no prompt (assume yes).'))
def do_snapshot_delete(hc, args):
    '''Delete a snapshot of a stack.'''
    show_deprecated('heat snapshot-delete', 'openstack stack snapshot delete')
    msg = "User did not confirm snapshot delete %sso taking no action."
    try:
        if not args.yes and sys.stdin.isatty():
            sys.stdout.write(
                _('Are you sure you want to delete the snapshot of this '
                  'stack [Y/N]?'))
            prompt_response = sys.stdin.readline().lower()
            if not prompt_response.startswith('y'):
                logger.info(msg, '')
                return
    except KeyboardInterrupt:  # ctrl-c
        logger.info(msg, '(ctrl-c) ')
        return
    except EOFError:  # ctrl-d
        logger.info(msg, '(ctrl-d) ')
        return
    fields = {'stack_id': args.id, 'snapshot_id': args.snapshot}
    try:
        hc.stacks.snapshot_delete(**fields)
        success_msg = _("Request to delete the snapshot %(snapshot_id)s of "
                        "the stack %(stack_id)s has been accepted.")
        print(success_msg % {'stack_id': args.id,
                             'snapshot_id': args.snapshot})
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or snapshot not found'))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of the stack containing the snapshot.'))
@utils.arg('snapshot', metavar='<SNAPSHOT>',
           help=_('The ID of the snapshot to restore.'))
def do_stack_restore(hc, args):
    '''Restore a snapshot of a stack.'''
    show_deprecated('heat stack-restore', 'openstack stack snapshot restore')

    fields = {'stack_id': args.id, 'snapshot_id': args.snapshot}
    try:
        hc.stacks.restore(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack or snapshot not found'))


@utils.arg('id', metavar='<NAME or ID>',
           help=_('Name or ID of the stack containing the snapshots.'))
def do_snapshot_list(hc, args):
    '''List the snapshots of a stack.'''
    show_deprecated('heat snapshot-list', 'openstack stack snapshot list')

    fields = {'stack_id': args.id}
    try:
        snapshots = hc.stacks.snapshot_list(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % args.id)
    else:
        fields = ['id', 'name', 'status', 'status_reason', 'creation_time']
        formatters = {
            'id': lambda x: x['id'],
            'name': lambda x: x['name'],
            'status': lambda x: x['status'],
            'status_reason': lambda x: x['status_reason'],
            'creation_time': lambda x: x['creation_time'],
        }
        utils.print_list(snapshots["snapshots"], fields, formatters=formatters)


def do_service_list(hc, args=None):
    '''List the Heat engines.'''
    show_deprecated('heat service-list',
                    'openstack orchestration service list')

    fields = ['hostname', 'binary', 'engine_id', 'host',
              'topic', 'updated_at', 'status']
    services = hc.services.list()
    utils.print_list(services, fields, sortby_index=1)


def do_template_version_list(hc, args):
    '''List the available template versions.'''
    show_deprecated('heat template-version-list',
                    'openstack orchestration template version list')

    versions = hc.template_versions.list()
    fields = ['version', 'type']
    utils.print_list(versions, fields, sortby_index=1)


@utils.arg('template_version', metavar='<TEMPLATE_VERSION>',
           help=_('Template version to get the functions for.'))
def do_template_function_list(hc, args):
    '''List the available functions.'''
    show_deprecated('heat template-function-list',
                    'openstack orchestration template function list')

    try:
        functions = hc.template_versions.get(args.template_version)
    except exc.HTTPNotFound:
        raise exc.CommandError(
            _('Template version not found: %s') % args.template_version)
    else:
        utils.print_list(functions, ['functions', 'description'])


def _do_stack_show(hc, fields):
    try:
        stack = hc.stacks.get(**fields)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') %
                               fields.get('stack_id'))
    else:
        formatters = {
            'description': utils.text_wrap_formatter,
            'template_description': utils.text_wrap_formatter,
            'stack_status_reason': utils.text_wrap_formatter,
            'parameters': utils.json_formatter,
            'outputs': utils.json_formatter,
            'links': utils.link_formatter,
            'tags': utils.json_formatter
        }
        utils.print_dict(stack.to_dict(), formatters=formatters)
