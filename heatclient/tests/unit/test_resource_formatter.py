#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

import json
import os

import io

from heatclient.common import resource_formatter
from heatclient.osc.v1 import resource
from heatclient.tests.unit.osc.v1 import fakes as orchestration_fakes
from heatclient.v1 import resources as v1_resources


TEST_VAR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'var'))


class TestStackResourceListDotFormat(orchestration_fakes.TestOrchestrationv1):

    response_path = os.path.join(TEST_VAR_DIR, 'dot_test.json')

    data = '''digraph G {
  graph [
    fontsize=10 fontname="Verdana" compound=true rankdir=LR
  ]
  r_f34a35baf594b319a741 [label="rg1
OS::Heat::ResourceGroup" ];
  r_121e343b017a6d246f36 [label="random2
OS::Heat::RandomString" ];
  r_dbcae38ad41dc991751d [label="random1
OS::Heat::RandomString" style=filled color=red];

  subgraph cluster_stack_16437984473ec64a8e6c {
    label="rg1";
    r_30e9aa76bc0d53310cde [label="1
OS::Heat::ResourceGroup" ];
    r_63c05d424cb708f1599f [label="0
OS::Heat::ResourceGroup" ];

  }

  subgraph cluster_stack_fbfb461c8cc84b686c08 {
    label="1";
    r_e2e5c36ae18e29d9c299 [label="1
OS::Heat::RandomString" ];
    r_56c62630a0d655bce234 [label="0
OS::Heat::RandomString" ];

  }

  subgraph cluster_stack_d427657dfccc28a131a7 {
    label="0";
    r_240756913e2e940387ff [label="1
OS::Heat::RandomString" ];
    r_81c64c43d9131aceedbb [label="0
OS::Heat::RandomString" ];

  }

  r_f34a35baf594b319a741 -> r_30e9aa76bc0d53310cde [
    color=dimgray lhead=cluster_stack_16437984473ec64a8e6c arrowhead=none
  ];
  r_30e9aa76bc0d53310cde -> r_e2e5c36ae18e29d9c299 [
    color=dimgray lhead=cluster_stack_fbfb461c8cc84b686c08 arrowhead=none
  ];
  r_63c05d424cb708f1599f -> r_240756913e2e940387ff [
    color=dimgray lhead=cluster_stack_d427657dfccc28a131a7 arrowhead=none
  ];

  r_dbcae38ad41dc991751d -> r_121e343b017a6d246f36;

}
'''

    def setUp(self):
        super(TestStackResourceListDotFormat, self).setUp()
        self.resource_client = self.app.client_manager.orchestration.resources
        self.cmd = resource.ResourceList(self.app, None)
        with open(self.response_path) as f:
            response = json.load(f)
        self.resources = []
        for r in response['resources']:
            self.resources.append(v1_resources.Resource(None, r))

    def test_resource_list(self):
        out = io.StringIO()
        formatter = resource_formatter.ResourceDotFormatter()
        formatter.emit_list(None, self.resources, out, None)

        self.assertEqual(self.data, out.getvalue())
