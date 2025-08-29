#!/usr/bin/env python3
"""
FHIR Service for Medical Reporting Module
Implements FHIR R4 standard for modern medical data exchange
"""

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class FHIRPatient:
    """FHIR Patient Resource"""
    id: str
    identifier: List[Dict] = None
    name: List[Dict] = None
    gender: str = ""
    birth_date: str = ""
    address: List[Dict] = None
    telecom: List[Dict] = None
    
    def __post_init__(self):
        if self.identifier is None:
            self.identifier = []
        if self.name is None:
            self.name = []
        if self.address is None:
            self.address = []
        if self.telecom is None:
            self.telecom = []

@dataclass
class FHIRObservation:
    """FHIR Observation Resource"""
    id: str
    status: str = "final"
    category: List[Dict] = None
    code: Dict = None
    subject: Dict = None
    effective_datetime: str = ""
    value: Any = None
    performer: List[Dict] = None
    
    def __post_init__(self):
        if self.category is None:
            self.category = []
        if self.performer is None:
            self.performer = []

@dataclass
class FHIRDiagnosticReport:
    """FHIR DiagnosticReport Resource"""
    id: str
    status: str = "final"
    category: List[Dict] = None
    code: Dict = None
    subject: Dict = None
    effective_datetime: str = ""
    issued: str = ""
    performer: List[Dict] = None
    result: List[Dict] = None
    conclusion: str = ""
    
    def __post_init__(self):
        if self.category is None:
            self.category = []
        if self.performer is None:
            self.performer = []
        if self.result is None:
            self.result = []

