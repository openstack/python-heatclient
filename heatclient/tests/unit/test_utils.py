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

import os
from unittest import mock

import testtools

from heatclient.common import utils
from heatclient import exc
from heatclient.v1 import resources as hc_res


class ShellTest(testtools.TestCase):

    def test_format_parameter_none(self):
        """
        Returns the : attribute of the value.

        Args:
            self: (todo): write your description
        """
        self.assertEqual({}, utils.format_parameters(None))

    def test_format_parameters(self):
        """
        Test if the test parameters.

        Args:
            self: (todo): write your description
        """
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
        """
        Split the test test parameters.

        Args:
            self: (todo): write your description
        """
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
        """
        Set the format_format of the format.

        Args:
            self: (todo): write your description
        """
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
        """
        The format of - specific values in the format expected values.

        Args:
            self: (todo): write your description
        """
        p = utils.format_parameters([
            'KeyName=heat_key',
            'DnsSecKey=hsgx1m31;PbaNF4WEcHlwj;IlCGgfOdoB;58/ww7a4oAO;NQ/fD==',
            'UpstreamDNS=8.8.8.8'])
        self.assertEqual({'KeyName': 'heat_key',
                          'DnsSecKey': 'hsgx1m31;PbaNF4WEcHlwj;IlCGgfOdoB;58/'
                                       'ww7a4oAO;NQ/fD==',
                          'UpstreamDNS': '8.8.8.8'}, p)

    def test_format_parameters_parse_semicolon_false(self):
        """
        Test if the test parameters are valid.

        Args:
            self: (todo): write your description
        """
        p = utils.format_parameters(
            ['KeyName=heat_key;UpstreamDNS=8.8.8.8;a=b'],
            parse_semicolon=False)
        self.assertEqual({'KeyName': 'heat_key;UpstreamDNS=8.8.8.8;a=b'}, p)

    def test_format_parameters_multiple_values_per_pamaters(self):
        """
        Set the pamaters_per_parameters.

        Args:
            self: (todo): write your description
        """
        p = utils.format_parameters([
            'status=COMPLETE',
            'status=FAILED'])
        self.assertIn('status', p)
        self.assertIn('COMPLETE', p['status'])
        self.assertIn('FAILED', p['status'])

    def test_format_parameter_bad_parameter(self):
        """
        Assigns_bad_format parameter to be used value.

        Args:
            self: (todo): write your description
        """
        params = ['KeyName=heat_key;UpstreamDNS8.8.8.8']
        ex = self.assertRaises(exc.CommandError,
                               utils.format_parameters, params)
        self.assertEqual('Malformed parameter(UpstreamDNS8.8.8.8). '
                         'Use the key=value format.', str(ex))

    def test_format_multiple_bad_parameter(self):
        """
        Test if there s a single bad bad value.

        Args:
            self: (todo): write your description
        """
        params = ['KeyName=heat_key', 'UpstreamDNS8.8.8.8']
        ex = self.assertRaises(exc.CommandError,
                               utils.format_parameters, params)
        self.assertEqual('Malformed parameter(UpstreamDNS8.8.8.8). '
                         'Use the key=value format.', str(ex))

    def test_link_formatter(self):
        """
        Test for formatter

        Args:
            self: (todo): write your description
        """
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
        """
        Test if nested nested resource identifier is valid.

        Args:
            self: (todo): write your description
        """
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
        """
        Stores the identifier of nested dictionaries

        Args:
            self: (todo): write your description
        """
        rsrc_info = {'resource_name': 'aresource',
                     'links': [{'href': u'http://foo/name/id/resources/0',
                                'rel': u'self'},
                               {'href': u'http://foo/name/id',
                                'rel': u'stack'}]}
        rsrc = hc_res.Resource(manager=None, info=rsrc_info)
        self.assertIsNone(utils.resource_nested_identifier(rsrc))

    def test_json_formatter(self):
        """
        Test for json formatter.

        Args:
            self: (todo): write your description
        """
        self.assertEqual('null', utils.json_formatter(None))
        self.assertEqual('{}', utils.json_formatter({}))
        self.assertEqual('{\n  "foo": "bar"\n}',
                         utils.json_formatter({"foo": "bar"}))
        self.assertEqual(u'{\n  "Uni": "test\u2665"\n}',
                         utils.json_formatter({"Uni": u"test\u2665"}))

    def test_yaml_formatter(self):
        """
        Formats yaml formatter.

        Args:
            self: (todo): write your description
        """
        self.assertEqual('null\n...\n', utils.yaml_formatter(None))
        self.assertEqual('{}\n', utils.yaml_formatter({}))
        self.assertEqual('foo: bar\n',
                         utils.yaml_formatter({"foo": "bar"}))

    def test_text_wrap_formatter(self):
        """
        Wrap text formatting.

        Args:
            self: (todo): write your description
        """
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
        """
        Handles new formatter.

        Args:
            self: (todo): write your description
        """
        self.assertEqual('', utils.newline_list_formatter(None))
        self.assertEqual('', utils.newline_list_formatter([]))
        self.assertEqual('one\ntwo',
                         utils.newline_list_formatter(['one', 'two']))

    def test_event_log_formatter(self):
        """
        Test for log formatter.

        Args:
            self: (todo): write your description
        """
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

    def test_event_log_formatter_resource_path_old_heat(self):
        """
        Formats the event log formatter

        Args:
            self: (todo): write your description
        """

        events = [{
            'resource_name': 'nested',
            'event_time': '2016-09-05T04:10:24Z',
            'links': [{
                'href': 'http://192.0.2.1:8004/v1/t/stacks/'
                'nested/1bed5d4d-41d6-4451-b274-c073ebee375d',
                'rel': 'stack'
            }],
            'logical_resource_id': 'nested',
            'resource_status': 'CREATE_IN_PROGRESS',
            'resource_status_reason': 'Stack CREATE started',
            'physical_resource_id': '1bed5d4d-41d6-4451-b274-c073ebee375d',
        }, {
            'resource_name': 'rg1',
            'event_time': '2016-09-05T04:10:24Z',
            'links': [{
                'href': 'http://192.0.2.1:8004/v1/t/stacks/'
                'nested/1bed5d4d-41d6-4451-b274-c073ebee375d',
                'rel': 'stack'
            }],
            'logical_resource_id': 'rg1',
            'resource_status': 'CREATE_IN_PROGRESS',
            'resource_status_reason': 'state changed',
            'physical_resource_id': None,  # note the None from old heat
            'id': '375c49ae-cefb-4fb3-8f4d-1d5f1b9e3e5d'
        }, {
            'resource_name': 'nested-rg1-m4zxcs4pra6t',
            'event_time': '2016-09-05T04:10:24Z',
            'links': [{
                'href': 'http://192.0.2.1:8004/v1/t/stacks/'
                'nested-rg1-m4zxcs4pra6t/'
                '3400bbad-a825-4226-ac23-c607846420db',
                'rel': 'stack'
            }],
            'logical_resource_id': 'nested-rg1-m4zxcs4pra6t',
            'resource_status': 'CREATE_IN_PROGRESS',
            'resource_status_reason': 'Stack CREATE started',
            'physical_resource_id': '3400bbad-a825-4226-ac23-c607846420db',
            'id': '7e521c84-cd35-4f4c-b0de-962bd3cc40a8'
        }, {
            'resource_name': '1',
            'event_time': '2016-09-05T04:10:24Z',
            'links': [{
                'href': 'http://192.0.2.1:8004/v1/t/stacks/'
                'nested-rg1-m4zxcs4pra6t/'
                '3400bbad-a825-4226-ac23-c607846420db',
                'rel': 'stack'
            }],
            'logical_resource_id': '1',
            'resource_status': 'CREATE_IN_PROGRESS',
            'resource_status_reason': 'state changed',
            'physical_resource_id': None,  # note the None from old heat
            'id': 'c6186c16-94ef-4214-a11a-7e3cc8a17f82'
        }]

        events_list = [hc_res.Resource(manager=None, info=event)
                       for event in events]

        expected = '''\
2016-09-05 04:10:24Z [nested]: \
CREATE_IN_PROGRESS  Stack CREATE started
2016-09-05 04:10:24Z [nested.rg1]: \
CREATE_IN_PROGRESS  state changed
2016-09-05 04:10:24Z [nested-rg1-m4zxcs4pra6t]: \
CREATE_IN_PROGRESS  Stack CREATE started
2016-09-05 04:10:24Z [nested-rg1-m4zxcs4pra6t.1]: \
CREATE_IN_PROGRESS  state changed'''
        self.assertEqual(expected, utils.event_log_formatter(events_list))

    def test_event_log_formatter_resource_path(self):
        """
        Generate the resource path

        Args:
            self: (todo): write your description
        """

        events = [{
            'resource_name': 'nested',
            'event_time': '2016-09-05T04:10:24Z',
            'links': [{
                'href': 'http://192.0.2.1:8004/v1/t/stacks/'
                'nested/1bed5d4d-41d6-4451-b274-c073ebee375d',
                'rel': 'stack'
            }],
            'logical_resource_id': 'nested',
            'resource_status': 'CREATE_IN_PROGRESS',
            'resource_status_reason': 'Stack CREATE started',
            'physical_resource_id': '1bed5d4d-41d6-4451-b274-c073ebee375d',
        }, {
            'resource_name': 'rg1',
            'event_time': '2016-09-05T04:10:24Z',
            'links': [{
                'href': 'http://192.0.2.1:8004/v1/t/stacks/'
                'nested/1bed5d4d-41d6-4451-b274-c073ebee375d',
                'rel': 'stack'
            }],
            'logical_resource_id': 'rg1',
            'resource_status': 'CREATE_IN_PROGRESS',
            'resource_status_reason': 'state changed',
            'physical_resource_id': 'nested-rg1-m4zxcs4pra6t',
            'id': '375c49ae-cefb-4fb3-8f4d-1d5f1b9e3e5d'
        }, {
            'resource_name': 'nested-rg1-m4zxcs4pra6t',
            'event_time': '2016-09-05T04:10:24Z',
            'links': [{
                'href': 'http://192.0.2.1:8004/v1/t/stacks/'
                'nested-rg1-m4zxcs4pra6t/'
                '3400bbad-a825-4226-ac23-c607846420db',
                'rel': 'stack'
            }],
            'logical_resource_id': 'nested-rg1-m4zxcs4pra6t',
            'resource_status': 'CREATE_IN_PROGRESS',
            'resource_status_reason': 'Stack CREATE started',
            'physical_resource_id': '3400bbad-a825-4226-ac23-c607846420db',
            'id': '7e521c84-cd35-4f4c-b0de-962bd3cc40a8'
        }, {
            'resource_name': '1',
            'event_time': '2016-09-05T04:10:24Z',
            'links': [{
                'href': 'http://192.0.2.1:8004/v1/t/stacks/'
                'nested-rg1-m4zxcs4pra6t/'
                '3400bbad-a825-4226-ac23-c607846420db',
                'rel': 'stack'
            }],
            'logical_resource_id': '1',
            'resource_status': 'CREATE_IN_PROGRESS',
            'resource_status_reason': 'state changed',
            'physical_resource_id': 'nested-rg1-m4zxcs4pra6t-1-z6sgpq54n6e7',
            'id': 'c6186c16-94ef-4214-a11a-7e3cc8a17f82'
        }]

        events_list = [hc_res.Resource(manager=None, info=event)
                       for event in events]

        expected = '''\
2016-09-05 04:10:24Z [nested]: \
CREATE_IN_PROGRESS  Stack CREATE started
2016-09-05 04:10:24Z [nested.rg1]: \
CREATE_IN_PROGRESS  state changed
2016-09-05 04:10:24Z [nested.rg1]: \
CREATE_IN_PROGRESS  Stack CREATE started
2016-09-05 04:10:24Z [nested.rg1.1]: \
CREATE_IN_PROGRESS  state changed'''
        self.assertEqual(expected, utils.event_log_formatter(events_list))


