# Copyright 2012, 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Forms."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    "AdminNodeWithMACAddressesForm",
    "CommissioningForm",
    "CommissioningScriptForm",
    "DownloadProgressForm",
    "get_action_form",
    "get_node_edit_form",
    "get_node_create_form",
    "MACAddressForm",
    "MAASAndNetworkForm",
    "BulkNodeActionForm",
    "NodeGroupInterfaceForm",
    "NodeGroupWithInterfacesForm",
    "NodeGroupEdit",
    "NodeWithMACAddressesForm",
    "SSHKeyForm",
    "UbuntuForm",
    "AdminNodeForm",
    "TagForm",
    ]

import collections
import json
import pipes
import re

from django import forms
from django.contrib import messages
from django.contrib.auth.forms import (
    UserChangeForm,
    UserCreationForm,
    )
from django.contrib.auth.models import (
    AnonymousUser,
    User,
    )
from django.core.exceptions import ValidationError
from django.forms import (
    Form,
    ModelForm,
    MultipleChoiceField,
    )
from lxml import etree
from maasserver.config_forms import SKIP_CHECK_NAME
from maasserver.enum import (
    ARCHITECTURE,
    ARCHITECTURE_CHOICES,
    DISTRO_SERIES,
    DISTRO_SERIES_CHOICES,
    LICENSE_REQUIRED_SERIES,
    NODE_AFTER_COMMISSIONING_ACTION,
    NODE_AFTER_COMMISSIONING_ACTION_CHOICES,
    NODE_STATUS,
    NODEGROUP_STATUS,
    NODEGROUPINTERFACE_MANAGEMENT,
    NODEGROUPINTERFACE_MANAGEMENT_CHOICES,
    SERIES_CHOICES,
    )
from maasserver.fields import (
    MACAddressFormField,
    NodeGroupFormField,
    )
from maasserver.forms_settings import (
    compose_invalid_choice_text,
    CONFIG_ITEMS_KEYS,
    get_config_field,
    INVALID_DISTRO_SERIES_MESSAGE,
    INVALID_SETTING_MSG_TEMPLATE,
    )
from maasserver.models import (
    Config,
    DownloadProgress,
    MACAddress,
    Node,
    NodeGroup,
    NodeGroupInterface,
    SSHKey,
    Tag,
    )
from maasserver.models.nodegroup import NODEGROUP_CLUSTER_NAME_TEMPLATE
from maasserver.node_action import (
    ACTION_CLASSES,
    ACTIONS_DICT,
    compile_node_actions,
    )
from maasserver.power_parameters import POWER_TYPE_PARAMETERS
from maasserver.utils import strip_domain
from metadataserver.fields import Bin
from metadataserver.models import CommissioningScript
from provisioningserver.enum import (
    POWER_TYPE,
    POWER_TYPE_CHOICES,
    )


INVALID_ARCHITECTURE_MESSAGE = compose_invalid_choice_text(
    'architecture', ARCHITECTURE_CHOICES)


class NodeForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(NodeForm, self).__init__(*args, **kwargs)
        if kwargs.get('instance') is None:
            # Creating a new node.  Offer choice of nodegroup.
            self.fields['nodegroup'] = NodeGroupFormField(
                required=False, empty_label="Default (master)")

    def clean_hostname(self):
        # Don't allow the hostname to be changed if the node is
        # currently allocated.  Juju knows the node by its old name, so
        # changing the name would confuse things.
        hostname = self.instance.hostname
        status = self.instance.status
        new_hostname = self.cleaned_data.get('hostname', hostname)
        if new_hostname != hostname and status == NODE_STATUS.ALLOCATED:
            raise ValidationError(
                "Can't change hostname to %s: node is in use." % new_hostname)

        return new_hostname

    def clean_license_key(self):
        key = self.cleaned_data.get('license_key')
        distro = self.cleaned_data.get('distro_series')

        if not key or len(key) == 0:
            if distro in LICENSE_REQUIRED_SERIES:
                raise ValidationError(
                "This OS requires a license key")
            return key

        r = re.compile('^([A-Za-z0-9]{5}-){4}[A-Za-z0-9]{5}$')
        if not r.match(key):
            raise ValidationError(
                "Invalid license key format")
        return key

    series_choices = forms.ChoiceField(
        choices=SERIES_CHOICES, required=False,
        initial="Ubuntu",
        label="OS",
        error_messages={'invalid_choice': INVALID_DISTRO_SERIES_MESSAGE})

    after_commissioning_action = forms.TypedChoiceField(
        label="After commissioning",
        choices=NODE_AFTER_COMMISSIONING_ACTION_CHOICES, required=False,
        empty_value=NODE_AFTER_COMMISSIONING_ACTION.DEFAULT)

    distro_series = forms.ChoiceField(
        choices=DISTRO_SERIES_CHOICES, required=False,
        initial=DISTRO_SERIES.default,
        label="Release",
        error_messages={'invalid_choice': INVALID_DISTRO_SERIES_MESSAGE})

    architecture = forms.ChoiceField(
        choices=ARCHITECTURE_CHOICES, required=True,
        initial=ARCHITECTURE.i386,
        error_messages={'invalid_choice': INVALID_ARCHITECTURE_MESSAGE})

    hostname = forms.CharField(
        label="Host name", required=False, help_text=(
            "The FQDN (Fully Qualified Domain Name) is derived from the "
            "host name: If the cluster controller for this node is managing "
            "DNS then the domain part in the host name (if any) is replaced "
            "by the domain defined on the cluster; if the cluster controller "
            "does not manage DNS, then the host name as entered will be the "
            "FQDN."))

    license_key = forms.CharField(
        label="License Key (Windows only)", required=False, help_text=(
            "License key for Windows operating systems"),
        max_length=30)

    class Meta:
        model = Node

        # Fields that the form should generate automatically from the
        # model:
        fields = (
            'hostname',
            'after_commissioning_action',
            'architecture',
            'series_choices',
            'distro_series',
            'license_key'
            )


def remove_None_values(data):
    """Return a new dictionary without the keys corresponding to None values.
    """
    return {key: value for key, value in data.items() if value is not None}


class APIEditMixin:
    """A mixin that clears None values after the cleaning phase.

    Form data contain None values for missing fields.  This class
    removes these None values before processing the data.
    """

    def _post_clean(self):
        """Override Django's private hook _post_save to remove None values
        from 'self.cleaned_data'.

        _post_clean is where the fields of the instance get set with the data
        from self.cleaned_data.  That's why the cleanup needs to happen right
        before that.
        """
        self.cleaned_data = remove_None_values(self.cleaned_data)
        super(APIEditMixin, self)._post_clean()


class AdminNodeForm(APIEditMixin, NodeForm):
    """A `NodeForm` which includes fields that only an admin may change."""

    cpu_count = forms.IntegerField(
        required=False, initial=0,
        label="CPU Count")
    memory = forms.IntegerField(
        required=False, initial=0,
        label="Memory")
    storage = forms.IntegerField(
        required=False, initial=0,
        label="Disk space")

    class Meta:
        model = Node

        # Fields that the form should generate automatically from the
        # model:
        fields = NodeForm.Meta.fields + (
            'power_type',
            'power_parameters',
            'cpu_count',
            'memory',
            'storage',
            'zone',
            )

    def __init__(self, data=None, instance=None, **kwargs):
        super(AdminNodeForm, self).__init__(
            data=data, instance=instance, **kwargs)
        self.set_up_power_parameters_field(data, instance)

    def set_up_power_parameters_field(self, data, node):
        """Setup the 'power_parameter' field based on the value for the
        'power_type' field.

        We need to create the field for 'power_parameter' (which depend from
        the value of the field 'power_type') before the value for power_type
        gets validated.
        """
        if data is None:
            data = {}

        power_type = data.get('power_type', self.initial.get('power_type'))

        # If power_type is None (this is a node creation form or this
        # form deals with an API call which does not change the value of
        # 'power_type') or invalid: get the node's current 'power_type'
        # value or the default value if this form is not linked to a node.
        if power_type is None or power_type not in dict(POWER_TYPE_CHOICES):
            if node is not None:
                power_type = node.power_type
            else:
                power_type = POWER_TYPE.DEFAULT
        self.fields['power_parameters'] = (
            POWER_TYPE_PARAMETERS[power_type])

    def clean(self):
        cleaned_data = super(AdminNodeForm, self).clean()
        # If power_type is DEFAULT and power_parameters_skip_check is not
        # on, reset power_parameters (set it to the empty string).
        is_default = cleaned_data['power_type'] == POWER_TYPE.DEFAULT
        skip_check = (
            self.data.get('power_parameters_%s' % SKIP_CHECK_NAME) == 'true')
        if is_default and not skip_check:
            cleaned_data['power_parameters'] = ''
        return cleaned_data


