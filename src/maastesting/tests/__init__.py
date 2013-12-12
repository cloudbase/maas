# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from os.path import dirname

from django.utils.unittest import TestLoader


def suite():
    return TestLoader().discover(dirname(__file__))
