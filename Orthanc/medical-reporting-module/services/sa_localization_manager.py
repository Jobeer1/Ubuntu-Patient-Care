"""
South African Localization Manager for Medical Reporting Module
Handles South African medical terminology, workflows, and localization
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MedicalAidScheme(Enum):
    """Common South African medical aid schemes"""
    DISCOVERY = "Discovery Health"
    MOMENTUM = "Momentum Health"
    MEDSCHEME = "Medscheme"
    BONITAS = "Bonitas"
    BESTMED = "Bestmed"
    FEDHEALTH = "Fedhealth"
    GEMS = "GEMS"
    KEYHEALTH = "KeyHealth"
    MEDIHELP = "Medihelp"
    PROFMED = "Profmed"

@dataclass
class SAMedicalTemplate:
    """South African specific medical template"""
    id: str
    name: str
    category: str
    specialty: str
    template_text: str
    voice_commands: List[str]
    common_findings: List[str]

class SALocalizationManager:
    """Manages South African medical localization"""
    
    def __init__(self):
        """Initialize SA localization manager"""
        self.sa_medical_terms = self._load_sa_medical_dictionary()
        self.sa_pronunciation_map = self._load_sa_pronunciation_map()
        self.sa_templates = self._load_sa_medical_templates()
        self.medical_aid_schemes = self._load_medical_aid_schemes()
        
        logger.info(f"SA Localization Manager initialized with {len(self.sa_medical_terms)} medical terms")
    
    def _load_sa_medical_dictionary(self) -> Dict[str, str]:
        """Load South African medical terminology dictionary"""
        return {
            # TB and respiratory (high priority in SA)
            "tb": "tuberculosis",
            "tuberculosis": "tuberculosis",
            "mdr tb": "multi-drug resistant tuberculosis",
            "xdr tb": "extensively drug-resistant tuberculosis",
            "pneumoconiosis": "pneumoconiosis",
            "silicosis": "silicosis",
            "asbestosis": "asbestosis",
            "mesothelioma": "mesothelioma",
            
            # HIV-related conditions (high prevalence)
            "hiv": "HIV",
            "aids": "AIDS",
            "pneumocystis": "Pneumocystis jirovecii",
            "pcp": "Pneumocystis pneumonia",
            "kaposi": "Kaposi's sarcoma",
            "cryptococcal": "cryptococcal",
            "toxoplasmosis": "toxoplasmosis",
            "cmv": "cytomegalovirus",
            
            # Trauma (high incidence in SA)
            "gsw": "gunshot wound",
            "gunshot wound": "gunshot wound",
            "stab wound": "stab wound",
            "mva": "motor vehicle accident",
            "motor vehicle accident": "motor vehicle accident",
            "rta": "road traffic accident",
            "assault": "assault",
            "blunt trauma": "blunt trauma",
            "penetrating trauma": "penetrating trauma",
            
            # Malnutrition and related
            "kwashiorkor": "kwashiorkor",
            "marasmus": "marasmus",
            "pem": "protein-energy malnutrition",
            "stunting": "stunting",
            "wasting": "wasting",
            
            # Endemic diseases
            "malaria": "malaria",
            "bilharzia": "schistosomiasis",
            "schistosomiasis": "schistosomiasis",
            "typhoid": "typhoid fever",
            "hepatitis b": "hepatitis B",
            
            # Common SA medical terms
            "casualty": "emergency department",
            "theatre": "operating theatre",
            "ward round": "ward round",
            "referral letter": "referral letter",
            "discharge summary": "discharge summary",
            
            # Anatomical terms with SA pronunciation
            "oesophagus": "oesophagus",
            "colour": "colour",
            "centre": "centre",
            "metre": "metre",
            "litre": "litre",
            
            # Common findings
            "consolidation": "consolidation",
            "atelectasis": "atelectasis",
            "pleural effusion": "pleural effusion",
            "pneumothorax": "pneumothorax",
            "haemothorax": "haemothorax",
            "bilateral": "bilateral",
            "unilateral": "unilateral",
            "cardiomegaly": "cardiomegaly",
            "pulmonary oedema": "pulmonary oedema",
            
            # Standard phrases
            "within normal limits": "within normal limits",
            "no acute abnormality": "no acute abnormality",
            "unremarkable": "unremarkable",
            "consistent with": "consistent with",
            "suggestive of": "suggestive of",
            "cannot exclude": "cannot exclude",
            "recommend correlation": "recommend clinical correlation",
            
            # Anatomical regions
            "right upper lobe": "right upper lobe",
            "right middle lobe": "right middle lobe",
            "right lower lobe": "right lower lobe",
            "left upper lobe": "left upper lobe",
            "left lower lobe": "left lower lobe",
            "lingula": "lingula",
            "mediastinum": "mediastinum",
            "hilum": "hilum",
            "hila": "hila",
            "cardiac silhouette": "cardiac silhouette",
            "costophrenic angle": "costophrenic angle",
            "diaphragm": "diaphragm",
            
            # Measurements and units
            "millimetre": "millimetre",
            "centimetre": "centimetre",
            "hounsfield unit": "Hounsfield unit",
            "kilovolt": "kilovolt",
            "milliampere": "milliampere"
        }
    
    def _load_sa_pronunciation_map(self) -> Dict[str, List[str]]:
        """Load South African English pronunciation variations"""
        return {
            # Common mispronunciations that need correction
            "tuberculosis": ["tb", "tee bee", "tuber", "tuberc"],
            "pneumonia": ["pneum", "new monia", "pneu monia"],
            "oesophagus": ["esophagus", "ee sophagus"],
            "haemorrhage": ["hemorrhage", "hem rage"],
            "anaemia": ["anemia", "an emia"],
            "oedema": ["edema", "ee dema"],
            "colour": ["color"],
            "centre": ["center"],
            "metre": ["meter"],
            "litre": ["liter"],
            
            # Medical terms with SA accent variations
            "fracture": ["frak cher", "frac ture"],
            "pneumothorax": ["pneumo thorax", "new mo thorax"],
            "atelectasis": ["atel ectasis", "a tel ectasis"],
            "consolidation": ["con solid ation", "consol idation"],
            
            # Anatomical terms
            "diaphragm": ["dia phragm", "die a phragm"],
            "mediastinum": ["media stinum", "medi astinum"],
            "costophrenic": ["costo phrenic", "cost o phrenic"]
        }
    
    def _load_sa_medical_templates(self) -> List[SAMedicalTemplate]:
        """Load South African specific medical templates"""
        templates = []
        
        # TB Screening Template
        templates.append(SAMedicalTemplate(
            id="tb_screening_cxr",
            name="TB Screening Chest X-ray",
            category="Respiratory",
            specialty="Radiology",
            template_text="""
