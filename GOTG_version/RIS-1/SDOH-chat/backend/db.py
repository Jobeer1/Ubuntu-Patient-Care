"""
SDOH Chat - Database Initialization
Initialize SQLite database with schema
"""

import os
import sqlite3
from datetime import datetime
from RIS-1.SDOH-chat.backend.models import Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'sdoh_chat.db')

def init_db():
    """Initialize database with schema"""
    
    # Create SQLite engine
    engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print(f"✓ Database initialized at: {DB_PATH}")
    return engine

def get_session():
    """Get database session"""
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == '__main__':
    init_db()
    print("Database ready for SDOH Chat")
