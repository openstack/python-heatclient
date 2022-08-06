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

import json
import tempfile
from unittest import mock

import io
from oslo_serialization import base64
import testtools
from testtools import matchers
from urllib import error
import yaml

from heatclient.common import template_utils
from heatclient.common import utils
from heatclient import exc


class ShellEnvironmentTest(testtools.TestCase):

    template_a = b'{"heat_template_version": "2013-05-23"}'

    def collect_links(self, env, content, url, env_base_url=''):
        jenv = yaml.safe_load(env)
        files = {}
        if url:
            def side_effect(args):
                if url == args:
                    return io.BytesIO(content)
            with mock.patch('urllib.request.urlopen') as mock_url:
                mock_url.side_effect = side_effect
                template_utils.resolve_environment_urls(
                    jenv.get('resource_registry'), files, env_base_url)
                self.assertEqual(content.decode('utf-8'), files[url])
        else:
            template_utils.resolve_environment_urls(
                jenv.get('resource_registry'), files, env_base_url)

    @mock.patch('urllib.request.urlopen')
    def test_ignore_env_keys(self, mock_url):
        env_file = '/home/my/dir/env.yaml'
        env = b'''
        resource_registry:
          resources:
            bar:
              hooks: pre_create
              restricted_actions: replace
        '''
        mock_url.return_value = io.BytesIO(env)
        _, env_dict = template_utils.process_environment_and_files(
            env_file)
        self.assertEqual(
            {'resource_registry': {'resources': {
                'bar': {'hooks': 'pre_create',
                        'restricted_actions': 'replace'}}}},
            env_dict)
        mock_url.assert_called_with('file://%s' % env_file)

    @mock.patch('urllib.request.urlopen')
    def test_process_environment_file(self, mock_url):

        env_file = '/home/my/dir/env.yaml'
        env = b'''
        resource_registry:
          "OS::Thingy": "file:///home/b/a.yaml"
        '''
        mock_url.side_effect = [io.BytesIO(env), io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a)]

        files, env_dict = template_utils.process_environment_and_files(
            env_file)
        self.assertEqual(
            {'resource_registry': {
                'OS::Thingy': 'file:///home/b/a.yaml'}},
            env_dict)
        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/b/a.yaml'])
        mock_url.assert_has_calls([
            mock.call('file://%s' % env_file),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file:///home/b/a.yaml')
        ])

    @mock.patch('urllib.request.urlopen')
    def test_process_environment_relative_file(self, mock_url):

        env_file = '/home/my/dir/env.yaml'
        env_url = 'file:///home/my/dir/env.yaml'
        env = b'''
        resource_registry:
          "OS::Thingy": a.yaml
        '''

        mock_url.side_effect = [io.BytesIO(env), io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a)]

        self.assertEqual(
            env_url,
            utils.normalise_file_path_to_url(env_file))
        self.assertEqual(
            'file:///home/my/dir',
            utils.base_url_for_url(env_url))

        files, env_dict = template_utils.process_environment_and_files(
            env_file)

        self.assertEqual(
            {'resource_registry': {
                'OS::Thingy': 'file:///home/my/dir/a.yaml'}},
            env_dict)
        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/my/dir/a.yaml'])
        mock_url.assert_has_calls([
            mock.call(env_url),
            mock.call('file:///home/my/dir/a.yaml'),
            mock.call('file:///home/my/dir/a.yaml')
        ])

    def test_process_multiple_environment_files_container(self):

        env_list_tracker = []
        env_paths = ['/home/my/dir/env.yaml']
        files, env = template_utils.process_multiple_environments_and_files(
            env_paths, env_list_tracker=env_list_tracker,
            fetch_env_files=False)

        self.assertEqual(env_paths, env_list_tracker)
        self.assertEqual({}, files)
        self.assertEqual({}, env)

    @mock.patch('urllib.request.urlopen')
    def test_process_environment_relative_file_up(self, mock_url):

        env_file = '/home/my/dir/env.yaml'
        env_url = 'file:///home/my/dir/env.yaml'
        env = b'''
        resource_registry:
          "OS::Thingy": ../bar/a.yaml
        '''
        mock_url.side_effect = [io.BytesIO(env), io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a)]

        env_url = 'file://%s' % env_file
        self.assertEqual(
            env_url,
            utils.normalise_file_path_to_url(env_file))
        self.assertEqual(
            'file:///home/my/dir',
            utils.base_url_for_url(env_url))

        files, env_dict = template_utils.process_environment_and_files(
            env_file)

        self.assertEqual(
            {'resource_registry': {
                'OS::Thingy': 'file:///home/my/bar/a.yaml'}},
            env_dict)
        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/my/bar/a.yaml'])
        mock_url.assert_has_calls([
            mock.call(env_url),
            mock.call('file:///home/my/bar/a.yaml'),
            mock.call('file:///home/my/bar/a.yaml')
        ])

    @mock.patch('urllib.request.urlopen')
    def test_process_environment_url(self, mock_url):
        env = b'''
        resource_registry:
            "OS::Thingy": "a.yaml"
        '''
        url = 'http://no.where/some/path/to/file.yaml'
        tmpl_url = 'http://no.where/some/path/to/a.yaml'
        mock_url.side_effect = [io.BytesIO(env), io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a)]

        files, env_dict = template_utils.process_environment_and_files(
            url)

        self.assertEqual({'resource_registry': {'OS::Thingy': tmpl_url}},
                         env_dict)
        self.assertEqual(self.template_a.decode('utf-8'), files[tmpl_url])
        mock_url.assert_has_calls([
            mock.call(url),
            mock.call(tmpl_url),
            mock.call(tmpl_url)
        ])

    @mock.patch('urllib.request.urlopen')
    def test_process_environment_empty_file(self, mock_url):

        env_file = '/home/my/dir/env.yaml'
        env = b''
        mock_url.return_value = io.BytesIO(env)

        files, env_dict = template_utils.process_environment_and_files(
            env_file)

        self.assertEqual({}, env_dict)
        self.assertEqual({}, files)
        mock_url.assert_called_with('file://%s' % env_file)

    def test_no_process_environment_and_files(self):
        files, env = template_utils.process_environment_and_files()
        self.assertEqual({}, env)
        self.assertEqual({}, files)

    @mock.patch('urllib.request.urlopen')
    def test_process_multiple_environments_and_files(self, mock_url):

        env_file1 = '/home/my/dir/env1.yaml'
        env_file2 = '/home/my/dir/env2.yaml'

        env1 = b'''
        parameters:
          "param1": "value1"
        resource_registry:
          "OS::Thingy1": "file:///home/b/a.yaml"
        '''
        env2 = b'''
        parameters:
          "param2": "value2"
        resource_registry:
          "OS::Thingy2": "file:///home/b/b.yaml"
        '''

        mock_url.side_effect = [io.BytesIO(env1),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a),
                                io.BytesIO(env2),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a)]

        files, env = template_utils.process_multiple_environments_and_files(
            [env_file1, env_file2])
        self.assertEqual(
            {
                'resource_registry': {
                    'OS::Thingy1': 'file:///home/b/a.yaml',
                    'OS::Thingy2': 'file:///home/b/b.yaml'},
                'parameters': {
                    'param1': 'value1',
                    'param2': 'value2'}
            },
            env)
        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/b/a.yaml'])
        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/b/b.yaml'])
        mock_url.assert_has_calls([
            mock.call('file://%s' % env_file1),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file://%s' % env_file2),
            mock.call('file:///home/b/b.yaml'),
            mock.call('file:///home/b/b.yaml')
        ])

    @mock.patch('urllib.request.urlopen')
    def test_process_multiple_environments_default_resources(self, mock_url):

        env_file1 = '/home/my/dir/env1.yaml'
        env_file2 = '/home/my/dir/env2.yaml'

        env1 = b'''
        resource_registry:
          resources:
            resource1:
              "OS::Thingy1": "file:///home/b/a.yaml"
            resource2:
              "OS::Thingy2": "file:///home/b/b.yaml"
        '''
        env2 = b'''
        resource_registry:
          resources:
            resource1:
              "OS::Thingy3": "file:///home/b/a.yaml"
            resource2:
              "OS::Thingy4": "file:///home/b/b.yaml"
        '''
        mock_url.side_effect = [io.BytesIO(env1),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a),
                                io.BytesIO(env2),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a)]

        files, env = template_utils.process_multiple_environments_and_files(
            [env_file1, env_file2])
        self.assertEqual(
            {
                'resource_registry': {
                    'resources': {
                        'resource1': {
                            'OS::Thingy1': 'file:///home/b/a.yaml',
                            'OS::Thingy3': 'file:///home/b/a.yaml'
                        },
                        'resource2': {
                            'OS::Thingy2': 'file:///home/b/b.yaml',
                            'OS::Thingy4': 'file:///home/b/b.yaml'
                        }
                    }
                }
            },
            env)
        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/b/a.yaml'])
        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/b/b.yaml'])
        mock_url.assert_has_calls([
            mock.call('file://%s' % env_file1),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file:///home/b/b.yaml'),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file:///home/b/b.yaml'),
            mock.call('file://%s' % env_file2),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file:///home/b/b.yaml'),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file:///home/b/b.yaml'),

        ], any_order=True)

    def test_no_process_multiple_environments_and_files(self):
        files, env = template_utils.process_multiple_environments_and_files()
        self.assertEqual({}, env)
        self.assertEqual({}, files)

    def test_process_multiple_environments_and_files_from_object(self):

        env_object = 'http://no.where/path/to/env.yaml'
        env1 = b'''
        parameters:
          "param1": "value1"
        resource_registry:
          "OS::Thingy1": "b/a.yaml"
        '''

        self.object_requested = False

        def env_path_is_object(object_url):
            return True

        def object_request(method, object_url):
            self.object_requested = True
            self.assertEqual('GET', method)
            self.assertTrue(object_url.startswith("http://no.where/path/to/"))
            if object_url == env_object:
                return env1
            else:
                return self.template_a

        files, env = template_utils.process_multiple_environments_and_files(
            env_paths=[env_object], env_path_is_object=env_path_is_object,
            object_request=object_request)
        self.assertEqual(
            {
                'resource_registry': {
                    'OS::Thingy1': 'http://no.where/path/to/b/a.yaml'},
                'parameters': {'param1': 'value1'}
            },
            env)
        self.assertEqual(self.template_a.decode('utf-8'),
                         files['http://no.where/path/to/b/a.yaml'])

    @mock.patch('urllib.request.urlopen')
    def test_process_multiple_environments_and_files_tracker(self, mock_url):
        # Setup
        env_file1 = '/home/my/dir/env1.yaml'

        env1 = b'''
        parameters:
          "param1": "value1"
        resource_registry:
          "OS::Thingy1": "file:///home/b/a.yaml"
        '''
        mock_url.side_effect = [io.BytesIO(env1),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a)]

        # Test
        env_file_list = []
        files, env = template_utils.process_multiple_environments_and_files(
            [env_file1], env_list_tracker=env_file_list)

        # Verify
        expected_env = {'parameters': {'param1': 'value1'},
                        'resource_registry':
                            {'OS::Thingy1': 'file:///home/b/a.yaml'}
                        }
        self.assertEqual(expected_env, env)

        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/b/a.yaml'])

        self.assertEqual(['file:///home/my/dir/env1.yaml'], env_file_list)
        self.assertIn('file:///home/my/dir/env1.yaml', files)
        self.assertEqual(expected_env,
                         json.loads(files['file:///home/my/dir/env1.yaml']))
        mock_url.assert_has_calls([
            mock.call('file://%s' % env_file1),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file:///home/b/a.yaml'),

        ])

    @mock.patch('urllib.request.urlopen')
    def test_process_environment_relative_file_tracker(self, mock_url):

        env_file = '/home/my/dir/env.yaml'
        env_url = 'file:///home/my/dir/env.yaml'
        env = b'''
        resource_registry:
          "OS::Thingy": a.yaml
        '''
        mock_url.side_effect = [io.BytesIO(env),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a)]

        self.assertEqual(
            env_url,
            utils.normalise_file_path_to_url(env_file))
        self.assertEqual(
            'file:///home/my/dir',
            utils.base_url_for_url(env_url))

        env_file_list = []
        files, env = template_utils.process_multiple_environments_and_files(
            [env_file], env_list_tracker=env_file_list)

        # Verify
        expected_env = {'resource_registry':
                        {'OS::Thingy': 'file:///home/my/dir/a.yaml'}}
        self.assertEqual(expected_env, env)

        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/my/dir/a.yaml'])
        self.assertEqual(['file:///home/my/dir/env.yaml'], env_file_list)
        self.assertEqual(json.dumps(expected_env),
                         files['file:///home/my/dir/env.yaml'])
        mock_url.assert_has_calls([
            mock.call(env_url),
            mock.call('file:///home/my/dir/a.yaml'),
            mock.call('file:///home/my/dir/a.yaml'),

        ])

    @mock.patch('urllib.request.urlopen')
    def test_process_multiple_environments_empty_registry(self, mock_url):
        # Setup
        env_file1 = '/home/my/dir/env1.yaml'
        env_file2 = '/home/my/dir/env2.yaml'

        env1 = b'''
        resource_registry:
          "OS::Thingy1": "file:///home/b/a.yaml"
        '''
        env2 = b'''
        resource_registry:
        '''
        mock_url.side_effect = [io.BytesIO(env1),
                                io.BytesIO(self.template_a),
                                io.BytesIO(self.template_a),
                                io.BytesIO(env2)]

        # Test
        env_file_list = []
        files, env = template_utils.process_multiple_environments_and_files(
            [env_file1, env_file2], env_list_tracker=env_file_list)

        # Verify
        expected_env = {
            'resource_registry': {'OS::Thingy1': 'file:///home/b/a.yaml'}}
        self.assertEqual(expected_env, env)

        self.assertEqual(self.template_a.decode('utf-8'),
                         files['file:///home/b/a.yaml'])

        self.assertEqual(['file:///home/my/dir/env1.yaml',
                          'file:///home/my/dir/env2.yaml'], env_file_list)
        self.assertIn('file:///home/my/dir/env1.yaml', files)
        self.assertIn('file:///home/my/dir/env2.yaml', files)
        self.assertEqual(expected_env,
                         json.loads(files['file:///home/my/dir/env1.yaml']))
        mock_url.assert_has_calls([
            mock.call('file://%s' % env_file1),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file:///home/b/a.yaml'),
            mock.call('file://%s' % env_file2),

        ])

    def test_global_files(self):
        url = 'file:///home/b/a.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, self.template_a, url)

    def test_nested_files(self):
        url = 'file:///home/b/a.yaml'
        env = '''
        resource_registry:
          resources:
            freddy:
              "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, self.template_a, url)

    def test_http_url(self):
        url = 'http://no.where/container/a.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, self.template_a, url)

    def test_with_base_url(self):
        url = 'ftp://no.where/container/a.yaml'
        env = '''
        resource_registry:
          base_url: "ftp://no.where/container/"
          resources:
            server_for_me:
              "OS::Thingy": a.yaml
        '''
        self.collect_links(env, self.template_a, url)

    def test_with_built_in_provider(self):
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": OS::Compute::Server
        '''
        self.collect_links(env, self.template_a, None)

    def test_with_env_file_base_url_file(self):
        url = 'file:///tmp/foo/a.yaml'
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": a.yaml
        '''
        env_base_url = 'file:///tmp/foo'
        self.collect_links(env, self.template_a, url, env_base_url)

    def test_with_env_file_base_url_http(self):
        url = 'http://no.where/path/to/a.yaml'
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": to/a.yaml
        '''
        env_base_url = 'http://no.where/path'
        self.collect_links(env, self.template_a, url, env_base_url)

    def test_unsupported_protocol(self):
        env = '''
        resource_registry:
          "OS::Thingy": "sftp://no.where/dev/null/a.yaml"
        '''
        jenv = yaml.safe_load(env)
        fields = {'files': {}}
        self.assertRaises(exc.CommandError,
                          template_utils.get_file_contents,
                          jenv['resource_registry'],
                          fields)


