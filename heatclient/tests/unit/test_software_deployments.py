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
from heatclient.v1 import software_deployments


class SoftwareDeploymentTest(testtools.TestCase):

    def setUp(self):
        super(SoftwareDeploymentTest, self).setUp()
        deployment_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        self.deployment = software_deployments.SoftwareDeployment(
            mock.MagicMock(), info={'id': deployment_id})
        self.deployment_id = deployment_id

    def test_delete(self):
        self.deployment.manager.delete.return_value = None
        self.assertIsNone(self.deployment.delete())
        kwargs = self.deployment.manager.delete.call_args[1]
        self.assertEqual(self.deployment_id, kwargs['deployment_id'])

    def test_update(self):
        self.assertEqual(
            "<SoftwareDeployment {'id': '%s'}>" % self.deployment_id,
            str(self.deployment))
        self.deployment.manager.update.return_value = None
        config_id = 'd00ba4aa-db33-42e1-92f4-2a6469260107'
        self.assertIsNone(self.deployment.update(config_id=config_id))
        kwargs = self.deployment.manager.update.call_args[1]
        self.assertEqual(self.deployment_id, kwargs['deployment_id'])
        self.assertEqual(config_id, kwargs['config_id'])


class SoftwareDeploymentManagerTest(testtools.TestCase):

    def setUp(self):
        super(SoftwareDeploymentManagerTest, self).setUp()
        self.manager = software_deployments.SoftwareDeploymentManager(
            mock.MagicMock())

    def test_list(self):
        server_id = 'fc01f89f-e151-4dc5-9c28-543c0d20ed6a'
        self.manager.client.json_request.return_value = (
            {},
            {'software_deployments': []})
        result = self.manager.list(server_id=server_id)
        self.assertEqual([], result)
        call_args = self.manager.client.get.call_args
        self.assertEqual(
            ('/software_deployments?server_id=%s' % server_id,),
            *call_args)

    @mock.patch.object(utils, 'get_response_body')
    def test_metadata(self, mock_utils):
        server_id = 'fc01f89f-e151-4dc5-9c28-543c0d20ed6a'
        metadata = {
            'group1': [{'foo': 'bar'}],
            'group2': [{'foo': 'bar'}, {'bar': 'baz'}],
        }
        self.manager.client.get.return_value = {}
        mock_utils.return_value = {'metadata': metadata}
        result = self.manager.metadata(server_id=server_id)
        self.assertEqual(metadata, result)
        call_args = self.manager.client.get.call_args
        self.assertEqual(
            '/software_deployments/metadata/%s' % server_id,
            call_args[0][0])

    @mock.patch.object(utils, 'get_response_body')
    def test_get(self, mock_utils):
        deployment_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        config_id = 'd00ba4aa-db33-42e1-92f4-2a6469260107'
        server_id = 'fb322564-7927-473d-8aad-68ae7fbf2abf'
        data = {
            'id': deployment_id,
            'server_id': server_id,
            'input_values': {},
            'output_values': {},
            'action': 'INIT',
            'status': 'COMPLETE',
            'status_reason': None,
            'signal_id': None,
            'config_id': config_id,
            'config': '#!/bin/bash',
            'name': 'config_mysql',
            'group': 'Heat::Shell',
            'inputs': [],
            'outputs': [],
            'options': []}

        self.manager.client.get.return_value = {}
        mock_utils.return_value = {'software_deployment': data}
        result = self.manager.get(deployment_id=deployment_id)
        self.assertEqual(software_deployments.SoftwareDeployment(
            self.manager, data), result)
        call_args = self.manager.client.get.call_args
        self.assertEqual(
            ('/software_deployments/%s' % deployment_id,), *call_args)

    @mock.patch.object(utils, 'get_response_body')
    def test_create(self, mock_utils):
        deployment_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        config_id = 'd00ba4aa-db33-42e1-92f4-2a6469260107'
        server_id = 'fb322564-7927-473d-8aad-68ae7fbf2abf'
        body = {
            'server_id': server_id,
            'input_values': {},
            'action': 'INIT',
            'status': 'COMPLETE',
            'status_reason': None,
            'signal_id': None,
            'config_id': config_id}
        data = body.copy()
        data['id'] = deployment_id
        self.manager.client.post.return_value = {}
        mock_utils.return_value = {'software_deployment': data}
        result = self.manager.create(**body)
        self.assertEqual(software_deployments.SoftwareDeployment(
            self.manager, data), result)
        args, kwargs = self.manager.client.post.call_args
        self.assertEqual('/software_deployments', args[0])
        self.assertEqual({'data': body}, kwargs)

    def test_delete(self):
        deployment_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        self.manager.delete(deployment_id)
        call_args = self.manager.client.delete.call_args
        self.assertEqual(
            ('/software_deployments/%s' % deployment_id,), *call_args)

    @mock.patch.object(utils, 'get_response_body')
    def test_update(self, mock_utils):
        deployment_id = 'bca6871d-86c0-4aff-b792-58a1f6947b57'
        config_id = 'd00ba4aa-db33-42e1-92f4-2a6469260107'
        server_id = 'fb322564-7927-473d-8aad-68ae7fbf2abf'
        body = {
            'server_id': server_id,
            'input_values': {},
            'action': 'DEPLOYED',
            'status': 'COMPLETE',
            'status_reason': None,
            'signal_id': None,
            'config_id': config_id}
        data = body.copy()
        data['id'] = deployment_id
        self.manager.client.put.return_value = {}
        mock_utils.return_value = {'software_deployment': data}
        result = self.manager.update(deployment_id, **body)
        self.assertEqual(software_deployments.SoftwareDeployment(
            self.manager, data), result)
        args, kwargs = self.manager.client.put.call_args
        self.assertEqual('/software_deployments/%s' % deployment_id, args[0])
        self.assertEqual({'data': body}, kwargs)
