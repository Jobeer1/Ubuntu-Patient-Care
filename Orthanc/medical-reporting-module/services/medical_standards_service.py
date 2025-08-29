#!/usr/bin/env python3
"""
Medical Standards Compliance Service
Ensures compliance with SA medical standards, HPCSA guidelines, and international protocols
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ComplianceStandard(Enum):
    """Medical compliance standards"""
    HPCSA = "HPCSA"  # Health Professions Council of South Africa
    POPIA = "POPIA"  # Protection of Personal Information Act
    HL7_V2 = "HL7_V2"  # HL7 Version 2.x
    FHIR_R4 = "FHIR_R4"  # FHIR Release 4
    DICOM = "DICOM"  # Digital Imaging and Communications in Medicine
    ICD10 = "ICD10"  # International Classification of Diseases
    SNOMED_CT = "SNOMED_CT"  # Systematized Nomenclature of Medicine Clinical Terms

@dataclass
class ComplianceResult:
    """Result of compliance check"""
    standard: ComplianceStandard
    compliant: bool
    issues: List[str]
    recommendations: List[str]
    severity: str  # "low", "medium", "high", "critical"

class MedicalStandardsService:
    """Service for ensuring medical standards compliance"""
    
    def __init__(self):
        """Initialize Medical Standards Service"""
        self.standards = {
            ComplianceStandard.HPCSA: self._check_hpcsa_compliance,
            ComplianceStandard.POPIA: self._check_popia_compliance,
            ComplianceStandard.HL7_V2: self._check_hl7_compliance,
            ComplianceStandard.FHIR_R4: self._check_fhir_compliance,
            ComplianceStandard.DICOM: self._check_dicom_compliance,
            ComplianceStandard.ICD10: self._check_icd10_compliance,
            ComplianceStandard.SNOMED_CT: self._check_snomed_compliance
        }
        
        # SA Medical terminology and codes
        self.sa_medical_codes = {
            "provinces": ["GP", "WC", "KZN", "EC", "FS", "LP", "MP", "NC", "NW"],
            "languages": ["en", "af", "zu", "xh", "st", "tn", "ss", "ve", "ts", "nr", "nd"],
            "medical_schemes": ["GEMS", "POLMED", "BESTMED", "DISCOVERY", "MOMENTUM", "MEDSCHEME"]
        }
        
        logger.info("Medical Standards Compliance Service initialized for SA healthcare")
    
    def check_compliance(self, data: Dict, standards: List[ComplianceStandard] = None) -> List[ComplianceResult]:
        """Check compliance against specified standards"""
        if standards is None:
            standards = list(ComplianceStandard)
        
        results = []
        
        for standard in standards:
            if standard in self.standards:
                try:
                    result = self.standards[standard](data)
                    results.append(result)
                    logger.info(f"Compliance check completed for {standard.value}: {'PASS' if result.compliant else 'FAIL'}")
                except Exception as e:
                    logger.error(f"Compliance check failed for {standard.value}: {e}")
                    results.append(ComplianceResult(
                        standard=standard,
                        compliant=False,
                        issues=[f"Compliance check error: {str(e)}"],
                        recommendations=["Review data format and try again"],
                        severity="high"
                    ))
        
        return results
    
    def _check_hpcsa_compliance(self, data: Dict) -> ComplianceResult:
        """Check HPCSA (Health Professions Council of South Africa) compliance"""
        issues = []
        recommendations = []
        
        # Check practitioner registration
        practitioner = data.get('practitioner', {})
        if not practitioner.get('hpcsa_number'):
            issues.append("Missing HPCSA registration number")
            recommendations.append("Include valid HPCSA registration number")
        
        # Check professional title
        if not practitioner.get('title') or practitioner.get('title') not in ['Dr', 'Prof', 'Mr', 'Ms', 'Mrs']:
            issues.append("Invalid or missing professional title")
            recommendations.append("Use appropriate professional title (Dr, Prof, etc.)")
        
        # Check medical report structure
        report = data.get('report', {})
        required_sections = ['patient_details', 'clinical_findings', 'diagnosis', 'recommendations']
        for section in required_sections:
            if section not in report:
                issues.append(f"Missing required report section: {section}")
                recommendations.append(f"Include {section} section in medical report")
        
        # Check patient consent
        patient = data.get('patient', {})
        if not patient.get('consent_given'):
            issues.append("Patient consent not documented")
            recommendations.append("Ensure patient consent is properly documented")
        
        # Check date and time stamps
        if not report.get('report_date'):
            issues.append("Missing report date")
            recommendations.append("Include report creation date and time")
        
        severity = "critical" if len(issues) > 3 else "high" if len(issues) > 1 else "medium" if issues else "low"
        
        return ComplianceResult(
            standard=ComplianceStandard.HPCSA,
            compliant=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            severity=severity
        )
    
    def _check_popia_compliance(self, data: Dict) -> ComplianceResult:
        """Check POPIA (Protection of Personal Information Act) compliance"""
        issues = []
        recommendations = []
        
        patient = data.get('patient', {})
        
        # Check data minimization
        sensitive_fields = ['id_number', 'passport_number', 'financial_info', 'biometric_data']
        for field in sensitive_fields:
            if field in patient and not data.get('data_justification', {}).get(field):
                issues.append(f"Sensitive data '{field}' without justification")
                recommendations.append(f"Provide justification for collecting {field}")
        
        # Check consent
        if not patient.get('popia_consent'):
            issues.append("POPIA consent not obtained")
            recommendations.append("Obtain explicit POPIA consent from patient")
        
        # Check data retention policy
        if not data.get('retention_policy'):
            issues.append("Data retention policy not specified")
            recommendations.append("Define data retention and deletion policy")
        
        # Check access controls
        if not data.get('access_controls'):
            issues.append("Access controls not defined")
            recommendations.append("Implement proper access controls for patient data")
        
        # Check encryption
        if not data.get('encryption_status'):
            issues.append("Data encryption status not verified")
            recommendations.append("Ensure patient data is properly encrypted")
        
        severity = "critical" if len(issues) > 2 else "high" if len(issues) > 1 else "medium" if issues else "low"
        
        return ComplianceResult(
            standard=ComplianceStandard.POPIA,
            compliant=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            severity=severity
        )
    
    def _check_hl7_compliance(self, data: Dict) -> ComplianceResult:
        """Check HL7 v2.x compliance"""
        issues = []
        recommendations = []
        
        # Check message structure
        if 'hl7_message' in data:
            message = data['hl7_message']
            
            # Check MSH segment
            if not message.startswith('MSH|'):
                issues.append("Invalid HL7 message - missing MSH segment")
                recommendations.append("Ensure HL7 message starts with MSH segment")
            
            # Check field separators
            if '|' not in message or '^' not in message:
                issues.append("Invalid HL7 field separators")
                recommendations.append("Use proper HL7 field separators (| and ^)")
            
            # Check message type
            segments = message.split('\r')
            if segments:
                msh_fields = segments[0].split('|')
                if len(msh_fields) < 9 or not msh_fields[8]:
                    issues.append("Missing HL7 message type")
                    recommendations.append("Include valid HL7 message type in MSH segment")
        
        # Check patient identification
        patient = data.get('patient', {})
        if not patient.get('patient_id'):
            issues.append("Missing patient identifier")
            recommendations.append("Include unique patient identifier")
        
        severity = "high" if len(issues) > 1 else "medium" if issues else "low"
        
        return ComplianceResult(
            standard=ComplianceStandard.HL7_V2,
            compliant=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            severity=severity
        )
    
    def _check_fhir_compliance(self, data: Dict) -> ComplianceResult:
        """Check FHIR R4 compliance"""
        issues = []
        recommendations = []
        
        # Check FHIR resource structure
        if 'fhir_resource' in data:
            resource = data['fhir_resource']
            
            # Check resource type
            if 'resourceType' not in resource:
                issues.append("Missing FHIR resourceType")
                recommendations.append("Include resourceType in FHIR resource")
            
            # Check resource ID
            if 'id' not in resource:
                issues.append("Missing FHIR resource ID")
                recommendations.append("Include unique ID in FHIR resource")
            
            # Check meta information
            if 'meta' not in resource:
                issues.append("Missing FHIR meta information")
                recommendations.append("Include meta information with version and lastUpdated")
            
            # Resource-specific checks
            resource_type = resource.get('resourceType')
            if resource_type == 'Patient':
                if 'identifier' not in resource:
                    issues.append("Patient resource missing identifier")
                    recommendations.append("Include patient identifier in Patient resource")
            
            elif resource_type == 'Observation':
                required_fields = ['status', 'code', 'subject']
                for field in required_fields:
                    if field not in resource:
                        issues.append(f"Observation resource missing {field}")
                        recommendations.append(f"Include {field} in Observation resource")
        
        severity = "high" if len(issues) > 2 else "medium" if issues else "low"
        
        return ComplianceResult(
            standard=ComplianceStandard.FHIR_R4,
            compliant=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            severity=severity
        )
    
    def _check_dicom_compliance(self, data: Dict) -> ComplianceResult:
        """Check DICOM compliance"""
        issues = []
        recommendations = []
        
        # Check DICOM metadata
        dicom_data = data.get('dicom', {})
        
        # Check required DICOM tags
        required_tags = [
            'PatientID', 'PatientName', 'StudyInstanceUID', 
            'SeriesInstanceUID', 'SOPInstanceUID', 'Modality'
        ]
        
        for tag in required_tags:
            if tag not in dicom_data:
                issues.append(f"Missing required DICOM tag: {tag}")
                recommendations.append(f"Include {tag} in DICOM metadata")
        
        # Check patient privacy
        if dicom_data.get('PatientName') and not data.get('anonymization_applied'):
            issues.append("Patient name in DICOM without anonymization flag")
            recommendations.append("Apply anonymization or set anonymization flag")
        
        severity = "high" if len(issues) > 2 else "medium" if issues else "low"
        
        return ComplianceResult(
            standard=ComplianceStandard.DICOM,
            compliant=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            severity=severity
        )
    
    def _check_icd10_compliance(self, data: Dict) -> ComplianceResult:
        """Check ICD-10 compliance"""
        issues = []
        recommendations = []
        
        # Check diagnosis codes
        diagnoses = data.get('diagnoses', [])
        
        for diagnosis in diagnoses:
            code = diagnosis.get('icd10_code')
            if not code:
                issues.append("Missing ICD-10 code for diagnosis")
                recommendations.append("Include valid ICD-10 code for all diagnoses")
            elif not self._validate_icd10_format(code):
                issues.append(f"Invalid ICD-10 code format: {code}")
                recommendations.append("Use proper ICD-10 code format (e.g., A00.0)")
        
        severity = "medium" if issues else "low"
        
        return ComplianceResult(
            standard=ComplianceStandard.ICD10,
            compliant=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            severity=severity
        )
    
    def _check_snomed_compliance(self, data: Dict) -> ComplianceResult:
        """Check SNOMED CT compliance"""
        issues = []
        recommendations = []
        
        # Check clinical terms
        clinical_terms = data.get('clinical_terms', [])
        
        for term in clinical_terms:
            if not term.get('snomed_code'):
                issues.append("Missing SNOMED CT code for clinical term")
                recommendations.append("Include SNOMED CT codes for clinical terminology")
        
        severity = "low" if issues else "low"
        
        return ComplianceResult(
            standard=ComplianceStandard.SNOMED_CT,
            compliant=len(issues) == 0,
            issues=issues,
            recommendations=recommendations,
            severity=severity
        )
    
    def _validate_icd10_format(self, code: str) -> bool:
        """Validate ICD-10 code format"""
        import re
        # Basic ICD-10 format: Letter followed by 2 digits, optional decimal and 1-2 digits
        pattern = r'^[A-Z]\d{2}(\.\d{1,2})?$'
        return bool(re.match(pattern, code))
    
    def generate_compliance_report(self, results: List[ComplianceResult]) -> Dict:
        """Generate comprehensive compliance report"""
        total_standards = len(results)
        compliant_standards = sum(1 for r in results if r.compliant)
        
        # Categorize issues by severity
        critical_issues = []
        high_issues = []
        medium_issues = []
        low_issues = []
        
        for result in results:
            if result.severity == "critical":
                critical_issues.extend(result.issues)
            elif result.severity == "high":
                high_issues.extend(result.issues)
            elif result.severity == "medium":
                medium_issues.extend(result.issues)
            else:
                low_issues.extend(result.issues)
        
        # Overall compliance score
        compliance_score = (compliant_standards / total_standards) * 100 if total_standards > 0 else 0
        
        # Determine overall status
        if critical_issues:
            overall_status = "CRITICAL"
        elif high_issues:
            overall_status = "HIGH_RISK"
        elif medium_issues:
            overall_status = "MEDIUM_RISK"
        elif low_issues:
            overall_status = "LOW_RISK"
        else:
            overall_status = "COMPLIANT"
        
        report = {
            "report_id": f"COMPLIANCE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status,
            "compliance_score": round(compliance_score, 2),
            "standards_checked": total_standards,
            "compliant_standards": compliant_standards,
            "summary": {
                "critical_issues": len(critical_issues),
                "high_issues": len(high_issues),
                "medium_issues": len(medium_issues),
                "low_issues": len(low_issues)
            },
            "detailed_results": [
                {
                    "standard": result.standard.value,
                    "compliant": result.compliant,
                    "severity": result.severity,
                    "issues": result.issues,
                    "recommendations": result.recommendations
                }
                for result in results
            ],
            "next_steps": self._generate_next_steps(results)
        }
        
        logger.info(f"Generated compliance report: {overall_status} ({compliance_score:.1f}% compliant)")
        return report
    
    def _generate_next_steps(self, results: List[ComplianceResult]) -> List[str]:
        """Generate next steps based on compliance results"""
        next_steps = []
        
        # Critical issues first
        critical_results = [r for r in results if r.severity == "critical"]
        if critical_results:
            next_steps.append("URGENT: Address critical compliance issues immediately")
            for result in critical_results:
                next_steps.extend(result.recommendations[:2])  # Top 2 recommendations
        
        # High priority issues
        high_results = [r for r in results if r.severity == "high"]
        if high_results:
            next_steps.append("HIGH PRIORITY: Resolve high-risk compliance issues")
            for result in high_results:
                next_steps.extend(result.recommendations[:1])  # Top recommendation
        
        # General recommendations
        if not critical_results and not high_results:
            next_steps.append("Continue monitoring compliance status")
            next_steps.append("Review and update policies regularly")
            next_steps.append("Conduct regular compliance audits")
        
        return next_steps[:10]  # Limit to top 10 next steps