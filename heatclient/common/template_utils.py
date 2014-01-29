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
import urllib

from heatclient.common import environment_format
from heatclient.common import template_format
from heatclient import exc
from heatclient.openstack.common.py3kcompat import urlutils


def get_template_contents(template_file=None, template_url=None,
                          template_object=None, object_request=None):

    # Transform a bare file path to a file:// URL.
    if template_file:
        template_url = normalise_file_path_to_url(template_file)

    if template_url:
        tpl = urlutils.urlopen(template_url).read()

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
        return template_format.parse(tpl)
    except ValueError as e:
        raise exc.CommandError(
            'Error parsing template %s %s' % (template_url, e))


def get_file_contents(from_dict, files, base_url=None,
                      ignore_if=None):
    for key, value in iter(from_dict.items()):
        if ignore_if and ignore_if(key, value):
            continue

        if base_url and not base_url.endswith('/'):
            base_url = base_url + '/'

        str_url = urlutils.urljoin(base_url, value)
        try:
            files[str_url] = urlutils.urlopen(str_url).read()
        except urlutils.URLError:
            raise exc.CommandError('Could not fetch %s from the environment'
                                   % str_url)
        from_dict[key] = str_url


def base_url_for_url(url):
    parsed = urlutils.urlparse(url)
    parsed_dir = os.path.dirname(parsed.path)
    return urlutils.urljoin(url, parsed_dir)


def normalise_file_path_to_url(path):
    if urlutils.urlparse(path).scheme:
        return path
    path = os.path.abspath(path)
    return urlutils.urljoin('file:', urllib.pathname2url(path))


def process_environment_and_files(env_path=None, template_path=None):
    files = {}
    env = {}

    if not env_path:
        return files, env

    env_url = normalise_file_path_to_url(env_path)
    env_base_url = base_url_for_url(env_url)
    raw_env = urlutils.urlopen(env_url).read()
    env = environment_format.parse(raw_env)

    resolve_environment_urls(
        env.get('resource_registry'),
        files,
        env_base_url)

    return files, env


def resolve_environment_urls(resource_registry, files, env_base_url):
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
