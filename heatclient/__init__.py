# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

#NOTE(bcwaldon): this try/except block is needed to run setup.py due to
# its need to import local code before installing required dependencies
try:
    import heatclient.client
    Client = heatclient.client.Client
except ImportError:
    import warnings
    warnings.warn("Could not import heatclient.client", ImportWarning)

import heatclient.version

__version__ = heatclient.version.version_info.deferred_version_string()
