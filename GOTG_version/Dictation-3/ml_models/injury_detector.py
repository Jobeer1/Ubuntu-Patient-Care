#!/usr/bin/env python3
"""
Injury Detection & Assessment Module - GOTG Dictation-3

Lightweight ML-powered injury analysis from voice dictations.
Uses pattern matching and lightweight models for <1 second response time.
Designed for emergency medicine use case where every second counts.
"""

import json
import re
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

# ============================================================================
# MEDICAL TERMINOLOGY & INJURY PATTERNS
# ============================================================================

# Injury severity levels
SEVERITY_LEVELS = {
    'critical': 4,      # Life-threatening (immediate intervention)
    'severe': 3,        # Major injury (urgent)
    'moderate': 2,      # Moderate (needs attention)
    'minor': 1,         # Minor (can wait)
    'none': 0          # No injury detected
}

# Injury patterns (text → medical classification)
INJURY_PATTERNS = {
    # HEAD & NEUROLOGICAL
    'head_trauma': {
        'keywords': ['head', 'skull', 'brain', 'concussion', 'cerebral', 'intracranial', 'TBI'],
        'severity': 'severe',
        'icd10': 'S06',
        'category': 'neurological'
    },
    'facial_injury': {
        'keywords': ['face', 'facial', 'cheek', 'jaw', 'teeth', 'mandible', 'maxilla', 'orbit'],
        'severity': 'moderate',
        'icd10': 'S01',
        'category': 'facial'
    },
    'eye_injury': {
        'keywords': ['eye', 'ocular', 'vision', 'blindness', 'cornea', 'retina', 'globe'],
        'severity': 'severe',
        'icd10': 'S05',
        'category': 'ophthalmic'
    },
    
    # NECK & SPINAL
    'neck_injury': {
        'keywords': ['neck', 'cervical', 'c-spine', 'larynx', 'trachea', 'esophagus'],
        'severity': 'critical',
        'icd10': 'S10-S19',
        'category': 'spinal'
    },
    'spinal_injury': {
        'keywords': ['spine', 'spinal', 'vertebra', 'paraplegia', 'quadriplegia', 'paralysis'],
        'severity': 'critical',
        'icd10': 'S14',
        'category': 'spinal'
    },
    
    # CHEST & THORACIC
    'chest_trauma': {
        'keywords': ['chest', 'thoracic', 'rib', 'pneumothorax', 'hemothorax', 'flail'],
        'severity': 'severe',
        'icd10': 'S20-S27',
        'category': 'thoracic'
    },
    'cardiac_injury': {
        'keywords': ['cardiac', 'heart', 'pericardial', 'tamponade', 'myocardial', 'coronary'],
        'severity': 'critical',
        'icd10': 'S26',
        'category': 'cardiac'
    },
    'pulmonary_injury': {
        'keywords': ['lung', 'pulmonary', 'respiratory', 'breathing', 'asphyxia', 'suffocation'],
        'severity': 'critical',
        'icd10': 'S27',
        'category': 'pulmonary'
    },
    
    # ABDOMINAL & PELVIC
    'abdominal_trauma': {
        'keywords': ['abdomen', 'abdominal', 'belly', 'peritoneal', 'evisceration', 'laceration'],
        'severity': 'severe',
        'icd10': 'S30-S39',
        'category': 'abdominal'
    },
    'intra_abdominal_bleeding': {
        'keywords': ['bleeding', 'hemorrhage', 'bleed', 'hemorrhagic', 'hemodynamic'],
        'severity': 'critical',
        'icd10': 'S36-S37',
        'category': 'vascular'
    },
    'pelvic_injury': {
        'keywords': ['pelvis', 'pelvic', 'hip', 'fracture', 'stable', 'unstable'],
        'severity': 'severe',
        'icd10': 'S32',
        'category': 'pelvic'
    },
    
    # EXTREMITY
    'limb_injury': {
        'keywords': ['limb', 'arm', 'leg', 'hand', 'foot', 'digit', 'amputation'],
        'severity': 'moderate',
        'icd10': 'S40-S89',
        'category': 'extremity'
    },
    'fracture': {
        'keywords': ['fracture', 'broken', 'break', 'comminuted', 'compound', 'pathologic'],
        'severity': 'moderate',
        'icd10': 'S72',
        'category': 'fracture'
    },
    'soft_tissue_injury': {
        'keywords': ['laceration', 'wound', 'contusion', 'bruise', 'strain', 'sprain', 'tear'],
        'severity': 'minor',
        'icd10': 'S80-S89',
        'category': 'soft_tissue'
    },
    
    # BURNS
    'burn_injury': {
        'keywords': ['burn', 'thermal', 'scald', 'charred', 'degree', 'blistering'],
        'severity': 'severe',
        'icd10': 'T20-T32',
        'category': 'thermal'
    },
    
    # CHEMICAL/TOXIC
    'chemical_exposure': {
        'keywords': ['chemical', 'poison', 'toxic', 'caustic', 'corrosive', 'acid', 'alkali'],
        'severity': 'severe',
        'icd10': 'T54-T65',
        'category': 'chemical'
    },
    
    # SHOCK & HEMORRHAGE
    'hemorrhagic_shock': {
        'keywords': ['shock', 'hypotensive', 'pale', 'cool', 'clammy', 'unresponsive', 'losing consciousness'],
        'severity': 'critical',
        'icd10': 'R57',
        'category': 'shock'
    }
}

