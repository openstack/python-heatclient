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
#   Copyright 2015 IBM Corp.

import sys

from osc_lib.command import command
import six


class RawFormat(command.ShowOne):

    def produce_output(self, parsed_args, column_names, data):
        if data is None:
            return

        self.formatter.emit_one(column_names, data,
                                self.app.stdout, parsed_args)


class JsonFormat(RawFormat):

    @property
    def formatter_default(self):
        return 'json'


class YamlFormat(RawFormat):

    @property
    def formatter_default(self):
        return 'yaml'


class ShellFormat(RawFormat):

    @property
    def formatter_default(self):
        return 'shell'


class ValueFormat(RawFormat):

    @property
    def formatter_default(self):
        return 'value'


def indent_and_truncate(txt, spaces=0, truncate=False, truncate_limit=10,
                        truncate_prefix=None, truncate_postfix=None):
    """Indents supplied multiline text by the specified number of spaces

    """
    if txt is None:
        return
    lines = six.text_type(txt).splitlines()
    if truncate and len(lines) > truncate_limit:
        lines = lines[-truncate_limit:]
        if truncate_prefix is not None:
            lines.insert(0, truncate_prefix)
        if truncate_postfix is not None:
            lines.append(truncate_postfix)

    if spaces > 0:
        lines = [" " * spaces + line for line in lines]
    return '\n'.join(lines)


def print_software_deployment_output(data, name, out=sys.stdout, long=False):
    """Prints details of the software deployment for user consumption

    The format attempts to be valid yaml, but is primarily aimed at showing
    useful information to the user in a helpful layout.
    """
    if data is None:
        data = {}
    if name in ('deploy_stdout', 'deploy_stderr'):
        output = indent_and_truncate(
            data.get(name),
            spaces=4,
            truncate=not long,
            truncate_prefix='...',
            truncate_postfix='(truncated, view all with --long)')
        out.write('  %s: |\n%s\n' % (name, output))
    else:
        out.write('  %s: %s\n' % (name, data.get(name)))
