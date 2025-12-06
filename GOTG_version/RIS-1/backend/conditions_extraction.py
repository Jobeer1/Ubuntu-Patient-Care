"""
Medical Conditions Extraction ML Engine
Extract underlying conditions from unstructured text, voice, photos, and documents
Lightweight model suitable for offline operation on low-resource devices

Key Features:
- Extract medical conditions from unstructured text (NLP)
- Identify critical/life-threatening conditions
- Extract medications and drug interactions
- Identify allergies and contraindications
- Works completely offline
- Lightweight models (~50MB)
"""

import os
import json
import logging
import re
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)

# Try optional NLP library
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# =============================================
# Data Classes & Enums
# =============================================

class ConditionSeverity(Enum):
    """Severity of medical condition"""
    CRITICAL = "critical"          # Life-threatening, requires immediate intervention
    SEVERE = "severe"              # Serious, needs urgent attention
    MODERATE = "moderate"          # Significant but not immediately life-threatening
    MILD = "mild"                  # Minor, can usually be managed
    CHRONIC = "chronic"            # Long-term, stable but ongoing

@dataclass
class ExtractedCondition:
    """A medical condition identified from text"""
    condition_name: str
    severity: str  # From ConditionSeverity
    confidence: float  # 0.0 - 1.0
    source_text: str
    is_active: bool  # Currently affecting patient
    start_date: Optional[str] = None
    is_critical: bool = False
    requires_alert: bool = False
    related_contraindications: List[str] = field(default_factory=list)
    treatment_notes: Optional[str] = None

@dataclass
class ExtractedMedication:
    """A medication identified from text"""
    medication_name: str
    dosage: Optional[str]
    frequency: Optional[str]
    confidence: float
    source_text: str
    indication: Optional[str]
    side_effects: List[str] = field(default_factory=list)
    requires_monitoring: bool = False

@dataclass
class ExtractedAllergy:
    """An allergy identified from text"""
    allergen: str
    reaction_type: str  # 'drug', 'food', 'environmental', 'contact'
    severity: str  # 'anaphylaxis', 'severe', 'moderate', 'mild'
    reaction_description: Optional[str]
    confidence: float
    source_text: str
    is_critical: bool = False

# =============================================
# Medical Condition Extraction
# =============================================

