# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test related classes and functions for maas and its applications."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'MAASTestCase',
    ]

from contextlib import contextmanager
import doctest
import unittest

from maastesting.factory import factory
from maastesting.fixtures import TempDirectory
from maastesting.scenarios import WithScenarios
import mock
from nose.proxy import ResultProxy
from nose.tools import nottest
from provisioningserver.testing.worker_cache import WorkerCacheFixture
import testresources
import testtools
import testtools.matchers


@nottest
@contextmanager
def active_test(result, test):
    """Force nose to report for the test that's running.

    Nose presents a proxy result and passes on results using only the
    top-level test, rather than the actual running test. This attempts to undo
    this dubious choice.

    If the result is not a nose proxy then this is a no-op.
    """
    if isinstance(result, ResultProxy):
        orig = result.test.test
        result.test.test = test
        try:
            yield
        finally:
            result.test.test = orig
    else:
        yield


class MAASTestCase(WithScenarios, testtools.TestCase):
    """Base `TestCase` for MAAS.

    Supports `test resources`_, `test scenarios`_, and `fixtures`_.

    .. _test resources: https://launchpad.net/testresources

    .. _test scenarios: https://launchpad.net/testscenarios

    .. _fixtures: https://launchpad.net/python-fixtures

    """

    # Allow testtools to generate longer diffs when tests fail.
    maxDiff = testtools.TestCase.maxDiff * 3

    # testresources.ResourcedTestCase does something similar to this class
    # (with respect to setUpResources and tearDownResources) but it explicitly
    # up-calls to unittest.TestCase instead of using super() even though it is
    # not guaranteed that the next class in the inheritance chain is
    # unittest.TestCase.

    resources = (
        # (resource-name, resource),
        )

    scenarios = (
        # (scenario-name, {instance-attribute-name: value, ...}),
        )

    def setUp(self):
        super(MAASTestCase, self).setUp()
        self.useFixture(WorkerCacheFixture())
        self.setUpResources()

    def setUpResources(self):
        testresources.setUpResources(
            self, self.resources, testresources._get_result())

    def tearDown(self):
        self.tearDownResources()
        super(MAASTestCase, self).tearDown()

    def tearDownResources(self):
        testresources.tearDownResources(
            self, self.resources, testresources._get_result())

    def make_dir(self):
        """Create a temporary directory.

        This is a convenience wrapper around a fixture incantation.  That's
        the only reason why it's on the test case and not in a factory.
        """
        return self.useFixture(TempDirectory()).path

    def make_file(self, name=None, contents=None):
        """Create, and write to, a file.

        This is a convenience wrapper around `make_dir` and a factory
        call.  It ensures that the file is in a directory that will be
        cleaned up at the end of the test.
        """
        return factory.make_file(self.make_dir(), name, contents)

    # Django's implementation for this seems to be broken and was
    # probably only added to support compatibility with python 2.6.
    assertItemsEqual = unittest.TestCase.assertItemsEqual

    doctest_flags = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE

    def assertDocTestMatches(self, expected, observed, flags=None):
        """See if `observed` matches `expected`, a doctest sample.

        By default uses the doctest flags `NORMALIZE_WHITESPACE` and
        `ELLIPSIS`.
        """
        self.assertThat(observed, testtools.matchers.DocTestMatches(
            expected, self.doctest_flags if flags is None else flags))

    def run(self, result=None):
        with active_test(result, self):
            super(MAASTestCase, self).run(result)

    def __call__(self, result=None):
        with active_test(result, self):
            super(MAASTestCase, self).__call__(result)

    def patch(self, obj, attribute, value=mock.sentinel.unset):
        """Patch `obj.attribute` with `value`.

        If `value` is unspecified, a new `MagicMock` will be created and
        patched-in instead.

        This is a thin customisation of `testtools.TestCase.patch`, so refer
        to that in case of doubt.

        :return: The patched-in object.
        """
        if value is mock.sentinel.unset:
            value = mock.MagicMock()
        super(MAASTestCase, self).patch(obj, attribute, value)
        return value
