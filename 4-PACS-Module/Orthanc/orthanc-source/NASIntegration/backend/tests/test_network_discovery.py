import os
import sys
import pytest

# Ensure backend root is on sys.path so tests can import the 'routes' package when run from the backend folder
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from routes import network_discovery


def test_ping_range_max_hosts_cap(monkeypatch):
    # Create a small fake IP range generator
    start = '192.168.1.1'
    end = '192.168.1.254'

    # Monkeypatch ping_device to avoid real network I/O
    called = {'count': 0}

    def fake_ping(ip, timeout=2):
        called['count'] += 1
        return {'ip_address': ip, 'reachable': False, 'response_time': 'N/A', 'success': False}

    monkeypatch.setattr(network_discovery, 'ping_device', fake_ping)

    # Request with a tight max_hosts to force capping
    result = network_discovery.ping_range(start, end, timeout=1, max_concurrent=5, max_hosts=10)

    assert 'results' in result
    assert len(result['results']) <= 10


def test_enhanced_discovery_arp_fallback(monkeypatch):
    # Prepare fake ARP table and fake ping_range
    fake_arp = [
        {'ip_address': '10.0.0.5', 'mac_address': 'aa:bb:cc:dd:ee:ff', 'hostname': 'DeviceA', 'manufacturer': 'Acme', 'type': 'Network Device', 'last_seen': 'Active', 'source': 'ARP Table'}
    ]

    def fake_get_arp_table():
        return fake_arp

    def fake_ping_range(start, end, timeout=2, max_concurrent=10, max_hosts=None):
        # Return empty results to simulate blocked ICMP
        return {'results': [], 'statistics': {'total_pinged': 0}, 'range': {'start_ip': start, 'end_ip': end}}

    monkeypatch.setattr(network_discovery, 'get_arp_table', fake_get_arp_table)
    monkeypatch.setattr(network_discovery, 'ping_range', fake_ping_range)

    res = network_discovery.enhanced_network_discovery(include_arp=True, include_ping_range=True, start_ip='10.0.0.1', end_ip='10.0.0.10', timeout=1)

    assert res['success'] is True
    # ARP device should be present and marked source 'ARP Table'
    ips = [d['ip_address'] for d in res['discovered_devices']]
    assert '10.0.0.5' in ips

