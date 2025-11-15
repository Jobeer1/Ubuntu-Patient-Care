"""
Patient adapter - converts OpenEMR patient records to/from FHIR Patient resource.

Mapping (P1-MAP-002):
    OpenEMR.PID -> FHIR.Patient.identifier (system: urn:openemr:pid)
    OpenEMR.fname -> FHIR.Patient.name[0].given[0]
    OpenEMR.lname -> FHIR.Patient.name[0].family
    OpenEMR.sex -> FHIR.Patient.gender
    OpenEMR.DOB -> FHIR.Patient.birthDate
"""

from typing import Dict, Any
from ..core import BaseAdapter


class PatientAdapter(BaseAdapter):
    """Adapter for Patient resources"""
    
    resource_type = "Patient"
    
    def to_fhir(self, local_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert OpenEMR patient to FHIR Patient.
        
        Expected local_record fields:
            - pid: Patient ID (required)
            - fname: First name
            - lname: Last name
            - sex: Gender (M/F/U)
            - DOB: Date of birth (YYYY-MM-DD)
            - phone_home: Home phone
            - email: Email address
        """
        fhir_patient = {
            "resourceType": "Patient",
            "identifier": [{
                "system": "urn:openemr:pid",
                "value": str(local_record["pid"])
            }]
        }
        
        # Name
        if "fname" in local_record or "lname" in local_record:
            name = {}
            if "lname" in local_record:
                name["family"] = local_record["lname"]
            if "fname" in local_record:
                name["given"] = [local_record["fname"]]
            fhir_patient["name"] = [name]
        
        # Gender mapping
        gender_map = {
            "M": "male",
            "F": "female",
            "U": "unknown",
            "O": "other"
        }
        if "sex" in local_record:
            fhir_patient["gender"] = gender_map.get(
                local_record["sex"].upper(),
                "unknown"
            )
        
        # Birth date
        if "DOB" in local_record:
            fhir_patient["birthDate"] = local_record["DOB"]
        
        # Contact info
        telecom = []
        if "phone_home" in local_record and local_record["phone_home"]:
            telecom.append({
                "system": "phone",
                "value": local_record["phone_home"],
                "use": "home"
            })
        if "email" in local_record and local_record["email"]:
            telecom.append({
                "system": "email",
                "value": local_record["email"]
            })
        if telecom:
            fhir_patient["telecom"] = telecom
        
        return fhir_patient
    
    def from_fhir(self, fhir_resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FHIR Patient to OpenEMR format.
        
        Returns local record with fields:
            - pid: Patient ID
            - fname: First name
            - lname: Last name
            - sex: Gender (M/F/U/O)
            - DOB: Date of birth
            - phone_home: Home phone
            - email: Email
        """
        local_record = {}
        
        # Extract PID from identifier
        if "identifier" in fhir_resource:
            for identifier in fhir_resource["identifier"]:
                if identifier.get("system") == "urn:openemr:pid":
                    local_record["pid"] = identifier["value"]
                    break
        
        # Extract name
        if "name" in fhir_resource and len(fhir_resource["name"]) > 0:
            name = fhir_resource["name"][0]
            if "family" in name:
                local_record["lname"] = name["family"]
            if "given" in name and len(name["given"]) > 0:
                local_record["fname"] = name["given"][0]
        
        # Gender mapping (reverse)
        gender_map = {
            "male": "M",
            "female": "F",
            "unknown": "U",
            "other": "O"
        }
        if "gender" in fhir_resource:
            local_record["sex"] = gender_map.get(fhir_resource["gender"], "U")
        
        # Birth date
        if "birthDate" in fhir_resource:
            local_record["DOB"] = fhir_resource["birthDate"]
        
        # Contact info
        if "telecom" in fhir_resource:
            for contact in fhir_resource["telecom"]:
                if contact.get("system") == "phone":
                    local_record["phone_home"] = contact["value"]
                elif contact.get("system") == "email":
                    local_record["email"] = contact["value"]
        
        return local_record
