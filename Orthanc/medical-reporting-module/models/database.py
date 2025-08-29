"""
Database initialization and management for Medical Reporting Module
"""

import os
import logging
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logger = logging.getLogger(__name__)

# Create a unified base
Base = declarative_base()

class DatabaseManager:
    """Database manager for Medical Reporting Module"""
    
    def __init__(self, database_url=None):
        """Initialize database manager"""
        self.database_url = database_url or os.environ.get(
            'DATABASE_URL', 
            'sqlite:///medical_reporting.db'
        )
        self.engine = None
        self.session_factory = None
        self.Session = None
        
    def initialize(self):
        """Initialize database connection and create tables"""
        try:
            # Create engine
            self.engine = create_engine(
                self.database_url,
                echo=os.environ.get('SQL_DEBUG', 'false').lower() == 'true',
                pool_pre_ping=True
            )
            
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(self.session_factory)
            
            # Create all tables
            self.create_tables()
            
            logger.info("Database initialized successfully")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def create_tables(self):
        """Create all database tables"""
        try:
            # Import all models to ensure they're registered
            from .report import Report, OfflineChange
            from .template import ReportTemplate, TemplateSection
            from .layout import ScreenLayout, ViewportConfiguration
            from .voice_session import VoiceSession, AudioSegment, VoiceCommand
            
            # Create all tables using unified base
            Base.metadata.create_all(self.engine)
            
            logger.info("Database tables created successfully")
            
        except SQLAlchemyError as e:
            logger.error(f"Table creation failed: {e}")
            raise
    
    def get_session(self):
        """Get a database session"""
        if not self.Session:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.Session()
    
    def close_session(self, session):
        """Close a database session"""
        if session:
            session.close()
    
    def drop_tables(self):
        """Drop all database tables (use with caution)"""
        try:
            Base.metadata.drop_all(self.engine)
            
            logger.info("Database tables dropped successfully")
            
        except SQLAlchemyError as e:
            logger.error(f"Table dropping failed: {e}")
            raise
    
    def reset_database(self):
        """Reset database by dropping and recreating tables"""
        logger.warning("Resetting database - all data will be lost!")
        self.drop_tables()
        self.create_tables()
    
    def get_table_info(self):
        """Get information about database tables"""
        try:
            metadata = MetaData()
            metadata.reflect(bind=self.engine)
            
            table_info = {}
            for table_name in metadata.tables:
                table = metadata.tables[table_name]
                table_info[table_name] = {
                    'columns': [col.name for col in table.columns],
                    'primary_keys': [col.name for col in table.primary_key.columns],
                    'foreign_keys': [
                        {
                            'column': fk.parent.name,
                            'references': f"{fk.column.table.name}.{fk.column.name}"
                        }
                        for fk in table.foreign_keys
                    ]
                }
            
            return table_info
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get table info: {e}")
            return {}

