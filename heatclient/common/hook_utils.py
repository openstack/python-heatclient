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

from oslo_utils import fnmatch

from heatclient._i18n import _
from heatclient import exc

logger = logging.getLogger(__name__)


def clear_hook(hc, stack_id, resource_name, hook_type):
    try:
        hc.resources.signal(
            stack_id=stack_id,
            resource_name=resource_name,
            data={'unset_hook': hook_type})
    except exc.HTTPNotFound:
        logger.error(
            "Stack %(stack)s or resource %(resource)s "
            "not found for hook %(hook_type)s",
            {'resource': resource_name, 'stack': stack_id,
             'hook_type': hook_type})


def clear_wildcard_hooks(hc, stack_id, stack_patterns, hook_type,
                         resource_pattern):
    if stack_patterns:
        for resource in hc.resources.list(stack_id):
            res_name = resource.resource_name
            if fnmatch.fnmatchcase(res_name, stack_patterns[0]):
                nested_stack = hc.resources.get(
                    stack_id=stack_id,
                    resource_name=res_name)
                clear_wildcard_hooks(
                    hc,
                    nested_stack.physical_resource_id,
                    stack_patterns[1:], hook_type, resource_pattern)
    else:
        for resource in hc.resources.list(stack_id):
            res_name = resource.resource_name
            if fnmatch.fnmatchcase(res_name, resource_pattern):
                clear_hook(hc, stack_id, res_name, hook_type)


def get_hook_type_via_status(hc, stack_id):
    # Figure out if the hook should be pre-create, pre-update or
    # pre-delete based on the stack status, also sanity assertions
    # that we're in-progress.
    try:
        stack = hc.stacks.get(stack_id=stack_id)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % stack_id)
    else:
        if 'IN_PROGRESS' not in stack.stack_status:
            raise exc.CommandError(_('Stack status %s not IN_PROGRESS') %
                                   stack.stack_status)

    if 'CREATE' in stack.stack_status:
        hook_type = 'pre-create'
    elif 'UPDATE' in stack.stack_status:
        hook_type = 'pre-update'
    elif 'DELETE' in stack.stack_status:
        hook_type = 'pre-delete'
    else:
        raise exc.CommandError(_('Unexpected stack status %s, '
                                 'only create, update and delete supported')
                               % stack.stack_status)
    return hook_type
