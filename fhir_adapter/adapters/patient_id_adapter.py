"""
P1-MAP-002: Patient ID Mapping Adapter

Provides bidirectional mapping between OpenEMR patient IDs and FHIR UUIDs.
This enables seamless patient identification across different systems.

Supports:
- OpenEMR → FHIR UUID mapping
- FHIR UUID → OpenEMR mapping
- External ID systems (insurance, government IDs)
- Caching for performance
- Validation and error handling

Example:
    adapter = PatientIDAdapter()
    fhir_uuid = adapter.get_fhir_id("PAT-123")  # Convert OpenEMR ID
    openemr_id = adapter.get_openemr_id(fhir_uuid)  # Reverse mapping
"""

import uuid
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class ExternalIDType(Enum):
    """Types of external patient identifiers"""
    SSN = "ssn"
    INSURANCE = "insurance"
    MEDICAID = "medicaid"
    MEDICARE = "medicare"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"


@dataclass
class ExternalID:
    """External patient identifier (e.g., SSN, insurance ID)"""
    id_type: ExternalIDType
    value: str
    system: str = ""  # e.g., "urn:oid:2.16.840.1.113883.4.1" for SSN
    
    def to_fhir_identifier(self) -> Dict:
        """Convert to FHIR Identifier structure"""
        return {
            "system": self.system or f"urn:patient-id:{self.id_type.value}",
            "value": self.value,
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": self.id_type.value.upper()
                    }
                ]
            }
        }


@dataclass
class PatientIDMapping:
    """Bidirectional patient ID mapping"""
    openemr_id: str
    fhir_uuid: str
    external_ids: List[ExternalID] = None
    
    def __post_init__(self):
        if self.external_ids is None:
            self.external_ids = []


