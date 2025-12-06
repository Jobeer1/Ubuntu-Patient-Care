"""
Medication Safety & Critical Alert Intelligence System
Identify drug interactions, allergies, and life-threatening conditions
Prevent medication errors in disaster scenarios with fragmented data

Key Features:
- Comprehensive drug interaction database
- Allergy-drug conflict detection
- Critical condition alerts
- Urgency scoring for triage
- Works completely offline
"""

import os
import json
import logging
import sqlite3
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)

# =============================================
# Data Classes & Enums
# =============================================

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"      # Stop all medication, immediate intervention required
    HIGH = "high"              # Verify before administration
    MEDIUM = "medium"          # Consider alternative
    LOW = "low"                # Note for record

class InteractionType(Enum):
    """Type of drug-drug interaction"""
    CONTRAINDICATED = "contraindicated"  # Absolute contraindication
    MAJOR = "major"                      # Severe interaction risk
    MODERATE = "moderate"                # Moderate interaction risk
    MINOR = "minor"                      # Minor interaction

@dataclass
class DrugInteraction:
    """A potential interaction between two drugs"""
    drug_1: str
    drug_2: str
    interaction_type: str  # From InteractionType
    severity: str  # From AlertSeverity
    description: str
    management: str  # What to do
    confidence: float  # 0.0 - 1.0
    evidence_count: int

@dataclass
class MedicationAlert:
    """Alert about a medication issue"""
    alert_id: str
    alert_type: str  # 'interaction', 'allergy', 'contraindication', 'overdose', 'underdose'
    severity: str  # From AlertSeverity
    message: str
    details: Dict[str, Any]
    patient_id: Optional[int]
    medication_involved: List[str]
    requires_action: bool
    suggested_action: Optional[str]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class UrgencyScore:
    """Patient urgency assessment for triage"""
    patient_id: int
    urgency_level: int  # 1-5 (1=immediate, 5=minor)
    score: float  # 0.0 - 1.0
    critical_factors: List[str]
    stable_factors: List[str]
    reasoning: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

# =============================================
# Drug Interaction Database
# =============================================

