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
from testtools.matchers import MatchesRegex
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
        files = {}
        if url:
            self.m.StubOutWithMock(urlutils, 'urlopen')
            urlutils.urlopen(url).AndReturn(six.StringIO(content))
            self.m.ReplayAll()

        template_utils.resolve_environment_urls(
            jenv.get('resource_registry'), files, env_base_url)
        if url:
            self.assertEqual(files[url], content)

    def test_process_environment_file(self):

        self.m.StubOutWithMock(urlutils, 'urlopen')
        env_file = '/home/my/dir/env.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": "file:///home/b/a.yaml"
        '''
        tmpl = '{"foo": "bar"}'

        urlutils.urlopen('file://%s' % env_file).AndReturn(
            six.StringIO(env))
        urlutils.urlopen('file:///home/b/a.yaml').AndReturn(
            six.StringIO(tmpl))
        self.m.ReplayAll()

        files, env_dict = template_utils.process_environment_and_files(
            env_file)
        self.assertEqual(
            {'resource_registry': {
                'OS::Thingy': 'file:///home/b/a.yaml'}},
            env_dict)
        self.assertEqual('{"foo": "bar"}', files['file:///home/b/a.yaml'])

    def test_process_environment_relative_file(self):

        self.m.StubOutWithMock(urlutils, 'urlopen')
        env_file = '/home/my/dir/env.yaml'
        env_url = 'file:///home/my/dir/env.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": a.yaml
        '''
        tmpl = '{"foo": "bar"}'

        urlutils.urlopen(env_url).AndReturn(
            six.StringIO(env))
        urlutils.urlopen('file:///home/my/dir/a.yaml').AndReturn(
            six.StringIO(tmpl))
        self.m.ReplayAll()

        self.assertEqual(
            env_url,
            template_utils.normalise_file_path_to_url(env_file))
        self.assertEqual(
            'file:///home/my/dir',
            template_utils.base_url_for_url(env_url))

        files, env_dict = template_utils.process_environment_and_files(
            env_file)

        self.assertEqual(
            {'resource_registry': {
                'OS::Thingy': 'file:///home/my/dir/a.yaml'}},
            env_dict)
        self.assertEqual(
            '{"foo": "bar"}', files['file:///home/my/dir/a.yaml'])

    def test_process_environment_relative_file_up(self):

        self.m.StubOutWithMock(urlutils, 'urlopen')
        env_file = '/home/my/dir/env.yaml'
        env_url = 'file:///home/my/dir/env.yaml'
        env = '''
        resource_registry:
          "OS::Thingy": ../bar/a.yaml
        '''
        tmpl = '{"foo": "bar"}'

        urlutils.urlopen(env_url).AndReturn(
            six.StringIO(env))
        urlutils.urlopen('file:///home/my/bar/a.yaml').AndReturn(
            six.StringIO(tmpl))
        self.m.ReplayAll()

        env_url = 'file://%s' % env_file
        self.assertEqual(
            env_url,
            template_utils.normalise_file_path_to_url(env_file))
        self.assertEqual(
            'file:///home/my/dir',
            template_utils.base_url_for_url(env_url))

        files, env_dict = template_utils.process_environment_and_files(
            env_file)

        self.assertEqual(
            {'resource_registry': {
                'OS::Thingy': 'file:///home/my/bar/a.yaml'}},
            env_dict)
        self.assertEqual(
            '{"foo": "bar"}', files['file:///home/my/bar/a.yaml'])

    def test_process_environment_url(self):
        env = '''
        resource_registry:
            "OS::Thingy": "a.yaml"
        '''
        url = 'http://no.where/some/path/to/file.yaml'
        tmpl_url = 'http://no.where/some/path/to/a.yaml'
        tmpl = '{"foo": "bar"}'

        self.m.StubOutWithMock(urlutils, 'urlopen')
        urlutils.urlopen(url).AndReturn(six.StringIO(env))
        urlutils.urlopen(tmpl_url).AndReturn(six.StringIO(tmpl))
        self.m.ReplayAll()

        files, env_dict = template_utils.process_environment_and_files(
            url)

        self.assertEqual({'resource_registry': {'OS::Thingy': tmpl_url}},
                         env_dict)
        self.assertEqual(tmpl, files[tmpl_url])

    def test_process_environment_empty_file(self):

        self.m.StubOutWithMock(urlutils, 'urlopen')
        env_file = '/home/my/dir/env.yaml'
        env = ''

        urlutils.urlopen('file://%s' % env_file).AndReturn(six.StringIO(env))
        self.m.ReplayAll()

        files, env_dict = template_utils.process_environment_and_files(
            env_file)

        self.assertEqual({}, env_dict)
        self.assertEqual({}, files)

    def test_no_process_environment_and_files(self):
        files, env = template_utils.process_environment_and_files()
        self.assertEqual({}, env)
        self.assertEqual({}, files)

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


