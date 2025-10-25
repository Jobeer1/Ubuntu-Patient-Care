"""
Orthanc Management Business Logic - Authorization Manager
Handles patient authorization operations for referring doctors
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc

from ..database.manager import DatabaseManager
from ..models.patient_authorization import PatientAuthorization
from ..models.referring_doctor import ReferringDoctor
from ..models.audit_log import AuditLog


class AuthorizationManager:
    """
    Business logic manager for patient authorizations
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_authorization(self, doctor_id: str, patient_id: str, study_instance_uid: str = None,
                           access_level: str = 'view', expires_at: datetime = None,
                           notes: str = None, created_by: str = None) -> Tuple[PatientAuthorization, list]:
        """
        Create a new patient authorization
        
        Returns:
            Tuple of (authorization, validation_errors)
        """
        try:
            with self.db_manager.get_session() as session:
                # Verify doctor exists and is active
                doctor = session.query(ReferringDoctor).filter(
                    and_(
                        ReferringDoctor.id == doctor_id,
                        ReferringDoctor.is_active == True
                    )
                ).first()
                
                if not doctor:
                    return None, ["Doctor not found or inactive"]
                
                # Create authorization
                auth = PatientAuthorization(
                    doctor_id=doctor_id,
                    patient_id=patient_id,
                    study_instance_uid=study_instance_uid,
                    access_level=access_level,
                    expires_at=expires_at,
                    notes=notes,
                    granted_by=created_by  # Fix: set the granted_by field
                )
                
                # Validate
                errors = auth.validate()
                if errors:
                    return None, errors
                
                # Check for duplicate active authorization
                existing = self.get_active_authorization(
                    doctor_id, patient_id, study_instance_uid, session
                )
                if existing:
                    return None, ["Active authorization already exists for this doctor/patient/study combination"]
                
                # Save and commit
                session.add(auth)
                session.commit()
                
                # Get auth ID and create fresh session for return
                auth_id = auth.id
                
                # Create audit log
                self._create_audit_log(
                    action='grant_access',
                    resource_id=auth_id,
                    user_id=created_by,
                    details={
                        'doctor_id': doctor_id,
                        'doctor_name': doctor.name,
                        'hpcsa_number': doctor.hpcsa_number,
                        'patient_id': patient_id,
                        'study_instance_uid': study_instance_uid,
                        'access_level': access_level
                    },
                    patient_id=patient_id,
                    study_uid=study_instance_uid,
                    session=session
                )
                
            # Return fresh object from new session
            return self.get_authorization_by_id(auth_id), []
                
        except Exception as e:
            return None, [f"Database error: {str(e)}"]
    
    def get_authorization_by_id(self, auth_id: str, session: Session = None) -> Optional[PatientAuthorization]:
        """Get authorization by ID"""
        def _get_auth(s):
            return s.query(PatientAuthorization).options(
                joinedload(PatientAuthorization.doctor)
            ).filter(PatientAuthorization.id == auth_id).first()
        
        if session:
            return _get_auth(session)
        else:
            with self.db_manager.get_session() as s:
                return _get_auth(s)
    
    def get_active_authorization(self, doctor_id: str, patient_id: str,
                               study_uid: str = None, session: Session = None) -> Optional[PatientAuthorization]:
        """Get active authorization for doctor/patient/study combination"""
        def _get_auth(s):
            query = s.query(PatientAuthorization).filter(
                and_(
                    PatientAuthorization.doctor_id == doctor_id,
                    PatientAuthorization.patient_id == patient_id,
                    PatientAuthorization.is_active == True
                )
            )
            
            if study_uid:
                query = query.filter(PatientAuthorization.study_instance_uid == study_uid)
            else:
                query = query.filter(PatientAuthorization.study_instance_uid.is_(None))
            
            # Check expiry
            query = query.filter(
                or_(
                    PatientAuthorization.expires_at.is_(None),
                    PatientAuthorization.expires_at > datetime.utcnow()
                )
            )
            
            return query.first()
        
        if session:
            return _get_auth(session)
        else:
            with self.db_manager.get_session() as s:
                return _get_auth(s)
    
    def get_doctor_authorizations(self, doctor_id: str, active_only: bool = True,
                                limit: int = 100, offset: int = 0) -> List[PatientAuthorization]:
        """Get all authorizations for a doctor"""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(PatientAuthorization).options(
                    joinedload(PatientAuthorization.doctor)
                ).filter(PatientAuthorization.doctor_id == doctor_id)
                
                if active_only:
                    query = query.filter(
                        and_(
                            PatientAuthorization.is_active == True,
                            or_(
                                PatientAuthorization.expires_at.is_(None),
                                PatientAuthorization.expires_at > datetime.utcnow()
                            )
                        )
                    )
                
                query = query.order_by(desc(PatientAuthorization.created_at))
                
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                return query.all()
                
        except Exception:
            return []
    
    def get_patient_authorizations(self, patient_id: str, active_only: bool = True,
                                 limit: int = 100, offset: int = 0) -> List[PatientAuthorization]:
        """Get all authorizations for a patient"""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(PatientAuthorization).options(
                    joinedload(PatientAuthorization.doctor)
                ).filter(PatientAuthorization.patient_id == patient_id)
                
                if active_only:
                    query = query.filter(
                        and_(
                            PatientAuthorization.is_active == True,
                            or_(
                                PatientAuthorization.expires_at.is_(None),
                                PatientAuthorization.expires_at > datetime.utcnow()
                            )
                        )
                    )
                
                query = query.order_by(desc(PatientAuthorization.created_at))
                
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                return query.all()
                
        except Exception:
            return []
    
    def update_authorization(self, auth_id: str, updates: Dict[str, Any],
                           updated_by: str = None) -> Tuple[PatientAuthorization, list]:
        """Update authorization"""
        try:
            with self.db_manager.get_session() as session:
                auth = self.get_authorization_by_id(auth_id, session)
                if not auth:
                    return None, ["Authorization not found"]
                
                # Store original values for audit
                original_values = {}
                
                # Apply updates
                for field, value in updates.items():
                    if hasattr(auth, field):
                        original_values[field] = getattr(auth, field)
                        setattr(auth, field, value)
                
                # Validate
                errors = auth.validate()
                if errors:
                    return None, errors
                
                # Update timestamp
                auth.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='update_authorization',
                    resource_id=auth.id,
                    user_id=updated_by,
                    details={
                        'doctor_id': auth.doctor_id,
                        'patient_id': auth.patient_id,
                        'study_uid': auth.study_instance_uid,
                        'updates': updates,
                        'original_values': original_values
                    },
                    patient_id=auth.patient_id,
                    study_uid=auth.study_instance_uid,
                    session=session
                )
                
                return auth, []
                
        except Exception as e:
            return None, [f"Database error: {str(e)}"]
    
    def revoke_authorization(self, auth_id: str, revoked_by: str = None,
                           reason: str = None) -> Tuple[bool, list]:
        """Revoke an authorization"""
        try:
            with self.db_manager.get_session() as session:
                auth = self.get_authorization_by_id(auth_id, session)
                if not auth:
                    return False, ["Authorization not found"]
                
                if not auth.is_active:
                    return False, ["Authorization is already revoked"]
                
                # Revoke
                auth.is_active = False
                auth.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='revoke_access',
                    resource_id=auth.id,
                    user_id=revoked_by,
                    details={
                        'doctor_id': auth.doctor_id,
                        'patient_id': auth.patient_id,
                        'study_uid': auth.study_instance_uid,
                        'reason': reason
                    },
                    patient_id=auth.patient_id,
                    study_uid=auth.study_instance_uid,
                    session=session
                )
                
                return True, []
                
        except Exception as e:
            return False, [f"Database error: {str(e)}"]
    
    def extend_authorization(self, auth_id: str, new_expires_at: datetime,
                           extended_by: str = None) -> Tuple[bool, list]:
        """Extend authorization expiry"""
        try:
            with self.db_manager.get_session() as session:
                auth = self.get_authorization_by_id(auth_id, session)
                if not auth:
                    return False, ["Authorization not found"]
                
                if not auth.is_active:
                    return False, ["Cannot extend revoked authorization"]
                
                if auth.is_expired():
                    return False, ["Cannot extend expired authorization"]
                
                if new_expires_at <= datetime.utcnow():
                    return False, ["New expiry date must be in the future"]
                
                old_expires_at = auth.expires_at
                auth.expires_at = new_expires_at
                auth.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='extend_authorization',
                    resource_id=auth.id,
                    user_id=extended_by,
                    details={
                        'doctor_id': auth.doctor_id,
                        'patient_id': auth.patient_id,
                        'study_uid': auth.study_instance_uid,
                        'old_expires_at': old_expires_at.isoformat() if old_expires_at else None,
                        'new_expires_at': new_expires_at.isoformat()
                    },
                    patient_id=auth.patient_id,
                    study_uid=auth.study_instance_uid,
                    session=session
                )
                
                return True, []
                
        except Exception as e:
            return False, [f"Database error: {str(e)}"]
    
    def bulk_create_authorizations(self, authorizations: List[Dict[str, Any]],
                                 created_by: str = None) -> Tuple[List[PatientAuthorization], List[str]]:
        """Create multiple authorizations in bulk"""
        created_auths = []
        all_errors = []
        
        try:
            with self.db_manager.get_session() as session:
                for i, auth_data in enumerate(authorizations):
                    try:
                        # Verify doctor exists
                        doctor_id = auth_data.get('doctor_id')
                        doctor = session.query(ReferringDoctor).filter(
                            and_(
                                ReferringDoctor.id == doctor_id,
                                ReferringDoctor.is_active == True
                            )
                        ).first()
                        
                        if not doctor:
                            all_errors.append(f"Authorization {i+1}: Doctor not found or inactive")
                            continue
                        
                        # Create authorization
                        auth = PatientAuthorization(**auth_data)
                        
                        # Validate
                        errors = auth.validate()
                        if errors:
                            all_errors.extend([f"Authorization {i+1}: {error}" for error in errors])
                            continue
                        
                        # Check for duplicates
                        existing = self.get_active_authorization(
                            auth.doctor_id, auth.patient_id, auth.study_instance_uid, session
                        )
                        if existing:
                            all_errors.append(f"Authorization {i+1}: Duplicate authorization exists")
                            continue
                        
                        session.add(auth)
                        created_auths.append(auth)
                        
                    except Exception as e:
                        all_errors.append(f"Authorization {i+1}: {str(e)}")
                
                if created_auths and not all_errors:
                    session.commit()
                    
                    # Create audit logs
                    for auth in created_auths:
                        self._create_audit_log(
                            action='grant_access',
                            resource_id=auth.id,
                            user_id=created_by,
                            details={
                                'bulk_operation': True,
                                'doctor_id': auth.doctor_id,
                                'patient_id': auth.patient_id,
                                'study_uid': auth.study_instance_uid,
                                'access_level': auth.access_level
                            },
                            patient_id=auth.patient_id,
                            study_uid=auth.study_instance_uid,
                            session=session
                        )
                
                return created_auths, all_errors
                
        except Exception as e:
            return [], [f"Database error: {str(e)}"]
    
    def check_doctor_access(self, doctor_id: str, patient_id: str,
                           study_uid: str = None) -> Tuple[bool, str, Optional[PatientAuthorization]]:
        """
        Check if doctor has access to patient/study
        
        Returns:
            Tuple of (has_access, access_level, authorization)
        """
        try:
            with self.db_manager.get_session() as session:
                # Check doctor is active
                doctor = session.query(ReferringDoctor).filter(
                    and_(
                        ReferringDoctor.id == doctor_id,
                        ReferringDoctor.is_active == True
                    )
                ).first()
                
                if not doctor:
                    return False, 'none', None
                
                # Check global access level first
                if doctor.access_level == 'admin':
                    return True, 'admin', None
                
                # Check specific authorization
                auth = self.get_active_authorization(doctor_id, patient_id, study_uid, session)
                if auth:
                    return True, auth.access_level, auth
                
                # Check patient-level authorization (no specific study)
                if study_uid:
                    patient_auth = self.get_active_authorization(doctor_id, patient_id, None, session)
                    if patient_auth:
                        return True, patient_auth.access_level, patient_auth
                
                return False, 'none', None
                
        except Exception:
            return False, 'none', None
    
    def get_expiring_authorizations(self, days_ahead: int = 7) -> List[PatientAuthorization]:
        """Get authorizations expiring within specified days"""
        try:
            with self.db_manager.get_session() as session:
                expiry_threshold = datetime.utcnow() + timedelta(days=days_ahead)
                
                return session.query(PatientAuthorization).options(
                    joinedload(PatientAuthorization.doctor)
                ).filter(
                    and_(
                        PatientAuthorization.is_active == True,
                        PatientAuthorization.expires_at.isnot(None),
                        PatientAuthorization.expires_at <= expiry_threshold,
                        PatientAuthorization.expires_at > datetime.utcnow()
                    )
                ).order_by(PatientAuthorization.expires_at).all()
                
        except Exception:
            return []
    
    def cleanup_expired_authorizations(self, cleaned_by: str = None) -> int:
        """Clean up expired authorizations"""
        try:
            with self.db_manager.get_session() as session:
                expired_auths = session.query(PatientAuthorization).filter(
                    and_(
                        PatientAuthorization.is_active == True,
                        PatientAuthorization.expires_at.isnot(None),
                        PatientAuthorization.expires_at <= datetime.utcnow()
                    )
                ).all()
                
                count = len(expired_auths)
                
                for auth in expired_auths:
                    auth.is_active = False
                    auth.last_updated = datetime.utcnow()
                    
                    # Create audit log
                    self._create_audit_log(
                        action='expire_authorization',
                        resource_id=auth.id,
                        user_id=cleaned_by,
                        details={
                            'doctor_id': auth.doctor_id,
                            'patient_id': auth.patient_id,
                            'study_uid': auth.study_uid,
                            'expired_at': auth.expires_at.isoformat()
                        },
                        patient_id=auth.patient_id,
                        study_uid=auth.study_uid,
                        session=session
                    )
                
                session.commit()
                return count
                
        except Exception:
            return 0
    
    def get_authorization_statistics(self) -> Dict[str, Any]:
        """Get authorization statistics"""
        try:
            with self.db_manager.get_session() as session:
                total = session.query(PatientAuthorization).count()
                
                active = session.query(PatientAuthorization).filter(
                    and_(
                        PatientAuthorization.is_active == True,
                        or_(
                            PatientAuthorization.expires_at.is_(None),
                            PatientAuthorization.expires_at > datetime.utcnow()
                        )
                    )
                ).count()
                
                expired = session.query(PatientAuthorization).filter(
                    and_(
                        PatientAuthorization.is_active == True,
                        PatientAuthorization.expires_at.isnot(None),
                        PatientAuthorization.expires_at <= datetime.utcnow()
                    )
                ).count()
                
                revoked = session.query(PatientAuthorization).filter(
                    PatientAuthorization.is_active == False
                ).count()
                
                # Access level breakdown
                access_levels = session.query(
                    PatientAuthorization.access_level,
                    func.count(PatientAuthorization.id)
                ).filter(
                    and_(
                        PatientAuthorization.is_active == True,
                        or_(
                            PatientAuthorization.expires_at.is_(None),
                            PatientAuthorization.expires_at > datetime.utcnow()
                        )
                    )
                ).group_by(PatientAuthorization.access_level).all()
                
                return {
                    'total_authorizations': total,
                    'active_authorizations': active,
                    'expired_authorizations': expired,
                    'revoked_authorizations': revoked,
                    'access_level_breakdown': dict(access_levels)
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def _create_audit_log(self, action: str, resource_id: str, user_id: str = None,
                         details: Dict[str, Any] = None, patient_id: str = None,
                         study_uid: str = None, session: Session = None):
        """Create audit log entry"""
        if not session:
            return
        
        try:
            audit_log = AuditLog(
                user_id=user_id,
                user_type='admin',  # Assume admin for authorization management
                action=action,
                resource_type='authorization',
                resource_id=resource_id,
                compliance_category='hpcsa'
            )
            
            if details:
                audit_log.set_details(details)
            
            if patient_id:
                audit_log.add_patient_access(patient_id, study_uid)
            
            session.add(audit_log)
            # Don't commit here - let parent transaction handle it
            
        except Exception:
            # Don't fail the main operation if audit logging fails
            pass
