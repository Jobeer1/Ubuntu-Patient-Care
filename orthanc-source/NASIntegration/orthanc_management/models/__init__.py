"""
Orthanc Management Models
Comprehensive data models for the Orthanc Management Module
"""

# Import all models
from .referring_doctor import ReferringDoctor
from .patient_referral import PatientReferral

# Import database schema components
from ..database.schema import Base, DatabaseCompatibleMixin

# Import these when the remaining models are created
# from .patient_authorization import PatientAuthorization
# from .patient_share import PatientShare
# from .orthanc_config import OrthancConfig
# from .audit_log import AuditLog

# Export all models
__all__ = [
    'Base',
    'DatabaseCompatibleMixin',
    'ReferringDoctor',
    'PatientReferral',
    # 'PatientAuthorization',
    # 'PatientShare', 
    # 'OrthancConfig',
    # 'AuditLog'
]
