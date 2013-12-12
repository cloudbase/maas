# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `maastesting.httpd`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from contextlib import closing
import gzip
from io import BytesIO
from os.path import relpath
from socket import (
    gethostbyname,
    gethostname,
    )
from unittest import skip
from urllib2 import (
    Request,
    urlopen,
    )
from urlparse import urljoin

from maastesting.fixtures import ProxiesDisabledFixture
from maastesting.httpd import (
    HTTPServerFixture,
    ThreadingHTTPServer,
    )
from maastesting.testcase import MAASTestCase
from testtools.matchers import FileExists


class TestHTTPServerFixture(MAASTestCase):

    def setUp(self):
        super(TestHTTPServerFixture, self).setUp()
        self.useFixture(ProxiesDisabledFixture())

    @skip(
        "XXX: bigjools 2013-09-13 bug=1224837: Causes intermittent failures")
    def test_init(self):
        host = gethostname()
        fixture = HTTPServerFixture(host=host)
        self.assertIsInstance(fixture.server, ThreadingHTTPServer)
        expected_url = "http://%s:%d/" % (
            gethostbyname(host), fixture.server.server_port)
        self.assertEqual(expected_url, fixture.url)

    def test_use(self):
        filename = relpath(__file__)
        self.assertThat(filename, FileExists())
        with HTTPServerFixture() as httpd:
            url = urljoin(httpd.url, filename)
            with closing(urlopen(url)) as http_in:
                http_data_in = http_in.read()
        with open(filename, "rb") as file_in:
            file_data_in = file_in.read()
        self.assertEqual(
            file_data_in, http_data_in,
            "The content of %s differs from %s." % (url, filename))

    def ungzip(self, content):
        gz = gzip.GzipFile(fileobj=BytesIO(content))
        return gz.read()

    def test_supports_gzip(self):
        filename = relpath(__file__)
        with HTTPServerFixture() as httpd:
            url = urljoin(httpd.url, filename)
            headers = {'Accept-Encoding': 'gzip, deflate'}
            request = Request(url, None, headers=headers)
            with closing(urlopen(request)) as http_in:
                http_headers = http_in.info()
                http_data_in = http_in.read()
        self.assertEqual('gzip', http_headers['Content-Encoding'])
        with open(filename, "rb") as file_in:
            file_data_in = file_in.read()
        http_data_decompressed = self.ungzip(http_data_in)
        self.assertEqual(
            file_data_in, http_data_decompressed,
            "The content of %s differs from %s." % (url, filename))
