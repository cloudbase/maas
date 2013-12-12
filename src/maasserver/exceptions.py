# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Exceptions."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    "ExternalComponentException",
    "MAASException",
    "MAASAPIBadRequest",
    "MAASAPIException",
    "MAASAPINotFound",
    "NodeStateViolation",
    "NodeGroupMisconfiguration",
    ]


import httplib

from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    )


class MAASException(Exception):
    """Base class for MAAS' exceptions."""


class CannotDeleteUserException(Exception):
    """User can't be deleted."""


class NoRabbit(MAASException):
    """Could not reach RabbitMQ."""


class MAASAPIException(Exception):
    """Base class for MAAS' API exceptions.

    :ivar api_error: The HTTP code that should be returned when this error
        is raised in the API (defaults to 500: "Internal Server Error").

    """
    api_error = httplib.INTERNAL_SERVER_ERROR

    def make_http_response(self):
        """Create an :class:`HttpResponse` representing this exception."""
        encoding = b'utf-8'
        return HttpResponse(
            status=self.api_error, content=unicode(self).encode(encoding),
            mimetype=b"text/plain; charset=%s" % encoding)


class ExternalComponentException(MAASAPIException):
    """An external component failed."""


class MAASAPIBadRequest(MAASAPIException):
    api_error = httplib.BAD_REQUEST


class MAASAPINotFound(MAASAPIException):
    api_error = httplib.NOT_FOUND


class Unauthorized(MAASAPIException):
    """HTTP error 401: Unauthorized.  Login required."""
    api_error = httplib.UNAUTHORIZED


class NodeStateViolation(MAASAPIException):
    """Operation on node not possible given node's current state."""
    api_error = httplib.CONFLICT


class NodesNotAvailable(NodeStateViolation):
    """Requested node(s) are not available to be acquired."""
    api_error = httplib.CONFLICT


class Redirect(MAASAPIException):
    """Redirect.  The exception message is the target URL."""
    api_error = httplib.FOUND

    def make_http_response(self):
        return HttpResponseRedirect(unicode(self))


class NodeGroupMisconfiguration(MAASAPIException):
    """Node Groups (aka Cluster Controllers) are misconfigured.

    This might mean that more than one controller is marked as managing the
    same network
    """
    api_error = httplib.CONFLICT
