#!/usr/bin/env python3
"""
HL7 Service for Medical Reporting Module
Implements HL7 v2.x and FHIR protocols for medical data exchange
"""

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class HL7MessageType(Enum):
    """HL7 Message Types"""
    ADT_A01 = "ADT^A01"  # Patient Admit
    ADT_A03 = "ADT^A03"  # Patient Discharge
    ADT_A08 = "ADT^A08"  # Patient Update
    ORU_R01 = "ORU^R01"  # Observation Result
    ORM_O01 = "ORM^O01"  # Order Message
    MDM_T02 = "MDM^T02"  # Medical Document Management

class HL7SegmentType(Enum):
    """HL7 Segment Types"""
    MSH = "MSH"  # Message Header
    PID = "PID"  # Patient Identification
    PV1 = "PV1"  # Patient Visit
    OBR = "OBR"  # Observation Request
    OBX = "OBX"  # Observation Result
    TXA = "TXA"  # Transcription Document Header

@dataclass
class HL7Patient:
    """HL7 Patient Information"""
    patient_id: str
    id_type: str = "MR"  # Medical Record Number
    family_name: str = ""
    given_name: str = ""
    middle_name: str = ""
    date_of_birth: str = ""
    gender: str = ""
    race: str = ""
    address: str = ""
    phone: str = ""
    ssn: str = ""

@dataclass
class HL7Observation:
    """HL7 Observation/Result"""
    observation_id: str
    observation_text: str
    value: str
    units: str = ""
    reference_range: str = ""
    abnormal_flags: str = ""
    result_status: str = "F"  # Final
    observation_datetime: str = ""

@dataclass
class HL7Report:
    """HL7 Medical Report"""
    report_id: str
    patient: HL7Patient
    report_type: str
    report_text: str
    report_status: str = "AU"  # Authenticated
    report_datetime: str = ""
    physician_id: str = ""
    physician_name: str = ""

