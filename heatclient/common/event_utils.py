# Copyright 2015 Red Hat Inc.
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

from heatclient.common import utils
import heatclient.exc as exc

from heatclient.openstack.common._i18n import _


def get_hook_events(hc, stack_id, event_args, nested_depth=0,
                    hook_type='pre-create'):
    if hook_type == 'pre-create':
        stack_action_reason = 'Stack CREATE started'
        hook_event_reason = 'CREATE paused until Hook pre-create is cleared'
        hook_clear_event_reason = 'Hook pre-create is cleared'
    elif hook_type == 'pre-update':
        stack_action_reason = 'Stack UPDATE started'
        hook_event_reason = 'UPDATE paused until Hook pre-update is cleared'
        hook_clear_event_reason = 'Hook pre-update is cleared'
    else:
        raise exc.CommandError(_('Unexpected hook type %s') % hook_type)

    events = get_events(hc, stack_id=stack_id, event_args=event_args,
                        nested_depth=nested_depth)

    # Get the most recent event associated with this action, which gives us the
    # event when we moved into IN_PROGRESS for the hooks we're interested in.
    stack_name = stack_id.split("/")[0]
    action_start_event = [e for e in enumerate(events)
                          if e[1].resource_status_reason == stack_action_reason
                          and e[1].stack_name == stack_name][-1]
    # Slice the events with the index from the enumerate
    action_start_index = action_start_event[0]
    events = events[action_start_index:]

    # Get hook events still pending by some list filtering/comparison
    # We build a map hook events per-resource, and remove any event
    # for which there is a corresponding hook-clear event.
    resource_event_map = {}
    for e in events:
        stack_resource = (e.stack_name, e.resource_name)
        if e.resource_status_reason == hook_event_reason:
            resource_event_map[(e.stack_name, e.resource_name)] = e
        elif e.resource_status_reason == hook_clear_event_reason:
            if resource_event_map.get(stack_resource):
                del(resource_event_map[(e.stack_name, e.resource_name)])
    return list(resource_event_map.values())


def get_events(hc, stack_id, event_args, nested_depth=0,
               marker=None, limit=None):
    events = _get_stack_events(hc, stack_id, event_args)
    if nested_depth > 0:
        events.extend(_get_nested_events(hc, nested_depth,
                                         stack_id, event_args))
        # Because there have been multiple stacks events mangled into
        # one list, we need to sort before passing to print_list
        # Note we can't use the prettytable sortby_index here, because
        # the "start" option doesn't allow post-sort slicing, which
        # will be needed to make "--marker" work for nested_depth lists
        events.sort(key=lambda x: x.event_time)

        # Slice the list if marker is specified
        if marker:
            marker_index = [e.id for e in events].index(marker)
            events = events[marker_index:]

        # Slice the list if limit is specified
        if limit:
            limit_index = min(int(limit), len(events))
            events = events[:limit_index]
    return events


def _get_nested_ids(hc, stack_id):
    nested_ids = []
    try:
        resources = hc.resources.list(stack_id=stack_id)
    except exc.HTTPNotFound:
        raise exc.CommandError(_('Stack not found: %s') % stack_id)
    for r in resources:
        nested_id = utils.resource_nested_identifier(r)
        if nested_id:
            nested_ids.append(nested_id)
    return nested_ids


def _get_nested_events(hc, nested_depth, stack_id, event_args):
    # FIXME(shardy): this is very inefficient, we should add nested_depth to
    # the event_list API in a future heat version, but this will be required
    # until kilo heat is EOL.
    nested_ids = _get_nested_ids(hc, stack_id)
    nested_events = []
    for n_id in nested_ids:
        stack_events = _get_stack_events(hc, n_id, event_args)
        if stack_events:
            nested_events.extend(stack_events)
        if nested_depth > 1:
            next_depth = nested_depth - 1
            nested_events.extend(_get_nested_events(
                hc, next_depth, n_id, event_args))
    return nested_events


def _get_stack_events(hc, stack_id, event_args):
    event_args['stack_id'] = stack_id
    try:
        events = hc.events.list(**event_args)
    except exc.HTTPNotFound as ex:
        # it could be the stack or resource that is not found
        # just use the message that the server sent us.
        raise exc.CommandError(str(ex))
    else:
        # Show which stack the event comes from (for nested events)
        for e in events:
            e.stack_name = stack_id.split("/")[0]
        return events
