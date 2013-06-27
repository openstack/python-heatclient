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

from heatclient.common import base
from heatclient.v1 import stacks

DEFAULT_PAGE_SIZE = 20


class Event(base.Resource):
    def __repr__(self):
        return "<Event %s>" % self._info

    def update(self, **fields):
        self.manager.update(self, **fields)

    def delete(self):
        return self.manager.delete(self)

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class EventManager(stacks.StackChildManager):
    resource_class = Event

    def list(self, stack_id, resource_name=None):
        """Get a list of events.
        :param stack_id: ID of stack the events belong to
        :param resource_name: Optional name of resources to filter events by
        :rtype: list of :class:`Event`
        """
        if resource_name is None:
            url = '/stacks/%s/events' % stack_id
        else:
            stack_id = self._resolve_stack_id(stack_id)
            url = '/stacks/%s/resources/%s/events' % (stack_id, resource_name)
        return self._list(url, "events")

    def get(self, stack_id, resource_name, event_id):
        """Get the details for a specific event.

        :param stack_id: ID of stack containing the event
        :param resource_name: ID of resource the event belongs to
        :param event_id: ID of event to get the details for
        """
        stack_id = self._resolve_stack_id(stack_id)
        url_str = '/stacks/%s/resources/%s/events/%s' % (stack_id,
                                                         resource_name,
                                                         event_id)
        resp, body = self.api.json_request('GET', url_str)
        return Event(self, body['event'])
