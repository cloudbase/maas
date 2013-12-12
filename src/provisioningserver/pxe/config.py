# Copyright 2012-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generating PXE configuration files.

For more about the format of these files:

http://www.syslinux.org/wiki/index.php/SYSLINUX#How_do_I_Configure_SYSLINUX.3F
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'render_pxe_config',
    ]


from errno import ENOENT
from os import path

from maasserver.enum import DISTRO_SERIES
from provisioningserver.kernel_opts import (
    compose_kernel_command_line,
    compose_kernel_command_line_centos)
from provisioningserver.pxe.tftppath import compose_image_path
from provisioningserver.utils import locate_config
import tempita

# Location of PXE templates, relative to the configuration directory.
TEMPLATES_DIR = 'templates/pxe'


def gen_pxe_template_filenames(purpose, arch, subarch):
    """List possible PXE template filenames.

    :param purpose: The boot purpose, e.g. "local".
    :param arch: Main machine architecture.
    :param subarch: Sub-architecture, or "generic" if there is none.
    :param release: The Ubuntu release to be used.

    Returns a list of possible PXE template filenames using the following
    lookup order:

      config.{purpose}.{arch}.{subarch}.template
      config.{purpose}.{arch}.template
      config.{purpose}.template
      config.template

    """
    elements = [purpose, arch, subarch]
    while len(elements) >= 1:
        yield "config.%s.template" % ".".join(elements)
        elements.pop()
    yield "config.template"


def get_pxe_template(purpose, arch, subarch):
    pxe_templates_dir = locate_config(TEMPLATES_DIR)
    # Templates are loaded each time here so that they can be changed on
    # the fly without restarting the provisioning server.
    for filename in gen_pxe_template_filenames(purpose, arch, subarch):
        template_name = path.join(pxe_templates_dir, filename)
        try:
            return tempita.Template.from_filename(
                template_name, encoding="UTF-8")
        except IOError as error:
            if error.errno != ENOENT:
                raise
    else:
        raise AssertionError(
            "No PXE template found in %r!" % pxe_templates_dir)


def render_pxe_config(kernel_params, **extra):
    BOOT_FILES = {
        DISTRO_SERIES.centos6: {
            'initrd': 'initrd.img',
            'linux': 'vmlinuz'
        },
        'default': {
            'initrd': 'initrd.gz',
            'linux': 'linux'
        }
    }
    KERNEL_COMMAND = {
        DISTRO_SERIES.centos6: compose_kernel_command_line_centos,
        'default': compose_kernel_command_line
    }
    """Render a PXE configuration file as a unicode string.

    :param kernel_params: An instance of `KernelParameters`.
    :param extra: Allow for other arguments. This is a safety valve;
        parameters generated in another component (for example, see
        `TFTPBackend.get_config_reader`) won't cause this to break.
    """
    template = get_pxe_template(
        kernel_params.purpose, kernel_params.arch,
        kernel_params.subarch)

    # The locations of the kernel image and the initrd are defined by
    # update_install_files(), in scripts/maas-import-pxe-files.

    def image_dir(params):
        return compose_image_path(
            params.arch, params.subarch,
            params.release, params.purpose)

    def initrd_path(params):
        info = BOOT_FILES.get(
            params.release,
            BOOT_FILES['default'])
        return "%s/%s" % (image_dir(params), info['initrd'])

    def kernel_path(params):
        info = BOOT_FILES.get(
            params.release,
            BOOT_FILES['default'])
        return "%s/%s" % (image_dir(params), info['linux'])

    def kernel_command(params):
        compose_method = KERNEL_COMMAND.get(
            params.release,
            KERNEL_COMMAND['default'])
        return compose_method(params)

    namespace = {
        "initrd_path": initrd_path,
        "kernel_command": kernel_command,
        "kernel_params": kernel_params,
        "kernel_path": kernel_path,
    }
    return template.substitute(namespace)
