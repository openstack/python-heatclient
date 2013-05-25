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
from heatclient.common import utils
import testtools


class shellTest(testtools.TestCase):

    def test_format_parameters(self):
        p = utils.format_parameters(
            'InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17')
        self.assertEqual({'InstanceType': 'm1.large',
                          'DBUsername': 'wp',
                          'DBPassword': 'verybadpassword',
                          'KeyName': 'heat_key',
                          'LinuxDistribution': 'F17'
                          }, p)
        self.assertEqual({}, utils.format_parameters(None))
