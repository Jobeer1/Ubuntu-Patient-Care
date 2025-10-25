"""Routes module"""
from .auth import router as auth_router
from .token import router as token_router
from .users import router as users_router
from .audit import router as audit_router
from .access_management import router as access_router
from .user_studies import router as user_studies_router

__all__ = ["auth_router", "token_router", "users_router", "audit_router", "access_router", "user_studies_router"]
