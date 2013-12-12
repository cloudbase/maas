# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Power parameters.  Each possible value of a Node's power_type field can
be associated with specific 'power parameters' wich will be used when
powering up or down the node in question.  These 'power parameters' will be
stored as a JSON object in the Node's power parameter field.  Even if we want
to allow arbitrary power parameters to be set using the API for maximum
flexibility, each value of power type is associated with a set of 'sensible'
power parameters.  That is used to validate data (but again, it is possible
to bypass that validation step and store arbitrary power parameters) and by
the UI to display the right power parameter fields that correspond to the
selected power_type.  The classes in this module are used to associate each
power type with a set of power parameters.

To define a new set of power parameters for a new power_type: create a new
mapping between the new power type and a DictCharField instance in
`POWER_TYPE_PARAMETERS`.
"""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'POWER_TYPE_PARAMETERS',
    ]


from django import forms
from maasserver.config_forms import DictCharField
from maasserver.fields import MACAddressFormField
from provisioningserver.enum import (
    IPMI_DRIVER,
    IPMI_DRIVER_CHOICES,
    POWER_TYPE,
    )


POWER_TYPE_PARAMETERS = {
    POWER_TYPE.DEFAULT: DictCharField(
        [], required=False, skip_check=True),
    POWER_TYPE.WAKE_ON_LAN: DictCharField(
        [
            ('mac_address',
             MACAddressFormField(label="MAC Address", required=False)),
        ],
        required=False,
        skip_check=True),
    POWER_TYPE.VMWARE: DictCharField(
        [
            ('power_address',
             forms.CharField(label="Address", required=False)),
            ('power_user',
             forms.CharField(label="Username", required=False)),
            ('power_pass',
             forms.CharField(
                widget=forms.PasswordInput(
                    render_value=True),
                label="Password", required=False)),
            ('power_id',
             forms.CharField(label="Power ID", required=False)),
        ],
        required=False,
        skip_check=True),
    POWER_TYPE.VIRSH: DictCharField(
        [
            ('power_address',
             forms.CharField(label="Address", required=False)),
            ('power_id',
             forms.CharField(label="Power ID", required=False)),
        ],
        required=False,
        skip_check=True),
    POWER_TYPE.CDU: DictCharField(
        [
            ('power_id',
             forms.CharField(label="Power ID", required=False)),
            ('power_address',
             forms.CharField(label="IP Address or Hostname", required=False)),
            ('power_user',
             forms.CharField(label="Username", required=False)),
            ('power_pass',
             forms.CharField(label="Password", required=False)),
        ],
        required=False,
        skip_check=True),
    POWER_TYPE.IPMI: DictCharField(
        [
            ('power_driver',
             forms.ChoiceField(
                 label="Driver", required=False,
                 choices=IPMI_DRIVER_CHOICES,
                 initial=IPMI_DRIVER.DEFAULT)),
            ('power_address',
             forms.CharField(label="IP Address or Hostname", required=False)),
            ('power_user',
             forms.CharField(label="Username", required=False)),
            ('power_pass',
             forms.CharField(label="Password", required=False)),
        ],
        required=False,
        skip_check=True),
    POWER_TYPE.MOONSHOT: DictCharField(
        [
            ('power_address',
             forms.CharField(
                 label="IP Address or Hostname", required=False)),
            ('power_user',
             forms.CharField(label="Username", required=False)),
            ('power_pass',
             forms.CharField(label="Password", required=False)),
            ('power_hwaddress',
             forms.CharField(label="Hardware Address", required=False)),
        ],
        required=False,
        skip_check=True),
    POWER_TYPE.SEAMICRO15K: DictCharField(
        [
            ('power_address',
             forms.CharField(
                 label="IP Address or Hostname", required=False)),
            ('power_user',
             forms.CharField(label="Username", required=False)),
            ('power_pass',
             forms.CharField(label="Password", required=False)),
            ('system_id',
             forms.CharField(label="System ID", required=False)),
        ],
        required=False,
        skip_check=True),
}
