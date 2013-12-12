# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for :class:`User`-related helpers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from apiclient.creds import (
    convert_string_to_tuple,
    convert_tuple_to_string,
    )
from maasserver.models.user import (
    create_auth_token,
    get_auth_tokens,
    get_creds_tuple,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import MAASServerTestCase
from piston.models import (
    KEY_SIZE,
    SECRET_SIZE,
    )


class AuthTokensTest(MAASServerTestCase):
    """Test creation and retrieval of auth tokens."""

    def assertTokenValid(self, token):
        self.assertIsInstance(token.key, unicode)
        self.assertEqual(KEY_SIZE, len(token.key))
        self.assertIsInstance(token.secret, unicode)
        self.assertEqual(SECRET_SIZE, len(token.secret))

    def assertConsumerValid(self, consumer):
        self.assertIsInstance(consumer.key, unicode)
        self.assertEqual(KEY_SIZE, len(consumer.key))
        self.assertEqual('', consumer.secret)

    def test_create_auth_token(self):
        user = factory.make_user()
        token = create_auth_token(user)
        self.assertEqual(user, token.user)
        self.assertEqual(user, token.consumer.user)
        self.assertTrue(token.is_approved)
        self.assertConsumerValid(token.consumer)
        self.assertTokenValid(token)

    def test_get_auth_tokens_finds_tokens_for_user(self):
        user = factory.make_user()
        token = create_auth_token(user)
        self.assertIn(token, get_auth_tokens(user))

    def test_get_auth_tokens_ignores_other_users(self):
        user, other_user = factory.make_user(), factory.make_user()
        unrelated_token = create_auth_token(other_user)
        self.assertNotIn(unrelated_token, get_auth_tokens(user))

    def test_get_auth_tokens_ignores_unapproved_tokens(self):
        user = factory.make_user()
        token = create_auth_token(user)
        token.is_approved = False
        token.save()
        self.assertNotIn(token, get_auth_tokens(user))

    def test_get_creds_tuple_returns_creds(self):
        token = create_auth_token(factory.make_user())
        self.assertEqual(
            (token.consumer.key, token.key, token.secret),
            get_creds_tuple(token))

    def test_get_creds_tuple_integrates_with_api_client(self):
        creds_tuple = get_creds_tuple(create_auth_token(factory.make_user()))
        self.assertEqual(
            creds_tuple,
            convert_string_to_tuple(convert_tuple_to_string(creds_tuple)))
