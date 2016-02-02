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
from heatclient.v1 import resources as hc_res
import mock
import os
import testtools


class ShellTest(testtools.TestCase):

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

    def test_format_parameters_parse_semicolon_false(self):
        p = utils.format_parameters(
            ['KeyName=heat_key;UpstreamDNS=8.8.8.8;a=b'],
            parse_semicolon=False)
        self.assertEqual({'KeyName': 'heat_key;UpstreamDNS=8.8.8.8;a=b'}, p)

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

    def test_resource_nested_identifier(self):
        rsrc_info = {'resource_name': 'aresource',
                     'links': [{'href': u'http://foo/name/id/resources/0',
                                'rel': u'self'},
                               {'href': u'http://foo/name/id',
                                'rel': u'stack'},
                               {'href': u'http://foo/n_name/n_id',
                                'rel': u'nested'}]}
        rsrc = hc_res.Resource(manager=None, info=rsrc_info)
        self.assertEqual('n_name/n_id', utils.resource_nested_identifier(rsrc))

    def test_resource_nested_identifier_none(self):
        rsrc_info = {'resource_name': 'aresource',
                     'links': [{'href': u'http://foo/name/id/resources/0',
                                'rel': u'self'},
                               {'href': u'http://foo/name/id',
                                'rel': u'stack'}]}
        rsrc = hc_res.Resource(manager=None, info=rsrc_info)
        self.assertIsNone(utils.resource_nested_identifier(rsrc))

    def test_json_formatter(self):
        self.assertEqual('null', utils.json_formatter(None))
        self.assertEqual('{}', utils.json_formatter({}))
        self.assertEqual('{\n  "foo": "bar"\n}',
                         utils.json_formatter({"foo": "bar"}))
        self.assertEqual(u'{\n  "Uni": "test\u2665"\n}',
                         utils.json_formatter({"Uni": u"test\u2665"}))

    def test_yaml_formatter(self):
        self.assertEqual('null\n...\n', utils.yaml_formatter(None))
        self.assertEqual('{}\n', utils.yaml_formatter({}))
        self.assertEqual('foo: bar\n',
                         utils.yaml_formatter({"foo": "bar"}))

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

    def test_event_log_formatter(self):
        event1 = {'event_time': '2015-09-28T12:12:12',
                  'id': '123456789',
                  'resource_name': 'res_name',
                  'resource_status': 'CREATE_IN_PROGRESS',
                  'resource_status_reason': 'CREATE started'}
        event2 = {'event_time': '2015-09-28T12:12:22',
                  'id': '123456789',
                  'resource_name': 'res_name',
                  'resource_status': 'CREATE_COMPLETE',
                  'resource_status_reason': 'CREATE completed'}
        events_list = [hc_res.Resource(manager=None, info=event1),
                       hc_res.Resource(manager=None, info=event2)]

        expected = ('2015-09-28 12:12:12 [res_name]: '
                    'CREATE_IN_PROGRESS  CREATE started\n'
                    '2015-09-28 12:12:22 [res_name]: '
                    'CREATE_COMPLETE  CREATE completed')
        self.assertEqual(expected, utils.event_log_formatter(events_list))
        self.assertEqual('', utils.event_log_formatter([]))


class ShellTestParameterFiles(testtools.TestCase):

    def test_format_parameter_file_none(self):
        self.assertEqual({}, utils.format_parameter_file(None))

    def test_format_parameter_file(self):
        tmpl_file = '/opt/stack/template.yaml'
        contents = 'DBUsername=wp\nDBPassword=verybadpassword'
        utils.read_url_content = mock.MagicMock()
        utils.read_url_content.return_value = ('DBUsername=wp\n'
                                               'DBPassword=verybadpassword')

        p = utils.format_parameter_file([
            'env_file1=test_file1'], tmpl_file)
        self.assertEqual({'env_file1': contents
                          }, p)

    def test_format_parameter_file_no_template(self):
        tmpl_file = None
        contents = 'DBUsername=wp\nDBPassword=verybadpassword'
        utils.read_url_content = mock.MagicMock()
        utils.read_url_content.return_value = ('DBUsername=wp\n'
                                               'DBPassword=verybadpassword')
        p = utils.format_parameter_file([
            'env_file1=test_file1'], tmpl_file)
        self.assertEqual({'env_file1': contents
                          }, p)

    def test_format_all_parameters(self):
        tmpl_file = '/opt/stack/template.yaml'
        contents = 'DBUsername=wp\nDBPassword=verybadpassword'
        params = ['KeyName=heat_key;UpstreamDNS=8.8.8.8']
        utils.read_url_content = mock.MagicMock()
        utils.read_url_content.return_value = ('DBUsername=wp\n'
                                               'DBPassword=verybadpassword')
        p = utils.format_all_parameters(params, [
            'env_file1=test_file1'], template_file=tmpl_file)
        self.assertEqual({'KeyName': 'heat_key',
                          'UpstreamDNS': '8.8.8.8',
                          'env_file1': contents}, p)


class TestURLFunctions(testtools.TestCase):

    def setUp(self):
        super(TestURLFunctions, self).setUp()
        self.m = mock.MagicMock()

        self.addCleanup(self.m.UnsetStubs)

    def test_normalise_file_path_to_url_relative(self):
        self.assertEqual(
            'file://%s/foo' % os.getcwd(),
            utils.normalise_file_path_to_url(
                'foo'))

    def test_normalise_file_path_to_url_absolute(self):
        self.assertEqual(
            'file:///tmp/foo',
            utils.normalise_file_path_to_url(
                '/tmp/foo'))

    def test_normalise_file_path_to_url_file(self):
        self.assertEqual(
            'file:///tmp/foo',
            utils.normalise_file_path_to_url(
                'file:///tmp/foo'))

    def test_normalise_file_path_to_url_http(self):
        self.assertEqual(
            'http://localhost/foo',
            utils.normalise_file_path_to_url(
                'http://localhost/foo'))

    def test_get_template_url(self):
        tmpl_file = '/opt/stack/template.yaml'
        tmpl_url = 'file:///opt/stack/template.yaml'
        self.assertEqual(utils.get_template_url(tmpl_file, None),
                         tmpl_url)
        self.assertEqual(utils.get_template_url(None, tmpl_url),
                         tmpl_url)
        self.assertEqual(utils.get_template_url(None, None),
                         None)

    def test_base_url_for_url(self):
        self.assertEqual(
            'file:///foo/bar',
            utils.base_url_for_url(
                'file:///foo/bar/baz'))
        self.assertEqual(
            'file:///foo/bar',
            utils.base_url_for_url(
                'file:///foo/bar/baz.txt'))
        self.assertEqual(
            'file:///foo/bar',
            utils.base_url_for_url(
                'file:///foo/bar/'))
        self.assertEqual(
            'file:///',
            utils.base_url_for_url(
                'file:///'))
        self.assertEqual(
            'file:///',
            utils.base_url_for_url(
                'file:///foo'))

        self.assertEqual(
            'http://foo/bar',
            utils.base_url_for_url(
                'http://foo/bar/'))
        self.assertEqual(
            'http://foo/bar',
            utils.base_url_for_url(
                'http://foo/bar/baz.template'))