class TestGetTemplateContents(testtools.TestCase):

    def test_get_template_contents_file(self):
        with tempfile.NamedTemporaryFile() as tmpl_file:
            tmpl = (b'{"AWSTemplateFormatVersion" : "2010-09-09",'
                    b' "foo": "bar"}')
            tmpl_file.write(tmpl)
            tmpl_file.flush()

            files, tmpl_parsed = template_utils.get_template_contents(
                tmpl_file.name)
            self.assertEqual({"AWSTemplateFormatVersion": "2010-09-09",
                              "foo": "bar"}, tmpl_parsed)
            self.assertEqual({}, files)

    def test_get_template_contents_file_empty(self):
        with tempfile.NamedTemporaryFile() as tmpl_file:

            ex = self.assertRaises(
                exc.CommandError,
                template_utils.get_template_contents,
                tmpl_file.name)
            self.assertEqual(
                'Could not fetch template from file://%s' % tmpl_file.name,
                str(ex))

    def test_get_template_file_nonextant(self):
        nonextant_file = '/template/dummy/file/path/and/name.yaml'
        ex = self.assertRaises(
            error.URLError,
            template_utils.get_template_contents,
            nonextant_file)
        self.assertEqual(
            "<urlopen error [Errno 2] No such file or directory: '%s'>"
            % nonextant_file,
            str(ex))

    def test_get_template_contents_file_none(self):
        ex = self.assertRaises(
            exc.CommandError,
            template_utils.get_template_contents)
        self.assertEqual(
            ('Need to specify exactly one of [--template-file, '
             '--template-url or --template-object] or --existing'),
            str(ex))

    def test_get_template_contents_file_none_existing(self):
        files, tmpl_parsed = template_utils.get_template_contents(
            existing=True)
        self.assertIsNone(tmpl_parsed)
        self.assertEqual({}, files)

    def test_get_template_contents_parse_error(self):
        with tempfile.NamedTemporaryFile() as tmpl_file:

            tmpl = b'{"foo": "bar"'
            tmpl_file.write(tmpl)
            tmpl_file.flush()

            ex = self.assertRaises(
                exc.CommandError,
                template_utils.get_template_contents,
                tmpl_file.name)
            self.assertThat(
                str(ex),
                matchers.MatchesRegex(
                    'Error parsing template file://%s ' % tmpl_file.name))

    @mock.patch('urllib.request.urlopen')
    def test_get_template_contents_url(self, mock_url):
        tmpl = b'{"AWSTemplateFormatVersion" : "2010-09-09", "foo": "bar"}'
        url = 'http://no.where/path/to/a.yaml'
        mock_url.return_value = io.BytesIO(tmpl)

        files, tmpl_parsed = template_utils.get_template_contents(
            template_url=url)
        self.assertEqual({"AWSTemplateFormatVersion": "2010-09-09",
                          "foo": "bar"}, tmpl_parsed)
        self.assertEqual({}, files)
        mock_url.assert_called_with(url)

    def test_get_template_contents_object(self):
        tmpl = '{"AWSTemplateFormatVersion" : "2010-09-09", "foo": "bar"}'
        url = 'http://no.where/path/to/a.yaml'

        self.object_requested = False

        def object_request(method, object_url):
            self.object_requested = True
            self.assertEqual('GET', method)
            self.assertEqual('http://no.where/path/to/a.yaml', object_url)
            return tmpl

        files, tmpl_parsed = template_utils.get_template_contents(
            template_object=url,
            object_request=object_request)

        self.assertEqual({"AWSTemplateFormatVersion": "2010-09-09",
                          "foo": "bar"}, tmpl_parsed)
        self.assertEqual({}, files)
        self.assertTrue(self.object_requested)

    def test_get_nested_stack_template_contents_object(self):
        tmpl = ('{"heat_template_version": "2016-04-08",'
                '"resources": {'
                '"FooBar": {'
                '"type": "foo/bar.yaml"}}}')
        url = 'http://no.where/path/to/a.yaml'

        self.object_requested = False

        def object_request(method, object_url):
            self.object_requested = True
            self.assertEqual('GET', method)
            self.assertTrue(object_url.startswith("http://no.where/path/to/"))
            if object_url == url:
                return tmpl
            else:
                return '{"heat_template_version": "2016-04-08"}'

        files, tmpl_parsed = template_utils.get_template_contents(
            template_object=url,
            object_request=object_request)

        self.assertEqual(files['http://no.where/path/to/foo/bar.yaml'],
                         '{"heat_template_version": "2016-04-08"}')
        self.assertTrue(self.object_requested)

    def check_non_utf8_content(self, filename, content):
        base_url = 'file:///tmp'
        url = '%s/%s' % (base_url, filename)
        template = {'resources':
                    {'one_init':
                     {'type': 'OS::Heat::CloudConfig',
                      'properties':
                      {'cloud_config':
                       {'write_files':
                        [{'path': '/tmp/%s' % filename,
                          'content': {'get_file': url},
                          'encoding': 'b64'}]}}}}}
        with mock.patch('urllib.request.urlopen') as mock_url:
            raw_content = base64.decode_as_bytes(content)
            response = io.BytesIO(raw_content)
            mock_url.return_value = response
            files = {}
            template_utils.resolve_template_get_files(
                template, files, base_url)
            self.assertEqual({url: content}, files)
            mock_url.assert_called_with(url)

    def test_get_zip_content(self):
        filename = 'heat.zip'
        content = b'''\
UEsDBAoAAAAAAEZZWkRbOAuBBQAAAAUAAAAIABwAaGVhdC50eHRVVAkAAxRbDVNYh\
t9SdXgLAAEE\n6AMAAATpAwAAaGVhdApQSwECHgMKAAAAAABGWVpEWzgLgQUAAAAF\
AAAACAAYAAAAAAABAAAApIEA\nAAAAaGVhdC50eHRVVAUAAxRbDVN1eAsAAQToAwA\
ABOkDAABQSwUGAAAAAAEAAQBOAAAARwAAAAAA\n'''
        # zip has '\0' in stream
        self.assertIn(b'\0', base64.decode_as_bytes(content))
        decoded_content = base64.decode_as_bytes(content)
        self.assertRaises(UnicodeDecodeError, decoded_content.decode)
        self.check_non_utf8_content(
            filename=filename, content=content)

    def test_get_utf16_content(self):
        filename = 'heat.utf16'
        content = b'//4tTkhTCgA=\n'
        # utf6 has '\0' in stream
        self.assertIn(b'\0', base64.decode_as_bytes(content))
        decoded_content = base64.decode_as_bytes(content)
        self.assertRaises(UnicodeDecodeError, decoded_content.decode)
        self.check_non_utf8_content(filename=filename, content=content)

    def test_get_gb18030_content(self):
        filename = 'heat.gb18030'
        content = b'1tDO5wo=\n'
        # gb18030 has no '\0' in stream
        self.assertNotIn('\0', base64.decode_as_bytes(content))
        decoded_content = base64.decode_as_bytes(content)
        self.assertRaises(UnicodeDecodeError, decoded_content.decode)
        self.check_non_utf8_content(filename=filename, content=content)