CLINICAL INDICATION: TB screening

FINDINGS:
The lungs are clear with no evidence of consolidation, cavitation, or pleural effusion.
The cardiac silhouette is within normal limits.
The mediastinal contours are unremarkable.
No hilar lymphadenopathy is identified.
The costophrenic angles are sharp.
No pneumothorax is present.

IMPRESSION:
No radiological evidence of active pulmonary tuberculosis.
Normal chest radiograph.

RECOMMENDATION:
Clinical correlation advised if symptoms persist.
            """.strip(),
            voice_commands=["tb screening", "tuberculosis screening", "chest x-ray tb"],
            common_findings=["normal", "consolidation", "cavitation", "pleural effusion", "hilar lymphadenopathy"]
        ))
        
        # Trauma Assessment Template
        templates.append(SAMedicalTemplate(
            id="trauma_cxr",
            name="Trauma Chest X-ray",
            category="Trauma",
            specialty="Emergency",
            template_text="""
CLINICAL INDICATION: Trauma assessment

FINDINGS:
The lungs are expanded and clear bilaterally.
No pneumothorax or haemothorax is identified.
The cardiac silhouette appears normal in size and contour.
The mediastinal width is within normal limits.
No obvious rib fractures are seen on this projection.
The diaphragmatic contours are intact.

IMPRESSION:
No acute cardiopulmonary abnormality identified.

RECOMMENDATION:
Clinical correlation advised.
Consider CT chest if high clinical suspicion for injury.
            """.strip(),
            voice_commands=["trauma chest", "trauma assessment", "emergency chest"],
            common_findings=["pneumothorax", "haemothorax", "rib fracture", "mediastinal widening"]
        ))
        
        # HIV-related Pneumonia Template
        templates.append(SAMedicalTemplate(
            id="hiv_pneumonia_cxr",
            name="HIV-related Pneumonia Assessment",
            category="Infectious Disease",
            specialty="Internal Medicine",
            template_text="""
CLINICAL INDICATION: HIV-positive patient with respiratory symptoms

FINDINGS:
Bilateral lower lobe consolidation is present.
No cavitation is identified.
No pleural effusion is seen.
The cardiac silhouette is within normal limits.
No hilar lymphadenopathy is evident.

IMPRESSION:
Bilateral lower lobe pneumonia.
Differential diagnosis includes:
- Pneumocystis jirovecii pneumonia (PCP)
- Bacterial pneumonia
- Atypical pneumonia

