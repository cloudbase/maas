# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the :class:`DHCPLease` model."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = []

from maasserver import dns
from maasserver.models import DHCPLease
from maasserver.testing.factory import factory
from maasserver.testing.testcase import MAASServerTestCase
from maasserver.utils import ignore_unused


def get_leases(nodegroup):
    """Return DHCPLease records for `nodegroup`."""
    return DHCPLease.objects.filter(nodegroup=nodegroup)


def map_leases(nodegroup):
    """Return IP/MAC mappings dict for leases in `nodegroup`."""
    return {lease.ip: lease.mac for lease in get_leases(nodegroup)}


class TestDHCPLease(MAASServerTestCase):
    """Tests for :class:`DHCPLease`."""

    def test_init(self):
        nodegroup = factory.make_node_group()
        ip = factory.getRandomIPAddress()
        mac = factory.getRandomMACAddress()

        lease = DHCPLease(nodegroup=nodegroup, ip=ip, mac=mac)
        lease.save()

        self.assertItemsEqual([lease], get_leases(nodegroup))
        self.assertEqual(nodegroup, lease.nodegroup)
        self.assertEqual(ip, lease.ip)
        self.assertEqual(mac, lease.mac)

    def test_dhcplease_gets_removed_when_corresponding_node_is_deleted(self):
        lease = factory.make_dhcp_lease()
        mac = factory.make_mac_address(address=lease.mac)
        mac.node.delete()
        self.assertItemsEqual(
            [], DHCPLease.objects.filter(mac=mac.mac_address))