@mock.patch('urllib.request.urlopen')
class TestTemplateGetFileFunctions(testtools.TestCase):

    hot_template = b'''heat_template_version: 2013-05-23
resources:
  resource1:
    type: OS::type1
    properties:
      foo: {get_file: foo.yaml}
      bar:
        get_file:
          'http://localhost/bar.yaml'
  resource2:
    type: OS::type1
    properties:
      baz:
      - {get_file: baz/baz1.yaml}
      - {get_file: baz/baz2.yaml}
      - {get_file: baz/baz3.yaml}
      ignored_list: {get_file: [ignore, me]}
      ignored_dict: {get_file: {ignore: me}}
      ignored_none: {get_file: }
    '''

    def test_hot_template(self, mock_url):

        tmpl_file = '/home/my/dir/template.yaml'
        url = 'file:///home/my/dir/template.yaml'
        mock_url.side_effect = [io.BytesIO(self.hot_template),
                                io.BytesIO(b'bar contents'),
                                io.BytesIO(b'foo contents'),
                                io.BytesIO(b'baz1 contents'),
                                io.BytesIO(b'baz2 contents'),
                                io.BytesIO(b'baz3 contents')]

        files, tmpl_parsed = template_utils.get_template_contents(
            template_file=tmpl_file)

        self.assertEqual({
            'heat_template_version': '2013-05-23',
            'resources': {
                'resource1': {
                    'type': 'OS::type1',
                    'properties': {
                        'bar': {'get_file': 'http://localhost/bar.yaml'},
                        'foo': {'get_file': 'file:///home/my/dir/foo.yaml'},
                    },
                },
                'resource2': {
                    'type': 'OS::type1',
                    'properties': {
                        'baz': [
                            {'get_file': 'file:///home/my/dir/baz/baz1.yaml'},
                            {'get_file': 'file:///home/my/dir/baz/baz2.yaml'},
                            {'get_file': 'file:///home/my/dir/baz/baz3.yaml'},
                        ],
                        'ignored_list': {'get_file': ['ignore', 'me']},
                        'ignored_dict': {'get_file': {'ignore': 'me'}},
                        'ignored_none': {'get_file': None},
                    },
                }
            }
        }, tmpl_parsed)
        mock_url.assert_has_calls([
            mock.call(url),
            mock.call('http://localhost/bar.yaml'),
            mock.call('file:///home/my/dir/foo.yaml'),
            mock.call('file:///home/my/dir/baz/baz1.yaml'),
            mock.call('file:///home/my/dir/baz/baz2.yaml'),
            mock.call('file:///home/my/dir/baz/baz3.yaml')
        ], any_order=True)

    def test_hot_template_outputs(self, mock_url):
        tmpl_file = '/home/my/dir/template.yaml'
        url = 'file://%s' % tmpl_file
        foo_url = 'file:///home/my/dir/foo.yaml'
        contents = b'''
heat_template_version: 2013-05-23\n\
outputs:\n\
  contents:\n\
    value:\n\
      get_file: foo.yaml\n'''
        mock_url.side_effect = [io.BytesIO(contents),
                                io.BytesIO(b'foo contents')]
        files = template_utils.get_template_contents(
            template_file=tmpl_file)[0]
        self.assertEqual({foo_url: b'foo contents'}, files)
        mock_url.assert_has_calls([
            mock.call(url),
            mock.call(foo_url)
        ])

    def test_hot_template_same_file(self, mock_url):
        tmpl_file = '/home/my/dir/template.yaml'
        url = 'file://%s' % tmpl_file
        foo_url = 'file:///home/my/dir/foo.yaml'
        contents = b'''
heat_template_version: 2013-05-23\n
outputs:\n\
  contents:\n\
    value:\n\
      get_file: foo.yaml\n\
  template:\n\
    value:\n\
      get_file: foo.yaml\n'''
        mock_url.side_effect = [io.BytesIO(contents),
                                io.BytesIO(b'foo contents')]
        # asserts that is fetched only once even though it is
        # referenced in the template twice
        files = template_utils.get_template_contents(
            template_file=tmpl_file)[0]
        self.assertEqual({foo_url: b'foo contents'}, files)
        mock_url.assert_has_calls([
            mock.call(url),
            mock.call(foo_url)
        ])


