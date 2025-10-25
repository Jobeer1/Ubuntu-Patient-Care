"""
Orthanc Management Database - Base Classes
SQLAlchemy base class and common database components
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Create the base class for all models
Base = declarative_base()

# Re-export from manager for compatibility
from .manager import Base as ManagerBase

# Use the manager's Base class to maintain consistency
Base = ManagerBase

__all__ = ["Base"]
