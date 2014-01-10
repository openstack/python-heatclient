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

from mox3 import mox
import os
import six
import tempfile
import testtools
import yaml

from heatclient.common import template_utils
from heatclient import exc
from heatclient.openstack.common.py3kcompat import urlutils


class ShellEnvironmentTest(testtools.TestCase):

    def setUp(self):
        super(ShellEnvironmentTest, self).setUp()
        self.m = mox.Mox()

        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def collect_links(self, env, content, url, env_base_url=''):

        jenv = yaml.safe_load(env)
        fields = {
            'files': {},
            'environment': jenv
        }
        if url:
            self.m.StubOutWithMock(urlutils, 'urlopen')
            urlutils.urlopen(url).AndReturn(six.StringIO(content))
            self.m.ReplayAll()

        template_utils.resolve_environment_urls(fields, env_base_url)
        if url:
            self.assertEqual(fields['files'][url], content)

    def test_prepare_environment_file(self):
        with tempfile.NamedTemporaryFile() as env_file:
            env = '''
            resource_registry:
              "OS::Thingy": "file:///home/b/a.yaml"
            '''
            env_file.write(env)
            env_file.flush()
            env_url, env_dict = template_utils.prepare_environment(
                env_file.name)
            self.assertEqual(
                {'resource_registry': {'OS::Thingy': 'file:///home/b/a.yaml'}},
                env_dict)
            env_dir = os.path.dirname(env_file.name)
            self.assertEqual(env_url, 'file://%s' % env_dir)

    def test_prepare_environment_relative_file(self):
        with tempfile.NamedTemporaryFile() as env_file:
            env = '''
            resource_registry:
              "OS::Thingy": a.yaml
            '''
            env_file.write(env)
            env_file.flush()
            env_url, env_dict = template_utils.prepare_environment(
                env_file.name)
            self.assertEqual(
                {'resource_registry': {'OS::Thingy': 'a.yaml'}},
                env_dict)
            env_dir = os.path.dirname(env_file.name)
            self.assertEqual(env_url, 'file://%s' % env_dir)

    def test_prepare_environment_url(self):
        env = '''
        resource_registry:
            "OS::Thingy": "a.yaml"
        '''
        url = 'http://no.where/some/path/to/file.yaml'
        self.m.StubOutWithMock(urlutils, 'urlopen')
        urlutils.urlopen(url).AndReturn(six.StringIO(env))
        self.m.ReplayAll()
        env_url, env_dict = template_utils.prepare_environment(url)
        self.assertEqual({'resource_registry': {'OS::Thingy': 'a.yaml'}},
                         env_dict)
        self.assertEqual('http://no.where/some/path/to', env_url)

    def test_process_environment_and_files(self):
        env = '''
        resource_registry:
            "OS::Thingy": "a.yaml"
        '''
        url = 'http://no.where/some/path/to/file.yaml'
        a_url = 'http://no.where/some/path/to/a.yaml'
        self.m.StubOutWithMock(urlutils, 'urlopen')
        urlutils.urlopen(url).AndReturn(six.StringIO(env))
        urlutils.urlopen(a_url).AndReturn(six.StringIO("A's contents."))

        self.m.ReplayAll()
        fields = {}
        template_utils.process_environment_and_files(fields, url)
        self.assertEqual("A's contents.", fields['files'][a_url])

    def test_global_files(self):
        a = "A's contents."
        url = 'file:///home/b/a.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, a, url)

    def test_nested_files(self):
        a = "A's contents."
        url = 'file:///home/b/a.yaml'
        env = '''
        resource_registry:
          resources:
            freddy:
              "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, a, url)

    def test_http_url(self):
        a = "A's contents."
        url = 'http://no.where/container/a.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": "%s"
        ''' % url
        self.collect_links(env, a, url)

    def test_with_base_url(self):
        a = "A's contents."
        url = 'ftp://no.where/container/a.yaml'
        env = '''
        resource_registry:
          base_url: "ftp://no.where/container/"
          resources:
            server_for_me:
              "OS::Thingy": a.yaml
        '''
        self.collect_links(env, a, url)

    def test_with_built_in_provider(self):
        a = "A's contents."
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": OS::Compute::Server
        '''
        self.collect_links(env, a, None)

    def test_with_env_file_base_url_file(self):
        a = "A's contents."
        url = 'file:///tmp/foo/a.yaml'
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": a.yaml
        '''
        env_base_url = 'file:///tmp/foo'
        self.collect_links(env, a, url, env_base_url)

    def test_with_env_file_base_url_http(self):
        a = "A's contents."
        url = 'http://no.where/path/to/a.yaml'
        env = '''
        resource_registry:
          resources:
            server_for_me:
              "OS::Thingy": to/a.yaml
        '''
        env_base_url = 'http://no.where/path'
        self.collect_links(env, a, url, env_base_url)

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