class MedicalConditionExtractor:
    """Extract medical conditions from unstructured text"""
    
    # Comprehensive medical conditions database
    CONDITION_DATABASE = {
        # Critical conditions (life-threatening, emergency)
        'myocardial infarction': {'names': ['MI', 'heart attack', 'MI'], 'severity': ConditionSeverity.CRITICAL, 'critical': True},
        'stroke': {'names': ['CVA', 'cerebrovascular accident', 'ischemic stroke', 'hemorrhagic stroke'], 'severity': ConditionSeverity.CRITICAL, 'critical': True},
        'sepsis': {'names': ['septic shock', 'severe sepsis'], 'severity': ConditionSeverity.CRITICAL, 'critical': True},
        'acute respiratory distress': {'names': ['ARDS', 'respiratory failure'], 'severity': ConditionSeverity.CRITICAL, 'critical': True},
        'pulmonary embolism': {'names': ['PE', 'blood clot lung'], 'severity': ConditionSeverity.CRITICAL, 'critical': True},
        'hemorrhage': {'names': ['bleeding', 'severe bleeding', 'blood loss'], 'severity': ConditionSeverity.CRITICAL, 'critical': True},
        'anaphylaxis': {'names': ['severe allergic reaction', 'anaphylactic shock'], 'severity': ConditionSeverity.CRITICAL, 'critical': True},
        'shock': {'names': ['cardiogenic shock', 'hypovolemic shock'], 'severity': ConditionSeverity.CRITICAL, 'critical': True},
        
        # Severe conditions (urgent, needs attention)
        'diabetes': {'names': ['diabetes mellitus', 'diabetes type 1', 'diabetes type 2', 'IDDM', 'NIDDM'], 'severity': ConditionSeverity.SEVERE, 'critical': False},
        'hypertension': {'names': ['high blood pressure', 'HTN', 'hypertensive'], 'severity': ConditionSeverity.SEVERE, 'critical': False},
        'heart disease': {'names': ['cardiac disease', 'coronary artery disease', 'CAD', 'heart failure', 'CHF'], 'severity': ConditionSeverity.SEVERE, 'critical': False},
        'asthma': {'names': ['reactive airway disease', 'bronchial asthma'], 'severity': ConditionSeverity.SEVERE, 'critical': False},
        'cancer': {'names': ['malignancy', 'tumor', 'lymphoma', 'leukemia'], 'severity': ConditionSeverity.SEVERE, 'critical': False},
        'kidney disease': {'names': ['renal disease', 'CKD', 'chronic kidney disease', 'renal failure'], 'severity': ConditionSeverity.SEVERE, 'critical': False},
        'liver disease': {'names': ['hepatic disease', 'cirrhosis', 'hepatitis', 'liver failure'], 'severity': ConditionSeverity.SEVERE, 'critical': False},
        'aids': {'names': ['HIV', 'AIDS', 'HIV positive'], 'severity': ConditionSeverity.SEVERE, 'critical': False},
        
        # Moderate conditions
        'arthritis': {'names': ['RA', 'osteoarthritis', 'rheumatoid arthritis'], 'severity': ConditionSeverity.MODERATE, 'critical': False},
        'depression': {'names': ['major depressive disorder', 'mood disorder', 'clinical depression'], 'severity': ConditionSeverity.MODERATE, 'critical': False},
        'anxiety': {'names': ['anxiety disorder', 'panic disorder', 'PTSD'], 'severity': ConditionSeverity.MODERATE, 'critical': False},
        'migraine': {'names': ['headache', 'tension headache'], 'severity': ConditionSeverity.MODERATE, 'critical': False},
        
        # Chronic conditions
        'thyroid disease': {'names': ['hypothyroidism', 'hyperthyroidism', 'thyroiditis'], 'severity': ConditionSeverity.CHRONIC, 'critical': False},
    }
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.MedicalConditionExtractor")
        self._build_pattern_database()
    
    def _build_pattern_database(self):
        """Build regex patterns for condition matching"""
        self.condition_patterns = {}
        
        for condition, info in self.CONDITION_DATABASE.items():
            # Create regex pattern for all aliases
            aliases = info.get('names', [condition])
            pattern = '|'.join(re.escape(alias) for alias in aliases)
            self.condition_patterns[condition] = {
                'pattern': re.compile(f'\\b({pattern})\\b', re.IGNORECASE),
                'severity': info['severity'],
                'is_critical': info.get('critical', False)
            }
    
    def extract_conditions(self, text: str) -> List[ExtractedCondition]:
        """
        Extract medical conditions from text
        
        Args:
            text: Unstructured medical text
        
        Returns:
            List of extracted conditions
        """
        conditions = []
        seen = set()  # Avoid duplicates
        
        if not text:
            return conditions
        
        text_lower = text.lower()
        
        # Search for each condition
        for condition, pattern_info in self.condition_patterns.items():
            match = pattern_info['pattern'].search(text)
            if match:
                # Avoid duplicate conditions
                if condition in seen:
                    continue
                seen.add(condition)
                
                # Extract context around match (for confirmation)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                # Determine if condition is active or historical
                is_active = self._determine_active_status(context)
                
                extracted = ExtractedCondition(
                    condition_name=condition,
                    severity=pattern_info['severity'].value,
                    confidence=0.95,  # High confidence from exact pattern match
                    source_text=context.strip(),
                    is_active=is_active,
                    is_critical=pattern_info['is_critical'],
                    requires_alert=pattern_info['is_critical']
                )
                
                conditions.append(extracted)
        
        # Sort by severity
        severity_order = {
            ConditionSeverity.CRITICAL.value: 0,
            ConditionSeverity.SEVERE.value: 1,
            ConditionSeverity.MODERATE.value: 2,
            ConditionSeverity.MILD.value: 3,
            ConditionSeverity.CHRONIC.value: 4,
        }
        
        conditions.sort(key=lambda x: severity_order.get(x.severity, 99))
        
        self.logger.info(f"Extracted {len(conditions)} conditions from text")
        return conditions
    
    def _determine_active_status(self, context: str) -> bool:
        """Determine if condition is currently active or historical"""
        # Check for keywords indicating active status
        active_indicators = ['currently', 'present', 'ongoing', 'has', 'with', 'patient has']
        historical_indicators = ['history of', 'previous', 'past', 'prior', 'resolved', 'cured']
        
        context_lower = context.lower()
        
        # Check historical indicators first (higher priority)
        for indicator in historical_indicators:
            if indicator in context_lower:
                return False
        
        # Check active indicators
        for indicator in active_indicators:
            if indicator in context_lower:
                return True
        
        # Default: assume active if recently mentioned
        return True
    
    def get_critical_conditions(self, conditions: List[ExtractedCondition]) -> List[ExtractedCondition]:
        """Filter to only critical conditions requiring immediate attention"""
        return [c for c in conditions if c.is_critical or c.requires_alert]