class TestTemplateTypeFunctions(testtools.TestCase):

    hot_template = b'''heat_template_version: 2013-05-23
parameters:
  param1:
    type: string
resources:
  resource1:
    type: foo.yaml
    properties:
      foo: bar
  resource2:
    type: OS::Heat::ResourceGroup
    properties:
      resource_def:
        type: spam/egg.yaml
    '''

    foo_template = b'''heat_template_version: "2013-05-23"
parameters:
  foo:
    type: string
    '''

    egg_template = b'''heat_template_version: "2013-05-23"
parameters:
  egg:
    type: string
    '''

    @mock.patch('urllib.request.urlopen')
    def test_hot_template(self, mock_url):
        tmpl_file = '/home/my/dir/template.yaml'
        url = 'file:///home/my/dir/template.yaml'

        def side_effect(args):
            if url == args:
                return io.BytesIO(self.hot_template)
            if 'file:///home/my/dir/foo.yaml' == args:
                return io.BytesIO(self.foo_template)
            if 'file:///home/my/dir/spam/egg.yaml' == args:
                return io.BytesIO(self.egg_template)
        mock_url.side_effect = side_effect

        files, tmpl_parsed = template_utils.get_template_contents(
            template_file=tmpl_file)

        self.assertEqual(yaml.safe_load(self.foo_template.decode('utf-8')),
                         json.loads(files.get('file:///home/my/dir/foo.yaml')))

        self.assertEqual(
            yaml.safe_load(self.egg_template.decode('utf-8')),
            json.loads(files.get('file:///home/my/dir/spam/egg.yaml')))

        self.assertEqual({
            'heat_template_version': '2013-05-23',
            'parameters': {
                'param1': {
                    'type': 'string'
                }
            },
            'resources': {
                'resource1': {
                    'type': 'file:///home/my/dir/foo.yaml',
                    'properties': {'foo': 'bar'}
                },
                'resource2': {
                    'type': 'OS::Heat::ResourceGroup',
                    'properties': {
                        'resource_def': {
                            'type': 'file:///home/my/dir/spam/egg.yaml'
                        }
                    }
                }
            }
        }, tmpl_parsed)

        mock_url.assert_has_calls([
            mock.call('file:///home/my/dir/foo.yaml'),
            mock.call(url),
            mock.call('file:///home/my/dir/spam/egg.yaml'),
        ], any_order=True)


