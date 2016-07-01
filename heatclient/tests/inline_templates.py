#
#    Copyright 2016 IBM Corp.
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

FULL_TEMPLATE = '''
heat_template_version: 2016-04-08

description: a template

parameter_groups:
  - label: param_group_1
    description: parameter group 1
    parameters:
      - param1
      - param2
  - label: param_group_2
    description: parameter group 2
    parameters:
      - param3

parameters:
  param1:
    type: string
    label: parameter 5
    description: parameter 5
    default: foo
    hidden: false
    constraints:
      - allowed_values: ['foo', 'bar', 'bax']
  param2:
    type: number
    default: 0
    constraints:
      - range: {min: 0, max: 10}
        description: must be between 0 and 10
  param3:
    type: boolean

resources:
  resource1:
    type: OS::Heat::None
    properties:
      prop1: { get_param: param1 }
      prop2: { get_param: param2 }
      prop3: value
  resource2:
    type: OS::Heat::None
    properties:
      prop1: { get_param: param3 }
    depends_on: resource1

outputs:
  output1:
    description: resource 1 prop 3
    value: { get_attr: [resource1, prop3] }
  output2:
    description: resource 2 prop 1
    value: { get_attr: [resource2, prop1] }
'''

SHORT_TEMPLATE = '''
heat_template_version: 2016-04-08

resources:
  res1:
    type: OS::Heat::None
'''