class PatientIDAdapter:
    """
    Adapter for mapping patient IDs across systems.
    
    Maintains bidirectional mapping between:
    - OpenEMR patient IDs (e.g., "PAT-123")
    - FHIR Patient UUIDs
    - External IDs (SSN, insurance, etc.)
    
    Uses in-memory cache for performance.
    For production, implement with persistent storage (database).
    """
    
    def __init__(self, auto_generate_uuid: bool = True):
        """
        Initialize adapter.
        
        Args:
            auto_generate_uuid: If True, automatically generate UUIDs for new IDs
        """
        self.auto_generate_uuid = auto_generate_uuid
        self._openemr_to_fhir: Dict[str, str] = {}
        self._fhir_to_openemr: Dict[str, str] = {}
        self._external_ids: Dict[str, List[ExternalID]] = {}  # UUID -> external IDs
    
    def register_mapping(
        self,
        openemr_id: str,
        fhir_uuid: Optional[str] = None,
        external_ids: Optional[List[ExternalID]] = None
    ) -> str:
        """
        Register a new patient ID mapping.
        
        If fhir_uuid is not provided and auto_generate_uuid is True,
        a UUID will be generated automatically.
        
        Args:
            openemr_id: OpenEMR patient ID (e.g., "PAT-123")
            fhir_uuid: FHIR Patient UUID (optional, auto-generated if not provided)
            external_ids: List of external identifiers
            
        Returns:
            The FHIR UUID
            
        Raises:
            ValueError: If openemr_id is invalid or already mapped differently
        """
        if not openemr_id or not isinstance(openemr_id, str):
            raise ValueError("openemr_id must be a non-empty string")
        
        # Check for existing mapping with different UUID
        if openemr_id in self._openemr_to_fhir:
            existing_uuid = self._openemr_to_fhir[openemr_id]
            if fhir_uuid and fhir_uuid != existing_uuid:
                raise ValueError(
                    f"openemr_id {openemr_id} already mapped to {existing_uuid}, "
                    f"cannot map to {fhir_uuid}"
                )
            fhir_uuid = existing_uuid
        
        # Generate UUID if needed
        if not fhir_uuid:
            if not self.auto_generate_uuid:
                raise ValueError("fhir_uuid required when auto_generate_uuid=False")
            fhir_uuid = str(uuid.uuid4())
        
        # Validate UUID format
        try:
            uuid.UUID(fhir_uuid)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {fhir_uuid}")
        
        # Store bidirectional mapping
        self._openemr_to_fhir[openemr_id] = fhir_uuid
        self._fhir_to_openemr[fhir_uuid] = openemr_id
        
        # Store external IDs
        if external_ids:
            self._external_ids[fhir_uuid] = external_ids
        
        return fhir_uuid
    
    def get_fhir_id(self, openemr_id: str) -> Optional[str]:
        """
        Get FHIR UUID from OpenEMR patient ID.
        
        Args:
            openemr_id: OpenEMR patient ID
            
        Returns:
            FHIR UUID if mapped, None otherwise
        """
        return self._openemr_to_fhir.get(openemr_id)
    
    def get_openemr_id(self, fhir_uuid: str) -> Optional[str]:
        """
        Get OpenEMR patient ID from FHIR UUID.
        
        Args:
            fhir_uuid: FHIR Patient UUID
            
        Returns:
            OpenEMR patient ID if mapped, None otherwise
        """
        return self._fhir_to_openemr.get(fhir_uuid)
    
    def get_external_ids(self, fhir_uuid: str) -> List[ExternalID]:
        """
        Get external IDs for a patient (by FHIR UUID).
        
        Args:
            fhir_uuid: FHIR Patient UUID
            
        Returns:
            List of ExternalID objects
        """
        return self._external_ids.get(fhir_uuid, [])
    
    def find_by_external_id(self, id_type: ExternalIDType, value: str) -> Optional[str]:
        """
        Find FHIR UUID by external ID (e.g., SSN).
        
        Args:
            id_type: Type of external ID
            value: Value of external ID
            
        Returns:
            FHIR UUID if found, None otherwise
        """
        for fhir_uuid, ext_ids in self._external_ids.items():
            for ext_id in ext_ids:
                if ext_id.id_type == id_type and ext_id.value == value:
                    return fhir_uuid
        return None
    
    def add_external_id(self, fhir_uuid: str, external_id: ExternalID) -> bool:
        """
        Add external ID to existing patient mapping.
        
        Args:
            fhir_uuid: FHIR Patient UUID
            external_id: External ID to add
            
        Returns:
            True if successful, False if UUID not found
        """
        if fhir_uuid not in self._fhir_to_openemr:
            return False
        
        if fhir_uuid not in self._external_ids:
            self._external_ids[fhir_uuid] = []
        
        # Avoid duplicates
        for existing in self._external_ids[fhir_uuid]:
            if existing.id_type == external_id.id_type and existing.value == external_id.value:
                return True  # Already exists
        
        self._external_ids[fhir_uuid].append(external_id)
        return True
    
    def get_mapping(self, openemr_id: str) -> Optional[PatientIDMapping]:
        """
        Get complete mapping for an OpenEMR patient ID.
        
        Args:
            openemr_id: OpenEMR patient ID
            
        Returns:
            PatientIDMapping if found, None otherwise
        """
        fhir_uuid = self.get_fhir_id(openemr_id)
        if not fhir_uuid:
            return None
        
        external_ids = self.get_external_ids(fhir_uuid)
        
        return PatientIDMapping(
            openemr_id=openemr_id,
            fhir_uuid=fhir_uuid,
            external_ids=external_ids
        )
    
    def to_fhir_identifier(self, openemr_id: str) -> Optional[Dict]:
        """
        Convert OpenEMR ID to FHIR Identifier structure.
        
        Returns FHIR-compliant identifier with system and value.
        
        Args:
            openemr_id: OpenEMR patient ID
            
        Returns:
            FHIR Identifier dict if found, None otherwise
        """
        fhir_uuid = self.get_fhir_id(openemr_id)
        if not fhir_uuid:
            return None
        
        return {
            "system": "urn:openemr-patient-id",
            "value": openemr_id,
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "MRN"
                    }
                ],
                "text": "Medical Record Number"
            }
        }
    
    def merge_patients(self, primary_uuid: str, duplicate_uuid: str) -> bool:
        """
        Merge duplicate patient records.
        
        Combines mappings for patients that represent the same person.
        
        Args:
            primary_uuid: UUID to keep
            duplicate_uuid: UUID to merge (will be superseded)
            
        Returns:
            True if successful, False otherwise
        """
        if primary_uuid not in self._fhir_to_openemr:
            return False
        if duplicate_uuid not in self._fhir_to_openemr:
            return False
        
        # Get OpenEMR IDs
        primary_openemr = self._fhir_to_openemr[primary_uuid]
        duplicate_openemr = self._fhir_to_openemr[duplicate_uuid]
        
        # Merge external IDs
        dup_ext_ids = self._external_ids.get(duplicate_uuid, [])
        if dup_ext_ids:
            if primary_uuid not in self._external_ids:
                self._external_ids[primary_uuid] = []
            self._external_ids[primary_uuid].extend(dup_ext_ids)
        
        # Remove duplicate mappings
        del self._openemr_to_fhir[duplicate_openemr]
        del self._fhir_to_openemr[duplicate_uuid]
        if duplicate_uuid in self._external_ids:
            del self._external_ids[duplicate_uuid]
        
        return True
    
    def list_all_mappings(self) -> List[PatientIDMapping]:
        """
        Get list of all mappings.
        
        Returns:
            List of all PatientIDMapping objects
        """
        mappings = []
        for openemr_id, fhir_uuid in self._openemr_to_fhir.items():
            external_ids = self.get_external_ids(fhir_uuid)
            mappings.append(PatientIDMapping(openemr_id, fhir_uuid, external_ids))
        return mappings
    
    def stats(self) -> Dict:
        """
        Get adapter statistics.
        
        Returns:
            Dict with counts and info
        """
        return {
            "total_mappings": len(self._openemr_to_fhir),
            "total_external_ids": sum(len(ids) for ids in self._external_ids.values()),
            "external_id_types": list(set(
                ext_id.id_type.value
                for ids in self._external_ids.values()
                for ext_id in ids
            ))
        }


# Example usage
if __name__ == "__main__":
    # Create adapter
    adapter = PatientIDAdapter(auto_generate_uuid=True)
    
    # Register patient
    fhir_uuid = adapter.register_mapping(
        "PAT-123",
        external_ids=[
            ExternalID(ExternalIDType.SSN, "123-45-6789"),
            ExternalID(ExternalIDType.INSURANCE, "INS-999-888-777")
        ]
    )
    
    print(f"OpenEMR ID PAT-123 → FHIR UUID: {fhir_uuid}")
    
    # Reverse mapping
    openemr_id = adapter.get_openemr_id(fhir_uuid)
    print(f"FHIR UUID {fhir_uuid} → OpenEMR ID: {openemr_id}")
    
    # Find by external ID
    found_uuid = adapter.find_by_external_id(ExternalIDType.SSN, "123-45-6789")
    print(f"Found by SSN: {found_uuid}")
    
    # Get complete mapping
    mapping = adapter.get_mapping("PAT-123")
    print(f"Complete mapping: {mapping}")
    
    # Statistics
    print(f"Adapter stats: {adapter.stats()}")
