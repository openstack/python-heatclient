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

import sys
import time

from heatclient._i18n import _
from heatclient.common import utils
import heatclient.exc as exc
from heatclient.v1 import events as events_mod


def get_hook_events(hc, stack_id, event_args, nested_depth=0,
                    hook_type='pre-create'):
    """
    Get events for the stack.

    Args:
        hc: (todo): write your description
        stack_id: (str): write your description
        event_args: (todo): write your description
        nested_depth: (int): write your description
        hook_type: (str): write your description
    """
    if hook_type == 'pre-create':
        stack_action_reason = 'Stack CREATE started'
        hook_event_reason = 'CREATE paused until Hook pre-create is cleared'
        hook_clear_event_reason = 'Hook pre-create is cleared'
    elif hook_type == 'pre-update':
        stack_action_reason = 'Stack UPDATE started'
        hook_event_reason = 'UPDATE paused until Hook pre-update is cleared'
        hook_clear_event_reason = 'Hook pre-update is cleared'
    elif hook_type == 'pre-delete':
        stack_action_reason = 'Stack DELETE started'
        hook_event_reason = 'DELETE paused until Hook pre-delete is cleared'
        hook_clear_event_reason = 'Hook pre-delete is cleared'
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
    """
    Return a list of events from a stack.

    Args:
        hc: (str): write your description
        stack_id: (str): write your description
        event_args: (str): write your description
        nested_depth: (int): write your description
        marker: (str): write your description
        limit: (str): write your description
    """
    event_args = dict(event_args)
    if marker:
        event_args['marker'] = marker
    if limit:
        event_args['limit'] = limit
    if not nested_depth:
        # simple call with no nested_depth
        return _get_stack_events(hc, stack_id, event_args)

    # assume an API which supports nested_depth
    event_args['nested_depth'] = nested_depth
    events = _get_stack_events(hc, stack_id, event_args)

    if not events:
        return events

    first_links = getattr(events[0], 'links', [])
    root_stack_link = [l for l in first_links
                       if l.get('rel') == 'root_stack']
    if root_stack_link:
        # response has a root_stack link, indicating this is an API which
        # supports nested_depth
        return events

    # API doesn't support nested_depth, do client-side paging and recursive
    # event fetch
    marker = event_args.pop('marker', None)
    limit = event_args.pop('limit', None)
    event_args.pop('nested_depth', None)
    events = _get_stack_events(hc, stack_id, event_args)
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
        try:
            marker_index = [e.id for e in events].index(marker)
            events = events[marker_index:]
        except ValueError:
            pass

    # Slice the list if limit is specified
    if limit:
        limit_index = min(int(limit), len(events))
        events = events[:limit_index]
    return events


def _get_nested_ids(hc, stack_id):
    """
    Returns a list of dictionaries.

    Args:
        hc: (str): write your description
        stack_id: (str): write your description
    """
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
    """
    Get a list of events from the stack.

    Args:
        hc: (str): write your description
        nested_depth: (int): write your description
        stack_id: (str): write your description
        event_args: (todo): write your description
    """
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


def _get_stack_name_from_links(event):
    """
    Get the stack name of a list.

    Args:
        event: (str): write your description
    """
    links = dict((l.get('rel'),
                  l.get('href')) for l in getattr(event, 'links', []))
    href = links.get('stack')
    if not href:
        return
    return href.split('/stacks/', 1)[-1].split('/')[0]


def _get_stack_events(hc, stack_id, event_args):
    """
    Get events from stack_id

    Args:
        hc: (str): write your description
        stack_id: (str): write your description
        event_args: (todo): write your description
    """
    event_args['stack_id'] = stack_id
    try:
        events = hc.events.list(**event_args)
    except exc.HTTPNotFound as ex:
        # it could be the stack or resource that is not found
        # just use the message that the server sent us.
        raise exc.CommandError(str(ex))
    else:
        stack_name = stack_id.split("/")[0]
        # Show which stack the event comes from (for nested events)
        for e in events:
            e.stack_name = _get_stack_name_from_links(e) or stack_name
        return events


def poll_for_events(hc, stack_name, action=None, poll_period=5, marker=None,
                    out=None, nested_depth=0):
    """Continuously poll events and logs for performed action on stack."""

    if action:
        stop_status = ('%s_FAILED' % action, '%s_COMPLETE' % action)
        stop_check = lambda a: a in stop_status  # noqa: E731
    else:
        stop_check = lambda a: a.endswith('_COMPLETE') or a.endswith('_FAILED')  # noqa E731

    no_event_polls = 0
    msg_template = _("\n Stack %(name)s %(status)s \n")
    if not out:
        out = sys.stdout
    event_log_context = utils.EventLogContext()

    def is_stack_event(event):
        """
        Checks if event is an event

        Args:
            event: (todo): write your description
        """
        if getattr(event, 'resource_name', '') != stack_name:
            return False

        phys_id = getattr(event, 'physical_resource_id', '')
        links = dict((l.get('rel'),
                      l.get('href')) for l in getattr(event, 'links', []))
        stack_id = links.get('stack', phys_id).rsplit('/', 1)[-1]
        return stack_id == phys_id

    while True:
        events = get_events(hc, stack_id=stack_name, nested_depth=nested_depth,
                            event_args={'sort_dir': 'asc',
                                        'marker': marker})

        if len(events) == 0:
            no_event_polls += 1
        else:
            no_event_polls = 0
            # set marker to last event that was received.
            marker = getattr(events[-1], 'id', None)
            events_log = utils.event_log_formatter(events, event_log_context)
            out.write(events_log)
            out.write('\n')

            for event in events:
                # check if stack event was also received
                if is_stack_event(event):
                    stack_status = getattr(event, 'resource_status', '')
                    msg = msg_template % dict(
                        name=stack_name, status=stack_status)
                    if stop_check(stack_status):
                        return stack_status, msg

        if no_event_polls >= 2:
            # after 2 polls with no events, fall back to a stack get
            stack = hc.stacks.get(stack_name, resolve_outputs=False)
            stack_status = stack.stack_status
            msg = msg_template % dict(
                name=stack_name, status=stack_status)
            if stop_check(stack_status):
                return stack_status, msg
            # go back to event polling again
            no_event_polls = 0

        time.sleep(poll_period)


def wait_for_events(ws, stack_name, out=None):
    """Receive events over the passed websocket and wait for final status."""
    msg_template = _("\n Stack %(name)s %(status)s \n")
    if not out:
        out = sys.stdout
    event_log_context = utils.EventLogContext()
    while True:
        data = ws.recv()['body']
        event = events_mod.Event(None, data['payload'], True)
        # Keep compatibility with the HTTP API
        event.event_time = data['timestamp']
        event.resource_status = '%s_%s' % (event.resource_action,
                                           event.resource_status)
        events_log = utils.event_log_formatter([event], event_log_context)
        out.write(events_log)
        out.write('\n')
        if data['payload']['resource_name'] == stack_name:
            stack_status = data['payload']['resource_status']
            if stack_status in ('COMPLETE', 'FAILED'):
                msg = msg_template % dict(
                    name=stack_name, status=event.resource_status)
                return '%s_%s' % (event.resource_action, stack_status), msg
