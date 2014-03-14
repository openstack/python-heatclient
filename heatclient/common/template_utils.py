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
import six
from six.moves.urllib import error
from six.moves.urllib import parse
from six.moves.urllib import request

from heatclient.common import environment_format
from heatclient.common import template_format
from heatclient import exc


def get_template_contents(template_file=None, template_url=None,
                          template_object=None, object_request=None):

    # Transform a bare file path to a file:// URL.
    if template_file:
        template_url = normalise_file_path_to_url(template_file)

    if template_url:
        tpl = request.urlopen(template_url).read()

    elif template_object:
        template_url = template_object
        tpl = object_request and object_request('GET',
                                                template_object)
    else:
        raise exc.CommandError('Need to specify exactly one of '
                               '--template-file, --template-url '
                               'or --template-object')

    if not tpl:
        raise exc.CommandError('Could not fetch template from %s'
                               % template_url)

    try:
        if isinstance(tpl, six.binary_type):
            tpl = tpl.decode('utf-8')
        template = template_format.parse(tpl)
    except ValueError as e:
        raise exc.CommandError(
            'Error parsing template %s %s' % (template_url, e))

    files = {}
    tmpl_base_url = base_url_for_url(template_url)
    resolve_template_get_files(template, files, tmpl_base_url)
    resolve_template_type(template, files, tmpl_base_url)
    return files, template


def resolve_template_get_files(template, files, template_base_url):

    def ignore_if(key, value):
        if key != 'get_file':
            return True
        if not isinstance(value, six.string_types):
            return True

    def recurse_if(value):
        return isinstance(value, (dict, list))

    get_file_contents(template, files, template_base_url,
                      ignore_if, recurse_if)


def resolve_template_type(template, files, template_base_url):

    def ignore_if(key, value):
        if key != 'type':
            return True
        if not isinstance(value, six.string_types):
            return True
        if not value.endswith(('.yaml', '.template')):
            return True
        return False

    def recurse_if(value):
        return isinstance(value, (dict, list))

    get_file_contents(template, files, template_base_url,
                      ignore_if, recurse_if)


def get_file_contents(from_data, files, base_url=None,
                      ignore_if=None, recurse_if=None):

    if recurse_if and recurse_if(from_data):
        if isinstance(from_data, dict):
            recurse_data = six.itervalues(from_data)
        else:
            recurse_data = from_data
        for value in recurse_data:
            get_file_contents(value, files, base_url, ignore_if, recurse_if)

    if isinstance(from_data, dict):
        for key, value in iter(from_data.items()):
            if ignore_if and ignore_if(key, value):
                continue

            if base_url and not base_url.endswith('/'):
                base_url = base_url + '/'

            str_url = parse.urljoin(base_url, value)
            try:
                files[str_url] = request.urlopen(str_url).read()
            except error.URLError:
                raise exc.CommandError('Could not fetch contents for %s'
                                       % str_url)

            # replace the data value with the normalised absolute URL
            from_data[key] = str_url


def base_url_for_url(url):
    parsed = parse.urlparse(url)
    parsed_dir = os.path.dirname(parsed.path)
    return parse.urljoin(url, parsed_dir)


def normalise_file_path_to_url(path):
    if parse.urlparse(path).scheme:
        return path
    path = os.path.abspath(path)
    return parse.urljoin('file:', request.pathname2url(path))


def process_environment_and_files(env_path=None, template=None,
                                  template_url=None):
    files = {}
    env = {}

    if env_path:
        env_url = normalise_file_path_to_url(env_path)
        env_base_url = base_url_for_url(env_url)
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

    get_file_contents(rr, files, base_url, ignore_if)

    for res_name, res_dict in iter(rr.get('resources', {}).items()):
        res_base_url = res_dict.get('base_url', base_url)
        get_file_contents(res_dict, files, res_base_url, ignore_if)
