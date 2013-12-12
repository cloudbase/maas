# Copyright 2012-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `provisioningserver.pxe.config`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from collections import OrderedDict
import errno
import os
import re

from fixtures import EnvironmentVariableFixture
from maastesting.factory import factory
from maastesting.matchers import ContainsAll
from maastesting.testcase import MAASTestCase
import mock
from provisioningserver import kernel_opts
from provisioningserver.pxe import config
from provisioningserver.pxe.config import render_pxe_config
from provisioningserver.pxe.tftppath import compose_image_path
from provisioningserver.tests.test_kernel_opts import make_kernel_parameters
from provisioningserver.utils import locate_config
import tempita
from testtools.matchers import (
    Contains,
    IsInstance,
    MatchesAll,
    MatchesRegex,
    StartsWith,
    )


class TestFunctions(MAASTestCase):
    """Test for functions in `provisioningserver.pxe.config`."""

    def test_gen_pxe_template_filenames(self):
        purpose = factory.make_name("purpose")
        arch, subarch = factory.make_names("arch", "subarch")
        expected = [
            "config.%s.%s.%s.template" % (purpose, arch, subarch),
            "config.%s.%s.template" % (purpose, arch),
            "config.%s.template" % (purpose, ),
            "config.template",
            ]
        observed = config.gen_pxe_template_filenames(purpose, arch, subarch)
        self.assertSequenceEqual(expected, list(observed))

    def test_get_pxe_template(self):
        purpose = factory.make_name("purpose")
        arch, subarch = factory.make_names("arch", "subarch")
        filename = factory.make_name("filename")
        # Set up the mocks that we've patched in.
        gen_filenames = self.patch(config, "gen_pxe_template_filenames")
        gen_filenames.return_value = [filename]
        from_filename = self.patch(tempita.Template, "from_filename")
        from_filename.return_value = mock.sentinel.template
        # The template returned matches the return value above.
        template = config.get_pxe_template(purpose, arch, subarch)
        self.assertEqual(mock.sentinel.template, template)
        # gen_pxe_template_filenames is called to obtain filenames.
        gen_filenames.assert_called_once_with(purpose, arch, subarch)
        # Tempita.from_filename is called with an absolute path derived from
        # the filename returned from gen_pxe_template_filenames.
        from_filename.assert_called_once_with(
            locate_config(config.TEMPLATES_DIR, filename), encoding="UTF-8")

    def make_fake_templates_dir(self):
        """Set up a fake PXE templates dir, and return its path."""
        fake_etc_maas = self.make_dir()
        self.useFixture(EnvironmentVariableFixture(
            'MAAS_CONFIG_DIR', fake_etc_maas))
        fake_templates = os.path.join(fake_etc_maas, config.TEMPLATES_DIR)
        os.makedirs(fake_templates)
        return fake_templates

    def test_get_pxe_template_gets_default_if_available(self):
        # If there is no template matching the purpose, arch, and subarch,
        # but there is a completely generic template, then get_pxe_template()
        # falls back to that as the default.
        templates_dir = self.make_fake_templates_dir()
        generic_template = factory.make_file(templates_dir, 'config.template')
        purpose = factory.make_name("purpose")
        arch, subarch = factory.make_names("arch", "subarch")
        self.assertEqual(
            generic_template,
            config.get_pxe_template(purpose, arch, subarch).name)

    def test_get_pxe_template_not_found(self):
        # It is a critical and unrecoverable error if the default PXE template
        # is not found.
        self.make_fake_templates_dir()
        self.assertRaises(
            AssertionError, config.get_pxe_template,
            *factory.make_names("purpose", "arch", "subarch"))

    def test_get_pxe_templates_only_suppresses_ENOENT(self):
        # The IOError arising from trying to load a template that doesn't
        # exist is suppressed, but other errors are not.
        from_filename = self.patch(tempita.Template, "from_filename")
        from_filename.side_effect = IOError()
        from_filename.side_effect.errno = errno.EACCES
        self.assertRaises(
            IOError, config.get_pxe_template,
            *factory.make_names("purpose", "arch", "subarch"))


