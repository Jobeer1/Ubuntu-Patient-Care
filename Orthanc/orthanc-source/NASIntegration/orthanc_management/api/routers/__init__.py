"""
Orthanc Management API - Router Package
Exports all API routers for inclusion in main application
"""

from .auth import router as auth_router
from .doctors import router as doctors_router
from .authorizations import router as authorizations_router
from .configurations import router as configurations_router
from .dashboard import router as dashboard_router
from .audit import router as audit_router
from .shares import router as shares_router

__all__ = [
    "auth_router",
    "doctors_router", 
    "authorizations_router",
    "configurations_router",
    "dashboard_router",
    "audit_router",
    "shares_router"
]