class DrugInteractionDatabase:
    """Comprehensive drug-drug interaction database"""
    
    # Critical interactions that contraindicate use
    CONTRAINDICATED_PAIRS = {
        ('warfarin', 'aspirin'): {
            'description': 'Increased bleeding risk - major interaction',
            'management': 'Use alternative antiplatelet or reduce warfarin monitoring',
            'evidence_count': 500,
        },
        ('metformin', 'contrast_dye'): {
            'description': 'Risk of lactic acidosis',
            'management': 'Hold metformin 48h before and after contrast',
            'evidence_count': 200,
        },
        ('nsaid', 'ace_inhibitor'): {
            'description': 'Acute kidney injury risk',
            'management': 'Monitor renal function, consider alternative',
            'evidence_count': 150,
        },
        ('lithium', 'thiazide'): {
            'description': 'Increased lithium toxicity',
            'management': 'Monitor lithium levels closely',
            'evidence_count': 100,
        },
    }
    
    # Major interactions requiring verification
    MAJOR_INTERACTIONS = {
        ('warfarin', 'nsaid'): {
            'description': 'Increased bleeding risk',
            'management': 'Use lowest NSAID dose, monitor INR',
        },
        ('methotrexate', 'nsaid'): {
            'description': 'Reduced methotrexate clearance',
            'management': 'Monitor for MTX toxicity',
        },
        ('statins', 'macrolide_antibiotic'): {
            'description': 'Increased statin myopathy risk',
            'management': 'Consider alternative antibiotic',
        },
        ('beta_blocker', 'calcium_channel_blocker'): {
            'description': 'Bradycardia, AV block risk',
            'management': 'Use cautiously, monitor heart rate',
        },
    }
    
    # Moderate interactions
    MODERATE_INTERACTIONS = {
        ('ssri', 'tramadol'): {
            'description': 'Serotonin syndrome risk',
            'management': 'Use lower tramadol dose, monitor',
        },
        ('metformin', 'alcohol'): {
            'description': 'Increased lactic acidosis risk',
            'management': 'Counsel on alcohol use limits',
        },
    }
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.DrugInteractionDatabase")
    
    def check_interaction(self, drug1: str, drug2: str) -> Optional[DrugInteraction]:
        """Check for interaction between two drugs"""
        
        drug1_lower = drug1.lower().strip()
        drug2_lower = drug2.lower().strip()
        
        # Check contraindicated pairs (both directions)
        for (d1, d2), info in self.CONTRAINDICATED_PAIRS.items():
            if (drug1_lower.startswith(d1) or d1.startswith(drug1_lower)) and \
               (drug2_lower.startswith(d2) or d2.startswith(drug2_lower)):
                return DrugInteraction(
                    drug_1=drug1,
                    drug_2=drug2,
                    interaction_type=InteractionType.CONTRAINDICATED.value,
                    severity=AlertSeverity.CRITICAL.value,
                    description=info['description'],
                    management=info['management'],
                    confidence=0.95,
                    evidence_count=info['evidence_count']
                )
            elif (drug1_lower.startswith(d2) or d2.startswith(drug1_lower)) and \
                 (drug2_lower.startswith(d1) or d1.startswith(drug2_lower)):
                return DrugInteraction(
                    drug_1=drug1,
                    drug_2=drug2,
                    interaction_type=InteractionType.CONTRAINDICATED.value,
                    severity=AlertSeverity.CRITICAL.value,
                    description=info['description'],
                    management=info['management'],
                    confidence=0.95,
                    evidence_count=info['evidence_count']
                )
        
        # Check major interactions
        for (d1, d2), info in self.MAJOR_INTERACTIONS.items():
            if (drug1_lower.startswith(d1) or d1.startswith(drug1_lower)) and \
               (drug2_lower.startswith(d2) or d2.startswith(drug2_lower)):
                return DrugInteraction(
                    drug_1=drug1,
                    drug_2=drug2,
                    interaction_type=InteractionType.MAJOR.value,
                    severity=AlertSeverity.HIGH.value,
                    description=info['description'],
                    management=info['management'],
                    confidence=0.90,
                    evidence_count=50
                )
        
        # Check moderate interactions
        for (d1, d2), info in self.MODERATE_INTERACTIONS.items():
            if (drug1_lower.startswith(d1) or d1.startswith(drug1_lower)) and \
               (drug2_lower.startswith(d2) or d2.startswith(drug2_lower)):
                return DrugInteraction(
                    drug_1=drug1,
                    drug_2=drug2,
                    interaction_type=InteractionType.MODERATE.value,
                    severity=AlertSeverity.MEDIUM.value,
                    description=info['description'],
                    management=info['management'],
                    confidence=0.85,
                    evidence_count=20
                )
        
        return None

# =============================================
# Medication Safety Checker
# =============================================

