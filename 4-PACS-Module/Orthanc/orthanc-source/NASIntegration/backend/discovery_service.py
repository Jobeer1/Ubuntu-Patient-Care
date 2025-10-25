import platform
import re
import subprocess
from typing import List, Dict
from .config import ARP_COMMAND_TIMEOUT
import logging

logger = logging.getLogger(__name__)


def parse_arp_windows(output: str) -> List[Dict]:
    devices = []
    for line in output.splitlines():
        m = re.match(r'\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-:-]{17})\s+(\w+)', line)
        if m:
            ip, mac, typ = m.groups()
            devices.append({'ip_address': ip, 'mac_address': mac.replace('-', ':').upper(), 'arp_type': typ, 'source': 'arp_table'})
    return devices


def parse_unix_arp(output: str) -> List[Dict]:
    devices = []
    for line in output.splitlines():
        m1 = re.search(r'(\d+\.\d+\.\d+\.\d+).*?([0-9a-fA-F:]{17})', line)
        m2 = re.search(r'(\d+\.\d+\.\d+\.\d+).*?lladdr\s+([0-9a-fA-F:]{17})', line)
        m = m1 or m2
        if m:
            ip, mac = m.groups()
            devices.append({'ip_address': ip, 'mac_address': mac.upper(), 'arp_type': 'dynamic', 'source': 'arp_table'})
    return devices


def scan_arp() -> List[Dict]:
    system = platform.system().lower()
    commands = []
    if system == 'windows':
        commands = [['arp', '-a']]
    else:
        commands = [['arp', '-a'], ['ip', 'neigh', 'show'], ['cat', '/proc/net/arp']]

    for cmd in commands:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=ARP_COMMAND_TIMEOUT)
            if res.returncode == 0 and res.stdout:
                out = res.stdout
                if system == 'windows':
                    return parse_arp_windows(out)
                else:
                    parsed = parse_unix_arp(out)
                    if parsed:
                        return parsed
        except Exception as e:
            logger.debug(f"ARP command failed {cmd}: {e}")
            continue

    return []
