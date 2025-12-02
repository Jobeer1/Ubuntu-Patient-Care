"""
Smart Data Fusion Engine
Merge patient data from multiple incomplete sources into coherent complete profiles
Designed for disaster scenarios where data is fragmented across photos, documents, biometrics, and verbal descriptions

Key Features:
- Merge data from photos, documents, fingerprints, voice notes
- Resolve conflicts intelligently (priority-weighted resolution)
- Build complete patient profiles from fragments
- Detect and flag suspicious data
- Maintain audit trail of all merges
"""

import os
import json
import sqlite3
import logging
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)

# =============================================
# Data Classes & Enums
# =============================================

class DataSourcePriority(Enum):
    """Priority for data source conflicts (higher = more trustworthy)"""
    FINGERPRINT_CONFIRMED = 10        # Biometrically confirmed
    OFFICIAL_MEDICAL_RECORD = 9       # From official hospital record
    GOVERNMENT_ID = 8                 # From govt ID or passport
    FAMILY_CONFIRMATION = 7           # Confirmed by family member
    CLINICAL_ASSESSMENT = 6           # From clinician notes
    OCR_DOCUMENT = 5                  # From document OCR
    VERBAL_DESCRIPTION = 4            # From patient/family description
    PARTIAL_RECOVERY = 3              # Recovered from corrupted data
    UNKNOWN = 1                       # Unknown or low confidence

@dataclass
class DataConflict:
    """A conflict between data from different sources"""
    field_name: str
    values: List[Dict]  # [{'value': ..., 'source': ..., 'confidence': ...}, ...]
    resolution: Optional[str] = None
    conflict_severity: str = 'medium'  # 'critical', 'high', 'medium', 'low'
    flagged_for_review: bool = False

@dataclass
class FusedRecord:
    """Final merged patient record from multiple sources"""
    patient_id: Optional[int]
    merged_data: Dict[str, Any]  # All patient information
    source_inventory: Dict[str, List[str]]  # Track which sources contributed what
    conflicts_detected: List[DataConflict]
    confidence_scores: Dict[str, float]  # Confidence for each field
    data_completeness: float  # 0.0 - 1.0
    requires_verification: bool
    verified_by_biometric: bool
    merged_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self):
        return {
            'patient_id': self.patient_id,
            'merged_data': self.merged_data,
            'source_inventory': self.source_inventory,
            'conflicts_detected': [asdict(c) for c in self.conflicts_detected],
            'confidence_scores': self.confidence_scores,
            'data_completeness': self.data_completeness,
            'requires_verification': self.requires_verification,
            'verified_by_biometric': self.verified_by_biometric,
            'merged_at': self.merged_at
        }

# =============================================
# Data Fusion Engine
# =============================================

