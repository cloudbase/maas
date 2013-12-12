# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Twisted Application Plugin for the MAAS provisioning server."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []


try:
    from provisioningserver.plugin import ProvisioningServiceMaker
except ImportError:
    pass  # Ignore.
else:
    # Construct objects which *provide* the relevant interfaces. The name of
    # these variables is irrelevant, as long as there are *some* names bound
    # to providers of IPlugin and IServiceMaker.
    service = ProvisioningServiceMaker("maas-pserv", "...")  # TODO: finish
