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

from oslo_serialization import jsonutils


class FakeRaw(object):
    version = 110


class FakeHTTPResponse(object):

    version = 1.1

    def __init__(self, status_code, reason, headers, content):
        """
        Initialize the http response.

        Args:
            self: (todo): write your description
            status_code: (int): write your description
            reason: (str): write your description
            headers: (list): write your description
            content: (str): write your description
        """
        self.headers = headers
        self.content = content
        self.status_code = status_code
        self.reason = reason
        self.raw = FakeRaw()

    def getheader(self, name, default=None):
        """
        Gets a response header.

        Args:
            self: (todo): write your description
            name: (str): write your description
            default: (todo): write your description
        """
        return self.headers.get(name, default)

    def getheaders(self):
        """
        Returns the headers.

        Args:
            self: (todo): write your description
        """
        return self.headers.items()

    def read(self, amt=None):
        """
        Reads the content from the stream.

        Args:
            self: (todo): write your description
            amt: (str): write your description
        """
        b = self.content
        self.content = None
        return b

    def iter_content(self, chunksize):
        """
        Iterate over the content.

        Args:
            self: (todo): write your description
            chunksize: (int): write your description
        """
        return self.content

    def json(self):
        """
        Returns the content - formatted as json.

        Args:
            self: (todo): write your description
        """
        return jsonutils.loads(self.content)
