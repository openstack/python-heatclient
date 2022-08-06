# Copyright 2013 IBM Corp.
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

from unittest import mock

import testtools
from urllib import parse

from heatclient.common import utils
from heatclient.v1 import resources


class FakeAPI(object):
    """Fake API and ensure request url is correct."""

    def __init__(self, expect, key):
        self.expect = expect
        self.key = key

    def get(self, *args, **kwargs):
        assert ('GET', args[0]) == self.expect

    def json_request(self, *args, **kwargs):
        assert args == self.expect
        ret = self.key and {self.key: []} or {}
        return {}, {self.key: ret}

    def raw_request(self, *args, **kwargs):
        assert args == self.expect
        return {}

    def head(self, url, **kwargs):
        return self.json_request("HEAD", url, **kwargs)

    def post(self, url, **kwargs):
        return self.json_request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.json_request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.raw_request("DELETE", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.json_request("PATCH", url, **kwargs)


class ResourceManagerTest(testtools.TestCase):

    def _base_test(self, func, fields, expect, key):
        manager = resources.ResourceManager(FakeAPI(expect, key))

        with mock.patch.object(manager, '_resolve_stack_id') as mock_rslv, \
                mock.patch.object(utils, 'get_response_body') as mock_resp:
            mock_resp.return_value = {key: key and {key: []} or {}}
            mock_rslv.return_value = 'teststack/abcd1234'

            getattr(manager, func)(**fields)

            mock_resp.assert_called_once_with(mock.ANY)
            mock_rslv.assert_called_once_with('teststack')

    def test_get(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': 'testresource'}
        expect = ('GET',
                  '/stacks/teststack/abcd1234/resources'
                  '/testresource')
        key = 'resource'

        self._base_test('get', fields, expect, key)

    def test_get_with_attr(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': 'testresource',
                  'with_attr': ['attr_a', 'attr_b']}
        expect = ('GET',
                  '/stacks/teststack/abcd1234/resources'
                  '/testresource?with_attr=attr_a&with_attr=attr_b')
        key = 'resource'

        self._base_test('get', fields, expect, key)

    def test_get_with_unicode_resource_name(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': '\u5de5\u4f5c'}
        expect = ('GET',
                  '/stacks/teststack/abcd1234/resources'
                  '/%E5%B7%A5%E4%BD%9C')
        key = 'resource'

        self._base_test('get', fields, expect, key)

    def _test_list(self, fields, expect):
        key = 'resources'

        class FakeResponse(object):
            def json(self):
                return {key: {}}

        class FakeClient(object):
            def get(self, *args, **kwargs):
                assert args[0] == expect
                return FakeResponse()

        manager = resources.ResourceManager(FakeClient())
        manager.list(**fields)

    def test_list(self):
        self._test_list(
            fields={'stack_id': 'teststack'},
            expect='/stacks/teststack/resources')

    def test_list_nested(self):
        self._test_list(
            fields={'stack_id': 'teststack', 'nested_depth': '99'},
            expect='/stacks/teststack/resources?%s' % parse.urlencode({
                'nested_depth': 99
            }, True)
        )

    def test_list_filtering(self):
        self._test_list(
            fields={'stack_id': 'teststack', 'filters': {'name': 'rsc_1'}},
            expect='/stacks/teststack/resources?%s' % parse.urlencode({
                'name': 'rsc_1'
            }, True)
        )

    def test_list_detail(self):
        self._test_list(
            fields={'stack_id': 'teststack', 'with_detail': 'True'},
            expect='/stacks/teststack/resources?%s' % parse.urlencode({
                'with_detail': True,
            }, True)
        )

    def test_metadata(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': 'testresource'}
        expect = ('GET',
                  '/stacks/teststack/abcd1234/resources'
                  '/testresource/metadata')
        key = 'metadata'

        self._base_test('metadata', fields, expect, key)

    def test_generate_template(self):
        fields = {'resource_name': 'testresource'}
        expect = ('GET', '/resource_types/testresource/template')
        key = None

        class FakeAPI(object):
            """Fake API and ensure request url is correct."""

            def get(self, *args, **kwargs):
                assert ('GET', args[0]) == expect

            def json_request(self, *args, **kwargs):
                assert args == expect
                ret = key and {key: []} or {}
                return {}, {key: ret}

        manager = resources.ResourceManager(FakeAPI())

        with mock.patch.object(utils, 'get_response_body') as mock_resp:
            mock_resp.return_value = {key: key and {key: []} or {}}

            manager.generate_template(**fields)

            mock_resp.assert_called_once_with(mock.ANY)

    def test_signal(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': 'testresource',
                  'data': 'Some content'}
        expect = ('POST',
                  '/stacks/teststack/abcd1234/resources'
                  '/testresource/signal')
        key = 'signal'

        self._base_test('signal', fields, expect, key)

    def test_mark_unhealthy(self):
        fields = {'stack_id': 'teststack',
                  'resource_name': 'testresource',
                  'mark_unhealthy': 'True',
                  'resource_status_reason': 'Anything'}
        expect = ('PATCH',
                  '/stacks/teststack/abcd1234/resources'
                  '/testresource')
        key = 'mark_unhealthy'

        self._base_test('mark_unhealthy', fields, expect, key)


class ResourceStackNameTest(testtools.TestCase):

    def test_stack_name(self):
        resource = resources.Resource(None, {"links": [{
            "href": "http://heat.example.com:8004/foo/12/resources/foobar",
            "rel": "self"
        }, {
            "href": "http://heat.example.com:8004/foo/12",
            "rel": "stack"
        }]})
        self.assertEqual('foo', resource.stack_name)

    def test_stack_name_no_links(self):
        resource = resources.Resource(None, {})
        self.assertIsNone(resource.stack_name)
