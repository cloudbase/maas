# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test ORM utilities."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from itertools import repeat

from django.core.exceptions import MultipleObjectsReturned
from maasserver.fields import MAC
from maasserver.utils.orm import (
    get_first,
    get_one,
    macs_contain,
    macs_do_not_contain,
    )
from maastesting.factory import factory
from maastesting.testcase import MAASTestCase
from mock import Mock


class FakeModel:

    class MultipleObjectsReturned(MultipleObjectsReturned):
        pass

    def __init__(self, name):
        self.name == name

    def __repr__(self):
        return self.name


class FakeQueryResult:
    """Something that looks, to `get_one`, close enough to a Django model."""

    def __init__(self, model, items):
        self.model = model
        self.items = items

    def __iter__(self):
        return self.items.__iter__()

    def __repr__(self):
        return "<FakeQueryResult: %r>" % self.items


class TestGetOne(MAASTestCase):

    def test_get_one_returns_None_for_empty_list(self):
        self.assertIsNone(get_one([]))

    def test_get_one_returns_single_list_item(self):
        item = factory.getRandomString()
        self.assertEqual(item, get_one([item]))

    def test_get_one_returns_None_from_any_empty_sequence(self):
        self.assertIsNone(get_one("no item" for counter in range(0)))

    def test_get_one_returns_item_from_any_sequence_of_length_one(self):
        item = factory.getRandomString()
        self.assertEqual(item, get_one(item for counter in range(1)))

    def test_get_one_does_not_trigger_database_counting(self):
        # Avoid typical performance pitfall of querying objects *and*
        # the number of objects.
        item = factory.getRandomString()
        sequence = FakeQueryResult(type(item), [item])
        sequence.__len__ = Mock(side_effect=Exception("len() was called"))
        self.assertEqual(item, get_one(sequence))

    def test_get_one_does_not_iterate_long_sequence_indefinitely(self):
        # Avoid typical performance pitfall of retrieving all objects.
        # In rare failure cases, there may be large numbers.  Fail fast.

        class InfinityException(Exception):
            """Iteration went on indefinitely."""

        def infinite_sequence():
            """Generator: count to infinity (more or less), then fail."""
            for counter in range(3):
                yield counter
            raise InfinityException()

        # Raises MultipleObjectsReturned as spec'ed.  It does not
        # iterate to infinity first!
        self.assertRaises(
            MultipleObjectsReturned, get_one, infinite_sequence())

    def test_get_one_raises_model_error_if_query_result_is_too_big(self):
        self.assertRaises(
            FakeModel.MultipleObjectsReturned,
            get_one,
            FakeQueryResult(FakeModel, range(2)))

    def test_get_one_raises_generic_error_if_other_sequence_is_too_big(self):
        self.assertRaises(MultipleObjectsReturned, get_one, range(2))


class TestGetFirst(MAASTestCase):
    def test_get_first_returns_None_for_empty_list(self):
        self.assertIsNone(get_first([]))

    def test_get_first_returns_first_item(self):
        items = [factory.getRandomString() for counter in range(10)]
        self.assertEqual(items[0], get_first(items))

    def test_get_first_accepts_any_sequence(self):
        item = factory.getRandomString()
        self.assertEqual(item, get_first(repeat(item)))

    def test_get_first_does_not_retrieve_beyond_first_item(self):

        class SecondItemRetrieved(Exception):
            """Second item as retrieved.  It shouldn't be."""

        def multiple_items():
            yield "Item 1"
            raise SecondItemRetrieved()

        self.assertEqual("Item 1", get_first(multiple_items()))


class TestGetPredicateUtilities(MAASTestCase):

    def test_macs_contain_returns_predicate(self):
        macs = ['11:22:33:44:55:66', 'aa:bb:cc:dd:ee:ff']
        where, params = macs_contain('key', macs)
        self.assertEqual(
            (where, params),
            ('key @> ARRAY[%s, %s]::macaddr[]', macs))

    def test_macs_contain_returns_predicate_using_MACs(self):
        macs = [MAC('11:22:33:44:55:66')]
        where, params = macs_contain('key', macs)
        self.assertEqual(
            (where, params),
            ('key @> ARRAY[%s]::macaddr[]', macs))

    def test_macs_do_not_contain_returns_predicate(self):
        macs = ['11:22:33:44:55:66', 'aa:bb:cc:dd:ee:ff']
        where, params = macs_do_not_contain('key', macs)
        self.assertEqual(
            (where, params),
            (
                (
                    '((key IS NULL) OR NOT '
                    '(key @> ARRAY[%s]::macaddr[] OR '
                    'key @> ARRAY[%s]::macaddr[]))'
                ),
                macs,
            ))