class HL7Service:
    """HL7 Protocol Service for Medical Data Exchange"""
    
    def __init__(self):
        """Initialize HL7 Service"""
        self.sending_application = "SA_MEDICAL_REPORTING"
        self.sending_facility = "SA_HOSPITAL"
        self.receiving_application = "HIS"
        self.receiving_facility = "SA_HOSPITAL"
        self.version = "2.5"
        
        logger.info("HL7 Service initialized with SA Medical compliance")
    
    def generate_message_control_id(self) -> str:
        """Generate unique message control ID"""
        return str(uuid.uuid4()).replace('-', '')[:20]
    
    def format_timestamp(self, dt: datetime = None) -> str:
        """Format timestamp for HL7"""
        if dt is None:
            dt = datetime.now(timezone.utc)
        return dt.strftime("%Y%m%d%H%M%S")
    
    def create_msh_segment(self, message_type: HL7MessageType, control_id: str = None) -> str:
        """Create MSH (Message Header) segment"""
        if control_id is None:
            control_id = self.generate_message_control_id()
        
        timestamp = self.format_timestamp()
        
        msh_fields = [
            "MSH",
            "|",
            "^~\\&",
            self.sending_application,
            self.sending_facility,
            self.receiving_application,
            self.receiving_facility,
            timestamp,
            "",
            message_type.value,
            control_id,
            "P",  # Processing ID
            self.version
        ]
        
        return "|".join(msh_fields)
    
    def create_pid_segment(self, patient: HL7Patient) -> str:
        """Create PID (Patient Identification) segment"""
        pid_fields = [
            "PID",
            "1",  # Set ID
            "",   # Patient ID (External)
            f"{patient.patient_id}^^^{patient.id_type}",  # Patient Identifier List
            "",   # Alternate Patient ID
            f"{patient.family_name}^{patient.given_name}^{patient.middle_name}",  # Patient Name
            "",   # Mother's Maiden Name
            patient.date_of_birth,  # Date/Time of Birth
            patient.gender,  # Administrative Sex
            "",   # Patient Alias
            patient.race,  # Race
            patient.address,  # Patient Address
            "",   # County Code
            patient.phone,  # Phone Number - Home
            "",   # Phone Number - Business
            "",   # Primary Language
            "",   # Marital Status
            "",   # Religion
            "",   # Patient Account Number
            patient.ssn  # SSN Number - Patient
        ]
        
        return "|".join(pid_fields)
    
    def create_obr_segment(self, order_id: str, procedure_code: str, procedure_name: str) -> str:
        """Create OBR (Observation Request) segment"""
        timestamp = self.format_timestamp()
        
        obr_fields = [
            "OBR",
            "1",  # Set ID
            order_id,  # Placer Order Number
            "",   # Filler Order Number
            f"{procedure_code}^{procedure_name}^L",  # Universal Service Identifier
            "",   # Priority
            timestamp,  # Requested Date/Time
            "",   # Observation Date/Time
            "",   # Observation End Date/Time
            "",   # Collection Volume
            "",   # Collector Identifier
            "",   # Specimen Action Code
            "",   # Danger Code
            "",   # Relevant Clinical Information
            timestamp,  # Specimen Received Date/Time
            "",   # Specimen Source
            "",   # Ordering Provider
            "",   # Order Callback Phone Number
            "",   # Placer Field 1
            "",   # Placer Field 2
            "",   # Filler Field 1
            "",   # Filler Field 2
            timestamp,  # Results Rpt/Status Chng - Date/Time
            "",   # Charge to Practice
            "",   # Diagnostic Serv Sect ID
            "F"   # Result Status
        ]
        
        return "|".join(obr_fields)
    
    def create_obx_segment(self, observation: HL7Observation, set_id: int = 1) -> str:
        """Create OBX (Observation Result) segment"""
        obx_fields = [
            "OBX",
            str(set_id),  # Set ID
            "TX",  # Value Type (Text)
            f"{observation.observation_id}^{observation.observation_text}^L",  # Observation Identifier
            "",   # Observation Sub-ID
            observation.value,  # Observation Value
            observation.units,  # Units
            observation.reference_range,  # References Range
            observation.abnormal_flags,  # Abnormal Flags
            "",   # Probability
            "",   # Nature of Abnormal Test
            observation.result_status,  # Observation Result Status
            "",   # Effective Date of Reference Range
            "",   # User Defined Access Checks
            observation.observation_datetime if observation.observation_datetime else self.format_timestamp()
        ]
        
        return "|".join(obx_fields)
    
    def create_txa_segment(self, report: HL7Report) -> str:
        """Create TXA (Transcription Document Header) segment"""
        timestamp = self.format_timestamp()
        
        txa_fields = [
            "TXA",
            "1",  # Set ID
            "11",  # Document Type (Medical Report)
            "",   # Document Content Presentation
            "",   # Activity Date/Time
            f"{report.physician_id}^{report.physician_name}",  # Primary Activity Provider
            timestamp,  # Origination Date/Time
            "",   # Transcription Date/Time
            "",   # Edit Date/Time
            f"{report.physician_id}^{report.physician_name}",  # Originator
            "",   # Assigned Document Authenticator
            "",   # Transcriptionist
            report.report_id,  # Unique Document Number
            "",   # Parent Document Number
            "",   # Placer Order Number
            "",   # Filler Order Number
            "",   # Unique Document File Name
            report.report_status,  # Document Completion Status
            "",   # Document Confidentiality Status
            "",   # Document Availability Status
            "",   # Document Storage Status
            "",   # Document Change Reason
            "",   # Authentication Person, Time Stamp
            "",   # Distributed Copies
        ]
        
        return "|".join(txa_fields)
    
    def create_medical_report_message(self, report: HL7Report) -> str:
        """Create complete HL7 medical report message (MDM^T02)"""
        try:
            control_id = self.generate_message_control_id()
            
            # Create segments
            msh = self.create_msh_segment(HL7MessageType.MDM_T02, control_id)
            pid = self.create_pid_segment(report.patient)
            txa = self.create_txa_segment(report)
            
            # Create observation for report text
            observation = HL7Observation(
                observation_id="REPORT",
                observation_text="Medical Report",
                value=report.report_text,
                observation_datetime=report.report_datetime
            )
            obx = self.create_obx_segment(observation)
            
            # Combine segments with carriage return
            message = "\r".join([msh, pid, txa, obx])
            
            logger.info(f"Created HL7 medical report message for patient {report.patient.patient_id}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to create HL7 medical report message: {e}")
            raise
    
    def create_observation_result_message(self, patient: HL7Patient, observations: List[HL7Observation]) -> str:
        """Create HL7 observation result message (ORU^R01)"""
        try:
            control_id = self.generate_message_control_id()
            
            # Create segments
            msh = self.create_msh_segment(HL7MessageType.ORU_R01, control_id)
            pid = self.create_pid_segment(patient)
            obr = self.create_obr_segment("ORDER001", "RAD", "Radiology Report")
            
            # Create OBX segments for each observation
            obx_segments = []
            for i, obs in enumerate(observations, 1):
                obx_segments.append(self.create_obx_segment(obs, i))
            
            # Combine segments
            segments = [msh, pid, obr] + obx_segments
            message = "\r".join(segments)
            
            logger.info(f"Created HL7 observation result message for patient {patient.patient_id}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to create HL7 observation result message: {e}")
            raise
    
    def parse_hl7_message(self, message: str) -> Dict[str, Any]:
        """Parse incoming HL7 message"""
        try:
            segments = message.split('\r')
            parsed_message = {
                'message_type': '',
                'control_id': '',
                'patient': {},
                'observations': [],
                'raw_segments': segments
            }
            
            for segment in segments:
                if not segment:
                    continue
                    
                fields = segment.split('|')
                segment_type = fields[0]
                
                if segment_type == 'MSH':
                    parsed_message['message_type'] = fields[9] if len(fields) > 9 else ''
                    parsed_message['control_id'] = fields[10] if len(fields) > 10 else ''
                
                elif segment_type == 'PID':
                    if len(fields) > 5:
                        name_parts = fields[5].split('^')
                        parsed_message['patient'] = {
                            'patient_id': fields[3].split('^')[0] if len(fields) > 3 else '',
                            'family_name': name_parts[0] if len(name_parts) > 0 else '',
                            'given_name': name_parts[1] if len(name_parts) > 1 else '',
                            'date_of_birth': fields[7] if len(fields) > 7 else '',
                            'gender': fields[8] if len(fields) > 8 else ''
                        }
                
                elif segment_type == 'OBX':
                    if len(fields) > 5:
                        observation = {
                            'observation_id': fields[3].split('^')[0] if len(fields) > 3 else '',
                            'observation_text': fields[3].split('^')[1] if len(fields) > 3 and '^' in fields[3] else '',
                            'value': fields[5] if len(fields) > 5 else '',
                            'units': fields[6] if len(fields) > 6 else '',
                            'result_status': fields[11] if len(fields) > 11 else ''
                        }
                        parsed_message['observations'].append(observation)
            
            logger.info(f"Parsed HL7 message: {parsed_message['message_type']}")
            return parsed_message
            
        except Exception as e:
            logger.error(f"Failed to parse HL7 message: {e}")
            raise
    
    def validate_hl7_message(self, message: str) -> bool:
        """Validate HL7 message format"""
        try:
            if not message:
                return False
            
            segments = message.split('\r')
            if not segments:
                return False
            
            # Check for MSH segment
            msh_segment = segments[0]
            if not msh_segment.startswith('MSH|'):
                return False
            
            # Basic field validation
            msh_fields = msh_segment.split('|')
            if len(msh_fields) < 12:
                return False
            
            logger.info("HL7 message validation passed")
            return True
            
        except Exception as e:
            logger.error(f"HL7 message validation failed: {e}")
            return False
    
    def get_supported_message_types(self) -> List[str]:
        """Get list of supported HL7 message types"""
        return [msg_type.value for msg_type in HL7MessageType]
    
    def create_ack_message(self, original_control_id: str, ack_code: str = "AA") -> str:
        """Create HL7 ACK (Acknowledgment) message"""
        try:
            control_id = self.generate_message_control_id()
            timestamp = self.format_timestamp()
            
            msh_fields = [
                "MSH",
                "|",
                "^~\\&",
                self.sending_application,
                self.sending_facility,
                self.receiving_application,
                self.receiving_facility,
                timestamp,
                "",
                "ACK",
                control_id,
                "P",
                self.version
            ]
            
            msa_fields = [
                "MSA",
                ack_code,  # Acknowledgment Code (AA=Application Accept, AE=Application Error)
                original_control_id,
                "Message processed successfully" if ack_code == "AA" else "Message processing failed"
            ]
            
            msh = "|".join(msh_fields)
            msa = "|".join(msa_fields)
            
            message = "\r".join([msh, msa])
            
            logger.info(f"Created HL7 ACK message for control ID {original_control_id}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to create HL7 ACK message: {e}")
            raise