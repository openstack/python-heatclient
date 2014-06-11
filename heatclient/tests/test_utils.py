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
from heatclient.common import utils
from heatclient import exc
import testtools


class shellTest(testtools.TestCase):

    def test_format_parameter_none(self):
        self.assertEqual({}, utils.format_parameters(None))

    def test_format_parameters(self):
        p = utils.format_parameters([
            'InstanceType=m1.large;DBUsername=wp;'
            'DBPassword=verybadpassword;KeyName=heat_key;'
            'LinuxDistribution=F17'])
        self.assertEqual({'InstanceType': 'm1.large',
                          'DBUsername': 'wp',
                          'DBPassword': 'verybadpassword',
                          'KeyName': 'heat_key',
                          'LinuxDistribution': 'F17'
                          }, p)

    def test_format_parameters_split(self):
        p = utils.format_parameters([
            'KeyName=heat_key;'
            'DnsSecKey=hsgx1m31PbamNF4WEcHlwjIlCGgifOdoB58/wwC7a4oAONQ/fDV5ct'
            'qrYBoLlKHhTfkyQEw9iVScKYZbbMtMNg==;'
            'UpstreamDNS=8.8.8.8'])
        self.assertEqual({'KeyName': 'heat_key',
                          'DnsSecKey': 'hsgx1m31PbamNF4WEcHlwjIlCGgifOdoB58/ww'
                          'C7a4oAONQ/fDV5ctqrYBoLlKHhTfkyQEw9iVScKYZbbMtMNg==',
                          'UpstreamDNS': '8.8.8.8'}, p)

    def test_format_parameters_multiple(self):
        p = utils.format_parameters([
            'KeyName=heat_key',
            'DnsSecKey=hsgx1m31PbamNF4WEcHlwjIlCGgifOdoB58/wwC7a4oAONQ/fDV5ct'
            'qrYBoLlKHhTfkyQEw9iVScKYZbbMtMNg==',
            'UpstreamDNS=8.8.8.8'])
        self.assertEqual({'KeyName': 'heat_key',
                          'DnsSecKey': 'hsgx1m31PbamNF4WEcHlwjIlCGgifOdoB58/ww'
                          'C7a4oAONQ/fDV5ctqrYBoLlKHhTfkyQEw9iVScKYZbbMtMNg==',
                          'UpstreamDNS': '8.8.8.8'}, p)

    def test_format_parameters_multiple_semicolon_values(self):
        p = utils.format_parameters([
            'KeyName=heat_key',
            'DnsSecKey=hsgx1m31;PbaNF4WEcHlwj;IlCGgfOdoB;58/ww7a4oAO;NQ/fD==',
            'UpstreamDNS=8.8.8.8'])
        self.assertEqual({'KeyName': 'heat_key',
                          'DnsSecKey': 'hsgx1m31;PbaNF4WEcHlwj;IlCGgfOdoB;58/'
                                       'ww7a4oAO;NQ/fD==',
                          'UpstreamDNS': '8.8.8.8'}, p)

    def test_format_parameters_multiple_values_per_pamaters(self):
        p = utils.format_parameters([
            'status=COMPLETE',
            'status=FAILED'])
        self.assertIn('status', p)
        self.assertIn('COMPLETE', p['status'])
        self.assertIn('FAILED', p['status'])

    def test_format_parameter_bad_parameter(self):
        params = ['KeyName=heat_key;UpstreamDNS8.8.8.8']
        ex = self.assertRaises(exc.CommandError,
                               utils.format_parameters, params)
        self.assertEqual('Malformed parameter(UpstreamDNS8.8.8.8). '
                         'Use the key=value format.', str(ex))

    def test_format_multiple_bad_parameter(self):
        params = ['KeyName=heat_key', 'UpstreamDNS8.8.8.8']
        ex = self.assertRaises(exc.CommandError,
                               utils.format_parameters, params)
        self.assertEqual('Malformed parameter(UpstreamDNS8.8.8.8). '
                         'Use the key=value format.', str(ex))

    def test_link_formatter(self):
        self.assertEqual('', utils.link_formatter(None))
        self.assertEqual('', utils.link_formatter([]))
        self.assertEqual(
            'http://foo.example.com\nhttp://bar.example.com',
            utils.link_formatter([
                {'href': 'http://foo.example.com'},
                {'href': 'http://bar.example.com'}]))
        self.assertEqual(
            'http://foo.example.com (a)\nhttp://bar.example.com (b)',
            utils.link_formatter([
                {'href': 'http://foo.example.com', 'rel': 'a'},
                {'href': 'http://bar.example.com', 'rel': 'b'}]))
        self.assertEqual(
            '\n',
            utils.link_formatter([
                {'hrf': 'http://foo.example.com'},
                {}]))

    def test_json_formatter(self):
        self.assertEqual('null', utils.json_formatter(None))
        self.assertEqual('{}', utils.json_formatter({}))
        self.assertEqual('{\n  "foo": "bar"\n}',
                         utils.json_formatter({"foo": "bar"}))
        self.assertEqual(u'{\n  "Uni": "test\u2665"\n}',
                         utils.json_formatter({"Uni": u"test\u2665"}))

    def test_text_wrap_formatter(self):
        self.assertEqual('', utils.text_wrap_formatter(None))
        self.assertEqual('', utils.text_wrap_formatter(''))
        self.assertEqual('one two three',
                         utils.text_wrap_formatter('one two three'))
        self.assertEqual(
            'one two three four five six seven eight nine ten eleven\ntwelve',
            utils.text_wrap_formatter(
                ('one two three four five six seven '
                 'eight nine ten eleven twelve')))

    def test_newline_list_formatter(self):
        self.assertEqual('', utils.newline_list_formatter(None))
        self.assertEqual('', utils.newline_list_formatter([]))
        self.assertEqual('one\ntwo',
                         utils.newline_list_formatter(['one', 'two']))
