from dataclasses import dataclass, asdict
from typing import Dict


@dataclass
class MedicalDevice:
    id: str
    name: str
    modality_type: str
    manufacturer: str
    model: str
    ae_title: str
    ip_address: str
    port: int
    department: str
    location: str
    serial_number: str = ""
    installation_date: str = ""
    last_service_date: str = ""
    status: str = "active"
    notes: str = ""
    created_date: str = ""
    updated_date: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'MedicalDevice':
        return cls(**dict(data))
