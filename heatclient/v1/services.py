# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from heatclient.common import base


class Service(base.Resource):
    def __repr__(self):
        """
        Return a repr representation of - repr representation of this object.

        Args:
            self: (todo): write your description
        """
        return "<Service %s>" % self._info


class ServiceManager(base.BaseManager):
    resource_class = Service

    def list(self):
        """Get a list of services.

        :rtype: list of :class:`Service`
        """
        url = '/services'
        return self._list(url, "services")
