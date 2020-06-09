# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

import testtools

from heatclient.common import utils
from heatclient.v1 import software_configs


class SoftwareConfigTest(testtools.TestCase):

    def setUp(self):
        super(SoftwareConfigTest, self).setUp()
        config_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        self.config = software_configs.SoftwareConfig(mock.MagicMock(),
                                                      info={'id': config_id})
        self.config_id = config_id

    def test_delete(self):
        self.config.manager.delete.return_value = None
        self.assertIsNone(self.config.delete())
        kwargs = self.config.manager.delete.call_args[1]
        self.assertEqual(self.config_id, kwargs['config_id'])

    def test_data(self):
        self.assertEqual(
            "<SoftwareConfig {'id': '%s'}>" % self.config_id, str(self.config))
        self.config.manager.data.return_value = None
        self.config.data(name='config_mysql')
        kwargs = self.config.manager.data.call_args[1]
        self.assertEqual('config_mysql', kwargs['name'])


class SoftwareConfigManagerTest(testtools.TestCase):

    def setUp(self):
        super(SoftwareConfigManagerTest, self).setUp()
        self.manager = software_configs.SoftwareConfigManager(mock.MagicMock())

    def test_list(self):
        config_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        self.manager.client.json_request.return_value = (
            {},
            {'software_configs': []})
        result = self.manager.list(limit=1, marker=config_id)
        self.assertEqual([], result)
        call_args = self.manager.client.get.call_args
        self.assertEqual(
            ('/software_configs?limit=1&marker=%s' % config_id,), *call_args)

    @mock.patch.object(utils, 'get_response_body')
    def test_get(self, mock_body):
        config_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        data = {
            'id': config_id,
            'name': 'config_mysql',
            'group': 'Heat::Shell',
            'config': '#!/bin/bash',
            'inputs': [],
            'ouputs': [],
            'options': []}

        self.manager.client.json_request.return_value = (
            {}, {'software_config': data})
        mock_body.return_value = {'software_config': data}
        result = self.manager.get(config_id=config_id)
        self.assertEqual(software_configs.SoftwareConfig(self.manager, data),
                         result)
        call_args = self.manager.client.get.call_args
        self.assertEqual(
            ('/software_configs/%s' % config_id,), *call_args)

    @mock.patch.object(utils, 'get_response_body')
    def test_create(self, mock_body):
        config_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        body = {
            'name': 'config_mysql',
            'group': 'Heat::Shell',
            'config': '#!/bin/bash',
            'inputs': [],
            'ouputs': [],
            'options': []}
        data = body.copy()
        data['id'] = config_id
        self.manager.client.json_request.return_value = (
            {}, {'software_config': data})
        mock_body.return_value = {'software_config': data}
        result = self.manager.create(**body)
        self.assertEqual(software_configs.SoftwareConfig(self.manager, data),
                         result)
        args, kargs = self.manager.client.post.call_args
        self.assertEqual('/software_configs', args[0])
        self.assertEqual({'data': body}, kargs)

    def test_delete(self):
        config_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        self.manager.delete(config_id)
        call_args = self.manager.client.delete.call_args
        self.assertEqual(
            ('/software_configs/%s' % config_id,), *call_args)
