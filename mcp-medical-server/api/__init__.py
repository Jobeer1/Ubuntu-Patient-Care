"""
API package initialization

Exports FastAPI application and configuration
"""

from .main import app, Base

__all__ = ["app", "Base"]
