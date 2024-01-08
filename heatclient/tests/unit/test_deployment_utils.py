# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import mock

import swiftclient.client
import testscenarios
import testtools
from testtools import matchers
import time

from heatclient.common import deployment_utils
from heatclient import exc
from heatclient.v1 import software_configs


load_tests = testscenarios.load_tests_apply_scenarios


def mock_sc(group=None, config=None, options=None,
            inputs=None, outputs=None):
    return software_configs.SoftwareConfig(None, {
        'group': group,
        'config': config,
        'options': options or {},
        'inputs': inputs or [],
        'outputs': outputs or [],
    }, True)


class DerivedConfigTest(testtools.TestCase):

    scenarios = [
        ('defaults', dict(
            action='UPDATE',
            source=mock_sc(),
            name='s1',
            input_values=None,
            server_id='1234',
            signal_transport='NO_SIGNAL',
            signal_id=None,
            result={
                'config': '',
                'group': 'Heat::Ungrouped',
                'inputs': [{
                    'description': 'ID of the server being deployed to',
                    'name': 'deploy_server_id',
                    'type': 'String',
                    'value': '1234'
                }, {
                    'description': 'Name of the current action '
                    'being deployed',
                    'name': 'deploy_action',
                    'type': 'String',
                    'value': 'UPDATE'
                }, {
                    'description': 'How the server should signal to '
                    'heat with the deployment output values.',
                    'name': 'deploy_signal_transport',
                    'type': 'String',
                    'value': 'NO_SIGNAL'}],
                'name': 's1',
                'options': {},
                'outputs': []})),
        ('defaults_empty', dict(
            action='UPDATE',
            source={},
            name='s1',
            input_values=None,
            server_id='1234',
            signal_transport='NO_SIGNAL',
            signal_id=None,
            result={
                'config': '',
                'group': 'Heat::Ungrouped',
                'inputs': [{
                    'description': 'ID of the server being deployed to',
                    'name': 'deploy_server_id',
                    'type': 'String',
                    'value': '1234'
                }, {
                    'description': 'Name of the current action '
                    'being deployed',
                    'name': 'deploy_action',
                    'type': 'String',
                    'value': 'UPDATE'
                }, {
                    'description': 'How the server should signal to '
                    'heat with the deployment output values.',
                    'name': 'deploy_signal_transport',
                    'type': 'String',
                    'value': 'NO_SIGNAL'}],
                'name': 's1',
                'options': {},
                'outputs': []})),

        ('config_values', dict(
            action='UPDATE',
            source=mock_sc(
                group='puppet',
                config='do the foo',
                inputs=[
                    {'name': 'one', 'default': '1'},
                    {'name': 'two'}],
                options={'option1': 'value'},
                outputs=[
                    {'name': 'output1'},
                    {'name': 'output2'}],
            ),
            name='s2',
            input_values={'one': 'foo', 'two': 'bar', 'three': 'baz'},
            server_id='1234',
            signal_transport='NO_SIGNAL',
            signal_id=None,
            result={
                'config': 'do the foo',
                'group': 'puppet',
                'inputs': [{
                    'name': 'one',
                    'default': '1',
                    'value': 'foo'
                }, {
                    'name': 'two',
                    'value': 'bar'
                }, {
                    'name': 'three',
                    'type': 'String',
                    'value': 'baz'
                }, {
                    'description': 'ID of the server being deployed to',
                    'name': 'deploy_server_id',
                    'type': 'String',
                    'value': '1234'
                }, {
                    'description': 'Name of the current action '
                    'being deployed',
                    'name': 'deploy_action',
                    'type': 'String',
                    'value': 'UPDATE'
                }, {
                    'description': 'How the server should signal to '
                    'heat with the deployment output values.',
                    'name': 'deploy_signal_transport',
                    'type': 'String',
                    'value': 'NO_SIGNAL'
                }],
                'name': 's2',
                'options': {'option1': 'value'},
                'outputs': [
                    {'name': 'output1'},
                    {'name': 'output2'}]})),
        ('temp_url', dict(
            action='UPDATE',
            source=mock_sc(),
            name='s1',
            input_values=None,
            server_id='1234',
            signal_transport='TEMP_URL_SIGNAL',
            signal_id='http://192.0.2.1:8080/foo',
            result={
                'config': '',
                'group': 'Heat::Ungrouped',
                'inputs': [{
                    'description': 'ID of the server being deployed to',
                    'name': 'deploy_server_id',
                    'type': 'String',
                    'value': '1234'
                }, {
                    'description': 'Name of the current action '
                    'being deployed',
                    'name': 'deploy_action',
                    'type': 'String',
                    'value': 'UPDATE'
                }, {
                    'description': 'How the server should signal to '
                    'heat with the deployment output values.',
                    'name': 'deploy_signal_transport',
                    'type': 'String',
                    'value': 'TEMP_URL_SIGNAL'
                }, {
                    'description': 'ID of signal to use for signaling '
                    'output values',
                    'name': 'deploy_signal_id',
                    'type': 'String',
                    'value': 'http://192.0.2.1:8080/foo'
                }, {
                    'description': 'HTTP verb to use for signaling '
                    'output values',
                    'name': 'deploy_signal_verb',
                    'type': 'String',
                    'value': 'PUT'}],
                'name': 's1',
                'options': {},
                'outputs': []})),
        ('unsupported', dict(
            action='UPDATE',
            source=mock_sc(),
            name='s1',
            input_values=None,
            server_id='1234',
            signal_transport='ASDF',
            signal_id=None,
            result_error=exc.CommandError,
            result_error_msg='Unsupported signal transport ASDF',
            result=None)),
    ]

    def test_build_derived_config_params(self):
        try:
            self.assertEqual(
                self.result,
                deployment_utils.build_derived_config_params(
                    action=self.action,
                    source=self.source,
                    name=self.name,
                    input_values=self.input_values,
                    server_id=self.server_id,
                    signal_transport=self.signal_transport,
                    signal_id=self.signal_id))
        except Exception as e:
            if not self.result_error:
                raise e
            self.assertIsInstance(e, self.result_error)
            self.assertEqual(self.result_error_msg, str(e))


