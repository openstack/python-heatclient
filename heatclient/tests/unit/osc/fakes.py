#   Copyright 2013 Nebula Inc.
#
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

import json

import requests
import six


class FakeStdout(object):
    def __init__(self):
        """
        Initialize the content.

        Args:
            self: (todo): write your description
        """
        self.content = []

    def write(self, text):
        """
        Writes text to the file.

        Args:
            self: (todo): write your description
            text: (str): write your description
        """
        self.content.append(text)

    def make_string(self):
        """
        Make a string from the input string.

        Args:
            self: (todo): write your description
        """
        result = ''
        for line in self.content:
            result = result + line
        return result


class FakeResponse(requests.Response):
    def __init__(self, headers={}, status_code=200, data=None, encoding=None):
        """
        Sets the http headers.

        Args:
            self: (todo): write your description
            headers: (list): write your description
            status_code: (int): write your description
            data: (todo): write your description
            encoding: (str): write your description
        """
        super(FakeResponse, self).__init__()

        self.status_code = status_code

        self.headers.update(headers)
        self._content = json.dumps(data)
        if not isinstance(self._content, six.binary_type):
            self._content = self._content.encode()
