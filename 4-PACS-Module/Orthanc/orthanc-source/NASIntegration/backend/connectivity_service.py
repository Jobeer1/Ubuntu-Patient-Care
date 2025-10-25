import socket
import time
from typing import Tuple
from .config import PING_TIMEOUT, SOCKET_TIMEOUT
import logging

logger = logging.getLogger(__name__)


def ping_ip(ip: str, timeout: int = PING_TIMEOUT) -> bool:
    try:
        # Use socket connect to commonly open port (80) as a lightweight reachability check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        res = sock.connect_ex((ip, 80))
        sock.close()
        return res == 0
    except Exception as e:
        logger.debug(f"Ping failed for {ip}: {e}")
        return False


def check_port(ip: str, port: int, timeout: int = SOCKET_TIMEOUT) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        res = sock.connect_ex((ip, port))
        sock.close()
        return res == 0
    except Exception as e:
        logger.debug(f"Port check failed {ip}:{port}: {e}")
        return False


# DICOM echo is optional and uses pynetdicom when present
try:
    from pynetdicom import AE
    from pynetdicom.sop_class import Verification
    DICOM_AVAILABLE = True
except Exception:
    DICOM_AVAILABLE = False


def dicom_echo(ip: str, port: int, ae_title: str, timeout: int = 5) -> Tuple[bool, str]:
    if not DICOM_AVAILABLE:
        return False, 'pynetdicom not installed'
    try:
        ae = AE()
        ae.add_requested_context(Verification)
        assoc = ae.associate(ip, port, ae_title=ae_title)
        if assoc.is_established:
            status = assoc.send_c_echo()
            assoc.release()
            return (True, 'OK') if status else (False, 'C-ECHO failed')
        return False, 'Association failed'
    except Exception as e:
        return False, str(e)