class TempURLSignalTest(testtools.TestCase):

    @mock.patch.object(swiftclient.client, 'Connection')
    def test_create_swift_client(self, sc_conn):
        auth = mock.MagicMock()
        auth.get_token.return_value = '1234'
        auth.get_endpoint.return_value = 'http://192.0.2.1:8080'

        session = mock.MagicMock()

        args = mock.MagicMock()
        args.os_region_name = 'Region1'
        args.os_project_name = 'project'
        args.os_username = 'user'
        args.os_cacert = None
        args.insecure = True

        sc_conn.return_value = mock.MagicMock()

        sc = deployment_utils.create_swift_client(auth, session, args)

        self.assertEqual(sc_conn.return_value, sc)

        self.assertEqual(
            mock.call(session),
            auth.get_token.call_args)

        self.assertEqual(
            mock.call(
                session,
                service_type='object-store',
                region_name='Region1'),
            auth.get_endpoint.call_args)

        self.assertEqual(
            mock.call(
                cacert=None,
                insecure=True,
                key=None,
                tenant_name='project',
                preauthtoken='1234',
                authurl=None,
                user='user',
                preauthurl='http://192.0.2.1:8080',
                auth_version='2.0'),
            sc_conn.call_args)

    def test_create_temp_url(self):
        swift_client = mock.MagicMock()
        swift_client.url = ("http://fake-host.com:8080/v1/AUTH_demo")
        swift_client.head_account = mock.Mock(return_value={
            'x-account-meta-temp-url-key': '123456'})
        swift_client.post_account = mock.Mock()

        uuid_pattern = ('[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB]'
                        '[a-f0-9]{3}-[a-f0-9]{12}')
        url = deployment_utils.create_temp_url(swift_client, 'bar', 60)
        self.assertFalse(swift_client.post_account.called)
        regexp = (r"http://fake-host.com:8080/v1/AUTH_demo/bar-%s"
                  r"/%s\?temp_url_sig=[0-9a-f]{40,64}&"
                  r"temp_url_expires=[0-9]{10}" % (uuid_pattern, uuid_pattern))
        self.assertThat(url, matchers.MatchesRegex(regexp))

        timeout = int(url.split('=')[-1])
        self.assertTrue(timeout < time.time() + 2*365*24*60*60)

    def test_get_temp_url_no_account_key(self):
        swift_client = mock.MagicMock()
        swift_client.url = ("http://fake-host.com:8080/v1/AUTH_demo")
        head_account = {}

        def post_account(data):
            head_account.update(data)

        swift_client.head_account = mock.Mock(return_value=head_account)
        swift_client.post_account = post_account

        self.assertNotIn('x-account-meta-temp-url-key', head_account)
        deployment_utils.create_temp_url(swift_client, 'bar', 60, 'foo')
        self.assertIn('x-account-meta-temp-url-key', head_account)

    def test_build_signal_id_no_signal(self):
        hc = mock.MagicMock()
        args = mock.MagicMock()
        args.signal_transport = 'NO_SIGNAL'
        self.assertIsNone(deployment_utils.build_signal_id(hc, args))

    def test_build_signal_id_no_client_auth(self):
        hc = mock.MagicMock()
        args = mock.MagicMock()
        args.os_no_client_auth = True
        args.signal_transport = 'TEMP_URL_SIGNAL'
        e = self.assertRaises(exc.CommandError,
                              deployment_utils.build_signal_id, hc, args)
        self.assertEqual((
            'Cannot use --os-no-client-auth, auth required to create '
            'a Swift TempURL.'),
            str(e))

    @mock.patch.object(deployment_utils, 'create_temp_url')
    @mock.patch.object(deployment_utils, 'create_swift_client')
    def test_build_signal_id(self, csc, ctu):
        hc = mock.MagicMock()
        args = mock.MagicMock()
        args.name = 'foo'
        args.timeout = 60
        args.os_no_client_auth = False
        args.signal_transport = 'TEMP_URL_SIGNAL'
        csc.return_value = mock.MagicMock()
        temp_url = (
            'http://fake-host.com:8080/v1/AUTH_demo/foo/'
            'a81a74d5-c395-4269-9670-ddd0824fd696'
            '?temp_url_sig=6a68371d602c7a14aaaa9e3b3a63b8b85bd9a503'
            '&temp_url_expires=1425270977')
        ctu.return_value = temp_url

        self.assertEqual(
            temp_url, deployment_utils.build_signal_id(hc, args))
        self.assertEqual(
            mock.call(hc.http_client.auth, hc.http_client.session, args),
            csc.call_args)
        self.assertEqual(
            mock.call(csc.return_value, 'foo', 60),
            ctu.call_args)