class TestTemplateInFileFunctions(testtools.TestCase):

    hot_template = b'''heat_template_version: 2013-05-23
resources:
  resource1:
    type: OS::Heat::Stack
    properties:
      template: {get_file: foo.yaml}
    '''

    foo_template = b'''heat_template_version: "2013-05-23"
resources:
  foo:
    type: OS::Type1
    properties:
      config: {get_file: bar.yaml}
    '''

    bar_template = b'''heat_template_version: "2013-05-23"
parameters:
  bar:
    type: string
    '''

    @mock.patch('urllib.request.urlopen')
    def test_hot_template(self, mock_url):
        tmpl_file = '/home/my/dir/template.yaml'
        url = 'file:///home/my/dir/template.yaml'
        foo_url = 'file:///home/my/dir/foo.yaml'
        bar_url = 'file:///home/my/dir/bar.yaml'

        def side_effect(args):
            if url == args:
                return io.BytesIO(self.hot_template)
            if foo_url == args:
                return io.BytesIO(self.foo_template)
            if bar_url == args:
                return io.BytesIO(self.bar_template)
        mock_url.side_effect = side_effect

        files, tmpl_parsed = template_utils.get_template_contents(
            template_file=tmpl_file)

        self.assertEqual(yaml.safe_load(self.bar_template.decode('utf-8')),
                         json.loads(files.get('file:///home/my/dir/bar.yaml')))

        self.assertEqual({
            'heat_template_version': '2013-05-23',
            'resources': {
                'foo': {
                    'type': 'OS::Type1',
                    'properties': {
                        'config': {
                            'get_file': 'file:///home/my/dir/bar.yaml'
                        }
                    }
                }
            }
        }, json.loads(files.get('file:///home/my/dir/foo.yaml')))

        self.assertEqual({
            'heat_template_version': '2013-05-23',
            'resources': {
                'resource1': {
                    'type': 'OS::Heat::Stack',
                    'properties': {
                        'template': {
                            'get_file': 'file:///home/my/dir/foo.yaml'
                        }
                    }
                }
            }
        }, tmpl_parsed)

        mock_url.assert_has_calls([
            mock.call(foo_url),
            mock.call(url),
            mock.call(bar_url),
        ], any_order=True)


