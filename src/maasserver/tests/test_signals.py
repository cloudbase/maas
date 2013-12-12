# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for signals helpers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from maasserver.signals import connect_to_field_change
from maasserver.testing.factory import factory
from maasserver.testing.testcase import MAASServerTestCase
from maasserver.tests.models import FieldChangeTestModel
from maastesting.djangotestcase import TestModelMixin
from mock import (
    call,
    Mock,
    )


class ConnectToFieldChangeTest(TestModelMixin, MAASServerTestCase):
    """Testing for the method `connect_to_field_change`."""

    app = 'maasserver.tests'

    def test_connect_to_field_change_calls_callback(self):
        callback = Mock()
        connect_to_field_change(callback, FieldChangeTestModel, 'name1')
        old_name1_value = factory.getRandomString()
        obj = FieldChangeTestModel(name1=old_name1_value)
        obj.save()
        obj.name1 = factory.getRandomString()
        obj.save()
        self.assertEqual(
            (1, call(obj, old_name1_value, deleted=False)),
            (callback.call_count, callback.call_args))

    def test_connect_to_field_change_calls_callback_for_each_save(self):
        callback = Mock()
        connect_to_field_change(callback, FieldChangeTestModel, 'name1')
        old_name1_value = factory.getRandomString()
        obj = FieldChangeTestModel(name1=old_name1_value)
        obj.save()
        obj.name1 = factory.getRandomString()
        obj.save()
        obj.name1 = factory.getRandomString()
        obj.save()
        self.assertEqual(2, callback.call_count)

    def test_connect_to_field_change_calls_callback_for_each_real_save(self):
        callback = Mock()
        connect_to_field_change(callback, FieldChangeTestModel, 'name1')
        old_name1_value = factory.getRandomString()
        obj = FieldChangeTestModel(name1=old_name1_value)
        obj.save()
        obj.name1 = factory.getRandomString()
        obj.save()
        obj.save()
        self.assertEqual(1, callback.call_count)

    def test_connect_to_field_change_calls_multiple_callbacks(self):
        callback1 = Mock()
        connect_to_field_change(callback1, FieldChangeTestModel, 'name1')
        callback2 = Mock()
        connect_to_field_change(callback2, FieldChangeTestModel, 'name1')
        old_name1_value = factory.getRandomString()
        obj = FieldChangeTestModel(name1=old_name1_value)
        obj.save()
        obj.name1 = factory.getRandomString()
        obj.save()
        self.assertEqual((1, 1), (callback1.call_count, callback2.call_count))

    def test_connect_to_field_change_ignores_changes_to_other_fields(self):
        obj = FieldChangeTestModel(name2=factory.getRandomString())
        obj.save()
        callback = Mock()
        connect_to_field_change(callback, FieldChangeTestModel, 'name1')
        obj.name2 = factory.getRandomString()
        obj.save()
        self.assertEqual(0, callback.call_count)

    def test_connect_to_field_change_ignores_object_creation(self):
        callback = Mock()
        connect_to_field_change(callback, FieldChangeTestModel, 'name1')
        obj = FieldChangeTestModel(name1=factory.getRandomString())
        obj.save()
        self.assertEqual(0, callback.call_count)

    def test_connect_to_field_change_ignores_deletion_by_default(self):
        obj = FieldChangeTestModel(name2=factory.getRandomString())
        obj.save()
        callback = Mock()
        connect_to_field_change(callback, FieldChangeTestModel, 'name1')
        obj.delete()
        self.assertEqual(0, callback.call_count)

    def test_connect_to_field_change_listens_to_deletion_if_delete_True(self):
        old_name1_value = factory.getRandomString()
        obj = FieldChangeTestModel(name1=old_name1_value)
        obj.save()
        callback = Mock()
        connect_to_field_change(
            callback, FieldChangeTestModel, 'name1', delete=True)
        obj.delete()
        self.assertEqual(
            (1, call(obj, old_name1_value, deleted=True)),
            (callback.call_count, callback.call_args))
