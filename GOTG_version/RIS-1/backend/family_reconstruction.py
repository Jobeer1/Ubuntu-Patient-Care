"""
Family Tree Reconstruction Engine
Reconstruct family relationships from fragmented data in disaster scenarios
Build family networks to reunite separated members

Key Features:
- Match patients to families from photos (multiple people)
- Reconstruct relationships from partial names and descriptions
- Link family members across hospitals and time periods
- Detect family clusters (patients sharing addresses, surnames)
- Priority matching for vulnerable family members (children, elderly)
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
import re
import threading

logger = logging.getLogger(__name__)

# =============================================
# Data Classes & Enums
# =============================================

class RelationshipType(Enum):
    """Types of family relationships"""
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    SPOUSE = "spouse"
    GRANDPARENT = "grandparent"
    GRANDCHILD = "grandchild"
    AUNT_UNCLE = "aunt_uncle"
    COUSIN = "cousin"
    OTHER = "other"

@dataclass
class FamilyMember:
    """A person in a family tree"""
    member_id: str
    name: str
    apparent_age: Optional[int] = None
    age_range: Optional[str] = None  # "child", "adult", "elderly"
    gender: Optional[str] = None
    identifying_features: List[str] = field(default_factory=list)
    phone: Optional[str] = None
    hospital_id: Optional[int] = None
    patient_id: Optional[int] = None
    last_known_location: Optional[str] = None
    last_seen: Optional[str] = None

@dataclass
class FamilyRelationship:
    """Connection between two family members"""
    member_1_id: str
    member_2_id: str
    relationship_type: str  # From RelationshipType
    confidence: float  # 0.0 - 1.0
    evidence: List[str]  # Evidence supporting this relationship
    verified: bool = False

@dataclass
class FamilyCluster:
    """A reconstructed family group"""
    cluster_id: str
    members: List[FamilyMember]
    relationships: List[FamilyRelationship]
    primary_surname: Optional[str]
    shared_address: Optional[str]
    contact_info: Dict[str, str]
    separated_count: int  # Members in different hospitals
    reunion_priority: int  # 1 = highest priority
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

# =============================================
# Family Tree Reconstruction Engine
# =============================================

class FamilyTreeReconstructor:
    """Reconstruct family relationships from disaster data"""
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.FamilyTreeReconstructor")
    
    def extract_family_from_photo(self, image_data: bytes) -> List[FamilyMember]:
        """
        Extract multiple people from group photo
        Identify relationships based on spatial proximity and visual similarity
        """
        members = []
        
        try:
            # This would use face detection and facial similarity matching
            # For now, placeholder implementation
            
            # Would use:
            # - Face detection to find all faces
            # - Age/gender estimation
            # - Facial similarity clustering (parents, siblings likely similar)
            # - Spatial relationships (parent-child height differences)
            
            pass
        
        except Exception as e:
            self.logger.error(f"Photo family extraction error: {str(e)}")
        
        return members
    
    def match_to_existing_family(self, new_patient: FamilyMember, 
                                 known_members: List[FamilyMember]) -> List[Tuple[FamilyMember, float]]:
        """
        Match new patient to existing family members
        Returns list of (potential_relative, confidence) sorted by confidence
        """
        matches = []
        
        for known in known_members:
            confidence = self._calculate_relationship_confidence(new_patient, known)
            if confidence > 0.5:
                matches.append((known, confidence))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def _calculate_relationship_confidence(self, person1: FamilyMember, 
                                          person2: FamilyMember) -> float:
        """
        Calculate likelihood of relationship between two people
        Uses: name similarity, age relationships, location, shared features
        """
        confidence = 0.0
        evidence_count = 0
        
        # Name similarity (parents share surnames with children)
        if person1.name and person2.name:
            # Extract surnames
            name1_parts = person1.name.split()
            name2_parts = person2.name.split()
            
            # Check for shared surname
            if name1_parts[-1].lower() == name2_parts[-1].lower():
                confidence += 0.3
                evidence_count += 1
        
        # Age relationship
        if person1.apparent_age and person2.apparent_age:
            age_diff = abs(person1.apparent_age - person2.apparent_age)
            
            # Parent-child: typically 20-40 years apart
            if 20 <= age_diff <= 40:
                confidence += 0.25
                evidence_count += 1
            # Siblings: typically <15 years apart
            elif age_diff < 15:
                confidence += 0.2
                evidence_count += 1
        
        # Age range grouping
        if person1.age_range == person2.age_range:
            confidence += 0.1
            evidence_count += 1
        
        # Location (family members often admitted together)
        if person1.hospital_id and person2.hospital_id:
            if person1.hospital_id == person2.hospital_id:
                confidence += 0.15
                evidence_count += 1
        
        # Normalize
        if evidence_count > 0:
            confidence = min(1.0, confidence)
        
        return confidence
    
    def reconstruct_family_tree(self, patients: List[Dict]) -> List[FamilyCluster]:
        """
        Reconstruct family trees from list of patients
        Groups related patients into families
        """
        clusters = []
        processed = set()
        
        for i, patient in enumerate(patients):
            if i in processed:
                continue
            
            # Start new family cluster
            cluster_members = [self._dict_to_family_member(patient, i)]
            related_indices = {i}
            
            # Find related patients
            for j, other_patient in enumerate(patients):
                if j <= i or j in processed:
                    continue
                
                similarity = self._calculate_relationship_confidence(
                    self._dict_to_family_member(patient, i),
                    self._dict_to_family_member(other_patient, j)
                )
                
                if similarity > 0.5:
                    cluster_members.append(self._dict_to_family_member(other_patient, j))
                    related_indices.add(j)
            
            processed.update(related_indices)
            
            # Build relationships within cluster
            relationships = []
            for m1 in cluster_members:
                for m2 in cluster_members:
                    if m1.member_id != m2.member_id:
                        rel_type = self._infer_relationship_type(m1, m2)
                        if rel_type:
                            confidence = self._calculate_relationship_confidence(m1, m2)
                            relationships.append(FamilyRelationship(
                                member_1_id=m1.member_id,
                                member_2_id=m2.member_id,
                                relationship_type=rel_type,
                                confidence=confidence,
                                evidence=[]
                            ))
            
            # Create cluster
            if len(cluster_members) > 0:
                cluster = FamilyCluster(
                    cluster_id=hashlib.sha256(
                        ''.join(m.member_id for m in cluster_members).encode()
                    ).hexdigest()[:12],
                    members=cluster_members,
                    relationships=relationships,
                    primary_surname=self._extract_surname(cluster_members[0].name),
                    shared_address=self._get_shared_address(cluster_members),
                    contact_info={},
                    separated_count=len(set(m.hospital_id for m in cluster_members if m.hospital_id))
                )
                
                clusters.append(cluster)
        
        # Prioritize reunification for separated families
        for cluster in clusters:
            if cluster.separated_count > 1:
                cluster.reunion_priority = 1  # Highest
            else:
                cluster.reunion_priority = 2
        
        self.logger.info(f"Reconstructed {len(clusters)} family clusters from {len(patients)} patients")
        return clusters
    
    def _dict_to_family_member(self, patient_dict: Dict, index: int) -> FamilyMember:
        """Convert patient dictionary to FamilyMember"""
        name = patient_dict.get('name', f'Unknown_{index}')
        
        return FamilyMember(
            member_id=hashlib.sha256(
                f"{name}{patient_dict.get('date_of_birth', '')}".encode()
            ).hexdigest()[:12],
            name=name,
            apparent_age=patient_dict.get('age'),
            gender=patient_dict.get('gender'),
            phone=patient_dict.get('phone'),
            hospital_id=patient_dict.get('hospital_id'),
            patient_id=patient_dict.get('patient_id')
        )
    
    def _infer_relationship_type(self, person1: FamilyMember, 
                                 person2: FamilyMember) -> Optional[str]:
        """Infer most likely relationship type between two people"""
        
        # Based on age difference
        if person1.apparent_age and person2.apparent_age:
            age_diff = person1.apparent_age - person2.apparent_age
            
            if 20 <= abs(age_diff) <= 40:
                return RelationshipType.PARENT.value if age_diff > 0 else RelationshipType.CHILD.value
            elif abs(age_diff) < 15:
                return RelationshipType.SIBLING.value
        
        # Default
        return RelationshipType.OTHER.value
    
    def _extract_surname(self, full_name: Optional[str]) -> Optional[str]:
        """Extract surname from full name"""
        if not full_name:
            return None
        
        parts = full_name.strip().split()
        return parts[-1] if parts else None
    
    def _get_shared_address(self, members: List[FamilyMember]) -> Optional[str]:
        """Get shared address if all members have same address"""
        addresses = [m.last_known_location for m in members if m.last_known_location]
        
        if addresses and len(set(addresses)) == 1:
            return addresses[0]
        
        return None
    
    def find_missing_family_members(self, known_member: FamilyMember, 
                                   all_patients: List[Dict]) -> List[Tuple[FamilyMember, float]]:
        """
        Find potential missing family members for a known patient
        Useful for reunification efforts
        """
        candidates = []
        
        for patient_dict in all_patients:
            candidate = self._dict_to_family_member(patient_dict, 0)
            confidence = self._calculate_relationship_confidence(known_member, candidate)
            
            if confidence > 0.6:
                candidates.append((candidate, confidence))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:5]  # Return top 5
    
    def resolve_name_variations(self, names: List[str]) -> Optional[str]:
        """
        Try to resolve multiple name variations to single person
        E.g., "Ahmed", "Ahmed Hassan", "A. Hassan" likely same person
        """
        if not names:
            return None
        
        if len(names) == 1:
            return names[0]
        
        # Find most complete name (most parts)
        longest = max(names, key=lambda x: len(x.split()))
        
        # Verify others are subsets/variations
        longest_parts = set(longest.lower().split())
        
        for name in names:
            name_parts = set(name.lower().split())
            # Check if name parts overlap significantly
            overlap = len(name_parts & longest_parts)
            if overlap < len(name_parts) * 0.7:
                return None  # Doesn't match
        
        return longest

# =============================================
# Family Reunification Coordinator
# =============================================

class FamilyReunificationCoordinator:
    """Coordinate family reunification efforts"""
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.reconstructor = FamilyTreeReconstructor(db_path)
        self.logger = logging.getLogger(f"{__name__}.FamilyReunificationCoordinator")
    
    def prioritize_reunifications(self, clusters: List[FamilyCluster]) -> List[Dict]:
        """
        Create prioritized list of family reunifications
        Prioritize: separated families, vulnerable members (children/elderly), critical conditions
        """
        reunifications = []
        
        for cluster in clusters:
            if cluster.separated_count <= 1:
                continue  # Already together
            
            # Calculate priority
            priority_score = 0
            
            # Base score from separation
            priority_score += cluster.separated_count * 10
            
            # Vulnerable members boost
            for member in cluster.members:
                if member.age_range in ['child', 'elderly']:
                    priority_score += 5
            
            reunifications.append({
                'cluster_id': cluster.cluster_id,
                'family_name': cluster.primary_surname or 'Unknown',
                'total_members': len(cluster.members),
                'separated_members': cluster.separated_count,
                'members': [
                    {
                        'name': m.name,
                        'hospital': m.hospital_id,
                        'priority_member': m.age_range in ['child', 'elderly']
                    }
                    for m in cluster.members
                ],
                'priority_score': priority_score,
                'created_at': cluster.created_at
            })
        
        # Sort by priority
        reunifications.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return reunifications
    
    def create_reunion_plan(self, cluster: FamilyCluster) -> Dict[str, Any]:
        """Create detailed plan for reunifying a separated family"""
        
        # Group by hospital
        by_hospital = {}
        for member in cluster.members:
            hosp = member.hospital_id or 'Unknown'
            if hosp not in by_hospital:
                by_hospital[hosp] = []
            by_hospital[hosp].append(member)
        
        # Create transfers to main hospital (first one)
        main_hospital = list(by_hospital.keys())[0]
        
        transfers = []
        for hosp, members in by_hospital.items():
            if hosp != main_hospital:
                for member in members:
                    transfers.append({
                        'from_hospital': hosp,
                        'to_hospital': main_hospital,
                        'patient_id': member.patient_id,
                        'patient_name': member.name,
                        'priority': 'high' if member.age_range in ['child', 'elderly'] else 'normal'
                    })
        
        return {
            'family_name': cluster.primary_surname,
            'total_members': len(cluster.members),
            'together_count': max(len(members) for members in by_hospital.values()),
            'main_hospital': main_hospital,
            'required_transfers': transfers,
            'contact_info': cluster.contact_info,
            'notes': f"Family has {cluster.separated_count} members at different hospitals"
        }
    
    def save_family_cluster(self, cluster: FamilyCluster) -> Tuple[bool, str]:
        """Save family cluster to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Save cluster
            cursor.execute("""
                INSERT OR REPLACE INTO family_clusters
                (cluster_id, family_name, members_count, separated_count, 
                 reunion_priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                cluster.cluster_id,
                cluster.primary_surname or 'Unknown',
                len(cluster.members),
                cluster.separated_count,
                cluster.reunion_priority,
                cluster.created_at
            ))
            
            # Save members
            for member in cluster.members:
                cursor.execute("""
                    INSERT OR IGNORE INTO family_members
                    (member_id, cluster_id, name, age, hospital_id, patient_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    member.member_id,
                    cluster.cluster_id,
                    member.name,
                    member.apparent_age,
                    member.hospital_id,
                    member.patient_id
                ))
            
            # Save relationships
            for rel in cluster.relationships:
                cursor.execute("""
                    INSERT OR IGNORE INTO family_relationships
                    (member_1_id, member_2_id, relationship_type, confidence)
                    VALUES (?, ?, ?, ?)
                """, (
                    rel.member_1_id,
                    rel.member_2_id,
                    rel.relationship_type,
                    rel.confidence
                ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Family cluster saved: {cluster.cluster_id}")
            return True, cluster.cluster_id
        
        except Exception as e:
            self.logger.error(f"Save cluster error: {str(e)}")
            return False, str(e)

