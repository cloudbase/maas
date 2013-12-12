# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Node IP/MAC mappings as leased from the workers' DHCP servers."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    'DHCPLease',
    ]


from django.db import connection
from django.db.models import (
    ForeignKey,
    IPAddressField,
    Manager,
    Model,
    )
from django.db.models.signals import post_delete
from django.dispatch import receiver
from maasserver import DefaultMeta
from maasserver.fields import MACAddressField
from maasserver.models.cleansave import CleanSave
from maasserver.models.macaddress import MACAddress
from maasserver.utils import strip_domain


class DHCPLeaseManager(Manager):
    """Utility that manages :class:`DHCPLease` objects.

    This will be a large and busy part of the database.  Try to perform
    operations in bulk, using this manager class, where at all possible.
    """

    def _delete_obsolete_leases(self, nodegroup, current_leases):
        """Delete leases for `nodegroup` that aren't in `current_leases`."""
        cursor = connection.cursor()
        clauses = ["nodegroup_id = %s" % nodegroup.id]
        if len(current_leases) > 0:
            leases = tuple(current_leases.items())
        if len(current_leases) == 0:
            pass
        elif len(current_leases) == 1:
            clauses.append(cursor.mogrify("(ip, mac) <> %s", leases))
        else:
            clauses.append(cursor.mogrify("(ip, mac) NOT IN %s", [leases]))
        cursor.execute(
            "DELETE FROM maasserver_dhcplease WHERE %s"
            % " AND ".join(clauses)),

    def _get_leased_ips(self, nodegroup):
        """Query the currently leased IP addresses for `nodegroup`."""
        cursor = connection.cursor()
        cursor.execute(
            "SELECT ip FROM maasserver_dhcplease WHERE nodegroup_id = %s"
            % nodegroup.id)
        return frozenset(ip for ip, in cursor.fetchall())

    def _add_missing_leases(self, nodegroup, leases):
        """Add items from `leases` that aren't in the database yet.

        This is assumed to be run right after _delete_obsolete_leases,
        so that a lease from `leases` is in the database if and only if
        `nodegroup` has a DHCPLease with the same `ip` field.  There
        can't be any DHCPLease entries with the same `ip` as in `leases`
        but a different `mac`.

        :return: Iterable of newly-leased IP addresses.
        """
        leased_ips = self._get_leased_ips(nodegroup)
        new_leases = tuple(
            (nodegroup.id, ip, mac)
            for ip, mac in leases.items() if ip not in leased_ips)
        if len(new_leases) > 0:
            cursor = connection.cursor()
            new_tuples = ", ".join(
                cursor.mogrify("%s", [lease]) for lease in new_leases)
            cursor.execute("""
                INSERT INTO maasserver_dhcplease (nodegroup_id, ip, mac)
                VALUES %s
                """ % new_tuples)
        return [ip for nodegroup_id, ip, mac in new_leases]

    def update_leases(self, nodegroup, leases):
        """Refresh our knowledge of a node group's IP mappings.

        This deletes entries that are no longer current, adds new ones,
        and updates or replaces ones that have changed.

        :param nodegroup: The node group that these updates are for.
        :param leases: A dict describing all current IP/MAC mappings as
            managed by the node group's DHCP server.  Keys are IP
            addresses, values are MAC addresses.  Any :class:`DHCPLease`
            entries for `nodegroup` that are not in `leases` will be
            deleted.
        :return: Iterable of IP addresses that were newly leased.
        """
        # Avoid circular imports.
        from maasserver import dns

        self._delete_obsolete_leases(nodegroup, leases)
        new_leases = self._add_missing_leases(nodegroup, leases)
        if len(new_leases) > 0:
            dns.change_dns_zones([nodegroup])
        return new_leases

    def get_hostname_ip_mapping(self, nodegroup):
        """Return a mapping {hostnames -> ips} for the currently leased
        IP addresses for the nodes in `nodegroup`.

        For each node, this will consider only the oldest `MACAddress` that
        has a `DHCPLease`.

        Any domain will be stripped from the hostnames.
        """
        cursor = connection.cursor()

        # The "DISTINCT ON" gives us the first matching row for any
        # given hostname, in the query's ordering.
        # The ordering must start with the hostname so that the database
        # can do this efficiently.  The next ordering criterion is the
        # MACAddress id, so that if there are multiple rows with the
        # same hostname, we get the one with the oldest MACAddress.
        #
        # If this turns out to be inefficient, be sure to try selecting
        # on node.nodegroup_id instead of lease.nodegroup_id.  It has
        # the same effect but may perform differently.
        cursor.execute("""
            SELECT DISTINCT ON (node.hostname)
                node.hostname, lease.ip
            FROM maasserver_macaddress AS mac
            JOIN maasserver_node AS node ON node.id = mac.node_id
            JOIN maasserver_dhcplease AS lease ON lease.mac = mac.mac_address
            WHERE lease.nodegroup_id = %s
            ORDER BY node.hostname, mac.id
            """, (nodegroup.id, ))
        return dict(
            (strip_domain(hostname), ip)
            for hostname, ip in cursor.fetchall()
            )


class DHCPLease(CleanSave, Model):
    """A known mapping of an IP address to a MAC address.

    These correspond to the latest-known DHCP leases handed out to nodes
    (or potential nodes -- they may not have been enlisted yet!) by the
    node group worker's DHCP server.
    """

    class Meta(DefaultMeta):
        """Needed for South to recognize this model."""

    objects = DHCPLeaseManager()

    nodegroup = ForeignKey('maasserver.NodeGroup', null=False, editable=False)
    ip = IPAddressField(null=False, editable=False, unique=True)
    mac = MACAddressField(null=False, editable=False, unique=False)

    def __unicode__(self):
        return "%s->%s" % (self.ip, self.mac)


# Register a signal receiver so that whenever a MAC address is deleted,
# the corresponding DHCPLease is deleted too.
@receiver(post_delete, sender=MACAddress)
def delete_lease(sender, instance, **kwargs):
    DHCPLease.objects.filter(mac=instance.mac_address).delete()