class TestNestedIncludes(testtools.TestCase):

    hot_template = b'''heat_template_version: 2013-05-23
parameters:
  param1:
    type: string
resources:
  resource1:
    type: foo.yaml
    properties:
      foo: bar
  resource2:
    type: OS::Heat::ResourceGroup
    properties:
      resource_def:
        type: spam/egg.yaml
      with: {get_file: spam/ham.yaml}
    '''

    egg_template = b'''heat_template_version: 2013-05-23
parameters:
  param1:
    type: string
resources:
  resource1:
    type: one.yaml
    properties:
      foo: bar
  resource2:
    type: OS::Heat::ResourceGroup
    properties:
      resource_def:
        type: two.yaml
      with: {get_file: three.yaml}
    '''

    foo_template = b'''heat_template_version: "2013-05-23"
parameters:
  foo:
    type: string
    '''

    @mock.patch('urllib.request.urlopen')
    def test_env_nested_includes(self, mock_url):
        env_file = '/home/my/dir/env.yaml'
        env_url = 'file:///home/my/dir/env.yaml'
        env = b'''
        resource_registry:
          "OS::Thingy": template.yaml
        '''
        template_url = 'file:///home/my/dir/template.yaml'
        foo_url = 'file:///home/my/dir/foo.yaml'
        egg_url = 'file:///home/my/dir/spam/egg.yaml'
        ham_url = 'file:///home/my/dir/spam/ham.yaml'
        one_url = 'file:///home/my/dir/spam/one.yaml'
        two_url = 'file:///home/my/dir/spam/two.yaml'
        three_url = 'file:///home/my/dir/spam/three.yaml'

        def side_effect(args):
            if env_url == args:
                return io.BytesIO(env)
            if template_url == args:
                return io.BytesIO(self.hot_template)
            if foo_url == args:
                return io.BytesIO(self.foo_template)
            if egg_url == args:
                return io.BytesIO(self.egg_template)
            if ham_url == args:
                return io.BytesIO(b'ham contents')
            if one_url == args:
                return io.BytesIO(self.foo_template)
            if two_url == args:
                return io.BytesIO(self.foo_template)
            if three_url == args:
                return io.BytesIO(b'three contents')
        mock_url.side_effect = side_effect

        files, env_dict = template_utils.process_environment_and_files(
            env_file)

        self.assertEqual(
            {'resource_registry': {
                'OS::Thingy': template_url}},
            env_dict)

        self.assertEqual({
            'heat_template_version': '2013-05-23',
            'parameters': {'param1': {'type': 'string'}},
            'resources': {
                'resource1': {
                    'properties': {'foo': 'bar'},
                    'type': foo_url
                },
                'resource2': {
                    'type': 'OS::Heat::ResourceGroup',
                    'properties': {
                        'resource_def': {
                            'type': egg_url},
                        'with': {'get_file': ham_url}
                    }
                }
            }
        }, json.loads(files.get(template_url)))

        self.assertEqual(yaml.safe_load(self.foo_template.decode('utf-8')),
                         json.loads(files.get(foo_url)))
        self.assertEqual({
            'heat_template_version': '2013-05-23',
            'parameters': {'param1': {'type': 'string'}},
            'resources': {
                'resource1': {
                    'properties': {'foo': 'bar'},
                    'type': one_url},
                'resource2': {
                    'type': 'OS::Heat::ResourceGroup',
                    'properties': {
                        'resource_def': {'type': two_url},
                        'with': {'get_file': three_url}
                    }
                }
            }
        }, json.loads(files.get(egg_url)))
        self.assertEqual(b'ham contents',
                         files.get(ham_url))
        self.assertEqual(yaml.safe_load(self.foo_template.decode('utf-8')),
                         json.loads(files.get(one_url)))
        self.assertEqual(yaml.safe_load(self.foo_template.decode('utf-8')),
                         json.loads(files.get(two_url)))
        self.assertEqual(b'three contents',
                         files.get(three_url))
        mock_url.assert_has_calls([
            mock.call(env_url),
            mock.call(template_url),
            mock.call(foo_url),
            mock.call(egg_url),
            mock.call(ham_url),
            mock.call(one_url),
            mock.call(two_url),
            mock.call(three_url),
        ], any_order=True)
