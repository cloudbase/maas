# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests configuration."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []


from django.conf import settings
from maasserver.testing.testcase import MAASServerTestCase


class TestConfiguration(MAASServerTestCase):

    def test_transactionmiddleware(self):
        # The 'TransactionMiddleware' is enabled.
        self.assertIn(
            'django.middleware.transaction.TransactionMiddleware',
            settings.MIDDLEWARE_CLASSES)
