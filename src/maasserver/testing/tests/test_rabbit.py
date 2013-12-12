# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maastesting.rabbit`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from django.conf import settings
from maasserver.testing.rabbit import RabbitServerSettings
from maastesting.factory import factory
from maastesting.testcase import MAASTestCase
from rabbitfixture.server import RabbitServerResources


class TestRabbitServerSettings(MAASTestCase):

    def test_patch(self):
        config = RabbitServerResources(
            hostname=factory.getRandomString(),
            port=factory.getRandomPort())
        self.useFixture(config)
        self.useFixture(RabbitServerSettings(config))
        self.assertEqual(
            "%s:%d" % (config.hostname, config.port),
            settings.RABBITMQ_HOST)
        self.assertEqual("guest", settings.RABBITMQ_PASSWORD)
        self.assertEqual("guest", settings.RABBITMQ_USERID)
        self.assertEqual("/", settings.RABBITMQ_VIRTUAL_HOST)
        self.assertTrue(settings.RABBITMQ_PUBLISH)
