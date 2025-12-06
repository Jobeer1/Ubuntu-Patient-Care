"""
Orthanc Management Business Logic - Doctor Manager
Handles all referring doctor operations and validations
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..database.manager import DatabaseManager
from ..models.referring_doctor import ReferringDoctor
from ..models.patient_referral import PatientReferral
from ..models.patient_authorization import PatientAuthorization
from ..models.audit_log import AuditLog


class DoctorManager:
    """
    Business logic manager for referring doctors
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_doctor(self, name: str, hpcsa_number: str, email: str,
                     phone: str = None, practice_name: str = None,
                     specialization: str = None, facility_type: str = None, 
                     province: str = None, access_level: str = 'view_only',
                     notes: str = None, emergency_contact: str = None,
                     created_by: str = None) -> Tuple[ReferringDoctor, list]:
        """
        Create a new referring doctor
        
        Returns:
            Tuple of (doctor, validation_errors)
        """
        try:
            with self.db_manager.get_session() as session:
                # Create doctor instance
                doctor = ReferringDoctor(
                    name=name,
                    hpcsa_number=hpcsa_number,
                    email=email,
                    phone=phone,
                    practice_name=practice_name,
                    specialization=specialization,
                    facility_type=facility_type,
                    province=province,
                    access_level=access_level,
                    notes=notes,
                    emergency_contact=emergency_contact
                )
                
                # Validate
                errors = doctor.validate()
                if errors:
                    return None, errors
                
                # Check for duplicates
                existing_hpcsa = self.get_doctor_by_hpcsa(hpcsa_number, session)
                if existing_hpcsa:
                    return None, [f"Doctor with HPCSA number {hpcsa_number} already exists"]
                
                existing_email = self.get_doctor_by_email(email, session)
                if existing_email:
                    return None, [f"Doctor with email {email} already exists"]
                
                # Save
                session.add(doctor)
                session.commit()
                
                # Refresh to load generated values
                session.refresh(doctor)
                
                # Create audit log
                self._create_audit_log(
                    action='create_doctor',
                    resource_id=doctor.id,
                    user_id=created_by,
                    details={'doctor_name': name, 'hpcsa_number': hpcsa_number},
                    session=session
                )
                
                # Return a detached copy to avoid session issues
                doctor_dict = {
                    'id': doctor.id,
                    'name': doctor.name,
                    'hpcsa_number': doctor.hpcsa_number,
                    'email': doctor.email,
                    'phone': doctor.phone,
                    'practice_name': doctor.practice_name,
                    'specialization': doctor.specialization,
                    'facility_type': doctor.facility_type,
                    'province': doctor.province,
                    'access_level': doctor.access_level,
                    'is_active': doctor.is_active,
                    'notes': doctor.notes,
                    'emergency_contact': doctor.emergency_contact,
                    'created_at': doctor.created_at,
                    'updated_at': doctor.updated_at
                }
                
                # Create a new instance outside the session
                result_doctor = ReferringDoctor(**doctor_dict)
                return result_doctor, []
                
        except Exception as e:
            return None, [f"Database error: {str(e)}"]
    
    def get_doctor_by_id(self, doctor_id: str, session: Session = None) -> Optional[ReferringDoctor]:
        """Get doctor by ID"""
        def _get_doctor(s):
            return s.query(ReferringDoctor).filter(ReferringDoctor.id == doctor_id).first()
        
        if session:
            return _get_doctor(session)
        else:
            with self.db_manager.get_session() as s:
                return _get_doctor(s)
    
    def get_doctor_by_hpcsa(self, hpcsa_number: str, session: Session = None) -> Optional[ReferringDoctor]:
        """Get doctor by HPCSA number"""
        def _get_doctor(s):
            return s.query(ReferringDoctor).filter(
                ReferringDoctor.hpcsa_number == hpcsa_number
            ).first()
        
        if session:
            return _get_doctor(session)
        else:
            with self.db_manager.get_session() as s:
                return _get_doctor(s)
    
    def get_doctor_by_email(self, email: str, session: Session = None) -> Optional[ReferringDoctor]:
        """Get doctor by email"""
        def _get_doctor(s):
            return s.query(ReferringDoctor).filter(
                ReferringDoctor.email == email
            ).first()
        
        if session:
            return _get_doctor(session)
        else:
            with self.db_manager.get_session() as s:
                return _get_doctor(s)
    
    def search_doctors(self, query: str = None, province: str = None,
                      specialization: str = None, access_level: str = None,
                      active_only: bool = True, limit: int = 100,
                      offset: int = 0) -> List[ReferringDoctor]:
        """
        Search doctors with various filters
        """
        try:
            with self.db_manager.get_session() as session:
                q = session.query(ReferringDoctor)
                
                # Apply filters
                if active_only:
                    q = q.filter(ReferringDoctor.is_active == True)
                
                if province:
                    q = q.filter(ReferringDoctor.province == province)
                
                if specialization:
                    q = q.filter(ReferringDoctor.specialization == specialization)
                
                if access_level:
                    q = q.filter(ReferringDoctor.access_level == access_level)
                
                if query:
                    search_term = f"%{query}%"
                    q = q.filter(or_(
                        ReferringDoctor.name.ilike(search_term),
                        ReferringDoctor.hpcsa_number.ilike(search_term),
                        ReferringDoctor.email.ilike(search_term),
                        ReferringDoctor.practice_name.ilike(search_term)
                    ))
                
                # Order and paginate
                q = q.order_by(ReferringDoctor.name)
                if offset:
                    q = q.offset(offset)
                if limit:
                    q = q.limit(limit)
                
                return q.all()
                
        except Exception as e:
            return []
    
    def update_doctor(self, doctor_id: str, updates: Dict[str, Any],
                     updated_by: str = None) -> Tuple[ReferringDoctor, list]:
        """
        Update doctor information
        
        Args:
            doctor_id: Doctor ID
            updates: Dictionary of fields to update
            updated_by: ID of user making the update
        
        Returns:
            Tuple of (doctor, validation_errors)
        """
        try:
            with self.db_manager.get_session() as session:
                doctor = self.get_doctor_by_id(doctor_id, session)
                if not doctor:
                    return None, ["Doctor not found"]
                
                # Store original values for audit
                original_values = {}
                
                # Apply updates
                for field, value in updates.items():
                    if hasattr(doctor, field):
                        original_values[field] = getattr(doctor, field)
                        setattr(doctor, field, value)
                
                # Validate
                errors = doctor.validate()
                if errors:
                    return None, errors
                
                # Check for duplicates if email or HPCSA changed
                if 'hpcsa_number' in updates:
                    existing = self.get_doctor_by_hpcsa(updates['hpcsa_number'], session)
                    if existing and existing.id != doctor_id:
                        return None, [f"HPCSA number {updates['hpcsa_number']} already exists"]
                
                if 'email' in updates:
                    existing = self.get_doctor_by_email(updates['email'], session)
                    if existing and existing.id != doctor_id:
                        return None, [f"Email {updates['email']} already exists"]
                
                # Update last_updated
                doctor.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='update_doctor',
                    resource_id=doctor.id,
                    user_id=updated_by,
                    details={
                        'doctor_name': doctor.name,
                        'updates': updates,
                        'original_values': original_values
                    },
                    session=session
                )
                
                return doctor, []
                
        except Exception as e:
            return None, [f"Database error: {str(e)}"]
    
    def deactivate_doctor(self, doctor_id: str, deactivated_by: str = None,
                         reason: str = None) -> Tuple[bool, list]:
        """
        Deactivate a doctor (soft delete)
        """
        try:
            with self.db_manager.get_session() as session:
                doctor = self.get_doctor_by_id(doctor_id, session)
                if not doctor:
                    return False, ["Doctor not found"]
                
                if not doctor.is_active:
                    return False, ["Doctor is already deactivated"]
                
                # Check for active authorizations
                active_auth_count = session.query(PatientAuthorization).filter(
                    and_(
                        PatientAuthorization.doctor_id == doctor_id,
                        PatientAuthorization.is_active == True,
                        or_(
                            PatientAuthorization.expires_at.is_(None),
                            PatientAuthorization.expires_at > datetime.utcnow()
                        )
                    )
                ).count()
                
                if active_auth_count > 0:
                    return False, [f"Cannot deactivate doctor with {active_auth_count} active patient authorizations"]
                
                # Deactivate
                doctor.is_active = False
                doctor.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='deactivate_doctor',
                    resource_id=doctor.id,
                    user_id=deactivated_by,
                    details={
                        'doctor_name': doctor.name,
                        'hpcsa_number': doctor.hpcsa_number,
                        'reason': reason
                    },
                    session=session
                )
                
                return True, []
                
        except Exception as e:
            return False, [f"Database error: {str(e)}"]
    
    def reactivate_doctor(self, doctor_id: str, reactivated_by: str = None) -> Tuple[bool, list]:
        """
        Reactivate a deactivated doctor
        """
        try:
            with self.db_manager.get_session() as session:
                doctor = self.get_doctor_by_id(doctor_id, session)
                if not doctor:
                    return False, ["Doctor not found"]
                
                if doctor.is_active:
                    return False, ["Doctor is already active"]
                
                doctor.is_active = True
                doctor.last_updated = datetime.utcnow()
                
                session.commit()
                
                # Create audit log
                self._create_audit_log(
                    action='reactivate_doctor',
                    resource_id=doctor.id,
                    user_id=reactivated_by,
                    details={
                        'doctor_name': doctor.name,
                        'hpcsa_number': doctor.hpcsa_number
                    },
                    session=session
                )
                
                return True, []
                
        except Exception as e:
            return False, [f"Database error: {str(e)}"]
    
    def get_doctor_statistics(self, doctor_id: str) -> Dict[str, Any]:
        """
        Get statistics for a doctor
        """
        try:
            with self.db_manager.get_session() as session:
                doctor = self.get_doctor_by_id(doctor_id, session)
                if not doctor:
                    return {}
                
                # Count referrals
                total_referrals = session.query(PatientReferral).filter(
                    PatientReferral.referring_doctor_id == doctor_id
                ).count()
                
                active_referrals = session.query(PatientReferral).filter(
                    and_(
                        PatientReferral.referring_doctor_id == doctor_id,
                        PatientReferral.status.in_(['pending', 'in_progress', 'reviewed'])
                    )
                ).count()
                
                # Count authorizations
                total_authorizations = session.query(PatientAuthorization).filter(
                    PatientAuthorization.doctor_id == doctor_id
                ).count()
                
                active_authorizations = session.query(PatientAuthorization).filter(
                    and_(
                        PatientAuthorization.doctor_id == doctor_id,
                        PatientAuthorization.is_active == True,
                        or_(
                            PatientAuthorization.expires_at.is_(None),
                            PatientAuthorization.expires_at > datetime.utcnow()
                        )
                    )
                ).count()
                
                # Last activity
                last_referral = session.query(PatientReferral).filter(
                    PatientReferral.referring_doctor_id == doctor_id
                ).order_by(desc(PatientReferral.created_at)).first()
                
                last_auth = session.query(PatientAuthorization).filter(
                    PatientAuthorization.doctor_id == doctor_id
                ).order_by(desc(PatientAuthorization.created_at)).first()
                
                last_activity = None
                if last_referral and last_auth:
                    last_activity = max(last_referral.created_at, last_auth.created_at)
                elif last_referral:
                    last_activity = last_referral.created_at
                elif last_auth:
                    last_activity = last_auth.created_at
                
                return {
                    'doctor_id': doctor_id,
                    'doctor_name': doctor.name,
                    'hpcsa_number': doctor.hpcsa_number,
                    'is_active': doctor.is_active,
                    'total_referrals': total_referrals,
                    'active_referrals': active_referrals,
                    'total_authorizations': total_authorizations,
                    'active_authorizations': active_authorizations,
                    'last_activity': last_activity.isoformat() if last_activity else None,
                    'created_at': doctor.created_at.isoformat() if doctor.created_at else None
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def get_doctors_by_province(self, province: str) -> List[ReferringDoctor]:
        """Get all active doctors in a province"""
        try:
            with self.db_manager.get_session() as session:
                return session.query(ReferringDoctor).filter(
                    and_(
                        ReferringDoctor.province == province,
                        ReferringDoctor.is_active == True
                    )
                ).order_by(ReferringDoctor.name).all()
        except Exception:
            return []
    
    def get_doctors_by_access_level(self, access_level: str) -> List[ReferringDoctor]:
        """Get all doctors with specific access level"""
        try:
            with self.db_manager.get_session() as session:
                return session.query(ReferringDoctor).filter(
                    and_(
                        ReferringDoctor.access_level == access_level,
                        ReferringDoctor.is_active == True
                    )
                ).order_by(ReferringDoctor.name).all()
        except Exception:
            return []
    
    def validate_hpcsa_number(self, hpcsa_number: str) -> bool:
        """Validate HPCSA number format"""
        return ReferringDoctor.validate_hpcsa_number(hpcsa_number)
    
    def validate_sa_phone_number(self, phone: str) -> bool:
        """Validate South African phone number"""
        return ReferringDoctor.validate_sa_phone_number(phone)
    
    def _create_audit_log(self, action: str, resource_id: str, user_id: str = None,
                         details: Dict[str, Any] = None, session: Session = None):
        """Create audit log entry"""
        if not session:
            return
        
        try:
            audit_log = AuditLog(
                user_id=user_id,
                user_type='admin',  # Assume admin for doctor management
                action=action,
                resource_type='doctor',
                resource_id=resource_id,
                compliance_category='hpcsa'
            )
            
            if details:
                audit_log.set_details(details)
            
            session.add(audit_log)
            # Don't commit here - let parent transaction handle it
            
        except Exception:
            # Don't fail the main operation if audit logging fails
            pass
