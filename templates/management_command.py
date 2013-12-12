# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# TODO: Document purpose.
"""Django command: """

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'Command',
    ]

from optparse import make_option

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        # TODO: Define actual options.
        make_option(
            '--option', dest='option', default=None,
            help="Describe option."),
    )
    # TODO: Describe the command.
    help = "Purpose of this command."

    def handle(self, *args, **options):
        # TODO: Replace the lines below with your actual code.
        option = options.get('option', None)
        print(option)