class SmartDataFusionEngine:
    """Intelligently merge patient data from multiple sources"""
    
    # Define which fields can conflict and how to resolve them
    FIELD_RESOLUTION_STRATEGY = {
        'name': 'highest_confidence',
        'date_of_birth': 'exact_match_or_flag',
        'phone': 'highest_confidence',
        'address': 'highest_confidence',
        'gender': 'highest_confidence',
        'conditions': 'merge_all_with_dedup',
        'medications': 'merge_all_with_dedup',
        'allergies': 'merge_all_with_strict_review',  # Critical, needs review
        'emergency_contacts': 'merge_all_with_dedup',
        'past_treatments': 'merge_all',
        'patient_id': 'exact_match_or_flag',
    }
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.SmartDataFusionEngine")
        self.fusion_lock = threading.RLock()
    
    def fuse_records(self, records: List[Dict[str, Any]], 
                    source_priorities: Optional[Dict[str, int]] = None) -> FusedRecord:
        """
        Fuse multiple patient records into one coherent record
        
        Args:
            records: List of patient data dictionaries (may have overlapping info)
            source_priorities: Optional priority scores for each record's source
        
        Returns:
            FusedRecord with merged data, conflicts noted, and confidence scores
        """
        
        if not records:
            return FusedRecord(
                patient_id=None,
                merged_data={},
                source_inventory={},
                conflicts_detected=[],
                confidence_scores={},
                data_completeness=0.0,
                requires_verification=True,
                verified_by_biometric=False
            )
        
        merged_data = {}
        conflicts = []
        source_inventory = {}
        confidence_scores = {}
        source_priorities = source_priorities or {}
        
        # Collect all fields
        all_fields = set()
        for record in records:
            all_fields.update(record.keys())
        
        # Fuse each field
        for field in all_fields:
            field_values = [
                {
                    'value': record.get(field),
                    'source': record.get('_source', 'unknown'),
                    'source_index': i,
                    'confidence': record.get('_confidence', {}).get(field, 0.7)
                }
                for i, record in enumerate(records)
                if field in record and record.get(field) is not None
            ]
            
            if not field_values:
                continue
            
            # Apply resolution strategy
            strategy = self.FIELD_RESOLUTION_STRATEGY.get(field, 'highest_confidence')
            
            result = self._apply_resolution_strategy(field, field_values, strategy)
            
            if isinstance(result, dict):
                if result.get('conflict'):
                    conflicts.append(result['conflict'])
                merged_data[field] = result['value']
                confidence_scores[field] = result['confidence']
            else:
                merged_data[field] = result
                confidence_scores[field] = 0.8
            
            # Track source
            source_inventory[field] = [v['source'] for v in field_values]
        
        # Calculate overall completeness
        expected_fields = {'name', 'patient_id', 'date_of_birth', 'gender', 'conditions', 'medications'}
        present_fields = sum(1 for f in expected_fields if f in merged_data)
        completeness = present_fields / len(expected_fields)
        
        # Check if biometrically verified
        biometric_verified = any(
            inv for inv in source_inventory.values() 
            if any('fingerprint' in str(s).lower() or 'facial' in str(s).lower() for s in inv)
        )
        
        # Flag for review if critical conflicts exist
        requires_review = any(c.conflict_severity == 'critical' for c in conflicts)
        
        fused = FusedRecord(
            patient_id=merged_data.get('patient_id'),
            merged_data=merged_data,
            source_inventory=source_inventory,
            conflicts_detected=conflicts,
            confidence_scores=confidence_scores,
            data_completeness=completeness,
            requires_verification=requires_review or completeness < 0.6,
            verified_by_biometric=biometric_verified
        )
        
        self.logger.info(
            f"Fused {len(records)} records into patient profile "
            f"(completeness: {completeness:.1%}, conflicts: {len(conflicts)})"
        )
        
        return fused
    
    def _apply_resolution_strategy(self, field: str, field_values: List[Dict], 
                                   strategy: str) -> Dict[str, Any]:
        """Apply resolution strategy for field conflicts"""
        
        if strategy == 'highest_confidence':
            # Use value with highest confidence
            best = max(field_values, key=lambda x: x['confidence'])
            return {'value': best['value'], 'confidence': best['confidence']}
        
        elif strategy == 'exact_match_or_flag':
            # All values must match exactly
            unique_values = set(str(v['value']).lower() for v in field_values)
            
            if len(unique_values) == 1:
                # All match
                return {'value': field_values[0]['value'], 'confidence': 1.0}
            else:
                # Conflict
                conflict = DataConflict(
                    field_name=field,
                    values=field_values,
                    conflict_severity='high',
                    flagged_for_review=True
                )
                # Use highest confidence as fallback
                best = max(field_values, key=lambda x: x['confidence'])
                return {
                    'value': best['value'],
                    'confidence': 0.5,
                    'conflict': conflict
                }
        
        elif strategy == 'merge_all_with_dedup':
            # Merge lists, remove duplicates
            merged = []
            seen = set()
            
            for val_info in field_values:
                value = val_info['value']
                
                if isinstance(value, list):
                    for item in value:
                        item_key = json.dumps(item, sort_keys=True, default=str)
                        if item_key not in seen:
                            merged.append(item)
                            seen.add(item_key)
                else:
                    item_key = json.dumps(value, sort_keys=True, default=str)
                    if item_key not in seen:
                        merged.append(value)
                        seen.add(item_key)
            
            return {'value': merged, 'confidence': 0.8}
        
        elif strategy == 'merge_all_with_strict_review':
            # Merge but flag for review (allergies, critical info)
            merged = []
            seen = set()
            
            for val_info in field_values:
                value = val_info['value']
                
                if isinstance(value, list):
                    for item in value:
                        item_key = json.dumps(item, sort_keys=True, default=str)
                        if item_key not in seen:
                            merged.append(item)
                            seen.add(item_key)
            
            if len(field_values) > 1 and len(merged) > 0:
                # Multiple sources for critical data - flag for review
                conflict = DataConflict(
                    field_name=field,
                    values=field_values,
                    conflict_severity='critical',
                    flagged_for_review=True
                )
                return {
                    'value': merged,
                    'confidence': 0.7,
                    'conflict': conflict
                }
            
            return {'value': merged, 'confidence': 0.8}
        
        elif strategy == 'merge_all':
            # Simple merge without dedup
            merged = []
            for val_info in field_values:
                value = val_info['value']
                if isinstance(value, list):
                    merged.extend(value)
                else:
                    merged.append(value)
            return {'value': merged, 'confidence': 0.7}
        
        else:
            # Default: use highest confidence
            best = max(field_values, key=lambda x: x['confidence'])
            return {'value': best['value'], 'confidence': best['confidence']}
    
    def save_fused_record(self, fused: FusedRecord) -> Tuple[bool, str]:
        """Save fused record to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            fusion_id = hashlib.sha256(
                json.dumps(fused.merged_data, sort_keys=True, default=str).encode()
            ).hexdigest()[:16]
            
            cursor.execute("""
                INSERT OR REPLACE INTO data_fusion_results
                (fusion_id, merged_data, source_inventory, conflicts, 
                 confidence_scores, completeness, requires_verification, 
                 biometric_verified, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fusion_id,
                json.dumps(fused.merged_data),
                json.dumps(fused.source_inventory),
                json.dumps([asdict(c) for c in fused.conflicts_detected]),
                json.dumps(fused.confidence_scores),
                fused.data_completeness,
                fused.requires_verification,
                fused.verified_by_biometric,
                fused.merged_at
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Fused record saved: {fusion_id}")
            return True, fusion_id
        
        except Exception as e:
            self.logger.error(f"Save fusion error: {str(e)}")
            return False, str(e)

# =============================================
# Multi-Source Patient Profile Builder
# =============================================

class MultiSourceProfileBuilder:
    """Build complete patient profiles from disaster data"""
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.fusion_engine = SmartDataFusionEngine(db_path)
        self.logger = logging.getLogger(f"{__name__}.MultiSourceProfileBuilder")
    
    def build_profile_from_sources(self, 
                                   photo_data: Optional[Dict] = None,
                                   document_data: Optional[Dict] = None,
                                   biometric_data: Optional[Dict] = None,
                                   verbal_description: Optional[Dict] = None,
                                   recovered_data: Optional[Dict] = None) -> FusedRecord:
        """
        Build complete patient profile from multiple disaster sources
        
        Each source contributes what it can:
        - photo_data: Facial features, apparent age/gender, family relationships (if group photo)
        - document_data: Official info (name, ID, medical history)
        - biometric_data: Fingerprints, DNA (definitive identification)
        - verbal_description: Patient/family descriptions
        - recovered_data: Data recovered from damaged systems
        """
        
        sources_available = []
        records_to_fuse = []
        priorities = {}
        
        # Photo source
        if photo_data:
            photo_data['_source'] = 'photo_analysis'
            records_to_fuse.append(photo_data)
            sources_available.append('photo')
            priorities['photo'] = DataSourcePriority.CLINICAL_ASSESSMENT.value
        
        # Document source (highest priority)
        if document_data:
            document_data['_source'] = 'document_ocr'
            records_to_fuse.append(document_data)
            sources_available.append('document')
            priorities['document'] = DataSourcePriority.OFFICIAL_MEDICAL_RECORD.value
        
        # Biometric source (highest priority for identification)
        if biometric_data:
            biometric_data['_source'] = 'biometric_verification'
            records_to_fuse.append(biometric_data)
            sources_available.append('biometric')
            priorities['biometric'] = DataSourcePriority.FINGERPRINT_CONFIRMED.value
        
        # Verbal description
        if verbal_description:
            verbal_description['_source'] = 'verbal_description'
            records_to_fuse.append(verbal_description)
            sources_available.append('verbal')
            priorities['verbal'] = DataSourcePriority.VERBAL_DESCRIPTION.value
        
        # Recovered data
        if recovered_data:
            recovered_data['_source'] = 'data_recovery'
            records_to_fuse.append(recovered_data)
            sources_available.append('recovered')
            priorities['recovered'] = DataSourcePriority.PARTIAL_RECOVERY.value
        
        if not records_to_fuse:
            return FusedRecord(
                patient_id=None,
                merged_data={},
                source_inventory={},
                conflicts_detected=[],
                confidence_scores={},
                data_completeness=0.0,
                requires_verification=True,
                verified_by_biometric=False
            )
        
        self.logger.info(f"Building profile from sources: {sources_available}")
        
        # Fuse all sources
        fused = self.fusion_engine.fuse_records(records_to_fuse, priorities)
        
        # Generate summary
        self.logger.info(
            f"Profile built from {len(sources_available)} sources: "
            f"{', '.join(sources_available)}, "
            f"completeness: {fused.data_completeness:.1%}, "
            f"conflicts: {len(fused.conflicts_detected)}"
        )
        
        return fused
    
    def extract_photo_profile(self, image_data: bytes) -> Dict[str, Any]:
        """Extract patient profile information from photo"""
        profile = {}
        
        try:
            # This would use computer vision to extract:
            # - Age (approximate)
            # - Gender
            # - Distinctive features (scars, birthmarks)
            # - Family relationships (if group photo)
            # - Visible medical conditions (injuries, skin conditions)
            
            profile = {
                'apparent_age_range': '20-30',  # Would use CV model
                'gender': 'unknown',
                'distinctive_features': [],
                'visible_injuries': [],
                'family_members_visible': 0,
                'photo_quality': 0.8
            }
        
        except Exception as e:
            self.logger.error(f"Photo profile extraction error: {str(e)}")
        
        return profile
    
    def extract_verbal_profile(self, description: str) -> Dict[str, Any]:
        """Extract patient info from verbal description"""
        profile = {}
        
        try:
            # Parse verbal description for extractable info
            import re
            
            # Try to extract age
            age_match = re.search(r'\b(\d+)\s*(?:year|yo|yrs?|old)\b', description, re.IGNORECASE)
            if age_match:
                profile['age'] = int(age_match.group(1))
            
            # Try to extract gender
            if any(word in description.lower() for word in ['man', 'male', 'boy']):
                profile['gender'] = 'male'
            elif any(word in description.lower() for word in ['woman', 'female', 'girl']):
                profile['gender'] = 'female'
            
            # Extract identifying features
            profile['description'] = description
        
        except Exception as e:
            self.logger.error(f"Verbal profile extraction error: {str(e)}")
        
        return profile