class TestGetTemplateContents(testtools.TestCase):

    def setUp(self):
        super(TestGetTemplateContents, self).setUp()
        self.m = mox.Mox()

        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def test_get_template_contents_file(self):
        with tempfile.NamedTemporaryFile() as tmpl_file:
            tmpl = b'{"foo": "bar"}'
            tmpl_file.write(tmpl)
            tmpl_file.flush()

            files, tmpl_parsed = template_utils.get_template_contents(
                tmpl_file.name)
            self.assertEqual({"foo": "bar"}, tmpl_parsed)
            self.assertEqual({}, files)

    def test_get_template_contents_file_empty(self):
        with tempfile.NamedTemporaryFile() as tmpl_file:

            ex = self.assertRaises(
                exc.CommandError,
                template_utils.get_template_contents,
                tmpl_file.name)
            self.assertEqual(
                str(ex),
                'Could not fetch template from file://%s' % tmpl_file.name)

    def test_get_template_contents_file_none(self):
        ex = self.assertRaises(
            exc.CommandError,
            template_utils.get_template_contents)
        self.assertEqual(
            str(ex),
            ('Need to specify exactly one of --template-file, '
             '--template-url or --template-object'))

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
                MatchesRegex(
                    'Error parsing template file://%s ' % tmpl_file.name))

    def test_get_template_contents_url(self):
        tmpl = '{"foo": "bar"}'
        url = 'http://no.where/path/to/a.yaml'
        self.m.StubOutWithMock(urlutils, 'urlopen')
        urlutils.urlopen(url).AndReturn(six.StringIO(tmpl))
        self.m.ReplayAll()

        files, tmpl_parsed = template_utils.get_template_contents(
            template_url=url)
        self.assertEqual({"foo": "bar"}, tmpl_parsed)
        self.assertEqual({}, files)

    def test_get_template_contents_object(self):
        tmpl = '{"foo": "bar"}'
        url = 'http://no.where/path/to/a.yaml'
        self.m.ReplayAll()

        self.object_requested = False

        def object_request(method, object_url):
            self.object_requested = True
            self.assertEqual('GET', method)
            self.assertEqual('http://no.where/path/to/a.yaml', object_url)
            return tmpl

        files, tmpl_parsed = template_utils.get_template_contents(
            template_object=url,
            object_request=object_request)

        self.assertEqual({"foo": "bar"}, tmpl_parsed)
        self.assertEqual({}, files)
        self.assertTrue(self.object_requested)


