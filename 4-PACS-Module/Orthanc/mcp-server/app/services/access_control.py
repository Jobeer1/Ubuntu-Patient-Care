"""
Access Control Service
Determines what images/patients a user can access based on their role and assignments

This service implements role-based access control (RBAC) for patient images:
- Admin/Radiologist: Access to all patients
- Referring Doctor: Access to assigned patients only
- Patient: Access to own records + family members (if configured)
- Technician: Access to assigned patients

Access is determined by:
1. User role (from MCP users table)
2. Patient relationships (patient_relationships table)
3. Doctor assignments (doctor_patient_assignments table)
4. Family access (family_access table)
"""
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime
from app.services.pacs_connector import PACSConnector

logger = logging.getLogger(__name__)

class AccessControlService:
    """
    Access Control Service
    
    Manages patient-level access control based on user roles
    and configured relationships.
    """
    
    def __init__(self, pacs_connector: PACSConnector, db_connection):
        """
        Initialize Access Control Service
        
        Args:
            pacs_connector: PACS database connector
            db_connection: MCP database connection
        """
        self.pacs = pacs_connector
        self.db = db_connection
    
    def get_accessible_patients(self, user_id: int, user_role: str) -> List[str]:
        """
        Get list of patient IDs this user can access
        
        Args:
            user_id: MCP user ID
            user_role: User's role (Admin, Radiologist, Doctor, Patient, etc.)
        
        Returns:
            List of patient IDs/MRNs user can access
            Returns ['*'] for admin/radiologist (all patients)
        """
        logger.debug(f"Getting accessible patients for user {user_id} (role: {user_role})")
        
        # Admin, Radiologist, and Technician: All patients
        if user_role in ['Admin', 'Radiologist', 'Technician']:
            logger.debug(f"User {user_id} has full access (role: {user_role})")
            return ['*']  # Wildcard for all patients
        
        accessible_patients = set()  # Use set to avoid duplicates
        
        # Referring Doctor: Assigned patients
        if user_role == 'Referring Doctor':
            doctor_patients = self._get_doctor_assigned_patients(user_id)
            accessible_patients.update(doctor_patients)
            logger.debug(f"Doctor {user_id} has access to {len(doctor_patients)} assigned patients")
        
        # Patient: Self and family
        if user_role == 'Patient':
            # Self access
            self_patients = self._get_patient_self_access(user_id)
            accessible_patients.update(self_patients)
            
            # Family access (children)
            family_patients = self._get_family_access(user_id)
            accessible_patients.update(family_patients)
            
            logger.debug(f"Patient {user_id} has access to {len(accessible_patients)} patient records")
        
        # Convert set to list
        result = list(accessible_patients)
        logger.info(f"User {user_id} ({user_role}) can access {len(result)} patient(s)")
        return result
    
    def _get_doctor_assigned_patients(self, doctor_user_id: int) -> List[str]:
        """
        Get patients assigned to a referring doctor
        
        Args:
            doctor_user_id: Doctor's MCP user ID
        
        Returns:
            List of patient IDs
        """
        try:
            cursor = self.db.execute("""
                SELECT DISTINCT patient_identifier 
                FROM doctor_patient_assignments
                WHERE doctor_user_id = ? 
                  AND is_active = 1
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (doctor_user_id,))
            
            patients = [row[0] for row in cursor.fetchall()]
            return patients
            
        except Exception as e:
            logger.error(f"Error fetching doctor assignments for user {doctor_user_id}: {e}")
            return []
    
    def _get_patient_self_access(self, patient_user_id: int) -> List[str]:
        """
        Get patient's own records
        
        Args:
            patient_user_id: Patient's MCP user ID
        
        Returns:
            List of patient IDs (usually just one - their own)
        """
        try:
            cursor = self.db.execute("""
                SELECT DISTINCT patient_identifier 
                FROM patient_relationships
                WHERE user_id = ? 
                  AND is_active = 1
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (patient_user_id,))
            
            patients = [row[0] for row in cursor.fetchall()]
            return patients
            
        except Exception as e:
            logger.error(f"Error fetching patient relationships for user {patient_user_id}: {e}")
            return []
    
    def _get_family_access(self, parent_user_id: int) -> List[str]:
        """
        Get children's records for a parent/guardian
        
        Args:
            parent_user_id: Parent/Guardian's MCP user ID
        
        Returns:
            List of child patient IDs
        """
        try:
            cursor = self.db.execute("""
                SELECT DISTINCT child_patient_identifier 
                FROM family_access
                WHERE parent_user_id = ? 
                  AND is_active = 1 
                  AND verified = 1
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (parent_user_id,))
            
            children = [row[0] for row in cursor.fetchall()]
            return children
            
        except Exception as e:
            logger.error(f"Error fetching family access for user {parent_user_id}: {e}")
            return []
    
    def can_access_patient(self, user_id: int, user_role: str, patient_id: str) -> bool:
        """
        Check if user can access specific patient
        
        Args:
            user_id: MCP user ID
            user_role: User's role
            patient_id: Patient ID/MRN to check
        
        Returns:
            True if user can access patient, False otherwise
        """
        accessible = self.get_accessible_patients(user_id, user_role)
        
        # Check for wildcard (all patients)
        if '*' in accessible:
            return True
        
        # Check if patient in accessible list
        result = patient_id in accessible
        
        if not result:
            logger.warning(f"Access denied: User {user_id} cannot access patient {patient_id}")
        
        return result
    
    def get_user_studies(self, user_id: int, user_role: str, limit: int = 100) -> List[Dict]:
        """
        Get all studies accessible to this user
        
        Args:
            user_id: MCP user ID
            user_role: User's role
            limit: Maximum number of studies to return
        
        Returns:
            List of study dictionaries
        """
        accessible_patients = self.get_accessible_patients(user_id, user_role)
        
        # If wildcard, get recent studies (paginated)
        if '*' in accessible_patients:
            logger.debug(f"User {user_id} has full access, returning recent studies")
            # For admin/radiologist, return most recent studies
            # In production, this should be paginated properly
            return self._get_recent_studies(limit)
        
        # Get studies for accessible patients
        all_studies = []
        for patient_id in accessible_patients:
            studies = self.pacs.get_patient_studies(patient_id)
            all_studies.extend(studies)
        
        # Sort by study date (most recent first)
        all_studies.sort(key=lambda x: x.get('study_date', ''), reverse=True)
        
        # Limit results
        return all_studies[:limit]
    
    def _get_recent_studies(self, limit: int = 100) -> List[Dict]:
        """
        Get most recent studies (for admin/radiologist)
        
        Args:
            limit: Maximum number of studies
        
        Returns:
            List of recent studies
        """
        try:
            conn = self.pacs.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id,
                    patient_id,
                    patient_name,
                    patient_birth_date,
                    patient_sex,
                    study_date,
                    study_description,
                    modality,
                    folder_path,
                    dicom_file_count,
                    folder_size_mb,
                    last_indexed
                FROM patient_studies 
                ORDER BY study_date DESC, last_indexed DESC
                LIMIT ?
            """, (limit,))
            
            studies = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return studies
            
        except Exception as e:
            logger.error(f"Error fetching recent studies: {e}")
            return []
    
    def get_accessible_patient_count(self, user_id: int, user_role: str) -> int:
        """
        Get count of patients user can access
        
        Args:
            user_id: MCP user ID
            user_role: User's role
        
        Returns:
            Number of accessible patients
        """
        accessible = self.get_accessible_patients(user_id, user_role)
        
        # If wildcard, get total patient count from PACS
        if '*' in accessible:
            stats = self.pacs.get_database_stats()
            return stats.get('total_patients', 0)
        
        return len(accessible)
    
    def log_access_attempt(self, user_id: int, patient_id: str, access_type: str, 
                          granted: bool, ip_address: str = None, user_agent: str = None):
        """
        Log access attempt for audit trail
        
        Args:
            user_id: MCP user ID
            patient_id: Patient ID accessed
            access_type: Type of access (view, download, share)
            granted: Whether access was granted
            ip_address: User's IP address
            user_agent: User's browser/client
        """
        try:
            self.db.execute("""
                INSERT INTO access_audit_log 
                (user_id, patient_identifier, access_type, access_granted, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, patient_id, access_type, granted, ip_address, user_agent))
            self.db.commit()
            
            logger.info(f"Access logged: User {user_id} -> Patient {patient_id} ({access_type}): {'GRANTED' if granted else 'DENIED'}")
            
        except Exception as e:
            logger.error(f"Error logging access attempt: {e}")
    
    def get_access_summary(self, user_id: int, user_role: str) -> Dict:
        """
        Get summary of user's access permissions
        
        Args:
            user_id: MCP user ID
            user_role: User's role
        
        Returns:
            Dictionary with access summary
        """
        accessible_patients = self.get_accessible_patients(user_id, user_role)
        
        summary = {
            'user_id': user_id,
            'user_role': user_role,
            'has_full_access': '*' in accessible_patients,
            'accessible_patient_count': self.get_accessible_patient_count(user_id, user_role),
            'accessible_patients': accessible_patients if '*' not in accessible_patients else [],
        }
        
        # Add role-specific details
        if user_role == 'Referring Doctor':
            summary['assigned_patients'] = self._get_doctor_assigned_patients(user_id)
        
        if user_role == 'Patient':
            summary['self_access'] = self._get_patient_self_access(user_id)
            summary['family_access'] = self._get_family_access(user_id)
        
        return summary


# Singleton instance
_access_control_service = None

def get_access_control_service(pacs_connector: PACSConnector = None, 
                               db_connection = None) -> AccessControlService:
    """
    Get or create Access Control Service singleton
    
    Args:
        pacs_connector: PACS connector instance
        db_connection: MCP database connection
    
    Returns:
        AccessControlService instance
    """
    global _access_control_service
    
    if _access_control_service is None:
        if pacs_connector is None or db_connection is None:
            raise ValueError("PACS connector and database connection required on first call")
        
        _access_control_service = AccessControlService(pacs_connector, db_connection)
    
    return _access_control_service
