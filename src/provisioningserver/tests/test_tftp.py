# Copyright 2005-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the maastftp Twisted plugin."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from functools import partial
import json
from os import path
from urllib import urlencode
from urlparse import (
    parse_qsl,
    urlparse,
    )

from maastesting.factory import factory
from maastesting.testcase import MAASTestCase
from provisioningserver import tftp as tftp_module
from provisioningserver.pxe.tftppath import compose_config_path
from provisioningserver.tests.test_kernel_opts import make_kernel_parameters
from provisioningserver.tftp import (
    BytesReader,
    TFTPBackend,
    )
from testtools.deferredruntest import AsynchronousDeferredRunTest
from tftp.backend import IReader
from twisted.internet.defer import (
    inlineCallbacks,
    succeed,
    )
from twisted.python import context
from zope.interface.verify import verifyObject


class TestBytesReader(MAASTestCase):
    """Tests for `provisioningserver.tftp.BytesReader`."""

    def test_interfaces(self):
        reader = BytesReader(b"")
        self.addCleanup(reader.finish)
        verifyObject(IReader, reader)

    def test_read(self):
        data = factory.getRandomString(size=10).encode("ascii")
        reader = BytesReader(data)
        self.addCleanup(reader.finish)
        self.assertEqual(data[:7], reader.read(7))
        self.assertEqual(data[7:], reader.read(7))
        self.assertEqual(b"", reader.read(7))

    def test_finish(self):
        reader = BytesReader(b"1234")
        reader.finish()
        self.assertRaises(ValueError, reader.read, 1)


class TestTFTPBackendRegex(MAASTestCase):
    """Tests for `provisioningserver.tftp.TFTPBackend.re_config_file`."""

    @staticmethod
    def get_example_path_and_components():
        """Return a plausible path and its components.

        The path is intended to match `re_config_file`, and the components are
        the expected groups from a match.
        """
        components = {"mac": factory.getRandomMACAddress("-"),
                      "arch": None,
                      "subarch": None}
        config_path = compose_config_path(components["mac"])
        return config_path, components

    def test_re_config_file_is_compatible_with_config_path_generator(self):
        # The regular expression for extracting components of the file path is
        # compatible with the PXE config path generator.
        regex = TFTPBackend.re_config_file
        for iteration in range(10):
            config_path, args = self.get_example_path_and_components()
            match = regex.match(config_path)
            self.assertIsNotNone(match, config_path)
            self.assertEqual(args, match.groupdict())

    def test_re_config_file_with_leading_slash(self):
        # The regular expression for extracting components of the file path
        # doesn't care if there's a leading forward slash; the TFTP server is
        # easy on this point, so it makes sense to be also.
        config_path, args = self.get_example_path_and_components()
        # Ensure there's a leading slash.
        config_path = "/" + config_path.lstrip("/")
        match = TFTPBackend.re_config_file.match(config_path)
        self.assertIsNotNone(match, config_path)
        self.assertEqual(args, match.groupdict())

    def test_re_config_file_without_leading_slash(self):
        # The regular expression for extracting components of the file path
        # doesn't care if there's no leading forward slash; the TFTP server is
        # easy on this point, so it makes sense to be also.
        config_path, args = self.get_example_path_and_components()
        # Ensure there's no leading slash.
        config_path = config_path.lstrip("/")
        match = TFTPBackend.re_config_file.match(config_path)
        self.assertIsNotNone(match, config_path)
        self.assertEqual(args, match.groupdict())

    def test_re_config_file_matches_classic_pxelinux_cfg(self):
        # The default config path is simply "pxelinux.cfg" (without
        # leading slash).  The regex matches this.
        mac = 'aa-bb-cc-dd-ee-ff'
        match = TFTPBackend.re_config_file.match('pxelinux.cfg/01-%s' % mac)
        self.assertIsNotNone(match)
        self.assertEqual({'mac': mac, 'arch': None, 'subarch': None},
                         match.groupdict())

    def test_re_config_file_matches_pxelinux_cfg_with_leading_slash(self):
        mac = 'aa-bb-cc-dd-ee-ff'
        match = TFTPBackend.re_config_file.match('/pxelinux.cfg/01-%s' % mac)
        self.assertIsNotNone(match)
        self.assertEqual({'mac': mac, 'arch': None, 'subarch': None},
                         match.groupdict())

    def test_re_config_file_does_not_match_non_config_file(self):
        self.assertIsNone(
            TFTPBackend.re_config_file.match('pxelinux.cfg/kernel'))

    def test_re_config_file_does_not_match_file_in_root(self):
        self.assertIsNone(
            TFTPBackend.re_config_file.match('01-aa-bb-cc-dd-ee-ff'))

    def test_re_config_file_does_not_match_file_not_in_pxelinux_cfg(self):
        self.assertIsNone(
            TFTPBackend.re_config_file.match('foo/01-aa-bb-cc-dd-ee-ff'))

    def test_re_config_file_with_default(self):
        match = TFTPBackend.re_config_file.match('pxelinux.cfg/default')
        self.assertIsNotNone(match)
        self.assertEqual(
            {'mac': None, 'arch': None, 'subarch': None},
            match.groupdict())

    def test_re_config_file_with_default_arch(self):
        arch = factory.make_name('arch', sep='')
        match = TFTPBackend.re_config_file.match('pxelinux.cfg/default.%s' %
                                                 arch)
        self.assertIsNotNone(match)
        self.assertEqual(
            {'mac': None, 'arch': arch, 'subarch': None},
            match.groupdict())

    def test_re_config_file_with_default_arch_and_subarch(self):
        arch = factory.make_name('arch', sep='')
        subarch = factory.make_name('subarch', sep='')
        match = TFTPBackend.re_config_file.match(
            'pxelinux.cfg/default.%s-%s' % (arch, subarch))
        self.assertIsNotNone(match)
        self.assertEqual(
            {'mac': None, 'arch': arch, 'subarch': subarch},
            match.groupdict())


