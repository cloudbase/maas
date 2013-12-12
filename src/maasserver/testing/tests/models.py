# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test model for tests of testing module."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'TestModel',
    ]

from django.db.models import (
    CharField,
    Model,
    )


class TestModel(Model):
    """A trivial model class for testing."""

    text = CharField(max_length=100)
