# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the FileStorage model."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from io import BytesIO

from maasserver.models import FileStorage
from maasserver.testing.factory import factory
from maasserver.testing.testcase import MAASServerTestCase
from maastesting.utils import sample_binary_data


class FileStorageTest(MAASServerTestCase):
    """Testing of the :class:`FileStorage` model."""

    def make_data(self, including_text='data'):
        """Return arbitrary data.

        :param including_text: Text to include in the data.  Leave something
            here to make failure messages more recognizable.
        :type including_text: unicode
        :return: A string of bytes, including `including_text`.
        :rtype: bytes
        """
        # Note that this won't automatically insert any non-ASCII bytes.
        # Proper handling of real binary data is tested separately.
        text = "%s %s" % (including_text, factory.getRandomString())
        return text.encode('ascii')

    def test_save_file_creates_storage(self):
        filename = factory.getRandomString()
        content = self.make_data()
        user = factory.make_user()
        storage = FileStorage.objects.save_file(
            filename, BytesIO(content), user)
        self.assertEqual(
            (filename, content, user),
            (storage.filename, storage.content, storage.owner))

    def test_storage_can_be_retrieved(self):
        filename = factory.getRandomString()
        content = self.make_data()
        factory.make_file_storage(filename=filename, content=content)
        storage = FileStorage.objects.get(filename=filename)
        self.assertEqual(
            (filename, content),
            (storage.filename, storage.content))

    def test_stores_binary_data(self):
        storage = factory.make_file_storage(content=sample_binary_data)
        self.assertEqual(sample_binary_data, storage.content)

    def test_overwrites_file(self):
        # If a file of the same name has already been stored, the
        # reference to the old data gets overwritten with one to the new
        # data.
        filename = factory.make_name('filename')
        old_storage = factory.make_file_storage(
            filename=filename, content=self.make_data('old data'))
        new_data = self.make_data('new-data')
        new_storage = factory.make_file_storage(
            filename=filename, content=new_data)
        self.assertEqual(old_storage.filename, new_storage.filename)
        self.assertEqual(
            new_data, FileStorage.objects.get(filename=filename).content)

    def test_key_gets_generated(self):
        # The generated system_id looks good.
        storage = factory.make_file_storage()
        self.assertEqual(len(storage.key), 36)

    def test_key_includes_random_part(self):
        storage1 = factory.make_file_storage()
        storage2 = factory.make_file_storage()
        self.assertNotEqual(storage1.key, storage2.key)
