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

from cliff import show


class RawFormat(show.ShowOne):

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