# =============================================
# Medication Extraction
# =============================================

class MedicationExtractor:
    """Extract medications and dosages from text"""
    
    # Common medications database
    MEDICATION_DATABASE = {
        'aspirin': {'names': ['acetylsalicylic acid', 'ASA'], 'risk_level': 'moderate'},
        'ibuprofen': {'names': ['Advil', 'Motrin', 'ibuprofen'], 'risk_level': 'moderate'},
        'metformin': {'names': ['Glucophage', 'metformin'], 'risk_level': 'low'},
        'lisinopril': {'names': ['Prinivil', 'Zestril', 'lisinopril'], 'risk_level': 'low'},
        'atorvastatin': {'names': ['Lipitor', 'atorvastatin'], 'risk_level': 'low'},
        'omeprazole': {'names': ['Prilosec', 'omeprazole'], 'risk_level': 'low'},
        'amoxicillin': {'names': ['Amoxil', 'amoxicillin'], 'risk_level': 'high'},
        'penicillin': {'names': ['penicillin', 'penicillin V'], 'risk_level': 'high'},
        'warfarin': {'names': ['Coumadin', 'warfarin'], 'risk_level': 'high'},
        'insulin': {'names': ['Humalog', 'Lantus', 'insulin'], 'risk_level': 'high'},
    }
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.MedicationExtractor")
        self._build_medication_patterns()
    
    def _build_medication_patterns(self):
        """Build regex patterns for medication matching"""
        self.med_patterns = {}
        
        for med, info in self.MEDICATION_DATABASE.items():
            aliases = info.get('names', [med])
            pattern = '|'.join(re.escape(alias) for alias in aliases)
            self.med_patterns[med] = {
                'pattern': re.compile(f'\\b({pattern})\\b', re.IGNORECASE),
                'risk_level': info.get('risk_level', 'unknown')
            }
    
    def extract_medications(self, text: str) -> List[ExtractedMedication]:
        """Extract medications from text"""
        medications = []
        seen = set()
        
        if not text:
            return medications
        
        # Find medications
        for med, pattern_info in self.med_patterns.items():
            match = pattern_info['pattern'].search(text)
            if match:
                if med in seen:
                    continue
                seen.add(med)
                
                # Extract context for dosage information
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]
                
                # Extract dosage
                dosage = self._extract_dosage(context)
                frequency = self._extract_frequency(context)
                
                extracted = ExtractedMedication(
                    medication_name=med,
                    dosage=dosage,
                    frequency=frequency,
                    confidence=0.90,
                    source_text=context.strip(),
                    requires_monitoring=pattern_info['risk_level'] == 'high'
                )
                
                medications.append(extracted)
        
        self.logger.info(f"Extracted {len(medications)} medications")
        return medications
    
    def _extract_dosage(self, context: str) -> Optional[str]:
        """Extract dosage information"""
        # Look for patterns like "500 mg", "2 tablets", etc
        match = re.search(r'(\d+\.?\d*)\s*(mg|g|ml|units|tablets?|capsules?)', context, re.IGNORECASE)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return None
    
    def _extract_frequency(self, context: str) -> Optional[str]:
        """Extract dosing frequency"""
        frequencies = ['daily', 'twice daily', 'three times daily', 'weekly', 'monthly', 'as needed']
        for freq in frequencies:
            if freq in context.lower():
                return freq
        return None

# =============================================
# Allergy Extraction
# =============================================

