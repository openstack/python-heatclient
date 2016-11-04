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

from heatclient.common import base
from heatclient.common import utils


class BuildInfo(base.Resource):
    def __repr__(self):
        return "<BuildInfo %s>" % self._info

    def build_info(self):
        return self.manager.build_info()


class BuildInfoManager(base.BaseManager):
    resource_class = BuildInfo

    def build_info(self):
        resp = self.client.get('/build_info')
        body = utils.get_response_body(resp)
        return body