class TestDHCPLeaseManager(MAASServerTestCase):
    """Tests for :class:`DHCPLeaseManager`."""

    def test_update_leases_accepts_empty_leases(self):
        nodegroup = factory.make_node_group()
        DHCPLease.objects.update_leases(nodegroup, {})
        self.assertItemsEqual([], get_leases(nodegroup))

    def test_update_leases_creates_new_lease(self):
        nodegroup = factory.make_node_group()
        lease = factory.make_random_leases()
        DHCPLease.objects.update_leases(nodegroup, lease)
        self.assertEqual(lease, map_leases(nodegroup))

    def test_update_leases_returns_new_leases(self):
        nodegroup = factory.make_node_group()
        obsolete_lease = factory.make_dhcp_lease(nodegroup=nodegroup)
        ignore_unused(obsolete_lease)
        remaining_lease = factory.make_dhcp_lease(nodegroup=nodegroup)
        new_lease = factory.make_random_leases()

        surviving_leases = {
            remaining_lease.ip: remaining_lease.mac,
            new_lease.keys()[0]: new_lease.values()[0],
        }

        self.assertItemsEqual(
            new_lease.keys(),
            DHCPLease.objects.update_leases(nodegroup, surviving_leases))

    def test_update_leases_deletes_obsolete_lease(self):
        nodegroup = factory.make_node_group()
        factory.make_dhcp_lease(nodegroup=nodegroup)
        DHCPLease.objects.update_leases(nodegroup, {})
        self.assertItemsEqual([], get_leases(nodegroup))

    def test_update_leases_replaces_reassigned_ip(self):
        nodegroup = factory.make_node_group()
        ip = factory.getRandomIPAddress()
        factory.make_dhcp_lease(nodegroup=nodegroup, ip=ip)
        new_mac = factory.getRandomMACAddress()
        DHCPLease.objects.update_leases(nodegroup, {ip: new_mac})
        self.assertEqual({ip: new_mac}, map_leases(nodegroup))

    def test_update_leases_keeps_unchanged_mappings(self):
        original_lease = factory.make_dhcp_lease()
        nodegroup = original_lease.nodegroup
        DHCPLease.objects.update_leases(
            nodegroup, {original_lease.ip: original_lease.mac})
        self.assertItemsEqual([original_lease], get_leases(nodegroup))

    def test_update_leases_adds_new_ip_to_mac(self):
        nodegroup = factory.make_node_group()
        mac = factory.getRandomMACAddress()
        ip1 = factory.getRandomIPAddress()
        ip2 = factory.getRandomIPAddress()
        factory.make_dhcp_lease(nodegroup=nodegroup, mac=mac, ip=ip1)
        DHCPLease.objects.update_leases(nodegroup, {ip1: mac, ip2: mac})
        self.assertEqual({ip1: mac, ip2: mac}, map_leases(nodegroup))

    def test_update_leases_deletes_only_obsolete_ips(self):
        nodegroup = factory.make_node_group()
        mac = factory.getRandomMACAddress()
        obsolete_ip = factory.getRandomIPAddress()
        current_ip = factory.getRandomIPAddress()
        factory.make_dhcp_lease(nodegroup=nodegroup, mac=mac, ip=obsolete_ip)
        factory.make_dhcp_lease(nodegroup=nodegroup, mac=mac, ip=current_ip)
        DHCPLease.objects.update_leases(nodegroup, {current_ip: mac})
        self.assertEqual({current_ip: mac}, map_leases(nodegroup))

    def test_update_leases_leaves_other_nodegroups_alone(self):
        innocent_nodegroup = factory.make_node_group()
        innocent_lease = factory.make_dhcp_lease(nodegroup=innocent_nodegroup)
        DHCPLease.objects.update_leases(
            factory.make_node_group(), factory.make_random_leases())
        self.assertItemsEqual(
            [innocent_lease], get_leases(innocent_nodegroup))

    def test_update_leases_combines_additions_deletions_and_replacements(self):
        nodegroup = factory.make_node_group()
        mac1 = factory.getRandomMACAddress()
        mac2 = factory.getRandomMACAddress()
        obsolete_lease = factory.make_dhcp_lease(
            nodegroup=nodegroup, mac=mac1)
        # The obsolete lease won't be in the update, so it'll disappear.
        ignore_unused(obsolete_lease)
        unchanged_lease = factory.make_dhcp_lease(
            nodegroup=nodegroup, mac=mac1)
        reassigned_lease = factory.make_dhcp_lease(
            nodegroup=nodegroup, mac=mac1)
        new_ip = factory.getRandomIPAddress()
        DHCPLease.objects.update_leases(nodegroup, {
            reassigned_lease.ip: mac2,
            unchanged_lease.ip: mac1,
            new_ip: mac1,
        })
        self.assertEqual(
            {
                reassigned_lease.ip: mac2,
                unchanged_lease.ip: mac1,
                new_ip: mac1,
            },
            map_leases(nodegroup))

    def test_update_leases_updates_dns_zone(self):
        self.patch(dns, 'change_dns_zones')
        nodegroup = factory.make_node_group()
        DHCPLease.objects.update_leases(
            nodegroup, factory.make_random_leases())
        dns.change_dns_zones.assert_called_once_with([nodegroup])

    def test_update_leases_does_not_update_dns_zone_if_nothing_added(self):
        self.patch(dns, 'change_dns_zones')
        nodegroup = factory.make_node_group()
        DHCPLease.objects.update_leases(nodegroup, {})
        self.assertFalse(dns.change_dns_zones.called)

    def test_get_hostname_ip_mapping_returns_mapping(self):
        nodegroup = factory.make_node_group()
        expected_mapping = {}
        for i in range(3):
            node = factory.make_node(
                nodegroup=nodegroup)
            mac = factory.make_mac_address(node=node)
            factory.make_mac_address(node=node)
            lease = factory.make_dhcp_lease(
                nodegroup=nodegroup, mac=mac.mac_address)
            expected_mapping[node.hostname] = lease.ip
        mapping = DHCPLease.objects.get_hostname_ip_mapping(nodegroup)
        self.assertEqual(expected_mapping, mapping)

    def test_get_hostname_ip_mapping_strips_out_domain(self):
        nodegroup = factory.make_node_group()
        hostname = factory.make_name('hostname')
        domain = factory.make_name('domain')
        node = factory.make_node(
            nodegroup=nodegroup,
            hostname='%s.%s' % (hostname, domain))
        mac = factory.make_mac_address(node=node)
        lease = factory.make_dhcp_lease(
            nodegroup=nodegroup, mac=mac.mac_address)
        mapping = DHCPLease.objects.get_hostname_ip_mapping(nodegroup)
        self.assertEqual({hostname: lease.ip}, mapping)

    def test_get_hostname_ip_mapping_picks_mac_with_lease(self):
        node = factory.make_node(hostname=factory.make_name('host'))
        factory.make_mac_address(node=node)
        second_mac = factory.make_mac_address(node=node)
        # Create a lease for the second MAC Address.
        lease = factory.make_dhcp_lease(
            nodegroup=node.nodegroup, mac=second_mac.mac_address)
        mapping = DHCPLease.objects.get_hostname_ip_mapping(node.nodegroup)
        self.assertEqual({node.hostname: lease.ip}, mapping)

    def test_get_hostname_ip_mapping_picks_oldest_mac_with_lease(self):
        node = factory.make_node(hostname=factory.make_name('host'))
        older_mac = factory.make_mac_address(node=node)
        newer_mac = factory.make_mac_address(node=node)

        factory.make_dhcp_lease(
            nodegroup=node.nodegroup, mac=newer_mac.mac_address)
        lease_for_older_mac = factory.make_dhcp_lease(
            nodegroup=node.nodegroup, mac=older_mac.mac_address)

        mapping = DHCPLease.objects.get_hostname_ip_mapping(node.nodegroup)
        self.assertEqual({node.hostname: lease_for_older_mac.ip}, mapping)

    def test_get_hostname_ip_mapping_considers_given_nodegroup(self):
        nodegroup = factory.make_node_group()
        node = factory.make_node(
            nodegroup=nodegroup)
        mac = factory.make_mac_address(node=node)
        factory.make_dhcp_lease(
            nodegroup=nodegroup, mac=mac.mac_address)
        another_nodegroup = factory.make_node_group()
        mapping = DHCPLease.objects.get_hostname_ip_mapping(
            another_nodegroup)
        self.assertEqual({}, mapping)
