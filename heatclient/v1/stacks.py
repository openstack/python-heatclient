# Copyright 2012 OpenStack LLC.
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

import copy
import errno
import json
import os
import urllib

from heatclient.common import base
from heatclient.common import utils

DEFAULT_PAGE_SIZE = 20


class Stack(base.Resource):
    def __repr__(self):
        return "<Stack %s>" % self._info

    def update(self, **fields):
        self.manager.update(self, **fields)

    def delete(self):
        return self.manager.delete(self)

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class StackManager(base.Manager):
    resource_class = Stack

    def list(self, **kwargs):
        """Get a list of stacks.

        :param page_size: number of items to request in each paginated request
        :param limit: maximum number of stacks to return
        :param marker: begin returning stacks that appear later in the stack
                       list than that represented by this stack id
        :param filters: dict of direct comparison filters that mimics the
                        structure of a stack object
        :rtype: list of :class:`Stack`
        """
        print kwargs
        absolute_limit = kwargs.get('limit')

        def paginate(qp, seen=0):
            url = '/stacks?%s' % urllib.urlencode(qp)

            stacks = self._list(url, "stacks")
            for stack in stacks:
                seen += 1
                if absolute_limit is not None and seen > absolute_limit:
                    return
                yield stack

            page_size = qp.get('limit')
            if (page_size and len(stacks) == page_size and
                    (absolute_limit is None or 0 < seen < absolute_limit)):
                qp['marker'] = stack.id
                for image in paginate(qp, seen):
                    yield image

        params = {'limit': kwargs.get('page_size', DEFAULT_PAGE_SIZE)}

        if 'marker' in kwargs:
            params['marker'] = kwargs['marker']

        filters = kwargs.get('filters', {})
        properties = filters.pop('properties', {})
        for key, value in properties.items():
            params['property-%s' % key] = value
        params.update(filters)

        return paginate(params)

    def create(self, **kwargs):
        """Create a stack"""
        resp, body_iter = self.api.json_request(
                'POST', '/stacks', body=kwargs)
        body = json.loads(''.join([c for c in body_iter]))
        return Stack(self, body)

    def delete(self, stack_id):
        """Delete a stack."""
        self._delete("/stacks/%s" % stack_id)

#    def get(self, image_id):
#        """Get the metadata for a specific stack.
#
#        :param image: image object or id to look up
#        :rtype: :class:`Image`
#        """
#        resp, body = self.api.raw_request('HEAD', '/v1/images/%s' % image_id)
#        meta = self._image_meta_from_headers(dict(resp.getheaders()))
#        return Stack(self, meta)
#
#    def data(self, image, do_checksum=True):
#        """Get the raw data for a specific image.
#
#        :param image: image object or id to look up
#        :param do_checksum: Enable/disable checksum validation
#        :rtype: iterable containing image data
#        """
#        image_id = base.getid(image)
#        resp, body = self.api.raw_request('GET', '/v1/images/%s' % image_id)
#        checksum = resp.getheader('x-image-meta-checksum', None)
#        if do_checksum and checksum is not None:
#            return utils.integrity_iter(body, checksum)
#        else:
#            return body
#
#    def delete(self, image):
#        """Delete an image."""
#        self._delete("/v1/images/%s" % base.getid(image))
#
#
#    def update(self, image, **kwargs):
#        """Update an image
#
#        TODO(bcwaldon): document accepted params
#        """
#        hdrs = {}
#        image_data = kwargs.pop('data', None)
#        if image_data is not None:
#            image_size = self._get_file_size(image_data)
#            if image_size != 0:
#                kwargs.setdefault('size', image_size)
#                hdrs['Content-Length'] = image_size
#            else:
#                image_data = None
#
#        try:
#            purge_props = 'true' if kwargs.pop('purge_props') else 'false'
#        except KeyError:
#            pass
#        else:
#            hdrs['x-heat-registry-purge-props'] = purge_props
#
#        fields = {}
#        for field in kwargs:
#            if field in UPDATE_PARAMS:
#                fields[field] = kwargs[field]
#            else:
#                msg = 'update() got an unexpected keyword argument \'%s\''
#                raise TypeError(msg % field)
#
#        copy_from = fields.pop('copy_from', None)
#        hdrs.update(self._image_meta_to_headers(fields))
#        if copy_from is not None:
#            hdrs['x-heat-api-copy-from'] = copy_from
#
#        url = '/v1/images/%s' % base.getid(image)
#        resp, body_iter = self.api.raw_request(
#                'PUT', url, headers=hdrs, body=image_data)
#        body = json.loads(''.join([c for c in body_iter]))
#        return Stack(self, self._format_image_meta_for_user(body['image']))