class TestTemplateGetFileFunctions(testtools.TestCase):

    hot_template = '''heat_template_version: 2013-05-23
resources:
  resource1:
    type: type1
    properties:
      foo: {get_file: foo.yaml}
      bar:
        get_file:
          'http://localhost/bar.yaml'
  resource2:
    type: type1
    properties:
      baz:
      - {get_file: baz/baz1.yaml}
      - {get_file: baz/baz2.yaml}
      - {get_file: baz/baz3.yaml}
      ignored_list: {get_file: [ignore, me]}
      ignored_dict: {get_file: {ignore: me}}
      ignored_none: {get_file: }
    '''

    def setUp(self):
        super(TestTemplateGetFileFunctions, self).setUp()
        self.m = mox.Mox()

        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def test_hot_template(self):
        self.m.StubOutWithMock(urlutils, 'urlopen')

        tmpl_file = '/home/my/dir/template.yaml'
        url = 'file:///home/my/dir/template.yaml'
        urlutils.urlopen(url).AndReturn(
            six.StringIO(self.hot_template))
        urlutils.urlopen(
            'http://localhost/bar.yaml').InAnyOrder().AndReturn(
                six.StringIO('bar contents'))
        urlutils.urlopen(
            'file:///home/my/dir/foo.yaml').InAnyOrder().AndReturn(
                six.StringIO('foo contents'))
        urlutils.urlopen(
            'file:///home/my/dir/baz/baz1.yaml').InAnyOrder().AndReturn(
                six.StringIO('baz1 contents'))
        urlutils.urlopen(
            'file:///home/my/dir/baz/baz2.yaml').InAnyOrder().AndReturn(
                six.StringIO('baz2 contents'))
        urlutils.urlopen(
            'file:///home/my/dir/baz/baz3.yaml').InAnyOrder().AndReturn(
                six.StringIO('baz3 contents'))

        self.m.ReplayAll()

        files, tmpl_parsed = template_utils.get_template_contents(
            template_file=tmpl_file)

        self.assertEqual({
            'http://localhost/bar.yaml': 'bar contents',
            'file:///home/my/dir/foo.yaml': 'foo contents',
            'file:///home/my/dir/baz/baz1.yaml': 'baz1 contents',
            'file:///home/my/dir/baz/baz2.yaml': 'baz2 contents',
            'file:///home/my/dir/baz/baz3.yaml': 'baz3 contents',
        }, files)
        self.assertEqual({
            'heat_template_version': '2013-05-23',
            'resources': {
                'resource1': {
                    'type': 'type1',
                    'properties': {
                        'bar': {'get_file': 'http://localhost/bar.yaml'},
                        'foo': {'get_file': 'file:///home/my/dir/foo.yaml'},
                    },
                },
                'resource2': {
                    'type': 'type1',
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

        self.m.VerifyAll()

    def test_hot_template_outputs(self):
        self.m.StubOutWithMock(urlutils, 'urlopen')
        tmpl_file = '/home/my/dir/template.yaml'
        url = 'file://%s' % tmpl_file
        contents = str('heat_template_version: 2013-05-23\n'
                       'outputs:\n'
                       '  contents:\n'
                       '    value:\n'
                       '      get_file: template.yaml\n')
        urlutils.urlopen(url).AndReturn(six.StringIO(contents))
        urlutils.urlopen(url).AndReturn(six.StringIO(contents))
        self.m.ReplayAll()
        files, tmpl_parsed = template_utils.get_template_contents(
            template_file=tmpl_file)
        self.assertEqual({url: contents}, files)
        self.m.VerifyAll()


class TestURLFunctions(testtools.TestCase):

    def setUp(self):
        super(TestURLFunctions, self).setUp()
        self.m = mox.Mox()

        self.addCleanup(self.m.VerifyAll)
        self.addCleanup(self.m.UnsetStubs)

    def test_normalise_file_path_to_url_relative(self):
        self.assertEqual(
            'file://%s/foo' % os.getcwd(),
            template_utils.normalise_file_path_to_url(
                'foo'))

    def test_normalise_file_path_to_url_absolute(self):
        self.assertEqual(
            'file:///tmp/foo',
            template_utils.normalise_file_path_to_url(
                '/tmp/foo'))

    def test_normalise_file_path_to_url_file(self):
        self.assertEqual(
            'file:///tmp/foo',
            template_utils.normalise_file_path_to_url(
                'file:///tmp/foo'))

    def test_normalise_file_path_to_url_http(self):
        self.assertEqual(
            'http://localhost/foo',
            template_utils.normalise_file_path_to_url(
                'http://localhost/foo'))

    def test_base_url_for_url(self):
        self.assertEqual(
            'file:///foo/bar',
            template_utils.base_url_for_url(
                'file:///foo/bar/baz'))
        self.assertEqual(
            'file:///foo/bar',
            template_utils.base_url_for_url(
                'file:///foo/bar/baz.txt'))
        self.assertEqual(
            'file:///foo/bar',
            template_utils.base_url_for_url(
                'file:///foo/bar/'))
        self.assertEqual(
            'file:///',
            template_utils.base_url_for_url(
                'file:///'))
        self.assertEqual(
            'file:///',
            template_utils.base_url_for_url(
                'file:///foo'))

        self.assertEqual(
            'http://foo/bar',
            template_utils.base_url_for_url(
                'http://foo/bar/'))
        self.assertEqual(
            'http://foo/bar',
            template_utils.base_url_for_url(
                'http://foo/bar/baz.template'))