class ShellTestParameterFiles(testtools.TestCase):

    def test_format_parameter_file_none(self):
        """
        Assigns the first file exists.

        Args:
            self: (todo): write your description
        """
        self.assertEqual({}, utils.format_parameter_file(None))

    def test_format_parameter_file(self):
        """
        Returns a file contents of - file.

        Args:
            self: (todo): write your description
        """
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
        """
        Reads the test for a test.

        Args:
            self: (todo): write your description
        """
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
        """
        Generate a test parameters for a test.

        Args:
            self: (todo): write your description
        """
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
        """
        Sets the mock.

        Args:
            self: (todo): write your description
        """
        super(TestURLFunctions, self).setUp()
        self.m = mock.MagicMock()

        self.addCleanup(self.m.UnsetStubs)

    def test_normalise_file_path_to_url_relative(self):
        """
        Normalize the url to a file.

        Args:
            self: (todo): write your description
        """
        self.assertEqual(
            'file://%s/foo' % os.getcwd(),
            utils.normalise_file_path_to_url(
                'foo'))

    def test_normalise_file_path_to_url_absolute(self):
        """
        Normalise the absolute url to the absolute path.

        Args:
            self: (todo): write your description
        """
        self.assertEqual(
            'file:///tmp/foo',
            utils.normalise_file_path_to_url(
                '/tmp/foo'))

    def test_normalise_file_path_to_url_file(self):
        """
        Normalize the url path to a test file.

        Args:
            self: (todo): write your description
        """
        self.assertEqual(
            'file:///tmp/foo',
            utils.normalise_file_path_to_url(
                'file:///tmp/foo'))

    def test_normalise_file_path_to_url_http(self):
        """
        Normalize the url file to be normalized.

        Args:
            self: (todo): write your description
        """
        self.assertEqual(
            'http://localhost/foo',
            utils.normalise_file_path_to_url(
                'http://localhost/foo'))

    def test_get_template_url(self):
        """
        Returns the url for the template template.

        Args:
            self: (todo): write your description
        """
        tmpl_file = '/opt/stack/template.yaml'
        tmpl_url = 'file:///opt/stack/template.yaml'
        self.assertEqual(utils.get_template_url(tmpl_file, None),
                         tmpl_url)
        self.assertEqual(utils.get_template_url(None, tmpl_url),
                         tmpl_url)
        self.assertIsNone(utils.get_template_url(None, None))

    def test_base_url_for_url(self):
        """
        Set the base url.

        Args:
            self: (todo): write your description
        """
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
