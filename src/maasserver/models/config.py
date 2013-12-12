# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Configuration items."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'Config',
    ]


from collections import defaultdict
import copy
from socket import gethostname

from django.db.models import (
    CharField,
    Manager,
    Model,
    )
from django.db.models.signals import post_save
from maasserver import DefaultMeta
from maasserver.enum import (
    DISTRO_SERIES,
    NODE_AFTER_COMMISSIONING_ACTION,
    )
from maasserver.fields import JSONObjectField
from provisioningserver.enum import POWER_TYPE


def get_default_config():
    return {
        ## settings default values.
        # Commissioning section configuration.
        'after_commissioning': NODE_AFTER_COMMISSIONING_ACTION.DEFAULT,
        'check_compatibility': False,
        'node_power_type': POWER_TYPE.WAKE_ON_LAN,
        # Ubuntu section configuration.
        'fallback_master_archive': False,
        'keep_mirror_list_uptodate': False,
        'fetch_new_releases': False,
        'main_archive': 'http://archive.ubuntu.com/ubuntu',
        'ports_archive': 'http://ports.ubuntu.com/ubuntu-ports',
        'cloud_images_archive': 'https://maas.ubuntu.com/images',
        # Network section configuration.
        'maas_name': gethostname(),
        'enlistment_domain': b'local',
        'default_distro_series': DISTRO_SERIES.precise,
        'commissioning_distro_series': DISTRO_SERIES.precise,
        'http_proxy': None,
        'upstream_dns': None,
        'ntp_server': '91.189.94.4',  # ntp.ubuntu.com
        ## /settings
        }


# Default values for config options.
DEFAULT_CONFIG = get_default_config()


class ConfigManager(Manager):
    """Manager for Config model class.

    Don't import or instantiate this directly; access as `Config.objects.
    """

    def __init__(self):
        super(ConfigManager, self).__init__()
        self._config_changed_connections = defaultdict(set)

    def get_config(self, name, default=None):
        """Return the config value corresponding to the given config name.
        Return None or the provided default if the config value does not
        exist.

        :param name: The name of the config item.
        :type name: unicode
        :param name: The optional default value to return if no such config
            item exists.
        :type name: object
        :return: A config value.
        :raises: Config.MultipleObjectsReturned
        """
        try:
            return self.get(name=name).value
        except Config.DoesNotExist:
            return copy.deepcopy(DEFAULT_CONFIG.get(name, default))

    def get_config_list(self, name):
        """Return the config value list corresponding to the given config
        name.

        :param name: The name of the config items.
        :type name: unicode
        :return: A list of the config values.
        :rtype: list
        """
        return [config.value for config in self.filter(name=name)]

    def set_config(self, name, value):
        """Set or overwrite a config value.

        :param name: The name of the config item to set.
        :type name: unicode
        :param value: The value of the config item to set.
        :type value: Any jsonizable object
        """
        config, freshly_created = self.get_or_create(
            name=name, defaults=dict(value=value))
        if not freshly_created:
            config.value = value
            config.save()

    def config_changed_connect(self, config_name, method):
        """Connect a method to Django's 'update' signal for given config name.

        :param config_name: The name of the config item to track.
        :type config_name: unicode
        :param method: The method to be called.
        :type method: callable

        The provided callable should follow Django's convention.  E.g::

          >>> def callable(sender, instance, created, **kwargs):
          ...     pass

          >>> Config.objects.config_changed_connect('config_name', callable)

        """
        self._config_changed_connections[config_name].add(method)

    def _config_changed(self, sender, instance, created, **kwargs):
        for connection in self._config_changed_connections[instance.name]:
            connection(sender, instance, created, **kwargs)


class Config(Model):
    """Configuration settings item.

    :ivar name: The name of the configuration option.
    :type name: unicode
    :ivar value: The configuration value.
    :type value: Any pickleable python object.
    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    name = CharField(max_length=255, unique=False)
    value = JSONObjectField(null=True)

    objects = ConfigManager()

    def __unicode__(self):
        return "%s: %s" % (self.name, self.value)


# Connect config manager's _config_changed to Config's post-save signal.
post_save.connect(Config.objects._config_changed, sender=Config)
