"""
SDOH Chat - Database Initialization
Initialize SQLite database with schema
"""

import os
import sqlite3
from datetime import datetime
try:
    from .models import User
except (ImportError, ValueError):
    from backend.models import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'sdoh_chat.db')

def init_db():
    """Initialize database with schema"""
    from .extensions import db
    from flask_app import app
    with app.app_context():
        db.create_all()
    
    print(f"✓ Database initialized at: {DB_PATH}")
    return True

def get_session():
    """Get database session"""
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == '__main__':
    init_db()
    print("Database ready for SDOH Chat")
