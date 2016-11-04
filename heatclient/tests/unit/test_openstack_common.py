# Copyright 2015 Huawei.
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

import testtools

from heatclient.common import base
from heatclient.v1 import events
from heatclient.v1 import stacks


class BaseTest(testtools.TestCase):

    def test_two_resources_with_same_id_are_not_equal(self):
        # Two resources with same ID: never equal if their info is not equal
        r1 = base.Resource(None, {'id': 1, 'name': 'hi'})
        r2 = base.Resource(None, {'id': 1, 'name': 'hello'})
        self.assertNotEqual(r1, r2)

    def test_two_resources_with_same_id_and_info_are_equal(self):
        # Two resources with same ID: equal if their info is equal
        r1 = base.Resource(None, {'id': 1, 'name': 'hello'})
        r2 = base.Resource(None, {'id': 1, 'name': 'hello'})
        self.assertEqual(r1, r2)

    def test_two_resources_with_diff_type_are_not_equal(self):
        # Two resoruces of different types: never equal
        r1 = base.Resource(None, {'id': 1})
        r2 = events.Event(None, {'id': 1})
        self.assertNotEqual(r1, r2)

    def test_two_resources_with_no_id_are_equal(self):
        # Two resources with no ID: equal if their info is equal
        r1 = base.Resource(None, {'name': 'joe', 'age': 12})
        r2 = base.Resource(None, {'name': 'joe', 'age': 12})
        self.assertEqual(r1, r2)

    def test_is_same_object(self):
        # Two resources with same type and same ID: is same object
        r1 = base.Resource(None, {'id': 1, 'name': 'hi'})
        r2 = base.Resource(None, {'id': 1, 'name': 'hello'})
        self.assertTrue(r1.is_same_obj(r2))
        self.assertTrue(r2.is_same_obj(r1))

    def test_is_diff_object_with_diff_id(self):
        # Two resources with same type and different ID: is different object
        r1 = base.Resource(None, {'id': 1, 'name': 'hello'})
        r2 = base.Resource(None, {'id': 2, 'name': 'hello'})
        self.assertFalse(r1.is_same_obj(r2))
        self.assertFalse(r2.is_same_obj(r1))

    def test_is_diff_object_with_diff_type(self):
        # Two resources with different types: is different object
        r1 = events.Event(None, {'id': 1})
        r2 = stacks.Stack(None, {'id': 1})
        self.assertFalse(r1.is_same_obj(r2))
        self.assertFalse(r2.is_same_obj(r1))

    def test_is_diff_object_with_no_id(self):
        # Two resources with no ID: is different object
        r1 = base.Resource(None, {'name': 'joe', 'age': 12})
        r2 = base.Resource(None, {'name': 'joe', 'age': 12})
        self.assertFalse(r1.is_same_obj(r2))
        self.assertFalse(r2.is_same_obj(r1))
