"""
ImagingStudy adapter - converts Orthanc metadata to/from FHIR ImagingStudy resource.

Mapping (P1-MAP-003):
    Orthanc.StudyInstanceUID -> FHIR.ImagingStudy.identifier
    Orthanc.PatientID -> FHIR.ImagingStudy.subject.identifier
    Orthanc.StudyDate + StudyTime -> FHIR.ImagingStudy.started
    Orthanc.ModalitiesInStudy -> FHIR.ImagingStudy.modality
    Orthanc.SeriesInstanceUID -> FHIR.ImagingStudy.series[].uid
"""

from typing import Dict, Any, List
from ..core import BaseAdapter


class ImagingStudyAdapter(BaseAdapter):
    """Adapter for ImagingStudy resources"""
    
    resource_type = "ImagingStudy"
    
    def to_fhir(self, local_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Orthanc study metadata to FHIR ImagingStudy.
        
        Expected local_record fields:
            - StudyInstanceUID: DICOM Study UID (required)
            - PatientID: Patient identifier (required)
            - StudyDate: Study date (YYYYMMDD)
            - StudyTime: Study time (HHMMSS)
            - ModalitiesInStudy: List of modalities (e.g., ['CT', 'MR'])
            - StudyDescription: Description
            - Series: List of series metadata (optional)
        """
        fhir_study = {
            "resourceType": "ImagingStudy",
            "status": "available",
            "identifier": [{
                "system": "urn:dicom:uid",
                "value": f"urn:oid:{local_record['StudyInstanceUID']}"
            }]
        }
        
        # Patient reference
        if "PatientID" in local_record:
            fhir_study["subject"] = {
                "identifier": {
                    "system": "urn:openemr:pid",
                    "value": local_record["PatientID"]
                }
            }
        
        # Study date/time
        if "StudyDate" in local_record:
            study_date = local_record["StudyDate"]
            study_time = local_record.get("StudyTime", "000000")
            
            # Convert DICOM format to ISO 8601
            # DICOM: YYYYMMDD and HHMMSS
            # ISO: YYYY-MM-DDTHH:MM:SSZ
            if len(study_date) == 8:
                iso_date = f"{study_date[0:4]}-{study_date[4:6]}-{study_date[6:8]}"
                if len(study_time) >= 6:
                    iso_time = f"{study_time[0:2]}:{study_time[2:4]}:{study_time[4:6]}"
                    fhir_study["started"] = f"{iso_date}T{iso_time}Z"
                else:
                    fhir_study["started"] = f"{iso_date}T00:00:00Z"
        
        # Modalities
        if "ModalitiesInStudy" in local_record:
            modalities = local_record["ModalitiesInStudy"]
            if isinstance(modalities, str):
                modalities = [modalities]
            
            fhir_study["modality"] = [{
                "system": "http://dicom.nema.org/resources/ontology/DCM",
                "code": modality
            } for modality in modalities]
        
        # Description
        if "StudyDescription" in local_record:
            fhir_study["description"] = local_record["StudyDescription"]
        
        # Number of series and instances
        if "NumberOfStudyRelatedSeries" in local_record:
            fhir_study["numberOfSeries"] = int(local_record["NumberOfStudyRelatedSeries"])
        if "NumberOfStudyRelatedInstances" in local_record:
            fhir_study["numberOfInstances"] = int(local_record["NumberOfStudyRelatedInstances"])
        
        # Series information
        if "Series" in local_record and local_record["Series"]:
            fhir_study["series"] = []
            for series in local_record["Series"]:
                fhir_series = {
                    "uid": series.get("SeriesInstanceUID", ""),
                    "modality": {
                        "system": "http://dicom.nema.org/resources/ontology/DCM",
                        "code": series.get("Modality", "OT")
                    }
                }
                
                if "SeriesNumber" in series:
                    fhir_series["number"] = int(series["SeriesNumber"])
                if "SeriesDescription" in series:
                    fhir_series["description"] = series["SeriesDescription"]
                if "NumberOfSeriesRelatedInstances" in series:
                    fhir_series["numberOfInstances"] = int(series["NumberOfSeriesRelatedInstances"])
                
                fhir_study["series"].append(fhir_series)
        
        return fhir_study
    
    def from_fhir(self, fhir_resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FHIR ImagingStudy to Orthanc format.
        
        Returns local record with fields:
            - StudyInstanceUID: DICOM Study UID
            - PatientID: Patient identifier
            - StudyDate: Study date (YYYYMMDD)
            - StudyTime: Study time (HHMMSS)
            - ModalitiesInStudy: List of modalities
            - StudyDescription: Description
            - Series: List of series
        """
        local_record = {}
        
        # Extract Study UID from identifier
        if "identifier" in fhir_resource:
            for identifier in fhir_resource["identifier"]:
                if identifier.get("system") == "urn:dicom:uid":
                    # Remove urn:oid: prefix if present
                    uid = identifier["value"]
                    if uid.startswith("urn:oid:"):
                        uid = uid[8:]
                    local_record["StudyInstanceUID"] = uid
                    break
        
        # Extract Patient ID
        if "subject" in fhir_resource:
            subject = fhir_resource["subject"]
            if "identifier" in subject:
                local_record["PatientID"] = subject["identifier"]["value"]
            elif "reference" in subject:
                # Extract ID from reference like "Patient/123"
                ref = subject["reference"]
                if "/" in ref:
                    local_record["PatientID"] = ref.split("/")[-1]
        
        # Convert started datetime to DICOM format
        if "started" in fhir_resource:
            # ISO: YYYY-MM-DDTHH:MM:SSZ
            # DICOM: YYYYMMDD and HHMMSS
            started = fhir_resource["started"].replace("-", "").replace(":", "")
            if "T" in started:
                date_part, time_part = started.split("T")
                local_record["StudyDate"] = date_part[:8]
                local_record["StudyTime"] = time_part[:6]
            else:
                local_record["StudyDate"] = started[:8]
        
        # Modalities
        if "modality" in fhir_resource:
            local_record["ModalitiesInStudy"] = [
                mod["code"] for mod in fhir_resource["modality"]
            ]
        
        # Description
        if "description" in fhir_resource:
            local_record["StudyDescription"] = fhir_resource["description"]
        
        # Counts
        if "numberOfSeries" in fhir_resource:
            local_record["NumberOfStudyRelatedSeries"] = fhir_resource["numberOfSeries"]
        if "numberOfInstances" in fhir_resource:
            local_record["NumberOfStudyRelatedInstances"] = fhir_resource["numberOfInstances"]
        
        # Series
        if "series" in fhir_resource:
            local_record["Series"] = []
            for fhir_series in fhir_resource["series"]:
                series = {
                    "SeriesInstanceUID": fhir_series.get("uid", "")
                }
                
                if "modality" in fhir_series:
                    series["Modality"] = fhir_series["modality"]["code"]
                if "number" in fhir_series:
                    series["SeriesNumber"] = fhir_series["number"]
                if "description" in fhir_series:
                    series["SeriesDescription"] = fhir_series["description"]
                if "numberOfInstances" in fhir_series:
                    series["NumberOfSeriesRelatedInstances"] = fhir_series["numberOfInstances"]
                
                local_record["Series"].append(series)
        
        return local_record