class FHIRService:
    """FHIR R4 Service for Modern Medical Data Exchange"""
    
    def __init__(self):
        """Initialize FHIR Service"""
        self.base_url = "https://sa-medical-reporting.local/fhir"
        self.version = "4.0.1"
        
        # SA Medical coding systems
        self.coding_systems = {
            "loinc": "http://loinc.org",
            "snomed": "http://snomed.info/sct",
            "icd10": "http://hl7.org/fhir/sid/icd-10",
            "sa_medical": "https://sa-medical-reporting.local/CodeSystem/sa-medical"
        }
        
        logger.info("FHIR R4 Service initialized for SA Medical compliance")
    
    def generate_uuid(self) -> str:
        """Generate UUID for FHIR resources"""
        return str(uuid.uuid4())
    
    def format_fhir_datetime(self, dt: datetime = None) -> str:
        """Format datetime for FHIR"""
        if dt is None:
            dt = datetime.now(timezone.utc)
        return dt.isoformat()
    
    def create_patient_resource(self, patient_data: Dict) -> Dict:
        """Create FHIR Patient resource"""
        try:
            patient_id = patient_data.get('id', self.generate_uuid())
            
            patient = {
                "resourceType": "Patient",
                "id": patient_id,
                "meta": {
                    "versionId": "1",
                    "lastUpdated": self.format_fhir_datetime(),
                    "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
                },
                "identifier": [
                    {
                        "use": "usual",
                        "type": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                    "code": "MR",
                                    "display": "Medical Record Number"
                                }
                            ]
                        },
                        "system": "https://sa-medical-reporting.local/patient-id",
                        "value": patient_data.get('medical_record_number', patient_id)
                    }
                ],
                "active": True,
                "name": [
                    {
                        "use": "official",
                        "family": patient_data.get('family_name', ''),
                        "given": [patient_data.get('given_name', '')],
                        "prefix": [patient_data.get('title', '')]
                    }
                ],
                "gender": patient_data.get('gender', '').lower(),
                "birthDate": patient_data.get('birth_date', ''),
                "address": [
                    {
                        "use": "home",
                        "type": "physical",
                        "text": patient_data.get('address', ''),
                        "city": patient_data.get('city', ''),
                        "state": patient_data.get('province', ''),
                        "postalCode": patient_data.get('postal_code', ''),
                        "country": "ZA"  # South Africa
                    }
                ],
                "telecom": []
            }
            
            # Add phone number if provided
            if patient_data.get('phone'):
                patient["telecom"].append({
                    "system": "phone",
                    "value": patient_data['phone'],
                    "use": "home"
                })
            
            # Add email if provided
            if patient_data.get('email'):
                patient["telecom"].append({
                    "system": "email",
                    "value": patient_data['email'],
                    "use": "home"
                })
            
            logger.info(f"Created FHIR Patient resource for ID: {patient_id}")
            return patient
            
        except Exception as e:
            logger.error(f"Failed to create FHIR Patient resource: {e}")
            raise
    
    def create_observation_resource(self, observation_data: Dict) -> Dict:
        """Create FHIR Observation resource"""
        try:
            observation_id = observation_data.get('id', self.generate_uuid())
            
            observation = {
                "resourceType": "Observation",
                "id": observation_id,
                "meta": {
                    "versionId": "1",
                    "lastUpdated": self.format_fhir_datetime(),
                    "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"]
                },
                "status": observation_data.get('status', 'final'),
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": observation_data.get('category_code', 'imaging'),
                                "display": observation_data.get('category_display', 'Imaging')
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": self.coding_systems['loinc'],
                            "code": observation_data.get('loinc_code', '18748-4'),
                            "display": observation_data.get('code_display', 'Diagnostic imaging study')
                        }
                    ],
                    "text": observation_data.get('code_text', 'Medical Observation')
                },
                "subject": {
                    "reference": f"Patient/{observation_data.get('patient_id', '')}",
                    "display": observation_data.get('patient_name', '')
                },
                "effectiveDateTime": observation_data.get('effective_datetime', self.format_fhir_datetime()),
                "issued": self.format_fhir_datetime(),
                "performer": [
                    {
                        "reference": f"Practitioner/{observation_data.get('performer_id', '')}",
                        "display": observation_data.get('performer_name', '')
                    }
                ]
            }
            
            # Add value based on type
            value_type = observation_data.get('value_type', 'string')
            value = observation_data.get('value', '')
            
            if value_type == 'string':
                observation["valueString"] = str(value)
            elif value_type == 'quantity':
                observation["valueQuantity"] = {
                    "value": float(value),
                    "unit": observation_data.get('unit', ''),
                    "system": "http://unitsofmeasure.org"
                }
            elif value_type == 'codeable_concept':
                observation["valueCodeableConcept"] = {
                    "coding": [
                        {
                            "system": observation_data.get('value_system', self.coding_systems['snomed']),
                            "code": observation_data.get('value_code', ''),
                            "display": str(value)
                        }
                    ],
                    "text": str(value)
                }
            
            logger.info(f"Created FHIR Observation resource for ID: {observation_id}")
            return observation
            
        except Exception as e:
            logger.error(f"Failed to create FHIR Observation resource: {e}")
            raise
    
    def create_diagnostic_report_resource(self, report_data: Dict) -> Dict:
        """Create FHIR DiagnosticReport resource"""
        try:
            report_id = report_data.get('id', self.generate_uuid())
            
            diagnostic_report = {
                "resourceType": "DiagnosticReport",
                "id": report_id,
                "meta": {
                    "versionId": "1",
                    "lastUpdated": self.format_fhir_datetime(),
                    "profile": ["http://hl7.org/fhir/StructureDefinition/DiagnosticReport"]
                },
                "status": report_data.get('status', 'final'),
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                                "code": report_data.get('category_code', 'RAD'),
                                "display": report_data.get('category_display', 'Radiology')
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": self.coding_systems['loinc'],
                            "code": report_data.get('loinc_code', '18748-4'),
                            "display": report_data.get('code_display', 'Diagnostic imaging study')
                        }
                    ],
                    "text": report_data.get('code_text', 'Medical Report')
                },
                "subject": {
                    "reference": f"Patient/{report_data.get('patient_id', '')}",
                    "display": report_data.get('patient_name', '')
                },
                "effectiveDateTime": report_data.get('effective_datetime', self.format_fhir_datetime()),
                "issued": self.format_fhir_datetime(),
                "performer": [
                    {
                        "reference": f"Practitioner/{report_data.get('performer_id', '')}",
                        "display": report_data.get('performer_name', '')
                    }
                ],
                "result": [],
                "conclusion": report_data.get('conclusion', ''),
                "conclusionCode": []
            }
            
            # Add results (observations)
            for result in report_data.get('results', []):
                diagnostic_report["result"].append({
                    "reference": f"Observation/{result.get('id', '')}",
                    "display": result.get('display', '')
                })
            
            # Add conclusion codes
            for code in report_data.get('conclusion_codes', []):
                diagnostic_report["conclusionCode"].append({
                    "coding": [
                        {
                            "system": code.get('system', self.coding_systems['snomed']),
                            "code": code.get('code', ''),
                            "display": code.get('display', '')
                        }
                    ]
                })
            
            logger.info(f"Created FHIR DiagnosticReport resource for ID: {report_id}")
            return diagnostic_report
            
        except Exception as e:
            logger.error(f"Failed to create FHIR DiagnosticReport resource: {e}")
            raise
    
    def create_practitioner_resource(self, practitioner_data: Dict) -> Dict:
        """Create FHIR Practitioner resource"""
        try:
            practitioner_id = practitioner_data.get('id', self.generate_uuid())
            
            practitioner = {
                "resourceType": "Practitioner",
                "id": practitioner_id,
                "meta": {
                    "versionId": "1",
                    "lastUpdated": self.format_fhir_datetime(),
                    "profile": ["http://hl7.org/fhir/StructureDefinition/Practitioner"]
                },
                "identifier": [
                    {
                        "use": "official",
                        "type": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                    "code": "PRN",
                                    "display": "Provider number"
                                }
                            ]
                        },
                        "system": "https://hpcsa.co.za/practitioner-id",
                        "value": practitioner_data.get('hpcsa_number', '')
                    }
                ],
                "active": True,
                "name": [
                    {
                        "use": "official",
                        "family": practitioner_data.get('family_name', ''),
                        "given": [practitioner_data.get('given_name', '')],
                        "prefix": [practitioner_data.get('title', 'Dr')]
                    }
                ],
                "telecom": [],
                "qualification": [
                    {
                        "identifier": [
                            {
                                "value": practitioner_data.get('qualification_number', '')
                            }
                        ],
                        "code": {
                            "coding": [
                                {
                                    "system": "https://hpcsa.co.za/qualifications",
                                    "code": practitioner_data.get('qualification_code', 'MD'),
                                    "display": practitioner_data.get('qualification_display', 'Doctor of Medicine')
                                }
                            ]
                        },
                        "issuer": {
                            "display": "Health Professions Council of South Africa (HPCSA)"
                        }
                    }
                ]
            }
            
            # Add contact information
            if practitioner_data.get('phone'):
                practitioner["telecom"].append({
                    "system": "phone",
                    "value": practitioner_data['phone'],
                    "use": "work"
                })
            
            if practitioner_data.get('email'):
                practitioner["telecom"].append({
                    "system": "email",
                    "value": practitioner_data['email'],
                    "use": "work"
                })
            
            logger.info(f"Created FHIR Practitioner resource for ID: {practitioner_id}")
            return practitioner
            
        except Exception as e:
            logger.error(f"Failed to create FHIR Practitioner resource: {e}")
            raise
    
    def create_bundle_resource(self, resources: List[Dict], bundle_type: str = "document") -> Dict:
        """Create FHIR Bundle resource"""
        try:
            bundle_id = self.generate_uuid()
            
            bundle = {
                "resourceType": "Bundle",
                "id": bundle_id,
                "meta": {
                    "versionId": "1",
                    "lastUpdated": self.format_fhir_datetime()
                },
                "type": bundle_type,
                "timestamp": self.format_fhir_datetime(),
                "total": len(resources),
                "entry": []
            }
            
            for resource in resources:
                entry = {
                    "fullUrl": f"{self.base_url}/{resource['resourceType']}/{resource['id']}",
                    "resource": resource
                }
                bundle["entry"].append(entry)
            
            logger.info(f"Created FHIR Bundle resource with {len(resources)} entries")
            return bundle
            
        except Exception as e:
            logger.error(f"Failed to create FHIR Bundle resource: {e}")
            raise
    
    def validate_fhir_resource(self, resource: Dict) -> bool:
        """Validate FHIR resource structure"""
        try:
            # Basic validation
            if not isinstance(resource, dict):
                return False
            
            if "resourceType" not in resource:
                return False
            
            if "id" not in resource:
                return False
            
            # Resource-specific validation
            resource_type = resource["resourceType"]
            
            if resource_type == "Patient":
                return self._validate_patient_resource(resource)
            elif resource_type == "Observation":
                return self._validate_observation_resource(resource)
            elif resource_type == "DiagnosticReport":
                return self._validate_diagnostic_report_resource(resource)
            elif resource_type == "Practitioner":
                return self._validate_practitioner_resource(resource)
            elif resource_type == "Bundle":
                return self._validate_bundle_resource(resource)
            
            logger.info(f"FHIR {resource_type} resource validation passed")
            return True
            
        except Exception as e:
            logger.error(f"FHIR resource validation failed: {e}")
            return False
    
    def _validate_patient_resource(self, resource: Dict) -> bool:
        """Validate Patient resource"""
        required_fields = ["resourceType", "id"]
        return all(field in resource for field in required_fields)
    
    def _validate_observation_resource(self, resource: Dict) -> bool:
        """Validate Observation resource"""
        required_fields = ["resourceType", "id", "status", "code", "subject"]
        return all(field in resource for field in required_fields)
    
    def _validate_diagnostic_report_resource(self, resource: Dict) -> bool:
        """Validate DiagnosticReport resource"""
        required_fields = ["resourceType", "id", "status", "code", "subject"]
        return all(field in resource for field in required_fields)
    
    def _validate_practitioner_resource(self, resource: Dict) -> bool:
        """Validate Practitioner resource"""
        required_fields = ["resourceType", "id"]
        return all(field in resource for field in required_fields)
    
    def _validate_bundle_resource(self, resource: Dict) -> bool:
        """Validate Bundle resource"""
        required_fields = ["resourceType", "id", "type", "entry"]
        return all(field in resource for field in required_fields)
    
    def convert_to_json(self, resource: Dict, indent: int = 2) -> str:
        """Convert FHIR resource to JSON string"""
        try:
            return json.dumps(resource, indent=indent, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to convert FHIR resource to JSON: {e}")
            raise
    
    def parse_from_json(self, json_str: str) -> Dict:
        """Parse FHIR resource from JSON string"""
        try:
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse FHIR resource from JSON: {e}")
            raise