class MedicationSafetyChecker:
    """Check medication safety for patient"""
    
    def __init__(self):
        self.interaction_db = DrugInteractionDatabase()
        self.logger = logging.getLogger(f"{__name__}.MedicationSafetyChecker")
    
    def check_patient_medications(self, medications: List[str], 
                                  allergies: List[str],
                                  conditions: List[str]) -> List[MedicationAlert]:
        """
        Check all medications for safety issues
        Returns list of alerts sorted by severity
        """
        alerts = []
        
        # Check drug-drug interactions
        for i in range(len(medications)):
            for j in range(i + 1, len(medications)):
                interaction = self.interaction_db.check_interaction(
                    medications[i],
                    medications[j]
                )
                
                if interaction:
                    alert = MedicationAlert(
                        alert_id=f"interaction_{i}_{j}",
                        alert_type='interaction',
                        severity=interaction.severity,
                        message=f"Drug-drug interaction: {interaction.description}",
                        details={
                            'drug_1': interaction.drug_1,
                            'drug_2': interaction.drug_2,
                            'management': interaction.management,
                            'interaction_type': interaction.interaction_type,
                        },
                        patient_id=None,
                        medication_involved=[medications[i], medications[j]],
                        requires_action=interaction.severity in [AlertSeverity.CRITICAL.value, AlertSeverity.HIGH.value],
                        suggested_action=interaction.management
                    )
                    alerts.append(alert)
        
        # Check drug-allergy conflicts
        for med in medications:
            for allergy in allergies:
                if self._check_allergy_conflict(med, allergy):
                    alert = MedicationAlert(
                        alert_id=f"allergy_{med}_{allergy}",
                        alert_type='allergy',
                        severity=AlertSeverity.CRITICAL.value,
                        message=f"CRITICAL: Patient is allergic to {allergy}, prescribed {med}",
                        details={
                            'medication': med,
                            'allergen': allergy,
                        },
                        patient_id=None,
                        medication_involved=[med],
                        requires_action=True,
                        suggested_action="DO NOT ADMINISTER. Choose alternative medication."
                    )
                    alerts.append(alert)
        
        # Check contraindications with conditions
        for med in medications:
            for condition in conditions:
                contraindication = self._check_contraindication(med, condition)
                if contraindication:
                    alert = MedicationAlert(
                        alert_id=f"contraind_{med}_{condition}",
                        alert_type='contraindication',
                        severity=AlertSeverity.HIGH.value,
                        message=f"Medication contraindicated in {condition}",
                        details={
                            'medication': med,
                            'condition': condition,
                            'reason': contraindication
                        },
                        patient_id=None,
                        medication_involved=[med],
                        requires_action=True,
                        suggested_action="Verify necessity or consider alternative"
                    )
                    alerts.append(alert)
        
        # Sort by severity
        severity_order = {
            AlertSeverity.CRITICAL.value: 0,
            AlertSeverity.HIGH.value: 1,
            AlertSeverity.MEDIUM.value: 2,
            AlertSeverity.LOW.value: 3,
        }
        
        alerts.sort(key=lambda a: severity_order.get(a.severity, 99))
        
        return alerts
    
    def _check_allergy_conflict(self, medication: str, allergen: str) -> bool:
        """Check if medication conflicts with known allergy"""
        med_lower = medication.lower()
        allergen_lower = allergen.lower()
        
        # Direct matches
        if med_lower == allergen_lower:
            return True
        
        # Partial matches (e.g., "penicillin" and "amoxicillin")
        penicillins = ['penicillin', 'amoxicillin', 'ampicillin', 'piperacillin']
        cephalosporins = ['cephalexin', 'ceftriaxone', 'cefazolin']
        
        med_is_penicillin = any(p in med_lower for p in penicillins)
        allergen_is_penicillin = any(p in allergen_lower for p in penicillins)
        
        if med_is_penicillin and allergen_is_penicillin:
            return True
        
        # Cross-reactivity penicillins and cephalosporins (1-3%)
        med_is_cephalosporin = any(c in med_lower for c in cephalosporins)
        if med_is_cephalosporin and allergen_is_penicillin:
            return True  # Assume cross-reactivity for safety
        
        return False
    
    def _check_contraindication(self, medication: str, condition: str) -> Optional[str]:
        """Check if medication is contraindicated in condition"""
        
        med_lower = medication.lower()
        condition_lower = condition.lower()
        
        contraindications = {
            ('nsaid', 'kidney disease'): 'NSAIDs can worsen renal function',
            ('metformin', 'kidney disease'): 'Metformin can cause lactic acidosis with renal impairment',
            ('ace_inhibitor', 'pregnancy'): 'ACE inhibitors teratogenic in pregnancy',
            ('warfarin', 'bleeding'): 'Anticoagulants contraindicated with active bleeding',
        }
        
        for (med_pattern, condition_pattern), reason in contraindications.items():
            if med_pattern in med_lower and condition_pattern in condition_lower:
                return reason
        
        return None

# =============================================
# Urgency Scoring & Triage
# =============================================