def get_node_edit_form(user):
    if user.is_superuser:
        return AdminNodeForm
    else:
        return NodeForm


class MACAddressForm(ModelForm):
    class Meta:
        model = MACAddress

    def __init__(self, node, *args, **kwargs):
        super(MACAddressForm, self).__init__(*args, **kwargs)
        self.node = node

    def save(self, *args, **kwargs):
        mac = super(MACAddressForm, self).save(commit=False)
        mac.node = self.node
        if kwargs.get('commit', True):
            mac.save(*args, **kwargs)
        return mac


class SSHKeyForm(ModelForm):
    key = forms.CharField(
        label="Public key",
        widget=forms.Textarea(attrs={'rows': '5', 'cols': '30'}),
        required=True)

    class Meta:
        model = SSHKey

    def __init__(self, user, *args, **kwargs):
        super(SSHKeyForm, self).__init__(*args, **kwargs)
        self.user = user

    def validate_unique(self):
        # This is a trick to work around a problem in Django.
        # See https://code.djangoproject.com/ticket/13091#comment:19 for
        # details.
        # Without this overridden validate_unique the validation error that
        # can occur if this user already has the same key registered would
        # occur when save() would be called.  The error would be an
        # IntegrityError raised when inserting the new key in the database
        # rather than a proper ValidationError raised by 'clean'.

        # Set the instance user.
        self.instance.user = self.user

        # Allow checking against the missing attribute.
        exclude = self._get_validation_exclusions()
        exclude.remove('user')
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            # Publish this error as a 'key' error rather than a 'general'
            # error because only the 'key' errors are displayed on the
            # 'add key' form.
            error = e.message_dict.pop('__all__')
            self._errors.setdefault('key', self.error_class()).extend(error)


