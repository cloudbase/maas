# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Settings views."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    "AccountsAdd",
    "AccountsDelete",
    "AccountsEdit",
    "AccountsView",
    "settings",
    ]

from django.contrib import messages
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import (
    get_object_or_404,
    render_to_response,
    )
from django.template import RequestContext
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    )
from django.views.generic.base import TemplateView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin
from maasserver.enum import NODEGROUP_STATUS
from maasserver.exceptions import CannotDeleteUserException
from maasserver.forms import (
    CommissioningForm,
    EditUserForm,
    GlobalKernelOptsForm,
    MAASAndNetworkForm,
    NewUserCreationForm,
    UbuntuForm,
    )
from maasserver.models import (
    NodeGroup,
    UserProfile,
    )
from maasserver.views import process_form
from metadataserver.models import CommissioningScript


class AccountsView(DetailView):
    """Read-only view of user's account information."""

    template_name = 'maasserver/user_view.html'

    context_object_name = 'view_user'

    def get_object(self):
        username = self.kwargs.get('username', None)
        user = get_object_or_404(User, username=username)
        return user


class AccountsAdd(CreateView):
    """Add-user view."""

    form_class = NewUserCreationForm

    template_name = 'maasserver/user_add.html'

    context_object_name = 'new_user'

    def get_success_url(self):
        return reverse('settings')

    def form_valid(self, form):
        messages.info(self.request, "User added.")
        return super(AccountsAdd, self).form_valid(form)


class AccountsDelete(DeleteView):

    template_name = 'maasserver/user_confirm_delete.html'
    context_object_name = 'user_to_delete'

    def get_object(self):
        username = self.kwargs.get('username', None)
        user = get_object_or_404(User, username=username)
        return user.get_profile()

    def get_next_url(self):
        return reverse('settings')

    def delete(self, request, *args, **kwargs):
        profile = self.get_object()
        username = profile.user.username
        try:
            profile.delete()
            messages.info(request, "User %s deleted." % username)
        except CannotDeleteUserException as e:
            messages.info(request, unicode(e))
        return HttpResponseRedirect(self.get_next_url())


class AccountsEdit(TemplateView, ModelFormMixin,
                   SingleObjectTemplateResponseMixin):

    model = User
    template_name = 'maasserver/user_edit.html'

    def get_object(self):
        username = self.kwargs.get('username', None)
        return get_object_or_404(User, username=username)

    def respond(self, request, profile_form, password_form):
        """Generate a response."""
        return self.render_to_response({
            'profile_form': profile_form,
            'password_form': password_form,
            })

    def get(self, request, *args, **kwargs):
        """Called by `TemplateView`: handle a GET request."""
        self.object = user = self.get_object()
        profile_form = EditUserForm(instance=user, prefix='profile')
        password_form = AdminPasswordChangeForm(user=user, prefix='password')
        return self.respond(request, profile_form, password_form)

    def post(self, request, *args, **kwargs):
        """Called by `TemplateView`: handle a POST request."""
        self.object = user = self.get_object()
        next_page = reverse('settings')

        # Process the profile-editing form, if that's what was submitted.
        profile_form, response = process_form(
            request, EditUserForm, next_page, 'profile', "Profile updated.",
            {'instance': user})
        if response is not None:
            return response

        # Process the password change form, if that's what was submitted.
        password_form, response = process_form(
            request, AdminPasswordChangeForm, next_page, 'password',
            "Password updated.", {'user': user})
        if response is not None:
            return response

        return self.respond(request, profile_form, password_form)


def settings(request):
    user_list = UserProfile.objects.all_users().order_by('username')
    # Process the MAAS & network form.
    maas_and_network_form, response = process_form(
        request, MAASAndNetworkForm, reverse('settings'), 'maas_and_network',
        "Configuration updated.")
    if response is not None:
        return response

    # Process the Commissioning form.
    commissioning_form, response = process_form(
        request, CommissioningForm, reverse('settings'), 'commissioning',
        "Configuration updated.")
    if response is not None:
        return response

    # Process the Ubuntu form.
    ubuntu_form, response = process_form(
        request, UbuntuForm, reverse('settings'), 'ubuntu',
        "Configuration updated.")
    if response is not None:
        return response

    # Process the Global Kernel Opts form.
    kernelopts_form, response = process_form(
        request, GlobalKernelOptsForm, reverse('settings'), 'kernelopts',
        "Configuration updated.")
    if response is not None:
        return response

    # Process accept clusters en masse.
    if 'mass_accept_submit' in request.POST:
        number = NodeGroup.objects.accept_all_pending()
        messages.info(request, "Accepted %d cluster(s)." % number)
        return HttpResponseRedirect(reverse('settings'))

    # Process reject clusters en masse.
    if 'mass_reject_submit' in request.POST:
        number = NodeGroup.objects.reject_all_pending()
        messages.info(request, "Rejected %d cluster(s)." % number)
        return HttpResponseRedirect(reverse('settings'))

    # Import PXE files for all the accepted clusters.
    if 'import_all_boot_images' in request.POST:
        NodeGroup.objects.import_boot_images_accepted_clusters()
        message = (
            "Import of boot images started on all cluster controllers.  "
            "Importing the boot images can take a long time depending on "
            "the available bandwidth.")
        messages.info(request, message)
        return HttpResponseRedirect(reverse('settings'))

    # Cluster listings.
    accepted_clusters = NodeGroup.objects.filter(
        status=NODEGROUP_STATUS.ACCEPTED).order_by('cluster_name')
    pending_clusters = NodeGroup.objects.filter(
        status=NODEGROUP_STATUS.PENDING).order_by('cluster_name')
    rejected_clusters = NodeGroup.objects.filter(
        status=NODEGROUP_STATUS.REJECTED).order_by('cluster_name')

    # Commissioning scripts.
    commissioning_scripts = CommissioningScript.objects.all()

    return render_to_response(
        'maasserver/settings.html',
        {
            'user_list': user_list,
            'commissioning_scripts': commissioning_scripts,
            'accepted_clusters': accepted_clusters,
            'pending_clusters': pending_clusters,
            'rejected_clusters': rejected_clusters,
            'maas_and_network_form': maas_and_network_form,
            'commissioning_form': commissioning_form,
            'ubuntu_form': ubuntu_form,
            'kernelopts_form': kernelopts_form,
        },
        context_instance=RequestContext(request))
