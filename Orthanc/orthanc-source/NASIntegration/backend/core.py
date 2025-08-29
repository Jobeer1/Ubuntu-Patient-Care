from .repository import DeviceRepository
from .models import MedicalDevice
from .discovery_service import scan_arp
from .connectivity_service import ping_ip, check_port, dicom_echo
from .config import DEFAULT_SCAN_PORTS
from typing import Dict, Tuple, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DeviceManager:
    def __init__(self, db_path: str = None):
        self.repo = DeviceRepository(db_path) if db_path else DeviceRepository()

    def generate_device_id(self, name: str) -> str:
        base_id = name.upper().replace(' ', '_').replace('-', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_id}_{timestamp}"

    def add_device(self, device_data: Dict) -> Tuple[bool, str, Optional[MedicalDevice]]:
        # Minimal validation and delegate to repository
        try:
            if 'id' not in device_data or not device_data['id']:
                device_data['id'] = self.generate_device_id(device_data.get('name', 'DEVICE'))

            now = datetime.now().isoformat()
            device_data.setdefault('created_date', now)
            device_data['updated_date'] = now

            device = MedicalDevice.from_dict(device_data)
            self.repo.add_device(device)
            return True, 'Device added', device
        except Exception as e:
            logger.error(f"Add device failed: {e}")
            return False, str(e), None

    def get_device_by_id(self, device_id: str) -> Optional[MedicalDevice]:
        return self.repo.get_device_by_id(device_id)

    def get_device_by_ae_title(self, ae_title: str) -> Optional[MedicalDevice]:
        return self.repo.get_device_by_ae_title(ae_title)

    def list_devices(self, **filters) -> List[MedicalDevice]:
        return self.repo.list_devices(**filters)

    # Discovery helpers
    def scan_arp_table(self) -> List[Dict]:
        return scan_arp()

    def test_connectivity(self, ip: str, port: int = 104) -> Dict:
        result = {'ip': ip, 'reachable': False, 'open_ports': [], 'dicom': None}
        if not ping_ip(ip):
            return result
        result['reachable'] = True
        for p in DEFAULT_SCAN_PORTS:
            if check_port(ip, p):
                result['open_ports'].append(p)
        # Optionally test DICOM on the requested port
        if 104 in result['open_ports']:
            ok, msg = dicom_echo(ip, 104, 'PACS_TEST')
            result['dicom'] = {'success': ok, 'msg': msg}
        return result


# Provide a module-level instance for backward compatibility
device_manager = DeviceManager()