RECOMMENDATION:
Clinical correlation and appropriate microbiological investigations advised.
Consider high-resolution CT chest for further characterization if clinically indicated.
            """.strip(),
            voice_commands=["hiv pneumonia", "pcp assessment", "aids pneumonia"],
            common_findings=["bilateral consolidation", "ground glass", "pneumocystis", "opportunistic infection"]
        ))
        
        return templates
    
    def _load_medical_aid_schemes(self) -> Dict[str, Dict]:
        """Load South African medical aid scheme information"""
        return {
            scheme.value: {
                "name": scheme.value,
                "code": scheme.name,
                "common_abbreviations": self._get_scheme_abbreviations(scheme)
            }
            for scheme in MedicalAidScheme
        }
    
    def _get_scheme_abbreviations(self, scheme: MedicalAidScheme) -> List[str]:
        """Get common abbreviations for medical aid schemes"""
        abbreviations = {
            MedicalAidScheme.DISCOVERY: ["DH", "Discovery", "Disc"],
            MedicalAidScheme.MOMENTUM: ["Momentum", "Mom"],
            MedicalAidScheme.MEDSCHEME: ["Medscheme", "Med"],
            MedicalAidScheme.BONITAS: ["Bonitas", "Bon"],
            MedicalAidScheme.BESTMED: ["Bestmed", "Best"],
            MedicalAidScheme.FEDHEALTH: ["Fedhealth", "Fed"],
            MedicalAidScheme.GEMS: ["GEMS", "Government"],
            MedicalAidScheme.KEYHEALTH: ["KeyHealth", "Key"],
            MedicalAidScheme.MEDIHELP: ["Medihelp", "Medi"],
            MedicalAidScheme.PROFMED: ["Profmed", "Prof"]
        }
        return abbreviations.get(scheme, [])
    
    def enhance_transcription_for_sa(self, text: str) -> str:
        """Enhance transcription with South African medical terminology"""
        try:
            enhanced_text = text.lower()
            
            # Apply SA medical vocabulary
            for term, correction in self.sa_medical_terms.items():
                pattern = r'\b' + re.escape(term.lower()) + r'\b'
                enhanced_text = re.sub(pattern, correction, enhanced_text, flags=re.IGNORECASE)
            
            # Apply pronunciation corrections
            for correct_term, variations in self.sa_pronunciation_map.items():
                for variation in variations:
                    pattern = r'\b' + re.escape(variation.lower()) + r'\b'
                    enhanced_text = re.sub(pattern, correct_term, enhanced_text, flags=re.IGNORECASE)
            
            # Capitalize sentences properly
            sentences = enhanced_text.split('. ')
            capitalized_sentences = [s.capitalize() for s in sentences if s.strip()]
            enhanced_text = '. '.join(capitalized_sentences)
            
            return enhanced_text
            
        except Exception as e:
            logger.error(f"Failed to enhance transcription for SA: {e}")
            return text
    
    def validate_sa_id_number(self, id_number: str) -> Tuple[bool, str]:
        """Validate South African ID number"""
        try:
            # Remove any spaces or special characters
            clean_id = re.sub(r'[^\d]', '', id_number)
            
            if len(clean_id) != 13:
                return False, "ID number must be 13 digits"
            
            # Basic format validation (YYMMDD + 4 digits + citizenship + 8th digit + checksum)
            year = int(clean_id[:2])
            month = int(clean_id[2:4])
            day = int(clean_id[4:6])
            
            # Validate date components
            if month < 1 or month > 12:
                return False, "Invalid month in ID number"
            
            if day < 1 or day > 31:
                return False, "Invalid day in ID number"
            
            # Validate checksum (Luhn algorithm)
            if not self._validate_id_checksum(clean_id):
                return False, "Invalid ID number checksum"
            
            return True, "Valid South African ID number"
            
        except Exception as e:
            logger.error(f"Failed to validate SA ID number: {e}")
            return False, "Error validating ID number"
    
    def _validate_id_checksum(self, id_number: str) -> bool:
        """Validate SA ID number using Luhn algorithm"""
        try:
            # Luhn algorithm for SA ID validation
            digits = [int(d) for d in id_number]
            checksum = 0
            
            for i in range(12):
                if i % 2 == 0:
                    checksum += digits[i]
                else:
                    doubled = digits[i] * 2
                    checksum += doubled if doubled < 10 else doubled - 9
            
            return (10 - (checksum % 10)) % 10 == digits[12]
            
        except Exception:
            return False
    
    def format_sa_id_number(self, id_number: str) -> str:
        """Format SA ID number with proper spacing"""
        try:
            clean_id = re.sub(r'[^\d]', '', id_number)
            if len(clean_id) == 13:
                return f"{clean_id[:6]} {clean_id[6:10]} {clean_id[10:]}"
            return id_number
        except Exception:
            return id_number
    
    def validate_medical_aid_scheme(self, scheme_name: str, member_number: str = None) -> Tuple[bool, str]:
        """Validate medical aid scheme"""
        try:
            scheme_name_lower = scheme_name.lower()
            
            # Check against known schemes
            for scheme_info in self.medical_aid_schemes.values():
                if (scheme_name_lower == scheme_info["name"].lower() or
                    scheme_name_lower in [abbr.lower() for abbr in scheme_info["common_abbreviations"]]):
                    
                    # Basic member number validation (if provided)
                    if member_number:
                        clean_number = re.sub(r'[^\w]', '', member_number)
                        if len(clean_number) < 6:
                            return False, f"Member number too short for {scheme_info['name']}"
                    
                    return True, f"Valid medical aid scheme: {scheme_info['name']}"
            
            return False, "Unknown medical aid scheme"
            
        except Exception as e:
            logger.error(f"Failed to validate medical aid scheme: {e}")
            return False, "Error validating medical aid scheme"
    
    def get_sa_medical_templates(self, specialty: str = None, category: str = None) -> List[SAMedicalTemplate]:
        """Get South African medical templates"""
        try:
            templates = self.sa_templates
            
            if specialty:
                templates = [t for t in templates if t.specialty.lower() == specialty.lower()]
            
            if category:
                templates = [t for t in templates if t.category.lower() == category.lower()]
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get SA medical templates: {e}")
            return []
    
    def get_template_by_voice_command(self, command: str) -> Optional[SAMedicalTemplate]:
        """Get template by voice command"""
        try:
            command_lower = command.lower().strip()
            
            for template in self.sa_templates:
                for voice_cmd in template.voice_commands:
                    if voice_cmd.lower() in command_lower or command_lower in voice_cmd.lower():
                        return template
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get template by voice command: {e}")
            return None
    
    def localize_interface_text(self, text_dict: Dict[str, str]) -> Dict[str, str]:
        """Localize interface text for South African context"""
        try:
            sa_localizations = {
                # Medical terminology
                "emergency_room": "casualty",
                "operating_room": "theatre",
                "color": "colour",
                "center": "centre",
                "meter": "metre",
                "liter": "litre",
                
                # Common UI terms
                "patient_id": "Patient ID / SA ID Number",
                "medical_insurance": "Medical Aid",
                "insurance_number": "Medical Aid Number",
                
                # Workflow terms
                "discharge_summary": "Discharge Summary",
                "referral_letter": "Referral Letter",
                "ward_round": "Ward Round",
                
                # Report sections
                "clinical_history": "Clinical History",
                "examination": "Examination",
                "findings": "Findings",
                "impression": "Impression",
                "recommendation": "Recommendation"
            }
            
            localized_dict = text_dict.copy()
            
            for key, value in text_dict.items():
                if key in sa_localizations:
                    localized_dict[key] = sa_localizations[key]
                elif isinstance(value, str):
                    # Apply terminology corrections to text values
                    for en_term, sa_term in sa_localizations.items():
                        localized_dict[key] = value.replace(en_term, sa_term)
            
            return localized_dict
            
        except Exception as e:
            logger.error(f"Failed to localize interface text: {e}")
            return text_dict
    
    def get_sa_healthcare_workflows(self) -> Dict[str, List[str]]:
        """Get South African healthcare workflow patterns"""
        return {
            "emergency_workflow": [
                "Triage assessment",
                "Clinical examination", 
                "Imaging if indicated",
                "Treatment plan",
                "Disposition (admit/discharge/refer)"
            ],
            "radiology_workflow": [
                "Clinical indication review",
                "Image acquisition",
                "Image interpretation",
                "Report dictation",
                "Report verification",
                "Communication of urgent findings"
            ],
            "ward_round_workflow": [
                "Patient review",
                "Examination findings",
                "Investigation results",
                "Treatment plan update",
                "Discharge planning"
            ]
        }
    
    def get_localization_stats(self) -> Dict[str, int]:
        """Get localization statistics"""
        return {
            "medical_terms": len(self.sa_medical_terms),
            "pronunciation_variations": len(self.sa_pronunciation_map),
            "medical_templates": len(self.sa_templates),
            "medical_aid_schemes": len(self.medical_aid_schemes)
        }

# Global SA localization manager instance
sa_localization_manager = SALocalizationManager()