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

from heatclient.common import http
from heatclient.v1 import actions
from heatclient.v1 import build_info
from heatclient.v1 import events
from heatclient.v1 import resource_types
from heatclient.v1 import resources
from heatclient.v1 import services
from heatclient.v1 import software_configs
from heatclient.v1 import software_deployments
from heatclient.v1 import stacks
from heatclient.v1 import template_versions


class Client(object):
    """Client for the Heat v1 API.

    :param string endpoint: A user-supplied endpoint URL for the heat
                            service.
    :param string token: Token for authentication.
    :param integer timeout: Allows customization of the timeout for client
                            http requests. (optional)
    """

    def __init__(self, *args, **kwargs):
        """Initialize a new client for the Heat v1 API."""
        self.http_client = http._construct_http_client(*args, **kwargs)
        self.stacks = stacks.StackManager(self.http_client)
        self.resources = resources.ResourceManager(self.http_client)
        self.resource_types = resource_types.ResourceTypeManager(
            self.http_client)
        self.events = events.EventManager(self.http_client)
        self.actions = actions.ActionManager(self.http_client)
        self.build_info = build_info.BuildInfoManager(self.http_client)
        self.software_deployments = (
            software_deployments.SoftwareDeploymentManager(
                self.http_client))
        self.software_configs = software_configs.SoftwareConfigManager(
            self.http_client)
        self.services = services.ServiceManager(self.http_client)
        self.template_versions = template_versions.TemplateVersionManager(
            self.http_client)
