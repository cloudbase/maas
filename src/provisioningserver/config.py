# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""MAAS Provisioning Configuration.

Configuration for most elements of a Cluster Controller can and be obtained by
using this module's `Config` class. At the time of writing the exceptions are
the Celery worker's configuration, the `CLUSTER_UUID` and `MAAS_URL`
environment variables (see `provisioningserver.cluster_config`), and the
configuration for ``maas-import-pxe-files`` (soon to be deprecated) and
``maas-import-ephemerals`` (deprecated).

It's pretty simple. Typical usage is::

  >>> config = Config.load_from_cache()
  {...}

This reads in a configuration file from `Config.DEFAULT_FILENAME` (see a note
about that later). The configuration file is parsed as YAML, and a plain `dict`
is returned with configuration nested within it. The configuration is validated
at load time using `formencode`. The policy for validation is laid out in this
module; see the various `formencode.Schema` subclasses.

All configuration is optional, and a sensible default is provided in every
instance. When adding or changing settings bear this policy in mind, and also
that the defaults should be geared towards a system in production, and not a
development environment. The defaults can be obtained by calling
`Config.get_defaults()`.

An alternative to `Config.load_from_cache()` is `Config.load()`, which loads
and validates a configuration file while bypassing the cache.  See `Config` for
other useful functions.

`Config.DEFAULT_FILENAME` is a class property, so does not need to be
referenced via an instance of `Config`. It refers to the
``MAAS_PROVISIONING_SETTINGS`` environment variable in the first instance, but
has a sensible default too. You can write to this property and it will update
the environment so that child processes will also use the same configuration
filename. To revert to the default - i.e. erase the environment variable - you
can `del Config.DEFAULT_FILENAME`.

When testing, see `provisioningserver.testing.config.ConfigFixture` to
temporarily use a different configuration.

"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    "Config",
    ]

from copy import deepcopy
from getpass import getuser
from os import environ
import os.path
from shutil import copyfile
from threading import RLock

from formencode import Schema
from formencode.declarative import DeclarativeMeta
from formencode.validators import (
    Int,
    RequireIfPresent,
    Set,
    String,
    )
from provisioningserver.utils import atomic_write
import yaml


class ConfigOops(Schema):
    """Configuration validator for OOPS options."""

    if_key_missing = None

    directory = String(if_missing=b"")
    reporter = String(if_missing=b"")

    chained_validators = (
        RequireIfPresent("reporter", present="directory"),
        )


class ConfigBroker(Schema):
    """Configuration validator for message broker options."""

    if_key_missing = None

    host = String(if_missing=b"localhost")
    port = Int(min=1, max=65535, if_missing=5673)
    username = String(if_missing=getuser())
    password = String(if_missing=b"test")
    vhost = String(if_missing="/")


class ConfigTFTP(Schema):
    """Configuration validator for the TFTP service."""

    if_key_missing = None

    root = String(if_missing="/var/lib/maas/tftp")
    port = Int(min=1, max=65535, if_missing=69)
    generator = String(if_missing=b"http://localhost/MAAS/api/1.0/pxeconfig/")


class ConfigBootEphemeral(Schema):
    """Configuration validator for ephemeral boot configuration."""

    if_key_missing = None

    images_directory = String(if_missing="/var/lib/maas/ephemeral")
    releases = Set(if_missing=None)


class ConfigBoot(Schema):
    """Configuration validator for boot configuration."""

    if_key_missing = None

    ephemeral = ConfigBootEphemeral
    architectures = Set(if_missing=None)


class ConfigWindows(Schema):
    """Configuration validator for boot configuration."""

    if_key_missing = None
    remote_path = String(if_missing="\\\\192.168.100.1\\reminst")


class ConfigMeta(DeclarativeMeta):
    """Metaclass for the root configuration schema."""

    def _get_default_filename(cls):
        # Avoid circular imports.
        from provisioningserver.utils import locate_config

        # Get the configuration filename from the environment. Failing that,
        # look for the configuration in its default locations.
        return environ.get(
            "MAAS_PROVISIONING_SETTINGS",
            locate_config('pserv.yaml'))

    def _set_default_filename(cls, filename):
        # Set the configuration filename in the environment.
        environ["MAAS_PROVISIONING_SETTINGS"] = filename

    def _delete_default_filename(cls):
        # Remove any setting of the configuration filename from the
        # environment.
        environ.pop("MAAS_PROVISIONING_SETTINGS", None)

    DEFAULT_FILENAME = property(
        _get_default_filename, _set_default_filename,
        _delete_default_filename, doc=(
            "The default config file to load. Refers to "
            "MAAS_PROVISIONING_SETTINGS in the environment."))


class Config(Schema):
    """Configuration validator."""

    __metaclass__ = ConfigMeta

    if_key_missing = None

    logfile = String(if_empty=b"pserv.log", if_missing=b"pserv.log")
    oops = ConfigOops
    broker = ConfigBroker
    tftp = ConfigTFTP
    boot = ConfigBoot
    windows = ConfigWindows

    @classmethod
    def parse(cls, stream):
        """Load a YAML configuration from `stream` and validate."""
        return cls.to_python(yaml.safe_load(stream))

    @classmethod
    def load(cls, filename=None):
        """Load a YAML configuration from `filename` and validate."""
        if filename is None:
            filename = cls.DEFAULT_FILENAME
        with open(filename, "rb") as stream:
            return cls.parse(stream)

    @classmethod
    def _get_backup_name(cls, message, filename=None):
        if filename is None:
            filename = cls.DEFAULT_FILENAME
        return "%s.%s.bak" % (filename, message)

    @classmethod
    def create_backup(cls, message, filename=None):
        """Create a backup of the YAML configuration.

        The given 'message' will be used in the name of the backup file.
        """
        backup_name = cls._get_backup_name(message, filename)
        if filename is None:
            filename = cls.DEFAULT_FILENAME
        copyfile(filename, backup_name)

    @classmethod
    def save(cls, config, filename=None):
        """Save a YAML configuration to `filename`, or to the default file."""
        if filename is None:
            filename = cls.DEFAULT_FILENAME
        dump = yaml.safe_dump(config)
        atomic_write(dump, filename)

    _cache = {}
    _cache_lock = RLock()

    @classmethod
    def load_from_cache(cls, filename=None):
        """Load or return a previously loaded configuration.

        Keeps an internal cache of config files.  If the requested config file
        is not in cache, it is loaded and inserted into the cache first.

        Each call returns a distinct (deep) copy of the requested config from
        the cache, so the caller can modify its own copy without affecting what
        other call sites see.

        This is thread-safe, so is okay to use from Django, for example.
        """
        if filename is None:
            filename = cls.DEFAULT_FILENAME
        filename = os.path.abspath(filename)
        with cls._cache_lock:
            if filename not in cls._cache:
                with open(filename, "rb") as stream:
                    cls._cache[filename] = cls.parse(stream)
            return deepcopy(cls._cache[filename])

    @classmethod
    def field(target, *steps):
        """Obtain a field by following `steps`."""
        for step in steps:
            target = target.fields[step]
        return target

    @classmethod
    def get_defaults(cls):
        """Return the default configuration."""
        return cls.to_python({})