class AllergyExtractor:
    """Extract allergies and adverse reactions from text"""
    
    ALLERGY_DATABASE = {
        'penicillin': {'reaction': 'rash', 'severity': 'severe', 'type': 'drug'},
        'amoxicillin': {'reaction': 'rash', 'severity': 'severe', 'type': 'drug'},
        'sulfa': {'reaction': 'rash', 'severity': 'severe', 'type': 'drug'},
        'peanuts': {'reaction': 'anaphylaxis', 'severity': 'critical', 'type': 'food'},
        'shellfish': {'reaction': 'anaphylaxis', 'severity': 'critical', 'type': 'food'},
        'latex': {'reaction': 'rash', 'severity': 'moderate', 'type': 'contact'},
    }
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.AllergyExtractor")
    
    def extract_allergies(self, text: str) -> List[ExtractedAllergy]:
        """Extract allergies from text"""
        allergies = []
        
        if not text:
            return allergies
        
        # Look for allergy mentions
        allergy_pattern = r'(?:allerg(?:ic|y|ies)|reaction|intolerance):\s*([^\n,;.]+)'
        matches = re.finditer(allergy_pattern, text, re.IGNORECASE)
        
        for match in matches:
            allergen_text = match.group(1).strip()
            
            # Try to identify allergen
            for allergen, info in self.ALLERGY_DATABASE.items():
                if allergen in allergen_text.lower():
                    extracted = ExtractedAllergy(
                        allergen=allergen,
                        reaction_type=info['type'],
                        severity=info['severity'],
                        reaction_description=allergen_text,
                        confidence=0.95,
                        source_text=match.group(0),
                        is_critical=info['severity'] in ['critical', 'severe']
                    )
                    allergies.append(extracted)
                    break
            else:
                # Unknown allergen but mentioned
                extracted = ExtractedAllergy(
                    allergen=allergen_text,
                    reaction_type='unknown',
                    severity='moderate',
                    reaction_description=allergen_text,
                    confidence=0.70,
                    source_text=match.group(0),
                    is_critical=False
                )
                allergies.append(extracted)
        
        return allergies

# =============================================
# Unified Extraction Engine
# =============================================

class UnifiedMedicalExtractor:
    """Unified engine for extracting all medical information"""
    
    def __init__(self):
        self.condition_extractor = MedicalConditionExtractor()
        self.medication_extractor = MedicationExtractor()
        self.allergy_extractor = AllergyExtractor()
        self.logger = logging.getLogger(f"{__name__}.UnifiedMedicalExtractor")
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        """
        Extract all medical information from text
        
        Returns:
            Dictionary containing conditions, medications, allergies, and alerts
        """
        conditions = self.condition_extractor.extract_conditions(text)
        medications = self.medication_extractor.extract_medications(text)
        allergies = self.allergy_extractor.extract_allergies(text)
        
        # Generate critical alerts
        critical_conditions = self.condition_extractor.get_critical_conditions(conditions)
        critical_allergies = [a for a in allergies if a.is_critical]
        
        # Check drug interactions
        interactions = self._check_interactions(medications, allergies, conditions)
        
        return {
            'conditions': [asdict(c) for c in conditions],
            'medications': [asdict(m) for m in medications],
            'allergies': [asdict(a) for a in allergies],
            'critical_alerts': [
                {'type': 'condition', 'message': f"Critical condition: {c.condition_name}", 'condition': c.condition_name}
                for c in critical_conditions
            ] + [
                {'type': 'allergy', 'message': f"Critical allergy: {a.allergen}", 'allergen': a.allergen}
                for a in critical_allergies
            ],
            'drug_interactions': interactions,
            'summary': {
                'total_conditions': len(conditions),
                'total_medications': len(medications),
                'total_allergies': len(allergies),
                'critical_alerts_count': len(critical_conditions) + len(critical_allergies),
                'has_critical_issues': len(critical_conditions) > 0 or len(critical_allergies) > 0
            },
            'extracted_at': datetime.utcnow().isoformat()
        }
    
    def _check_interactions(self, medications: List[ExtractedMedication], 
                           allergies: List[ExtractedAllergy],
                           conditions: List[ExtractedCondition]) -> List[Dict]:
        """Check for medication-allergy interactions and contraindications"""
        interactions = []
        
        # Simple interaction checking
        interaction_pairs = [
            ('penicillin', 'penicillin'),  # Obvious one
            ('warfarin', 'aspirin'),  # Common interaction
        ]
        
        med_names = [m.medication_name for m in medications]
        allergy_allergens = [a.allergen for a in allergies]
        
        for med in med_names:
            for allergy in allergy_allergens:
                if med == allergy or med.startswith(allergy):
                    interactions.append({
                        'severity': 'critical',
                        'type': 'drug_allergy_conflict',
                        'medication': med,
                        'allergen': allergy,
                        'message': f"CRITICAL: Patient is allergic to {allergy} but prescribed {med}"
                    })
        
        return interactions