# Modifying factors that increase severity
SEVERITY_MODIFIERS = {
    'critical_indicators': {
        'keywords': ['unconscious', 'unresponsive', 'no pulse', 'no breathing', 'dead', 'not breathing'],
        'multiplier': 1.5
    },
    'active_bleeding': {
        'keywords': ['bleeding', 'hemorrhage', 'hemorrhaging', 'spurting', 'gushing'],
        'multiplier': 1.3
    },
    'airway_compromise': {
        'keywords': ['airway', 'choking', 'aspiration', 'stridor', 'wheezing', 'difficulty breathing'],
        'multiplier': 1.4
    },
    'neurological_deficit': {
        'keywords': ['paralysis', 'weakness', 'numb', 'loss of sensation', 'altered mental'],
        'multiplier': 1.3
    }
}

# ============================================================================
# INJURY DETECTOR CLASS
# ============================================================================

class InjuryDetector:
    """Lightweight injury detection from medical dictations"""
    
    def __init__(self):
        self.injury_patterns = INJURY_PATTERNS
        self.severity_modifiers = SEVERITY_MODIFIERS
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for pattern matching"""
        # Convert to lowercase
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[.,;:!?]', '', text)
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _match_keywords(self, text: str, keywords: List[str]) -> int:
        """Count keyword matches in text (word boundaries)"""
        matches = 0
        normalized = self._normalize_text(text)
        
        for keyword in keywords:
            keyword_norm = keyword.lower()
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(keyword_norm) + r'\b'
            matches += len(re.findall(pattern, normalized))
        
        return matches
    
    def _detect_injuries(self, text: str) -> List[Dict]:
        """Detect all injuries mentioned in text"""
        injuries = []
        
        for injury_name, pattern_info in self.injury_patterns.items():
            match_count = self._match_keywords(text, pattern_info['keywords'])
            
            if match_count > 0:
                injuries.append({
                    'injury_type': injury_name,
                    'category': pattern_info['category'],
                    'match_count': match_count,
                    'base_severity': pattern_info['severity'],
                    'icd10_code': pattern_info['icd10'],
                    'confidence': min(0.95, 0.60 + (match_count * 0.10))  # Increase confidence with more matches
                })
        
        return injuries
    
    def _calculate_severity_score(self, injuries: List[Dict], text: str) -> Tuple[str, float]:
        """Calculate overall severity based on injuries and modifiers"""
        if not injuries:
            return 'none', 0.0
        
        # Start with highest injury severity
        max_severity = max([SEVERITY_LEVELS[inj['base_severity']] for inj in injuries])
        severity_score = float(max_severity)
        
        # Apply modifiers
        for modifier_name, modifier_info in self.severity_modifiers.items():
            if self._match_keywords(text, modifier_info['keywords']) > 0:
                severity_score *= modifier_info['multiplier']
        
        # Clamp between 0 and 4
        severity_score = min(4.0, max(0.0, severity_score))
        
        # Map back to level
        if severity_score >= 3.5:
            return 'critical', severity_score
        elif severity_score >= 2.5:
            return 'severe', severity_score
        elif severity_score >= 1.5:
            return 'moderate', severity_score
        elif severity_score >= 0.5:
            return 'minor', severity_score
        else:
            return 'none', 0.0
    
    def _extract_entities(self, text: str) -> Dict:
        """Extract specific medical entities from text"""
        entities = {
            'patient_condition': [],
            'vital_signs': {},
            'observations': [],
            'recommendations': []
        }
        
        # Look for vital signs patterns
        vital_patterns = {
            'heart_rate': r'(?:heart rate|HR|pulse|HR:?)\s*(\d+)',
            'blood_pressure': r'(?:BP|blood pressure)\s*(\d+[/\-]\d+)',
            'respiratory_rate': r'(?:RR|respiratory rate)\s*(\d+)',
            'oxygen_saturation': r'(?:O2|SpO2|oxygen sat)\s*(\d+%?)',
            'temperature': r'(?:temp|temperature)\s*([\d.]+)'
        }
        
        for vital, pattern in vital_patterns.items():
            match = re.search(pattern, text.lower())
            if match:
                entities['vital_signs'][vital] = match.group(1)
        
        # Look for clinical observations
        observation_keywords = [
            'conscious', 'alert', 'confused', 'drowsy', 'responsive',
            'pale', 'flushed', 'cyanotic', 'diaphoretic', 'trembling'
        ]
        
        for obs in observation_keywords:
            if obs in text.lower():
                entities['observations'].append(obs)
        
        return entities
    
    def analyze_transcription(self, transcription: str, language: str = 'en') -> Dict:
        """Main analysis function - returns structured injury assessment"""
        
        start_time = datetime.utcnow()
        
        # Detect injuries
        injuries = self._detect_injuries(transcription)
        
        # Calculate severity
        overall_severity, severity_score = self._calculate_severity_score(injuries, transcription)
        
        # Extract entities
        entities = self._extract_entities(transcription)
        
        # Prioritize injuries by severity
        injuries_sorted = sorted(
            injuries,
            key=lambda x: (SEVERITY_LEVELS[x['base_severity']], x['match_count']),
            reverse=True
        )
        
        # Build assessment
        assessment = {
            'timestamp': start_time.isoformat(),
            'transcription_length': len(transcription),
            'overall_severity': overall_severity,
            'severity_score': round(severity_score, 2),
            'primary_injury': injuries_sorted[0]['injury_type'] if injuries_sorted else None,
            'primary_category': injuries_sorted[0]['category'] if injuries_sorted else None,
            'all_injuries': [
                {
                    'type': inj['injury_type'],
                    'category': inj['category'],
                    'severity': inj['base_severity'],
                    'confidence': round(inj['confidence'], 2),
                    'icd10': inj['icd10_code'],
                    'mentions': inj['match_count']
                }
                for inj in injuries_sorted
            ],
            'vital_signs': entities['vital_signs'],
            'observations': entities['observations'],
            'has_critical_indicators': overall_severity == 'critical',
            'processing_time_ms': round((datetime.utcnow() - start_time).total_seconds() * 1000, 1)
        }
        
        # Generate human-friendly summary
        assessment['human_summary'] = self._generate_summary(assessment)
        
        return assessment
    
    def _generate_summary(self, assessment: Dict) -> str:
        """Generate human-friendly summary for emergency staff"""
        
        severity_icons = {
            'critical': '🚨 CRITICAL',
            'severe': '⚠️ SEVERE',
            'moderate': '⚠️ MODERATE',
            'minor': 'ℹ️ MINOR',
            'none': '✅ No injuries detected'
        }
        
        if not assessment['all_injuries']:
            return severity_icons['none']
        
        severity = assessment['overall_severity']
        primary = assessment['primary_injury']
        injuries_count = len(assessment['all_injuries'])
        
        icon = severity_icons.get(severity, '')
        
        if injuries_count == 1:
            return f"{icon} - {primary.replace('_', ' ').title()}"
        else:
            top_3 = ', '.join([
                inj['type'].replace('_', ' ').title() 
                for inj in assessment['all_injuries'][:3]
            ])
            return f"{icon} - Multiple injuries: {top_3}{'...' if injuries_count > 3 else ''}"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def analyze_injury_report(transcription: str) -> Dict:
    """Convenience function to analyze an injury report"""
    detector = InjuryDetector()
    return detector.analyze_transcription(transcription)


# ============================================================================
# TESTING/DEMO
# ============================================================================

if __name__ == '__main__':
    # Test cases
    test_cases = [
        "Patient presenting with severe head trauma, loss of consciousness, and suspected intracranial hemorrhage. Pupils fixed and dilated.",
        "MVA victim with compound fracture of left femur, active bleeding from wound, patient in hemorrhagic shock, BP 80/50, HR 130.",
        "Thermal burn injury, second and third degree burns covering 30% of body surface area, patient alert and in moderate pain.",
        "Laceration to left forearm with minor bleeding, patient stable, wound cleaned.",
        "No significant injuries noted. Patient alert and oriented, vital signs stable."
    ]
    
    detector = InjuryDetector()
    
    print("=" * 80)
    print("GOTG INJURY DETECTION SYSTEM - TEST RUN")
    print("=" * 80)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[TEST CASE {i}]")
        print(f"Input: {case[:60]}...")
        
        result = detector.analyze_transcription(case)
        
        print(f"Severity: {result['overall_severity'].upper()} ({result['severity_score']}/4.0)")
        print(f"Primary: {result['primary_injury']}")
        print(f"Summary: {result['human_summary']}")
        print(f"Processing: {result['processing_time_ms']}ms")
        
        if result['all_injuries']:
            print(f"Injuries detected: {len(result['all_injuries'])}")
            for inj in result['all_injuries'][:2]:
                print(f"  - {inj['type']}: {inj['severity'].upper()} (confidence: {inj['confidence']})")
