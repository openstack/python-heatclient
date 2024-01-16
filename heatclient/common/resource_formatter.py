#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

import collections
import hashlib

from cliff.formatters import base


class ResourceDotInfo(object):

    def __init__(self, res):
        self.resource = res
        links = {link['rel']: link['href'] for link in res.links}
        self.nested_dot_id = self.dot_id(links.get('nested'), 'stack')
        self.stack_dot_id = self.dot_id(links.get('stack'), 'stack')
        self.res_dot_id = self.dot_id(links.get('self'))

    @staticmethod
    def dot_id(url, prefix=None):
        """Build an id with a prefix and a truncated hash of the URL"""
        if not url:
            return None
        if not prefix:
            prefix = 'r'
        hash_object = hashlib.sha256(url.encode('utf-8'))
        return '%s_%s' % (prefix, hash_object.hexdigest()[:20])


class ResourceDotFormatter(base.ListFormatter):
    def add_argument_group(self, parser):
        pass

    def emit_list(self, column_names, data, stdout, parsed_args):
        writer = ResourceDotWriter(data, stdout)
        writer.write()


class ResourceDotWriter(object):

    def __init__(self, data, stdout):
        self.resources_by_stack = collections.defaultdict(
            collections.OrderedDict)
        self.resources_by_dot_id = collections.OrderedDict()
        self.nested_stack_ids = []
        self.stdout = stdout

        for r in data:
            rinfo = ResourceDotInfo(r)
            if rinfo.stack_dot_id:
                self.resources_by_stack[
                    rinfo.stack_dot_id][r.resource_name] = rinfo
            if rinfo.res_dot_id:
                self.resources_by_dot_id[rinfo.res_dot_id] = rinfo
            if rinfo.nested_dot_id:
                self.nested_stack_ids.append(rinfo.nested_dot_id)

    def write(self):
        stdout = self.stdout

        stdout.write('digraph G {\n')
        stdout.write('  graph [\n'
                     '    fontsize=10 fontname="Verdana" '
                     'compound=true rankdir=LR\n'
                     '  ]\n')

        self.write_root_nodes()
        self.write_subgraphs()
        self.write_nested_stack_edges()
        self.write_required_by_edges()
        stdout.write('}\n')

    def write_root_nodes(self):
        for stack_dot_id in set(self.resources_by_stack.keys()).difference(
                self.nested_stack_ids):
            resources = self.resources_by_stack[stack_dot_id]
            self.write_nodes(resources, 2)

    def write_subgraphs(self):
        for dot_id, rinfo in self.resources_by_dot_id.items():
            if rinfo.nested_dot_id:
                resources = self.resources_by_stack[rinfo.nested_dot_id]
                if resources:
                    self.write_subgraph(resources, rinfo)

    def write_nodes(self, resources, indent):
        stdout = self.stdout
        spaces = ' ' * indent
        for rinfo in resources.values():
            r = rinfo.resource
            dot_id = rinfo.res_dot_id
            if r.resource_status.endswith('FAILED'):
                style = 'style=filled color=red'
            else:
                style = ''
            stdout.write('%s%s [label="%s\n%s" %s];\n'
                         % (spaces, dot_id, r.resource_name,
                            r.resource_type, style))
        stdout.write('\n')

    def write_subgraph(self, resources, nested_resource):
        stdout = self.stdout
        stack_dot_id = nested_resource.nested_dot_id
        nested_name = nested_resource.resource.resource_name
        stdout.write('  subgraph cluster_%s {\n' % stack_dot_id)
        stdout.write('    label="%s";\n' % nested_name)
        self.write_nodes(resources, 4)
        stdout.write('  }\n\n')

    def write_required_by_edges(self):
        stdout = self.stdout
        for dot_id, rinfo in self.resources_by_dot_id.items():
            r = rinfo.resource

            required_by = r.required_by
            stack_dot_id = rinfo.stack_dot_id
            if not required_by or not stack_dot_id:
                continue

            stack_resources = self.resources_by_stack.get(stack_dot_id, {})
            for req in required_by:
                other_rinfo = stack_resources.get(req)
                if other_rinfo:
                    stdout.write('  %s -> %s;\n'
                                 % (rinfo.res_dot_id, other_rinfo.res_dot_id))
        stdout.write('\n')

    def write_nested_stack_edges(self):
        stdout = self.stdout
        for dot_id, rinfo in self.resources_by_dot_id.items():
            if rinfo.nested_dot_id:
                nested_resources = self.resources_by_stack[rinfo.nested_dot_id]
                if nested_resources:
                    first_resource = list(nested_resources.values())[0]
                    stdout.write(
                        '  %s -> %s [\n    color=dimgray lhead=cluster_%s '
                        'arrowhead=none\n  ];\n'
                        % (dot_id, first_resource.res_dot_id,
                           rinfo.nested_dot_id))
        stdout.write('\n')