def parse_pxe_config(text):
    """Parse a PXE config file.

    Returns a structure like the following, defining the sections::

      {"section_label": {"KERNEL": "...", "INITRD": "...", ...}, ...}

    Additionally, the returned dict - which is actually an `OrderedDict`, as
    are all mappings returned from this function - has a `header` attribute.
    This is an `OrderedDict` of the settings in the top part of the PXE config
    file, the part before any labelled sections.
    """
    result = OrderedDict()
    sections = re.split("^LABEL ", text, flags=re.MULTILINE)
    for index, section in enumerate(sections):
        elements = [
            line.split(None, 1) for line in section.splitlines()
            if line and not line.isspace()
            ]
        if index == 0:
            result.header = OrderedDict(elements)
        else:
            [label] = elements.pop(0)
            if label in result:
                raise AssertionError(
                    "Section %r already defined" % label)
            result[label] = OrderedDict(elements)
    return result


class TestParsePXEConfig(MAASTestCase):
    """Tests for `parse_pxe_config`."""

    def test_parse_with_no_header(self):
        config = parse_pxe_config("LABEL foo\nOPTION setting")
        self.assertEqual({"foo": {"OPTION": "setting"}}, config)
        self.assertEqual({}, config.header)

    def test_parse_with_no_labels(self):
        config = parse_pxe_config("OPTION setting")
        self.assertEqual({"OPTION": "setting"}, config.header)
        self.assertEqual({}, config)


class TestRenderPXEConfig(MAASTestCase):
    """Tests for `provisioningserver.pxe.config.render_pxe_config`."""

    def test_render(self):
        # Given the right configuration options, the PXE configuration is
        # correctly rendered.
        params = make_kernel_parameters(purpose="install")
        output = render_pxe_config(kernel_params=params)
        # The output is always a Unicode string.
        self.assertThat(output, IsInstance(unicode))
        # The template has rendered without error. PXELINUX configurations
        # typically start with a DEFAULT line.
        self.assertThat(output, StartsWith("DEFAULT "))
        # The PXE parameters are all set according to the options.
        image_dir = compose_image_path(
            arch=params.arch, subarch=params.subarch,
            release=params.release, purpose=params.purpose)
        self.assertThat(
            output, MatchesAll(
                MatchesRegex(
                    r'.*^\s+KERNEL %s/linux$' % re.escape(image_dir),
                    re.MULTILINE | re.DOTALL),
                MatchesRegex(
                    r'.*^\s+INITRD %s/initrd[.]gz$' % re.escape(image_dir),
                    re.MULTILINE | re.DOTALL),
                MatchesRegex(
                    r'.*^\s+APPEND .+?$',
                    re.MULTILINE | re.DOTALL)))

    def test_render_with_extra_arguments_does_not_affect_output(self):
        # render_pxe_config() allows any keyword arguments as a safety valve.
        options = {
            "kernel_params": make_kernel_parameters(purpose="install"),
        }
        # Capture the output before sprinking in some random options.
        output_before = render_pxe_config(**options)
        # Sprinkle some magic in.
        options.update(
            (factory.make_name("name"), factory.make_name("value"))
            for _ in range(10))
        # Capture the output after sprinking in some random options.
        output_after = render_pxe_config(**options)
        # The generated template is the same.
        self.assertEqual(output_before, output_after)

    def test_render_pxe_config_with_local_purpose(self):
        # If purpose is "local", the config.localboot.template should be
        # used.
        options = {
            "kernel_params": make_kernel_parameters(purpose="local"),
            }
        output = render_pxe_config(**options)
        self.assertIn("LOCALBOOT 0", output)

    def test_render_pxe_config_with_local_purpose_i386_arch(self):
        # Intel i386 is a special case and needs to use the chain.c32
        # loader as the LOCALBOOT PXE directive is unreliable.
        options = {
            "kernel_params": make_kernel_parameters(
                arch="i386", purpose="local"),
        }
        output = render_pxe_config(**options)
        self.assertIn("chain.c32", output)
        self.assertNotIn("LOCALBOOT", output)

    def test_render_pxe_config_with_local_purpose_amd64_arch(self):
        # Intel amd64 is a special case and needs to use the chain.c32
        # loader as the LOCALBOOT PXE directive is unreliable.
        options = {
            "kernel_params": make_kernel_parameters(
                arch="amd64", purpose="local"),
        }
        output = render_pxe_config(**options)
        self.assertIn("chain.c32", output)
        self.assertNotIn("LOCALBOOT", output)


