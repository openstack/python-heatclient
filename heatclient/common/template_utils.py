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

import collections
from oslo_serialization import jsonutils
import six
from six.moves.urllib import error
from six.moves.urllib import parse
from six.moves.urllib import request

from heatclient.common import environment_format
from heatclient.common import template_format
from heatclient.common import utils
from heatclient import exc
from heatclient.openstack.common._i18n import _


def process_template_path(template_path, object_request=None):
    """Read template from template path.

    Attempt to read template first as a file or url. If that is unsuccessful,
    try again to assuming path is to a template object.
    """
    try:
        return get_template_contents(template_file=template_path)
    except error.URLError:
        return get_template_contents(template_object=template_path,
                                     object_request=object_request)


def get_template_contents(template_file=None, template_url=None,
                          template_object=None, object_request=None,
                          files=None, existing=False):

    is_object = False
    # Transform a bare file path to a file:// URL.
    if template_file:
        template_url = utils.normalise_file_path_to_url(template_file)

    if template_url:
        tpl = request.urlopen(template_url).read()

    elif template_object:
        is_object = True
        template_url = template_object
        tpl = object_request and object_request('GET',
                                                template_object)
    elif existing:
        return {}, None
    else:
        raise exc.CommandError(_('Need to specify exactly one of '
                               '%(arg1)s, %(arg2)s or %(arg3)s') %
                               {
                                   'arg1': '--template-file',
                                   'arg2': '--template-url',
                                   'arg3': '--template-object'})

    if not tpl:
        raise exc.CommandError(_('Could not fetch template from %s')
                               % template_url)

    try:
        if isinstance(tpl, six.binary_type):
            tpl = tpl.decode('utf-8')
        template = template_format.parse(tpl)
    except ValueError as e:
        raise exc.CommandError(_('Error parsing template %(url)s %(error)s') %
                               {'url': template_url, 'error': e})

    tmpl_base_url = utils.base_url_for_url(template_url)
    if files is None:
        files = {}
    resolve_template_get_files(template, files, tmpl_base_url, is_object,
                               object_request)
    return files, template


def resolve_template_get_files(template, files, template_base_url,
                               is_object=False, object_request=None):

    def ignore_if(key, value):
        if key != 'get_file' and key != 'type':
            return True
        if not isinstance(value, six.string_types):
            return True
        if (key == 'type' and
                not value.endswith(('.yaml', '.template'))):
            return True
        return False

    def recurse_if(value):
        return isinstance(value, (dict, list))

    get_file_contents(template, files, template_base_url,
                      ignore_if, recurse_if, is_object, object_request)


def is_template(file_content):
    try:
        if isinstance(file_content, six.binary_type):
            file_content = file_content.decode('utf-8')
        template_format.parse(file_content)
    except (ValueError, TypeError):
        return False
    return True


def get_file_contents(from_data, files, base_url=None,
                      ignore_if=None, recurse_if=None,
                      is_object=False, object_request=None):

    if recurse_if and recurse_if(from_data):
        if isinstance(from_data, dict):
            recurse_data = six.itervalues(from_data)
        else:
            recurse_data = from_data
        for value in recurse_data:
            get_file_contents(value, files, base_url, ignore_if, recurse_if,
                              is_object, object_request)

    if isinstance(from_data, dict):
        for key, value in six.iteritems(from_data):
            if ignore_if and ignore_if(key, value):
                continue

            if base_url and not base_url.endswith('/'):
                base_url = base_url + '/'

            str_url = parse.urljoin(base_url, value)
            if str_url not in files:
                if is_object and object_request:
                    file_content = object_request('GET', str_url)
                else:
                    file_content = utils.read_url_content(str_url)
                if is_template(file_content):
                    if is_object:
                        template = get_template_contents(
                            template_object=str_url, files=files,
                            object_request=object_request)[1]
                    else:
                        template = get_template_contents(
                            template_url=str_url, files=files)[1]
                    file_content = jsonutils.dumps(template)
                files[str_url] = file_content
            # replace the data value with the normalised absolute URL
            from_data[key] = str_url


def read_url_content(url):
    '''DEPRECATED!  Use 'utils.read_url_content' instead.'''
    return utils.read_url_content(url)


def base_url_for_url(url):
    '''DEPRECATED! Use 'utils.base_url_for_url' instead.'''
    return utils.base_url_for_url(url)


def normalise_file_path_to_url(path):
    '''DEPRECATED! Use 'utils.normalise_file_path_to_url' instead.'''
    return utils.normalise_file_path_to_url(path)


def deep_update(old, new):
    '''Merge nested dictionaries.'''
    for k, v in new.items():
        if isinstance(v, collections.Mapping):
            r = deep_update(old.get(k, {}), v)
            old[k] = r
        else:
            old[k] = new[k]
    return old


def process_multiple_environments_and_files(env_paths=None, template=None,
                                            template_url=None):
    merged_files = {}
    merged_env = {}

    if env_paths:
        for env_path in env_paths:
            files, env = process_environment_and_files(env_path, template,
                                                       template_url)

            # 'files' looks like {"filename1": contents, "filename2": contents}
            # so a simple update is enough for merging
            merged_files.update(files)

            # 'env' can be a deeply nested dictionary, so a simple update is
            # not enough
            merged_env = deep_update(merged_env, env)

    return merged_files, merged_env


def process_environment_and_files(env_path=None, template=None,
                                  template_url=None):
    files = {}
    env = {}

    if env_path:
        env_url = utils.normalise_file_path_to_url(env_path)
        env_base_url = utils.base_url_for_url(env_url)
        raw_env = request.urlopen(env_url).read()
        env = environment_format.parse(raw_env)

        resolve_environment_urls(
            env.get('resource_registry'),
            files,
            env_base_url)

    return files, env


def resolve_environment_urls(resource_registry, files, env_base_url):
    if resource_registry is None:
        return

    rr = resource_registry
    base_url = rr.get('base_url', env_base_url)

    def ignore_if(key, value):
        if key == 'base_url':
            return True
        if isinstance(value, dict):
            return True
        if '::' in value:
            # Built in providers like: "X::Compute::Server"
            # don't need downloading.
            return True
        if key == 'hooks':
            return True

    get_file_contents(rr, files, base_url, ignore_if)

    for res_name, res_dict in six.iteritems(rr.get('resources', {})):
        res_base_url = res_dict.get('base_url', base_url)
        get_file_contents(
            res_dict, files, res_base_url, ignore_if)


def hooks_to_env(env, arg_hooks, hook):
    """Add hooks from args to environment's resource_registry section.

    Hooks are either "resource_name" (if it's a top-level resource) or
    "nested_stack/resource_name" (if the resource is in a nested stack).

    The environment expects each hook to be associated with the resource
    within `resource_registry/resources` using the `hooks: pre-create` format.
    """
    if 'resource_registry' not in env:
        env['resource_registry'] = {}
    if 'resources' not in env['resource_registry']:
        env['resource_registry']['resources'] = {}
    for hook_declaration in arg_hooks:
        hook_path = [r for r in hook_declaration.split('/') if r]
        resources = env['resource_registry']['resources']
        for nested_stack in hook_path:
            if nested_stack not in resources:
                resources[nested_stack] = {}
            resources = resources[nested_stack]
        else:
            resources['hooks'] = hook
