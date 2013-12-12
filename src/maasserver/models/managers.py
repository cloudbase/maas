# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Custom MAAS manager classes."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'BulkManager',
    ]


from django.db.models import Manager


class BulkManager(Manager):
    """A Manager which loads objects from the cache if it's populated.

    Even when iterator() is explicitely called (which happens in piston when
    related collections are fetched), this manager will fetch objects in bulk
    if the cache is populated (i.e. if prefetch_related was used).
    """

    def iterator(self):
        return self.all()