class TestRenderArmhfSubarchScenarios(MAASTestCase):
    """See bug https://bugs.launchpad.net/maas/+bug/1166994"""

    scenarios = [
        ("install_precise", dict(
            arch="armhf", purpose="install", release="precise",
            expect_in_output="highbank")),
        ("install_quantal", dict(
            arch="armhf", purpose="install", release="quantal",
            expect_in_output="highbank")),
        ("install_saucy", dict(
            arch="armhf", purpose="install", release="saucy",
            expect_in_output="generic")),
        ("commission_precise", dict(
            arch="armhf", purpose="commissioning", release="precise",
            expect_in_output="highbank")),
        ("commission_quantal", dict(
            arch="armhf", purpose="commissioning", release="quantal",
            expect_in_output="highbank")),
        ("commission_saucy", dict(
            arch="armhf", purpose="commissioning", release="saucy",
            expect_in_output="generic")),
    ]

    def test_highbank_scenarios(self):
        # get_ephemeral_name depends on ephemeral images being present but
        # doesn't affect the test outcome, so patch it out.
        self.patch(
            kernel_opts,
            "get_ephemeral_name").return_value = "ephemeral_name"
        options = {
            "kernel_params": make_kernel_parameters(
                arch=self.arch, purpose=self.purpose, subarch="highbank",
                release=self.release),
        }
        output = render_pxe_config(**options)
        self.assertIn(self.expect_in_output, output)


class TestRenderPXEConfigScenarios(MAASTestCase):
    """Tests for `provisioningserver.pxe.config.render_pxe_config`."""

    scenarios = [
        ("commissioning", dict(purpose="commissioning")),
        ("xinstall", dict(purpose="xinstall")),
        ]

    def test_render_pxe_config_scenarios(self):
        # The commissioning config uses an extra PXELINUX module to auto
        # select between i386 and amd64.
        get_ephemeral_name = self.patch(kernel_opts, "get_ephemeral_name")
        get_ephemeral_name.return_value = factory.make_name("ephemeral")
        options = {
            "kernel_params": make_kernel_parameters(purpose=self.purpose),
        }
        output = render_pxe_config(**options)
        config = parse_pxe_config(output)
        # The default section is defined.
        default_section_label = config.header["DEFAULT"]
        self.assertThat(config, Contains(default_section_label))
        default_section = config[default_section_label]
        # The default section uses the ifcpu64 module, branching to the "i386"
        # or "amd64" labels accordingly.
        self.assertEqual("ifcpu64.c32", default_section["KERNEL"])
        self.assertEqual(
            ["amd64", "--", "i386"],
            default_section["APPEND"].split())
        # Both "i386" and "amd64" sections exist.
        self.assertThat(config, ContainsAll(("i386", "amd64")))
        # Each section defines KERNEL, INITRD, and APPEND settings.  The
        # KERNEL and INITRD ones contain paths referring to their
        # architectures.
        for section_label in ("i386", "amd64"):
            section = config[section_label]
            self.assertThat(
                section, ContainsAll(("KERNEL", "INITRD", "APPEND")))
            contains_arch_path = StartsWith("%s/" % section_label)
            self.assertThat(section["KERNEL"], contains_arch_path)
            self.assertThat(section["INITRD"], contains_arch_path)
            self.assertIn("APPEND", section)
