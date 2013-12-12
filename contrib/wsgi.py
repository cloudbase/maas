# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""WSGI Application."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'application',
    ]

import os
import sys


current_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'maas.settings'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()


from maasserver.start_up import start_up
start_up()