class MultipleMACAddressField(forms.MultiValueField):

    def __init__(self, nb_macs=1, *args, **kwargs):
        fields = [MACAddressFormField() for i in range(nb_macs)]
        super(MultipleMACAddressField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return data_list
        return []


def initialize_node_group(node, form_value=None):
    """If `node` is not in a node group yet, initialize it.

    The initial value is `form_value` if given, or the master nodegroup
    otherwise.
    """
    if node.nodegroup_id is not None:
        return
    if form_value is None:
        node.nodegroup = NodeGroup.objects.ensure_master()
    else:
        node.nodegroup = form_value


IP_BASED_HOSTNAME_REGEXP = re.compile('\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}')


class WithMACAddressesMixin:
    """A form mixin which dynamically adds a MultipleMACAddressField to the
    list of fields.  This mixin also overrides the 'save' method to persist
    the list of MAC addresses and is intended to be used with a class
    inheriting from NodeForm.
    """

    def __init__(self, *args, **kwargs):
        super(WithMACAddressesMixin, self).__init__(*args, **kwargs)
        self.set_up_mac_addresses_field()

    def set_up_mac_addresses_field(self):
        macs = [mac for mac in self.data.getlist('mac_addresses') if mac]
        self.fields['mac_addresses'] = MultipleMACAddressField(len(macs))
        self.data = self.data.copy()
        self.data['mac_addresses'] = macs

    def is_valid(self):
        valid = super(WithMACAddressesMixin, self).is_valid()
        # If the number of MAC address fields is > 1, provide a unified
        # error message if the validation has failed.
        reformat_mac_address_error = (
            self.errors.get('mac_addresses', None) is not None and
            len(self.data['mac_addresses']) > 1)
        if reformat_mac_address_error:
            self.errors['mac_addresses'] = (
                ['One or more MAC addresses is invalid.'])
        return valid

    def clean_mac_addresses(self):
        data = self.cleaned_data['mac_addresses']
        for mac in data:
            if MACAddress.objects.filter(mac_address=mac.lower()).exists():
                raise ValidationError(
                    {'mac_addresses': [
                        'Mac address %s already in use.' % mac]})
        return data

    def save(self):
        """Save the form's data to the database.

        This implementation of `save` does not support the `commit` argument.
        """
        node = super(WithMACAddressesMixin, self).save(commit=False)
        # We have to save this node in order to attach MACAddress
        # records to it.  But its nodegroup must be initialized before
        # we can do that.
        # As a side effect, this prevents editing of the node group on
        # an existing node.  It's all horribly dependent on the order of
        # calls in this class family, but Django doesn't seem to give us
        # a good way around it.
        initialize_node_group(node, self.cleaned_data.get('nodegroup'))
        node.save()
        for mac in self.cleaned_data['mac_addresses']:
            node.add_mac_address(mac)
        hostname = self.cleaned_data['hostname']
        stripped_hostname = strip_domain(hostname)
        # Generate a hostname for this node if the provided hostname is
        # IP-based (because this means that this name comes from a DNS
        # reverse query to the MAAS DNS) or an empty string.
        generate_hostname = (
            hostname == "" or
            IP_BASED_HOSTNAME_REGEXP.match(stripped_hostname) is not None)
        if generate_hostname:
            node.set_random_hostname()
        return node


class AdminNodeWithMACAddressesForm(WithMACAddressesMixin, AdminNodeForm):
    """A version of the AdminNodeForm which includes the multi-MAC address
    field.
    """


class NodeWithMACAddressesForm(WithMACAddressesMixin, NodeForm):
    """A version of the NodeForm which includes the multi-MAC address field.
    """


def get_node_create_form(user):
    if user.is_superuser:
        return AdminNodeWithMACAddressesForm
    else:
        return NodeWithMACAddressesForm


class NodeActionForm(forms.Form):
    """Base form for performing a node action.

    This form class should not be used directly but through subclasses
    created using `get_action_form`.
    """

    user = AnonymousUser()
    request = None

    action = forms.ChoiceField(
        required=True,
        choices=[
            (action.name, action.display_bulk)
            for action in ACTION_CLASSES])

    # The name of the input button used with this form.
    input_name = 'action'

    def __init__(self, instance, *args, **kwargs):
        super(NodeActionForm, self).__init__(*args, **kwargs)
        self.node = instance
        self.actions = compile_node_actions(instance, self.user, self.request)
        self.action_buttons = self.actions.values()

    def display_message(self, message):
        """Show `message` as feedback after performing an action."""
        if self.request is not None:
            messages.add_message(self.request, messages.INFO, message)

    def clean_action(self):
        action_name = self.cleaned_data['action']
        # The field 'action' is required so 'action_name' will be None
        # here only if the field itself did not validate the data.
        if action_name is not None:
            action = self.actions.get(action_name)
            if action is None or not action.is_permitted():
                error_message = 'Not a permitted action: %s.' % action_name
                raise ValidationError(
                    {'action': [error_message]})
            if action is not None and action.inhibition is not None:
                raise ValidationError(
                    {'action': [action.inhibition]})
        return action_name

    def save(self, allow_redirect=True):
        """An action was requested.  Perform it.

        This implementation of `save` does not support the `commit` argument.
        """
        action_name = self.data.get('action')
        action = self.actions.get(action_name)
        message = action.execute(allow_redirect=allow_redirect)
        self.display_message(message)
        # Return updated node.
        return Node.objects.get(system_id=self.node.system_id)


def get_action_form(user, request=None):
    """Return a class derived from NodeActionForm for a specific user.

    :param user: The user for which to build a form derived from
        NodeActionForm.
    :type user: :class:`django.contrib.auth.models.User`
    :param request: An optional request object to publish action messages.
    :type request: django.http.HttpRequest
    :return: A form class derived from NodeActionForm.
    :rtype: class:`django.forms.Form`
    """
    return type(
        b"SpecificNodeActionForm", (NodeActionForm,),
        {'user': user, 'request': request})


class ProfileForm(ModelForm):
    # We use the field 'last_name' to store the user's full name (and
    # don't display Django's 'first_name' field).
    last_name = forms.CharField(
        label="Full name", max_length=30, required=False)

    class Meta:
        model = User
        fields = ('last_name', 'email')


class NewUserCreationForm(UserCreationForm):
    is_superuser = forms.BooleanField(
        label="MAAS administrator", required=False)

    def __init__(self, *args, **kwargs):
        super(NewUserCreationForm, self).__init__(*args, **kwargs)
        # Insert 'last_name' field at the right place (right after
        # the 'username' field).
        self.fields.insert(
            1, 'last_name',
            forms.CharField(label="Full name", max_length=30, required=False))
        # Insert 'email' field at the right place (right after
        # the 'last_name' field).
        self.fields.insert(
            2, 'email',
            forms.EmailField(
                label="E-mail address", max_length=75, required=False))

    def save(self, commit=True):
        user = super(NewUserCreationForm, self).save(commit=False)
        if self.cleaned_data.get('is_superuser', False):
            user.is_superuser = True
        new_last_name = self.cleaned_data.get('last_name', None)
        if new_last_name is not None:
            user.last_name = new_last_name
        new_email = self.cleaned_data.get('email', None)
        if new_email is not None:
            user.email = new_email
        if commit:
            user.save()
        return user

    def clean_email(self):
        """Validate that the supplied email address is unique for the
        site.
        """
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "User with this E-mail address already exists.")
        return email