def create_sample_data(db_manager):
    """Create sample data for testing"""
    # Import models here to avoid circular imports
    from .report import Report, OfflineChange
    from .template import ReportTemplate, TemplateSection
    from .layout import ScreenLayout, ViewportConfiguration
    from .voice_session import VoiceSession, AudioSegment, VoiceCommand
    
    session = db_manager.get_session()
    
    try:
        # Create sample templates
        chest_ct_template = ReportTemplate(
            name="CT Chest Standard",
            description="Standard CT chest reporting template",
            category="radiology",
            specialty="thoracic",
            procedure_type="CT Chest",
            voice_commands=["chest ct", "ct chest", "thoracic ct"],
            primary_command="chest ct",
            sections=[
                {
                    "name": "clinical_history",
                    "title": "Clinical History",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "technique",
                    "title": "Technique",
                    "type": "text",
                    "default": "Axial CT images of the chest were obtained"
                },
                {
                    "name": "findings",
                    "title": "Findings",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "impression",
                    "title": "Impression",
                    "type": "text",
                    "required": True
                }
            ],
            default_values={
                "technique": "Axial CT images of the chest were obtained with IV contrast"
            },
            required_fields=["clinical_history", "findings", "impression"],
            created_by="system",
            updated_by="system"
        )
        
        brain_mri_template = ReportTemplate(
            name="MRI Brain Standard",
            description="Standard MRI brain reporting template",
            category="radiology",
            specialty="neuroradiology",
            procedure_type="MRI Brain",
            voice_commands=["brain mri", "mri brain", "neuro mri"],
            primary_command="brain mri",
            sections=[
                {
                    "name": "clinical_history",
                    "title": "Clinical History",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "technique",
                    "title": "Technique",
                    "type": "text",
                    "default": "MRI brain with multiple sequences"
                },
                {
                    "name": "findings",
                    "title": "Findings",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "impression",
                    "title": "Impression",
                    "type": "text",
                    "required": True
                }
            ],
            default_values={
                "technique": "MRI brain performed with T1, T2, FLAIR, and DWI sequences"
            },
            required_fields=["clinical_history", "findings", "impression"],
            created_by="system",
            updated_by="system"
        )
        
        # Create sample layouts
        default_layout = ScreenLayout(
            name="Default 2x2 Layout",
            description="Standard 2x2 viewport layout",
            user_id="system",
            examination_type="general",
            layout_type="preset",
            viewport_config={
                "grid": {"rows": 2, "columns": 2},
                "viewports": [
                    {"index": 0, "position": {"x": 0, "y": 0}, "size": {"width": 50, "height": 50}},
                    {"index": 1, "position": {"x": 50, "y": 0}, "size": {"width": 50, "height": 50}},
                    {"index": 2, "position": {"x": 0, "y": 50}, "size": {"width": 50, "height": 50}},
                    {"index": 3, "position": {"x": 50, "y": 50}, "size": {"width": 50, "height": 50}}
                ]
            },
            panel_arrangement={
                "report_panel": {"position": "right", "width": 300},
                "tools_panel": {"position": "left", "width": 200},
                "status_panel": {"position": "bottom", "height": 100}
            },
            monitor_setup={
                "primary_monitor": {"width": 1920, "height": 1080},
                "secondary_monitor": None
            },
            is_default=True,
            is_system_preset=True,
            created_by="system",
            updated_by="system"
        )
        
        single_viewport_layout = ScreenLayout(
            name="Single Large Viewport",
            description="Single large viewport for detailed viewing",
            user_id="system",
            examination_type="general",
            layout_type="preset",
            viewport_config={
                "grid": {"rows": 1, "columns": 1},
                "viewports": [
                    {"index": 0, "position": {"x": 0, "y": 0}, "size": {"width": 100, "height": 100}}
                ]
            },
            panel_arrangement={
                "report_panel": {"position": "right", "width": 400},
                "tools_panel": {"position": "left", "width": 150}
            },
            monitor_setup={
                "primary_monitor": {"width": 1920, "height": 1080}
            },
            is_system_preset=True,
            created_by="system",
            updated_by="system"
        )
        
        # Add to session
        session.add_all([
            chest_ct_template,
            brain_mri_template,
            default_layout,
            single_viewport_layout
        ])
        
        # Commit changes
        session.commit()
        logger.info("Sample data created successfully")
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Failed to create sample data: {e}")
        raise
    finally:
        db_manager.close_session(session)

# Global database manager instance
db_manager = DatabaseManager()

def init_database(database_url=None, create_sample=False):
    """Initialize database with optional sample data"""
    global db_manager
    
    if database_url:
        db_manager = DatabaseManager(database_url)
    
    success = db_manager.initialize()
    
    if success and create_sample:
        try:
            create_sample_data(db_manager)
        except Exception as e:
            logger.error(f"Failed to create sample data: {e}")
    
    return success

def get_db_session():
    """Get a database session"""
    return db_manager.get_session()

def close_db_session(session):
    """Close a database session"""
    db_manager.close_session(session)

def init_db(database_url=None, create_sample=False):
    """Legacy function name for backward compatibility"""
    return init_database(database_url, create_sample)

# Legacy alias for backward compatibility
db = db_manager