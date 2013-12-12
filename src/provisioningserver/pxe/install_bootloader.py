# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Install a PXE pre-boot loader for TFTP download."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    "add_arguments",
    "run",
    ]

import filecmp
import os.path
from shutil import copyfile

from provisioningserver.config import Config
from provisioningserver.pxe.tftppath import (
    compose_bootloader_path,
    locate_tftp_path,
    )


def make_destination(tftproot):
    """Locate a loader's destination, creating the directory if needed.

    :param tftproot: The root directory served up by the TFTP server,
        e.g. /var/lib/maas/tftp/.
    :return: Full path describing the directory that the installed loader
        should end up having.
    """
    path = locate_tftp_path(
        compose_bootloader_path(),
        tftproot=tftproot)
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    return directory


def are_identical_files(old, new):
    """Are `old` and `new` identical?

    If `old` does not exist, the two are considered different (`new` is
    assumed to exist).
    """
    if os.path.isfile(old):
        return filecmp.cmp(old, new, shallow=False)
    else:
        return False


def install_bootloader(loader, destination):
    """Install bootloader file at path `loader` as `destination`.

    Installation will be atomic.  If an identical loader is already
    installed, it will be left untouched.

    However it is still conceivable, depending on the TFTP implementation,
    that a download that is already in progress may suddenly start receiving
    data from the new file instead of the one it originally started
    downloading.

    :param loader: Name of loader to install.
    :param destination: Loader's intended filename, including full path,
        where it will become available over TFTP.
    """
    if are_identical_files(destination, loader):
        return

    # Copy new loader next to the old one, to ensure that it is on the
    # same filesystem.  Once it is, we can replace the old one with an
    # atomic rename operation.
    temp_file = '%s.new' % destination
    if os.path.exists(temp_file):
        os.remove(temp_file)
    copyfile(loader, temp_file)
    os.rename(temp_file, destination)


def add_arguments(parser):
    parser.add_argument(
        '--loader', dest='loader', default=None,
        help="PXE pre-boot loader to install.")


def run(args):
    """Install a PXE pre-boot loader into the TFTP directory structure.

    This won't overwrite an existing loader if its contents are unchanged.
    """
    config = Config.load(args.config_file)
    tftproot = config["tftp"]["root"]
    destination_path = make_destination(tftproot)
    destination = os.path.join(destination_path, os.path.basename(args.loader))
    install_bootloader(args.loader, destination)
