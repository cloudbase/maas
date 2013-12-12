# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""API credentials for node-group workers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )
from logging import getLogger
logger = getLogger(__name__)

str = None

__metaclass__ = type
__all__ = [
    'get_recorded_api_credentials',
    'get_recorded_nodegroup_uuid',
    'record_api_credentials',
    'record_nodegroup_uuid',
    ]

from apiclient.creds import convert_string_to_tuple
from provisioningserver import cache

# Cache key for the API credentials as last sent by the server.
API_CREDENTIALS_CACHE_KEY = 'api_credentials'

# Cache key for the uuid of the nodegroup that this worker manages.
NODEGROUP_UUID_CACHE_KEY = 'nodegroup_uuid'


def record_api_credentials(api_credentials):
    """Update the recorded API credentials.

    :param api_credentials: Newly received API credentials, in the form of
        a single string: consumer key, resource token, and resource seret
        separated by colons.
    """
    cache.cache.set(API_CREDENTIALS_CACHE_KEY, api_credentials)


def get_recorded_api_credentials():
    """Return API credentials as last received from the server.

    :return: If credentials have been received, a tuple of
        (consumer_key, resource_token, resource_secret) as expected by
        :class:`MAASOauth`.  Otherwise, None.
    """
    credentials_string = cache.cache.get(API_CREDENTIALS_CACHE_KEY)
    if credentials_string is None:
        return None
    else:
        return convert_string_to_tuple(credentials_string)


def record_nodegroup_uuid(nodegroup_uuid):
    """Record the uuid of the nodegroup we manage, as sent by the server."""
    cache.cache.set(NODEGROUP_UUID_CACHE_KEY, nodegroup_uuid)


def get_recorded_nodegroup_uuid():
    """Return the uuid of this worker's nodegroup, as sent by the server.

    If the server has not sent the name yet, returns None.
    """
    return cache.cache.get(NODEGROUP_UUID_CACHE_KEY)
