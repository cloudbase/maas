# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

"""Access middleware."""

str = None

__metaclass__ = type
__all__ = [
    "AccessMiddleware",
    "APIErrorsMiddleware",
    "ErrorsMiddleware",
    "ExceptionMiddleware",
    ]

from abc import (
    ABCMeta,
    abstractproperty,
    )
import httplib
import json
import logging
import re

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    )
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    )
from django.http.request import build_request_repr
from django.utils.http import urlquote_plus
from maasserver import logger
from maasserver.exceptions import (
    ExternalComponentException,
    MAASAPIException,
    )


def get_relative_path(path):
    """If the url prefix settings.FORCE_SCRIPT_NAME is not None: strip the
    prefix from the given path.
    """
    prefix = settings.FORCE_SCRIPT_NAME
    if prefix is None:
        return path
    elif path.startswith(prefix):
        return path[len(prefix):]
    else:
        assert False, "Prefix '%s' not in path '%s'" % (prefix, path)


class AccessMiddleware:
    """Protect access to views.

    Most UI views are visible only to logged-in users, but there are pages
    that are accessible to anonymous users (e.g. the login page!) or that
    use other authentication (e.g. the MAAS API, which is managed through
    piston).
    """

    def __init__(self):
        # URL prefixes that do not require authentication by Django.
        public_url_roots = [
            # Login page: must be visible to anonymous users.
            reverse('login'),
            # The combo loaders are publicly accessible.
            reverse('combo-yui'),
            reverse('combo-maas'),
            reverse('combo-raphael'),
            # Static resources are publicly visible.
            settings.STATIC_URL_PATTERN,
            reverse('robots'),
            reverse('api-doc'),
            # Metadata service is for use by nodes; no login.
            reverse('metadata'),
            # API calls are protected by piston.
            settings.API_URL_REGEXP,
            ]
        self.public_urls = re.compile("|".join(public_url_roots))
        self.login_url = reverse('login')

    def process_request(self, request):
        # Public urls.
        if self.public_urls.match(get_relative_path(request.path)):
            return None
        else:
            if request.user.is_anonymous():
                return HttpResponseRedirect("%s?next=%s" % (
                    settings.LOGIN_URL, urlquote_plus(request.path)))
            else:
                return None


class ExternalComponentsMiddleware:
    """Middleware check external components at regular intervals.

    Right now nothing is checked, because Cobbler was the only component
    we checked, and we just ditched it.
    """
    def process_request(self, request):
        # This middleware hijacks the request to perform checks.  Any
        # error raised during these checks should be caught to avoid
        # disturbing the handling of the request.  Proper error reporting
        # should be handled in the check method itself.
        try:
            # TODO: Components checks here.
            pass
        except Exception:
            pass
        return None


class ExceptionMiddleware:
    """Convert exceptions into appropriate HttpResponse responses.

    For example, a MAASAPINotFound exception processed by a middleware
    based on this class will result in an http 404 response to the client.
    Validation errors become "bad request" responses.

    Use this as a base class for middleware_ classes that apply to
    sub-trees of the http path tree.  Subclass this class, provide a
    `path_regex`, and register your concrete class in
    settings.MIDDLEWARE_CLASSES.  Exceptions in that sub-tree will then
    come out as HttpResponses, insofar as they map neatly.

    .. middleware: https://docs.djangoproject.com
       /en/dev/topics/http/middleware/
    """

    __metaclass__ = ABCMeta

    path_regex = abstractproperty(
        "Regular expression for the paths that this should apply to.")

    def __init__(self):
        self.path_matcher = re.compile(self.path_regex)

    def process_exception(self, request, exception):
        """Django middleware callback."""
        if not self.path_matcher.match(get_relative_path(request.path)):
            # Not a path we're handling exceptions for.
            return None

        encoding = b'utf-8'
        if isinstance(exception, MAASAPIException):
            # This type of exception knows how to translate itself into
            # an http response.
            return exception.make_http_response()
        elif isinstance(exception, ValidationError):
            if hasattr(exception, 'message_dict'):
                # Complex validation error with multiple fields:
                # return a json version of the message_dict.
                return HttpResponseBadRequest(
                    json.dumps(exception.message_dict),
                    content_type='application/json')
            else:
                # Simple validation error: return the error message.
                return HttpResponseBadRequest(
                    unicode(''.join(exception.messages)).encode(encoding),
                    mimetype=b"text/plain; charset=%s" % encoding)
        elif isinstance(exception, PermissionDenied):
            return HttpResponseForbidden(
                content=unicode(exception).encode(encoding),
                mimetype=b"text/plain; charset=%s" % encoding)
        else:
            # Return an API-readable "Internal Server Error" response.
            return HttpResponse(
                content=unicode(exception).encode(encoding),
                status=httplib.INTERNAL_SERVER_ERROR,
                mimetype=b"text/plain; charset=%s" % encoding)


class APIErrorsMiddleware(ExceptionMiddleware):
    """Report exceptions from API requests as HTTP error responses."""

    path_regex = settings.API_URL_REGEXP


class ErrorsMiddleware:
    """Handle ExternalComponentException exceptions in POST requests: add a
    message with the error string and redirect to the same page (using GET).
    """

    def process_exception(self, request, exception):
        should_process_exception = (
            request.method == 'POST' and
            isinstance(exception, ExternalComponentException))
        if should_process_exception:
            messages.error(request, unicode(exception))
            return HttpResponseRedirect(request.path)
        else:
            # Not an ExternalComponentException or not a POST request: do not
            # handle it.
            return None


class ExceptionLoggerMiddleware:

    def process_exception(self, request, exception):
        import traceback
        import sys
        exc_info = sys.exc_info()
        logger.error(" Exception: %s ".center(79, "#") % unicode(exception))
        logger.error(''.join(traceback.format_exception(*exc_info)))


class DebuggingLoggerMiddleware:

    log_level = logging.DEBUG

    def process_request(self, request):
        if logger.isEnabledFor(self.log_level):
            header = " Request dump ".center(79, "#")
            logger.log(
                self.log_level,
                "%s\n%s", header, build_request_repr(request))
        return None  # Allow request processing to continue unabated.

    def process_response(self, request, response):
        if logger.isEnabledFor(self.log_level):
            header = " Response dump ".center(79, "#")
            content = getattr(response, "content", "{no content}")
            try:
                decoded_content = content.decode('utf-8')
            except UnicodeDecodeError:
                logger.log(
                    self.log_level,
                    "%s\n%s", header, "** non-utf-8 (binary?) content **")
            else:
                logger.log(
                    self.log_level,
                    "%s\n%s", header, decoded_content)
        return response  # Return response unaltered.