class TestTFTPBackend(MAASTestCase):
    """Tests for `provisioningserver.tftp.TFTPBackend`."""

    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=5)

    def test_init(self):
        temp_dir = self.make_dir()
        generator_url = "http://%s.example.com/%s" % (
            factory.make_name("domain"), factory.make_name("path"))
        backend = TFTPBackend(temp_dir, generator_url)
        self.assertEqual((True, False), (backend.can_read, backend.can_write))
        self.assertEqual(temp_dir, backend.base.path)
        self.assertEqual(generator_url, backend.generator_url.geturl())

    def test_get_generator_url(self):
        # get_generator_url() merges the parameters obtained from the request
        # file path (arch, subarch, name) into the configured generator URL.
        mac = factory.getRandomMACAddress("-")
        dummy = factory.make_name("dummy").encode("ascii")
        backend_url = b"http://example.com/?" + urlencode({b"dummy": dummy})
        backend = TFTPBackend(self.make_dir(), backend_url)
        # params is an example of the parameters obtained from a request.
        params = {"mac": mac}
        generator_url = urlparse(backend.get_generator_url(params))
        self.assertEqual("example.com", generator_url.hostname)
        query = parse_qsl(generator_url.query)
        query_expected = [
            ("dummy", dummy),
            ("mac", mac),
            ]
        self.assertItemsEqual(query_expected, query)

    @inlineCallbacks
    def test_get_reader_regular_file(self):
        # TFTPBackend.get_reader() returns a regular FilesystemReader for
        # paths not matching re_config_file.
        data = factory.getRandomString().encode("ascii")
        temp_file = self.make_file(name="example", contents=data)
        temp_dir = path.dirname(temp_file)
        backend = TFTPBackend(temp_dir, "http://nowhere.example.com/")
        reader = yield backend.get_reader("example")
        self.addCleanup(reader.finish)
        self.assertEqual(len(data), reader.size)
        self.assertEqual(data, reader.read(len(data)))
        self.assertEqual(b"", reader.read(1))

    @inlineCallbacks
    def test_get_reader_config_file(self):
        # For paths matching re_config_file, TFTPBackend.get_reader() returns
        # a Deferred that will yield a BytesReader.
        cluster_uuid = factory.getRandomUUID()
        self.patch(tftp_module, 'get_cluster_uuid').return_value = (
            cluster_uuid)
        mac = factory.getRandomMACAddress("-")
        config_path = compose_config_path(mac)
        backend = TFTPBackend(self.make_dir(), b"http://example.com/")
        # python-tx-tftp sets up call context so that backends can discover
        # more about the environment in which they're running.
        call_context = {
            "local": (
                factory.getRandomIPAddress(),
                factory.getRandomPort()),
            "remote": (
                factory.getRandomIPAddress(),
                factory.getRandomPort()),
            }

        @partial(self.patch, backend, "get_config_reader")
        def get_config_reader(params):
            params_json = json.dumps(params)
            params_json_reader = BytesReader(params_json)
            return succeed(params_json_reader)

        reader = yield context.call(
            call_context, backend.get_reader, config_path)
        output = reader.read(10000)
        # The addresses provided by python-tx-tftp in the call context are
        # passed over the wire as address:port strings.
        expected_params = {
            "mac": mac,
            "local": call_context["local"][0],  # address only.
            "remote": call_context["remote"][0],  # address only.
            "cluster_uuid": cluster_uuid,
            }
        observed_params = json.loads(output)
        self.assertEqual(expected_params, observed_params)

    @inlineCallbacks
    def test_get_config_reader_returns_rendered_params(self):
        # get_config_reader() takes a dict() of parameters and returns an
        # `IReader` of a PXE configuration, rendered by `render_pxe_config`.
        backend = TFTPBackend(self.make_dir(), b"http://example.com/")
        # Fake configuration parameters, as discovered from the file path.
        fake_params = {"mac": factory.getRandomMACAddress("-")}
        # Fake kernel configuration parameters, as returned from the API call.
        fake_kernel_params = make_kernel_parameters()

        # Stub get_page to return the fake API configuration parameters.
        fake_get_page_result = json.dumps(fake_kernel_params._asdict())
        get_page_patch = self.patch(backend, "get_page")
        get_page_patch.return_value = succeed(fake_get_page_result)

        # Stub render_pxe_config to return the render parameters.
        fake_render_result = factory.make_name("render")
        render_patch = self.patch(backend, "render_pxe_config")
        render_patch.return_value = fake_render_result

        # Get the rendered configuration, which will actually be a JSON dump
        # of the render-time parameters.
        reader = yield backend.get_config_reader(fake_params)
        self.addCleanup(reader.finish)
        self.assertIsInstance(reader, BytesReader)
        output = reader.read(10000)

        # The kernel parameters were fetched using `backend.get_page`.
        backend.get_page.assert_called_once()

        # The result has been rendered by `backend.render_pxe_config`.
        self.assertEqual(fake_render_result.encode("utf-8"), output)
        backend.render_pxe_config.assert_called_once_with(
            kernel_params=fake_kernel_params, **fake_params)