class UrgencyScoringEngine:
    """Score patient urgency for disaster triage"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.UrgencyScoringEngine")
    
    def calculate_urgency(self, patient_data: Dict[str, Any]) -> UrgencyScore:
        """
        Calculate urgency score for patient triage
        Returns 1-5 (1=immediate, 5=minor)
        
        Factors:
        - Critical conditions (immediate)
        - Vital signs (respiratory distress, hypotension)
        - Injuries (trauma score)
        - Age (elderly/children higher priority)
        - Allergies (can worsen if not managed)
        """
        
        score = 0.0
        critical_factors = []
        stable_factors = []
        
        # Critical conditions
        critical_conditions = ['myocardial infarction', 'stroke', 'sepsis', 'shock', 
                             'respiratory distress', 'bleeding', 'anaphylaxis']
        
        conditions = patient_data.get('conditions', [])
        for cond in conditions:
            cond_lower = cond.lower() if isinstance(cond, str) else str(cond).lower()
            if any(cc in cond_lower for cc in critical_conditions):
                score += 5.0
                critical_factors.append(f"Critical condition: {cond}")
        
        # Vital signs
        vitals = patient_data.get('vital_signs', {})
        
        respiratory_rate = vitals.get('respiratory_rate')
        if respiratory_rate and respiratory_rate > 30:
            score += 3.0
            critical_factors.append(f"Respiratory distress (RR: {respiratory_rate})")
        
        heart_rate = vitals.get('heart_rate')
        if heart_rate and (heart_rate > 120 or heart_rate < 40):
            score += 2.0
            critical_factors.append(f"Abnormal heart rate ({heart_rate})")
        
        systolic_bp = vitals.get('systolic_bp')
        if systolic_bp and systolic_bp < 90:
            score += 4.0
            critical_factors.append(f"Hypotension ({systolic_bp} mmHg)")
        elif systolic_bp and systolic_bp > 180:
            score += 1.0
            critical_factors.append(f"Hypertension ({systolic_bp} mmHg)")
        
        oxygen = vitals.get('oxygen_saturation')
        if oxygen and oxygen < 90:
            score += 4.0
            critical_factors.append(f"Low O2 saturation ({oxygen}%)")
        
        # Injuries
        injuries = patient_data.get('injuries', [])
        trauma_score = 0
        for injury in injuries:
            injury_lower = str(injury).lower()
            if 'head' in injury_lower or 'chest' in injury_lower or 'abdominal' in injury_lower:
                trauma_score += 3
            else:
                trauma_score += 1
        
        if trauma_score > 0:
            score += min(3.0, trauma_score / 2)
            critical_factors.append(f"Significant injuries ({len(injuries)})")
        
        # Age
        age = patient_data.get('age')
        if age:
            if age < 5 or age > 65:
                score += 1.0
                critical_factors.append("Vulnerable age group")
        
        # Allergies to critical drugs
        allergies = patient_data.get('allergies', [])
        medications = patient_data.get('medications', [])
        
        for allergy in allergies:
            allergy_lower = str(allergy).lower()
            if any(med_type in allergy_lower for med_type in ['penicillin', 'sulfa', 'contrast']):
                for med in medications:
                    med_lower = str(med).lower()
                    if any(p in med_lower for p in ['penicillin', 'sulfa', 'contrast']):
                        score += 2.0
                        critical_factors.append("Allergy-medication conflict")
                        break
        
        # Normalize to 1-5 scale
        # 0-2 = 5 (minor)
        # 2-5 = 4 (moderate)
        # 5-8 = 3 (urgent)
        # 8-12 = 2 (very urgent)
        # 12+ = 1 (immediate)
        
        if score >= 12:
            urgency_level = 1
        elif score >= 8:
            urgency_level = 2
        elif score >= 5:
            urgency_level = 3
        elif score >= 2:
            urgency_level = 4
        else:
            urgency_level = 5
            stable_factors.append("Stable vitals")
        
        normalized_score = 1.0 - min(1.0, score / 20.0)  # 0.0 - 1.0
        
        reasoning = f"Urgency {urgency_level}: "
        if critical_factors:
            reasoning += "; ".join(critical_factors[:2])
        elif stable_factors:
            reasoning += "; ".join(stable_factors)
        else:
            reasoning += "Routine admission"
        
        return UrgencyScore(
            patient_id=patient_data.get('patient_id'),
            urgency_level=urgency_level,
            score=normalized_score,
            critical_factors=critical_factors,
            stable_factors=stable_factors,
            reasoning=reasoning
        )