class EditUserForm(UserChangeForm):
    # Override the default label.
    is_superuser = forms.BooleanField(
        label="MAAS administrator", required=False)
    last_name = forms.CharField(
        label="Full name", max_length=30, required=False)

    class Meta:
        model = User
        fields = (
            'username', 'last_name', 'email', 'is_superuser')

    def __init__(self, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        # Django 1.4 overrides the field 'password' thus adding it
        # post-facto to the list of the selected fields (Meta.fields).
        # Here we don't want to use this form to edit the password.
        if 'password' in self.fields:
            del self.fields['password']


class ConfigForm(Form):
    """A base class for forms that save the content of their fields into
    Config objects.
    """

    def __init__(self, *args, **kwargs):
        super(ConfigForm, self).__init__(*args, **kwargs)
        if 'initial' not in kwargs:
            self._load_initials()

    def _load_initials(self):
        self.initial = {}
        for name in self.fields.keys():
            conf = Config.objects.get_config(name)
            if conf is not None:
                self.initial[name] = conf

    def clean(self):
        cleaned_data = super(Form, self).clean()
        for config_name in cleaned_data.keys():
            if config_name not in CONFIG_ITEMS_KEYS:
                self._errors[config_name] = self.error_class([
                    INVALID_SETTING_MSG_TEMPLATE % config_name])
        return cleaned_data

    def save(self):
        """Save the content of the fields into the database.

        This implementation of `save` does not support the `commit` argument.

        :return: Whether or not the content of the fields was valid and hence
            sucessfully saved into the detabase.
        :rtype: boolean
        """
        self.full_clean()
        if self._errors:
            return False
        else:
            for name, value in self.cleaned_data.items():
                Config.objects.set_config(name, value)
            return True


class MAASAndNetworkForm(ConfigForm):
    """Settings page, MAAS and Network section."""
    maas_name = get_config_field('maas_name')
    enlistment_domain = get_config_field('enlistment_domain')
    http_proxy = get_config_field('http_proxy')
    upstream_dns = get_config_field('upstream_dns')
    ntp_server = get_config_field('ntp_server')


class CommissioningForm(ConfigForm):
    """Settings page, Commissioning section."""
    check_compatibility = get_config_field('check_compatibility')
    after_commissioning = get_config_field('after_commissioning')
    commissioning_distro_series = forms.ChoiceField(
        choices=DISTRO_SERIES_CHOICES, required=False,
        label="Default distro series used for commissioning",
        error_messages={'invalid_choice': INVALID_DISTRO_SERIES_MESSAGE})


class UbuntuForm(ConfigForm):
    """Settings page, Ubuntu section."""
    default_distro_series = get_config_field('default_distro_series')
    main_archive = get_config_field('main_archive')
    ports_archive = get_config_field('ports_archive')
    cloud_images_archive = get_config_field('cloud_images_archive')


class GlobalKernelOptsForm(ConfigForm):
    """Settings page, Global Kernel Parameters section."""
    kernel_opts = get_config_field('kernel_opts')


class NodeGroupInterfaceForm(ModelForm):

    management = forms.TypedChoiceField(
        choices=NODEGROUPINTERFACE_MANAGEMENT_CHOICES, required=False,
        coerce=int, empty_value=NODEGROUPINTERFACE_MANAGEMENT.DEFAULT,
        help_text=(
            "If you enable DHCP management, you will need to install the "
            "'maas-dhcp' package on this cluster controller.  Similarly, you "
            "will need to install the 'maas-dns' package on this region "
            "controller to be able to enable DNS management."
            ))

    class Meta:
        model = NodeGroupInterface
        fields = (
            'interface',
            'management',
            'ip',
            'subnet_mask',
            'broadcast_ip',
            'router_ip',
            'ip_range_low',
            'ip_range_high',
            'foreign_dhcp_ip',
            )


INTERFACES_VALIDATION_ERROR_MESSAGE = (
    "Invalid json value: should be a list of dictionaries, each containing "
    "the information needed to initialize an interface.")


# The DNS zone name used for nodegroups when none is explicitly provided.
DEFAULT_DNS_ZONE_NAME = 'master'


class NodeGroupWithInterfacesForm(ModelForm):
    """Create a NodeGroup with unmanaged interfaces."""

    interfaces = forms.CharField(required=False)
    cluster_name = forms.CharField(required=False)

    class Meta:
        model = NodeGroup
        fields = (
            'cluster_name',
            'name',
            'uuid',
            )

    def __init__(self, status=None, *args, **kwargs):
        super(NodeGroupWithInterfacesForm, self).__init__(*args, **kwargs)
        self.status = status

    def clean_name(self):
        data = self.cleaned_data['name']
        if data == '':
            return DEFAULT_DNS_ZONE_NAME
        else:
            return data

    def clean(self):
        cleaned_data = super(NodeGroupWithInterfacesForm, self).clean()
        cluster_name = cleaned_data.get("cluster_name")
        uuid = cleaned_data.get("uuid")
        if uuid and not cluster_name:
            cleaned_data["cluster_name"] = (
                NODEGROUP_CLUSTER_NAME_TEMPLATE % {'uuid': uuid})
        return cleaned_data

    def clean_interfaces(self):
        data = self.cleaned_data['interfaces']
        # Stop here if the data is empty.
        if data == '':
            return data
        try:
            interfaces = json.loads(data)
        except ValueError:
            raise forms.ValidationError("Invalid json value.")
        else:
            managed = []
            # Raise an exception if the interfaces json object is not a list.
            if not isinstance(interfaces, collections.Iterable):
                raise forms.ValidationError(
                    INTERFACES_VALIDATION_ERROR_MESSAGE)
            for interface in interfaces:
                # Raise an exception if the interface object is not a dict.
                if not isinstance(interface, dict):
                    raise forms.ValidationError(
                        INTERFACES_VALIDATION_ERROR_MESSAGE)
                form = NodeGroupInterfaceForm(data=interface)
                if not form.is_valid():
                    raise forms.ValidationError(
                        "Invalid interface: %r (%r)." % (
                            interface, form._errors))
                management = interface.get('management', None)
                if management not in (
                        None, NODEGROUPINTERFACE_MANAGEMENT.UNMANAGED):
                    managed.append(management)
            # XXX: rvb 2012-09-18 bug=1052339: Only one "managed" interface
            # is supported per NodeGroup.
            if len(managed) > 1:
                raise ValidationError(
                    "Only one managed interface can be configured for this "
                    "cluster")
        return interfaces

    def save(self):
        nodegroup = super(NodeGroupWithInterfacesForm, self).save()
        for interface in self.cleaned_data['interfaces']:
            instance = NodeGroupInterface(nodegroup=nodegroup)
            form = NodeGroupInterfaceForm(data=interface, instance=instance)
            form.save()
        if self.status is not None:
            nodegroup.status = self.status
            nodegroup.save()
        return nodegroup


class NodeGroupEdit(ModelForm):

    name = forms.CharField(
        label="DNS zone name",
        help_text=(
            "Name of the related DNS zone.  Note that this will only "
            "be used if MAAS is managing a DNS zone for one of the interfaces "
            "of this cluster.  See the 'status' of the interfaces below."),
        required=False)

    class Meta:
        model = NodeGroup
        fields = (
            'cluster_name',
            'status',
            'name',
            )

    def clean_name(self):
        old_name = self.instance.name
        new_name = self.cleaned_data['name']
        if new_name == old_name or not new_name:
            # No change to the name.  Return old name.
            return old_name

        if self.instance.status != NODEGROUP_STATUS.ACCEPTED:
            # This nodegroup is not in use.  Change it at will.
            return new_name

        interface = self.instance.get_managed_interface()
        if interface is None:
            # No network interfaces.  It's weird, but there certainly
            # won't be a problem with the name change.
            return new_name

        if interface.management != NODEGROUPINTERFACE_MANAGEMENT.DHCP_AND_DNS:
            # MAAS is not managing DNS on this network, so the user can
            # rename the DNS zone at will.
            return new_name

        nodes_in_use = Node.objects.filter(
            nodegroup=self.instance, status=NODE_STATUS.ALLOCATED)
        if nodes_in_use.exists():
            raise ValidationError(
                "Can't rename DNS zone to %s; nodes are in use." % new_name)

        return new_name


class TagForm(ModelForm):

    class Meta:
        model = Tag
        fields = (
            'name',
            'comment',
            'definition',
            'kernel_opts',
            )

    def clean_definition(self):
        definition = self.cleaned_data['definition']
        if not definition:
            return ""
        try:
            etree.XPath(definition)
        except etree.XPathSyntaxError as e:
            msg = 'Invalid xpath expression: %s' % (e,)
            raise ValidationError({'definition': [msg]})
        return definition


class CommissioningScriptForm(forms.Form):

    content = forms.FileField(
        label="Commissioning script", allow_empty_file=False)

    def __init__(self, instance=None, *args, **kwargs):
        super(CommissioningScriptForm, self).__init__(*args, **kwargs)

    def clean_content(self):
        content = self.cleaned_data['content']
        name = content.name
        if pipes.quote(name) != name:
            raise forms.ValidationError(
                "Name contains disallowed characters (e.g. space or quotes).")
        if CommissioningScript.objects.filter(name=name).exists():
            raise forms.ValidationError(
                "A script with that name already exists.")
        return content

    def save(self, *args, **kwargs):
        content = self.cleaned_data['content']
        CommissioningScript.objects.create(
            name=content.name,
            content=Bin(content.read()))


class UnconstrainedMultipleChoiceField(MultipleChoiceField):
    """A MultipleChoiceField which does not constrain the given choices."""

    def validate(self, value):
        return value


class ValidatorMultipleChoiceField(MultipleChoiceField):
    """A MultipleChoiceField validating each given choice with a validator."""

    def __init__(self, validator, **kwargs):
        super(ValidatorMultipleChoiceField, self).__init__(**kwargs)
        self.validator = validator

    def validate(self, values):
        for value in values:
            self.validator(value)
        return values


class BulkNodeActionForm(forms.Form):
    # system_id is a multiple-choice field so it can actually contain
    # a list of system ids.
    system_id = UnconstrainedMultipleChoiceField()
    action = forms.ChoiceField(
        required=True,
        # Put an empty action as the first displayed option to avoid
        # fat-fingered bulk actions.
        choices=[('', '')] + [
            (action.name, action.display_bulk)
            for action in ACTION_CLASSES])

    def __init__(self, user, *args, **kwargs):
        super(BulkNodeActionForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_system_id(self):
        system_ids = self.cleaned_data['system_id']
        # Remove duplicates.
        system_ids = set(system_ids)
        if len(system_ids) == 0:
            raise forms.ValidationError("No node selected.")
        # Validate all the system ids.
        real_node_count = Node.objects.filter(
            system_id__in=system_ids).count()
        if real_node_count != len(system_ids):
            raise forms.ValidationError(
                "Some of the given system ids are invalid system ids.")
        return system_ids

    def save(self, *args, **kwargs):
        """Perform the action on the selected nodes.

        This method returns a tuple containing 3 elements: the number of
        nodes for which the action was successfully performed, the number of
        nodes for which the action could not be performed because that
        transition was not allowed and the number of nodes for which the
        action could not be performed because the user does not have the
        required permission.
        """
        action_name = self.cleaned_data['action']
        system_ids = self.cleaned_data['system_id']
        action_class = ACTIONS_DICT.get(action_name)
        not_actionable = 0
        not_permitted = 0
        done = 0
        for system_id in system_ids:
            node = Node.objects.get(system_id=system_id)
            if node.status in action_class.actionable_statuses:
                action_instance = action_class(node=node, user=self.user)
                if action_instance.inhibit() is not None:
                    not_actionable += 1
                else:
                    if action_instance.is_permitted():
                        # Do not let execute() raise a redirect exception
                        # because this action is part of a bulk operation.
                        action_instance.execute(allow_redirect=False)
                        done += 1
                    else:
                        not_permitted += 1
            else:
                not_actionable += 1
        return done, not_actionable, not_permitted


class DownloadProgressForm(ModelForm):
    """Form to update a `DownloadProgress`.

    The `get_download` helper will find the right progress record to update,
    or create one if needed.
    """

    class Meta:
        model = DownloadProgress
        fields = (
            'size',
            'bytes_downloaded',
            'error',
            )

    @staticmethod
    def get_download(nodegroup, filename, bytes_downloaded):
        """Find or create a `DownloadProgress` to update.

        Will create a new `DownloadProgress` if appropriate.  Use the form
        to update its fields.

        This returns `None` in exactly one situation: if `bytes_downloaded`
        is not `None`, but there was no existing record of the download.
        That is not something that will happen in proper usage.
        """
        if bytes_downloaded is None:
            # This is a new download.  Create a new DownloadProgress.
            return DownloadProgress.objects.create(
                nodegroup=nodegroup, filename=filename)
        else:
            # This is an ongoing download.  Update the existing one.
            return DownloadProgress.objects.get_latest_download(
                nodegroup, filename)

    def clean(self):
        if self.instance.id is None:
            # The form was left to create its own DownloadProgress.  This can
            # only happen if get_download returned None, which in turn can only
            # happen in this particular scenario.
            raise ValidationError(
                "bytes_downloaded was passed on a new download.")

        return super(DownloadProgressForm, self).clean()
