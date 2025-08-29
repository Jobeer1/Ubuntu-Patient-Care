#!/usr/bin/env python3
"""
🔄 SA Healthcare Data Migration Utilities
Comprehensive data migration system for moving Flask app data to Orthanc database
"""

import sqlite3
import json
import logging
import os
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import traceback
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class SADataMigrationUtilities:
    """Comprehensive data migration utilities for SA healthcare system"""
    
    def __init__(self, flask_db_path: str, orthanc_db_path: str, backup_dir: str = "migration_backups"):
        self.flask_db_path = flask_db_path
        self.orthanc_db_path = orthanc_db_path
        self.backup_dir = backup_dir
        self.migration_log = []
        self.rollback_data = {}
        
        # Ensure backup directory exists
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        
        # Migration statistics
        self.stats = {
            'users_migrated': 0,
            'healthcare_professionals_migrated': 0,
            'patients_migrated': 0,
            'medical_aid_records_migrated': 0,
            'audit_logs_migrated': 0,
            'errors': 0,
            'warnings': 0,
            'start_time': None,
            'end_time': None,
            'total_duration': 0
        }
    
    def create_backup(self, description: str = "Pre-migration backup") -> str:
        """Create backup of both databases before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_id)
        
        try:
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup Flask database
            if os.path.exists(self.flask_db_path):
                flask_backup = os.path.join(backup_path, "flask_db_backup.db")
                shutil.copy2(self.flask_db_path, flask_backup)
                logger.info(f"Flask database backed up to: {flask_backup}")
            
            # Backup Orthanc database
            if os.path.exists(self.orthanc_db_path):
                orthanc_backup = os.path.join(backup_path, "orthanc_db_backup.db")
                shutil.copy2(self.orthanc_db_path, orthanc_backup)
                logger.info(f"Orthanc database backed up to: {orthanc_backup}")
            
            # Create backup metadata
            metadata = {
                'backup_id': backup_id,
                'description': description,
                'created_at': datetime.now().isoformat(),
                'flask_db_path': self.flask_db_path,
                'orthanc_db_path': self.orthanc_db_path,
                'flask_db_size': os.path.getsize(self.flask_db_path) if os.path.exists(self.flask_db_path) else 0,
                'orthanc_db_size': os.path.getsize(self.orthanc_db_path) if os.path.exists(self.orthanc_db_path) else 0
            }
            
            metadata_file = os.path.join(backup_path, "backup_metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Backup created successfully: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def validate_databases(self) -> Dict[str, Any]:
        """Validate both databases before migration"""
        validation_results = {
            'flask_db_valid': False,
            'orthanc_db_valid': False,
            'flask_db_tables': [],
            'orthanc_db_tables': [],
            'flask_db_records': {},
            'orthanc_db_records': {},
            'errors': []
        }
        
        try:
            # Validate Flask database
            if os.path.exists(self.flask_db_path):
                with sqlite3.connect(self.flask_db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Get table list
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    flask_tables = [row[0] for row in cursor.fetchall()]
                    validation_results['flask_db_tables'] = flask_tables
                    
                    # Count records in each table
                    for table in flask_tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cursor.fetchone()[0]
                            validation_results['flask_db_records'][table] = count
                        except Exception as e:
                            validation_results['errors'].append(f"Error counting records in {table}: {e}")
                    
                    validation_results['flask_db_valid'] = True
                    logger.info(f"Flask database validation successful. Tables: {len(flask_tables)}")
            else:
                validation_results['errors'].append(f"Flask database not found: {self.flask_db_path}")
            
            # Validate Orthanc database
            if os.path.exists(self.orthanc_db_path):
                with sqlite3.connect(self.orthanc_db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Get table list
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    orthanc_tables = [row[0] for row in cursor.fetchall()]
                    validation_results['orthanc_db_tables'] = orthanc_tables
                    
                    # Count records in each table
                    for table in orthanc_tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cursor.fetchone()[0]
                            validation_results['orthanc_db_records'][table] = count
                        except Exception as e:
                            validation_results['errors'].append(f"Error counting records in {table}: {e}")
                    
                    validation_results['orthanc_db_valid'] = True
                    logger.info(f"Orthanc database validation successful. Tables: {len(orthanc_tables)}")
            else:
                validation_results['errors'].append(f"Orthanc database not found: {self.orthanc_db_path}")
            
            return validation_results
            
        except Exception as e:
            validation_results['errors'].append(f"Database validation error: {e}")
            logger.error(f"Database validation failed: {e}")
            return validation_results
    
    def migrate_users(self) -> Dict[str, Any]:
        """Migrate user accounts from Flask to Orthanc database"""
        migration_result = {
            'success': False,
            'migrated_count': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            with sqlite3.connect(self.flask_db_path) as flask_conn:
                flask_conn.row_factory = sqlite3.Row
                flask_cursor = flask_conn.cursor()
                
                with sqlite3.connect(self.orthanc_db_path) as orthanc_conn:
                    orthanc_cursor = orthanc_conn.cursor()
                    
                    # Get users from Flask database
                    flask_cursor.execute("""
                        SELECT * FROM users 
                        WHERE is_active = 1 AND is_deleted = 0
                    """)
                    
                    users = flask_cursor.fetchall()
                    logger.info(f"Found {len(users)} users to migrate")
                    
                    for user in users:
                        try:
                            # Check if user already exists in Orthanc database
                            orthanc_cursor.execute("""
                                SELECT id FROM sa_users WHERE username = ? OR email = ?
                            """, (user['username'], user['email']))
                            
                            existing_user = orthanc_cursor.fetchone()
                            if existing_user:
                                migration_result['warnings'].append(f"User {user['username']} already exists, skipping")
                                continue
                            
                            # Insert user into Orthanc database
                            orthanc_cursor.execute("""
                                INSERT INTO sa_users (
                                    username, email, password_hash, full_name, role,
                                    hpcsa_number, is_2fa_enabled, preferred_language,
                                    created_at, updated_at, is_active, is_deleted,
                                    last_login, login_count, metadata
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                user['username'],
                                user['email'],
                                user['password_hash'],
                                user['full_name'],
                                user['role'],
                                user.get('hpcsa_number'),
                                user.get('is_2fa_enabled', 0),
                                user.get('preferred_language', 'en'),
                                user['created_at'],
                                user['updated_at'],
                                user['is_active'],
                                user['is_deleted'],
                                user.get('last_login'),
                                user.get('login_count', 0),
                                json.dumps({'migrated_from_flask': True, 'migration_date': datetime.now().isoformat()})
                            ))
                            
                            migration_result['migrated_count'] += 1
                            self.stats['users_migrated'] += 1
                            
                        except Exception as e:
                            error_msg = f"Error migrating user {user['username']}: {e}"
                            migration_result['errors'].append(error_msg)
                            logger.error(error_msg)
                            self.stats['errors'] += 1
                    
                    orthanc_conn.commit()
                    migration_result['success'] = True
                    logger.info(f"Successfully migrated {migration_result['migrated_count']} users")
            
            return migration_result
            
        except Exception as e:
            error_msg = f"User migration failed: {e}"
            migration_result['errors'].append(error_msg)
            logger.error(error_msg)
            return migration_result
    
    def migrate_healthcare_professionals(self) -> Dict[str, Any]:
        """Migrate healthcare professionals from Flask to Orthanc database"""
        migration_result = {
            'success': False,
            'migrated_count': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            with sqlite3.connect(self.flask_db_path) as flask_conn:
                flask_conn.row_factory = sqlite3.Row
                flask_cursor = flask_conn.cursor()
                
                with sqlite3.connect(self.orthanc_db_path) as orthanc_conn:
                    orthanc_cursor = orthanc_conn.cursor()
                    
                    # Get healthcare professionals from Flask database
                    flask_cursor.execute("""
                        SELECT * FROM healthcare_professionals 
                        WHERE is_active = 1 AND is_deleted = 0
                    """)
                    
                    professionals = flask_cursor.fetchall()
                    logger.info(f"Found {len(professionals)} healthcare professionals to migrate")
                    
                    for professional in professionals:
                        try:
                            # Check if professional already exists
                            orthanc_cursor.execute("""
                                SELECT id FROM sa_healthcare_professionals 
                                WHERE hpcsa_number = ?
                            """, (professional['hpcsa_number'],))
                            
                            existing_professional = orthanc_cursor.fetchone()
                            if existing_professional:
                                migration_result['warnings'].append(f"Professional {professional['hpcsa_number']} already exists, skipping")
                                continue
                            
                            # Insert professional into Orthanc database
                            orthanc_cursor.execute("""
                                INSERT INTO sa_healthcare_professionals (
                                    hpcsa_number, first_name, last_name, middle_names,
                                    email, phone_primary, phone_secondary,
                                    registration_category, registration_status, specialization,
                                    province_code, practice_city, practice_address,
                                    initial_registration_date, current_registration_date,
                                    primary_qualification, practice_type, practice_name,
                                    hpcsa_validation_status, hpcsa_validation_date,
                                    created_at, updated_at, created_by, is_active, is_deleted,
                                    metadata
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                professional['hpcsa_number'],
                                professional['first_name'],
                                professional['last_name'],
                                professional.get('middle_names'),
                                professional.get('email'),
                                professional.get('phone_primary'),
                                professional.get('phone_secondary'),
                                professional['registration_category'],
                                professional.get('registration_status', 'ACTIVE'),
                                professional.get('specialization'),
                                professional['province_code'],
                                professional.get('practice_city'),
                                professional.get('practice_address'),
                                professional.get('initial_registration_date'),
                                professional.get('current_registration_date'),
                                professional.get('primary_qualification'),
                                professional.get('practice_type'),
                                professional.get('practice_name'),
                                'VALIDATED',  # Assume migrated data is validated
                                datetime.now().isoformat(),
                                professional['created_at'],
                                professional['updated_at'],
                                'MIGRATION_SYSTEM',
                                professional['is_active'],
                                professional['is_deleted'],
                                json.dumps({'migrated_from_flask': True, 'migration_date': datetime.now().isoformat()})
                            ))
                            
                            migration_result['migrated_count'] += 1
                            self.stats['healthcare_professionals_migrated'] += 1
                            
                        except Exception as e:
                            error_msg = f"Error migrating professional {professional['hpcsa_number']}: {e}"
                            migration_result['errors'].append(error_msg)
                            logger.error(error_msg)
                            self.stats['errors'] += 1
                    
                    orthanc_conn.commit()
                    migration_result['success'] = True
                    logger.info(f"Successfully migrated {migration_result['migrated_count']} healthcare professionals")
            
            return migration_result
            
        except Exception as e:
            error_msg = f"Healthcare professionals migration failed: {e}"
            migration_result['errors'].append(error_msg)
            logger.error(error_msg)
            return migration_result
    
    def migrate_patients(self) -> Dict[str, Any]:
        """Migrate patient data from Flask to Orthanc database"""
        migration_result = {
            'success': False,
            'migrated_count': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            with sqlite3.connect(self.flask_db_path) as flask_conn:
                flask_conn.row_factory = sqlite3.Row
                flask_cursor = flask_conn.cursor()
                
                with sqlite3.connect(self.orthanc_db_path) as orthanc_conn:
                    orthanc_cursor = orthanc_conn.cursor()
                    
                    # Get patients from Flask database
                    flask_cursor.execute("""
                        SELECT * FROM patients 
                        WHERE is_active = 1 AND is_deleted = 0
                    """)
                    
                    patients = flask_cursor.fetchall()
                    logger.info(f"Found {len(patients)} patients to migrate")
                    
                    for patient in patients:
                        try:
                            # Check if patient already exists
                            orthanc_cursor.execute("""
                                SELECT id FROM sa_patients 
                                WHERE sa_id_number = ? OR patient_id = ?
                            """, (patient.get('sa_id_number'), patient['patient_id']))
                            
                            existing_patient = orthanc_cursor.fetchone()
                            if existing_patient:
                                migration_result['warnings'].append(f"Patient {patient['patient_id']} already exists, skipping")
                                continue
                            
                            # Insert patient into Orthanc database
                            orthanc_cursor.execute("""
                                INSERT INTO sa_patients (
                                    patient_id, sa_id_number, first_name, last_name,
                                    date_of_birth, gender, phone_number, email,
                                    address, medical_scheme_code, medical_scheme_number,
                                    preferred_language, popia_consent_given, popia_consent_date,
                                    emergency_contact_name, emergency_contact_phone,
                                    created_at, updated_at, is_active, is_deleted,
                                    metadata
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                patient['patient_id'],
                                patient.get('sa_id_number'),
                                patient['first_name'],
                                patient['last_name'],
                                patient.get('date_of_birth'),
                                patient.get('gender'),
                                patient.get('phone_number'),
                                patient.get('email'),
                                patient.get('address'),
                                patient.get('medical_scheme_code'),
                                patient.get('medical_scheme_number'),
                                patient.get('preferred_language', 'en'),
                                patient.get('popia_consent_given', 0),
                                patient.get('popia_consent_date'),
                                patient.get('emergency_contact_name'),
                                patient.get('emergency_contact_phone'),
                                patient['created_at'],
                                patient['updated_at'],
                                patient['is_active'],
                                patient['is_deleted'],
                                json.dumps({'migrated_from_flask': True, 'migration_date': datetime.now().isoformat()})
                            ))
                            
                            migration_result['migrated_count'] += 1
                            self.stats['patients_migrated'] += 1
                            
                        except Exception as e:
                            error_msg = f"Error migrating patient {patient['patient_id']}: {e}"
                            migration_result['errors'].append(error_msg)
                            logger.error(error_msg)
                            self.stats['errors'] += 1
                    
                    orthanc_conn.commit()
                    migration_result['success'] = True
                    logger.info(f"Successfully migrated {migration_result['migrated_count']} patients")
            
            return migration_result
            
        except Exception as e:
            error_msg = f"Patient migration failed: {e}"
            migration_result['errors'].append(error_msg)
            logger.error(error_msg)
            return migration_result
    
    def migrate_audit_logs(self) -> Dict[str, Any]:
        """Migrate audit logs from Flask to Orthanc database"""
        migration_result = {
            'success': False,
            'migrated_count': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            with sqlite3.connect(self.flask_db_path) as flask_conn:
                flask_conn.row_factory = sqlite3.Row
                flask_cursor = flask_conn.cursor()
                
                with sqlite3.connect(self.orthanc_db_path) as orthanc_conn:
                    orthanc_cursor = orthanc_conn.cursor()
                    
                    # Get audit logs from Flask database (last 6 months only to avoid overwhelming)
                    cutoff_date = (datetime.now() - timedelta(days=180)).isoformat()
                    flask_cursor.execute("""
                        SELECT * FROM audit_logs 
                        WHERE created_at >= ?
                        ORDER BY created_at DESC
                    """, (cutoff_date,))
                    
                    audit_logs = flask_cursor.fetchall()
                    logger.info(f"Found {len(audit_logs)} audit logs to migrate (last 6 months)")
                    
                    for log in audit_logs:
                        try:
                            # Generate UUID for audit log
                            audit_uuid = hashlib.md5(f"{log['id']}{log['created_at']}{log['action']}".encode()).hexdigest()
                            
                            # Map Flask audit log to Orthanc audit log format
                            orthanc_cursor.execute("""
                                INSERT INTO sa_audit_log (
                                    audit_uuid, category_code, event_type, action,
                                    user_id, username, user_role, ip_address,
                                    resource_type, resource_id, description,
                                    event_timestamp, contains_phi, contains_pii,
                                    application_name, created_by, metadata
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                audit_uuid,
                                self._map_audit_category(log.get('action', 'UNKNOWN')),
                                'MIGRATED_EVENT',
                                log.get('action', 'UNKNOWN'),
                                log.get('user_id'),
                                log.get('username'),
                                log.get('user_role'),
                                log.get('ip_address'),
                                log.get('resource_type'),
                                log.get('resource_id'),
                                log.get('description'),
                                log['created_at'],
                                1 if log.get('contains_phi', 0) else 0,
                                1 if log.get('contains_pii', 0) else 0,
                                'FLASK_LEGACY',
                                'MIGRATION_SYSTEM',
                                json.dumps({
                                    'migrated_from_flask': True,
                                    'original_id': log['id'],
                                    'migration_date': datetime.now().isoformat()
                                })
                            ))
                            
                            migration_result['migrated_count'] += 1
                            self.stats['audit_logs_migrated'] += 1
                            
                        except Exception as e:
                            error_msg = f"Error migrating audit log {log['id']}: {e}"
                            migration_result['errors'].append(error_msg)
                            logger.error(error_msg)
                            self.stats['errors'] += 1
                    
                    orthanc_conn.commit()
                    migration_result['success'] = True
                    logger.info(f"Successfully migrated {migration_result['migrated_count']} audit logs")
            
            return migration_result
            
        except Exception as e:
            error_msg = f"Audit log migration failed: {e}"
            migration_result['errors'].append(error_msg)
            logger.error(error_msg)
            return migration_result
    
    def _map_audit_category(self, flask_action: str) -> str:
        """Map Flask audit actions to Orthanc audit categories"""
        action_mapping = {
            'LOGIN': 'AUTH_LOGIN',
            'LOGOUT': 'AUTH_LOGOUT',
            'FAILED_LOGIN': 'AUTH_FAILED',
            'VIEW_PATIENT': 'DATA_VIEW',
            'CREATE_PATIENT': 'DATA_CREATE',
            'UPDATE_PATIENT': 'DATA_UPDATE',
            'DELETE_PATIENT': 'DATA_DELETE',
            'VIEW_STUDY': 'DATA_VIEW',
            'DICOM_UPLOAD': 'DICOM_STORE',
            'DICOM_DOWNLOAD': 'DICOM_RETRIEVE',
            'SYSTEM_CONFIG': 'SYSTEM_CONFIG',
            'USER_ADMIN': 'ADMIN_USER'
        }
        
        return action_mapping.get(flask_action, 'SYSTEM_MAINTENANCE')
    
    def validate_migration_integrity(self) -> Dict[str, Any]:
        """Validate data integrity after migration"""
        validation_result = {
            'success': True,
            'checks_passed': 0,
            'checks_failed': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            with sqlite3.connect(self.flask_db_path) as flask_conn:
                flask_cursor = flask_conn.cursor()
                
                with sqlite3.connect(self.orthanc_db_path) as orthanc_conn:
                    orthanc_cursor = orthanc_conn.cursor()
                    
                    # Check user count consistency
                    flask_cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND is_deleted = 0")
                    flask_user_count = flask_cursor.fetchone()[0]
                    
                    orthanc_cursor.execute("SELECT COUNT(*) FROM sa_users WHERE is_active = 1 AND is_deleted = 0")
                    orthanc_user_count = orthanc_cursor.fetchone()[0]
                    
                    if flask_user_count <= orthanc_user_count:
                        validation_result['checks_passed'] += 1
                        logger.info(f"User count validation passed: Flask={flask_user_count}, Orthanc={orthanc_user_count}")
                    else:
                        validation_result['checks_failed'] += 1
                        validation_result['errors'].append(f"User count mismatch: Flask={flask_user_count}, Orthanc={orthanc_user_count}")
                    
                    # Check healthcare professionals count
                    flask_cursor.execute("SELECT COUNT(*) FROM healthcare_professionals WHERE is_active = 1 AND is_deleted = 0")
                    flask_prof_count = flask_cursor.fetchone()[0]
                    
                    orthanc_cursor.execute("SELECT COUNT(*) FROM sa_healthcare_professionals WHERE is_active = 1 AND is_deleted = 0")
                    orthanc_prof_count = orthanc_cursor.fetchone()[0]
                    
                    if flask_prof_count <= orthanc_prof_count:
                        validation_result['checks_passed'] += 1
                        logger.info(f"Healthcare professionals count validation passed: Flask={flask_prof_count}, Orthanc={orthanc_prof_count}")
                    else:
                        validation_result['checks_failed'] += 1
                        validation_result['errors'].append(f"Healthcare professionals count mismatch: Flask={flask_prof_count}, Orthanc={orthanc_prof_count}")
                    
                    # Check patients count
                    flask_cursor.execute("SELECT COUNT(*) FROM patients WHERE is_active = 1 AND is_deleted = 0")
                    flask_patient_count = flask_cursor.fetchone()[0]
                    
                    orthanc_cursor.execute("SELECT COUNT(*) FROM sa_patients WHERE is_active = 1 AND is_deleted = 0")
                    orthanc_patient_count = orthanc_cursor.fetchone()[0]
                    
                    if flask_patient_count <= orthanc_patient_count:
                        validation_result['checks_passed'] += 1
                        logger.info(f"Patient count validation passed: Flask={flask_patient_count}, Orthanc={orthanc_patient_count}")
                    else:
                        validation_result['checks_failed'] += 1
                        validation_result['errors'].append(f"Patient count mismatch: Flask={flask_patient_count}, Orthanc={orthanc_patient_count}")
                    
                    # Validate data integrity (check for required fields)
                    orthanc_cursor.execute("SELECT COUNT(*) FROM sa_users WHERE username IS NULL OR email IS NULL")
                    invalid_users = orthanc_cursor.fetchone()[0]
                    
                    if invalid_users == 0:
                        validation_result['checks_passed'] += 1
                        logger.info("User data integrity validation passed")
                    else:
                        validation_result['checks_failed'] += 1
                        validation_result['errors'].append(f"Found {invalid_users} users with missing required fields")
                    
                    # Check for duplicate HPCSA numbers
                    orthanc_cursor.execute("""
                        SELECT hpcsa_number, COUNT(*) as count 
                        FROM sa_healthcare_professionals 
                        WHERE hpcsa_number IS NOT NULL 
                        GROUP BY hpcsa_number 
                        HAVING COUNT(*) > 1
                    """)
                    
                    duplicate_hpcsa = orthanc_cursor.fetchall()
                    if len(duplicate_hpcsa) == 0:
                        validation_result['checks_passed'] += 1
                        logger.info("HPCSA number uniqueness validation passed")
                    else:
                        validation_result['checks_failed'] += 1
                        validation_result['errors'].append(f"Found {len(duplicate_hpcsa)} duplicate HPCSA numbers")
                    
                    validation_result['success'] = validation_result['checks_failed'] == 0
                    
            return validation_result
            
        except Exception as e:
            validation_result['success'] = False
            validation_result['errors'].append(f"Validation error: {e}")
            logger.error(f"Migration validation failed: {e}")
            return validation_result
    
    def create_rollback_plan(self, backup_id: str) -> Dict[str, Any]:
        """Create rollback plan for migration"""
        rollback_plan = {
            'backup_id': backup_id,
            'rollback_steps': [
                'Stop Orthanc service',
                'Restore Orthanc database from backup',
                'Restore Flask database from backup',
                'Restart services',
                'Validate rollback'
            ],
            'rollback_scripts': [],
            'estimated_time_minutes': 15,
            'created_at': datetime.now().isoformat()
        }
        
        # Save rollback plan
        rollback_file = os.path.join(self.backup_dir, backup_id, "rollback_plan.json")
        with open(rollback_file, 'w') as f:
            json.dump(rollback_plan, f, indent=2)
        
        logger.info(f"Rollback plan created: {rollback_file}")
        return rollback_plan
    
    def execute_full_migration(self) -> Dict[str, Any]:
        """Execute complete migration process"""
        self.stats['start_time'] = datetime.now()
        
        migration_report = {
            'success': False,
            'backup_id': None,
            'migration_steps': [],
            'total_errors': 0,
            'total_warnings': 0,
            'duration_seconds': 0,
            'statistics': {}
        }
        
        try:
            logger.info("Starting SA Healthcare data migration...")
            
            # Step 1: Create backup
            logger.info("Step 1: Creating backup...")
            backup_id = self.create_backup("Full migration backup")
            migration_report['backup_id'] = backup_id
            migration_report['migration_steps'].append({'step': 'backup', 'status': 'completed', 'timestamp': datetime.now().isoformat()})
            
            # Step 2: Validate databases
            logger.info("Step 2: Validating databases...")
            validation_result = self.validate_databases()
            if not validation_result['flask_db_valid'] or not validation_result['orthanc_db_valid']:
                raise Exception("Database validation failed")
            migration_report['migration_steps'].append({'step': 'validation', 'status': 'completed', 'timestamp': datetime.now().isoformat()})
            
            # Step 3: Migrate users
            logger.info("Step 3: Migrating users...")
            user_result = self.migrate_users()
            migration_report['total_errors'] += len(user_result['errors'])
            migration_report['total_warnings'] += len(user_result['warnings'])
            migration_report['migration_steps'].append({'step': 'users', 'status': 'completed' if user_result['success'] else 'failed', 'timestamp': datetime.now().isoformat()})
            
            # Step 4: Migrate healthcare professionals
            logger.info("Step 4: Migrating healthcare professionals...")
            prof_result = self.migrate_healthcare_professionals()
            migration_report['total_errors'] += len(prof_result['errors'])
            migration_report['total_warnings'] += len(prof_result['warnings'])
            migration_report['migration_steps'].append({'step': 'healthcare_professionals', 'status': 'completed' if prof_result['success'] else 'failed', 'timestamp': datetime.now().isoformat()})
            
            # Step 5: Migrate patients
            logger.info("Step 5: Migrating patients...")
            patient_result = self.migrate_patients()
            migration_report['total_errors'] += len(patient_result['errors'])
            migration_report['total_warnings'] += len(patient_result['warnings'])
            migration_report['migration_steps'].append({'step': 'patients', 'status': 'completed' if patient_result['success'] else 'failed', 'timestamp': datetime.now().isoformat()})
            
            # Step 6: Migrate audit logs
            logger.info("Step 6: Migrating audit logs...")
            audit_result = self.migrate_audit_logs()
            migration_report['total_errors'] += len(audit_result['errors'])
            migration_report['total_warnings'] += len(audit_result['warnings'])
            migration_report['migration_steps'].append({'step': 'audit_logs', 'status': 'completed' if audit_result['success'] else 'failed', 'timestamp': datetime.now().isoformat()})
            
            # Step 7: Validate migration integrity
            logger.info("Step 7: Validating migration integrity...")
            integrity_result = self.validate_migration_integrity()
            if not integrity_result['success']:
                migration_report['total_errors'] += len(integrity_result['errors'])
                migration_report['total_warnings'] += len(integrity_result['warnings'])
            migration_report['migration_steps'].append({'step': 'integrity_validation', 'status': 'completed' if integrity_result['success'] else 'failed', 'timestamp': datetime.now().isoformat()})
            
            # Step 8: Create rollback plan
            logger.info("Step 8: Creating rollback plan...")
            rollback_plan = self.create_rollback_plan(backup_id)
            migration_report['migration_steps'].append({'step': 'rollback_plan', 'status': 'completed', 'timestamp': datetime.now().isoformat()})
            
            # Calculate final statistics
            self.stats['end_time'] = datetime.now()
            self.stats['total_duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            migration_report['success'] = migration_report['total_errors'] == 0
            migration_report['duration_seconds'] = self.stats['total_duration']
            migration_report['statistics'] = self.stats
            
            # Save migration report
            report_file = os.path.join(self.backup_dir, backup_id, "migration_report.json")
            with open(report_file, 'w') as f:
                json.dump(migration_report, f, indent=2, default=str)
            
            if migration_report['success']:
                logger.info(f"Migration completed successfully in {self.stats['total_duration']:.2f} seconds")
            else:
                logger.warning(f"Migration completed with {migration_report['total_errors']} errors and {migration_report['total_warnings']} warnings")
            
            return migration_report
            
        except Exception as e:
            self.stats['end_time'] = datetime.now()
            self.stats['total_duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            migration_report['success'] = False
            migration_report['total_errors'] += 1
            migration_report['duration_seconds'] = self.stats['total_duration']
            migration_report['statistics'] = self.stats
            
            error_msg = f"Migration failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            return migration_report


def main():
    """Main migration execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SA Healthcare Data Migration Utilities')
    parser.add_argument('--flask-db', required=True, help='Path to Flask database')
    parser.add_argument('--orthanc-db', required=True, help='Path to Orthanc database')
    parser.add_argument('--backup-dir', default='migration_backups', help='Backup directory')
    parser.add_argument('--action', choices=['validate', 'migrate', 'backup'], default='migrate', help='Action to perform')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('sa_migration.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create migration utility
    migrator = SADataMigrationUtilities(args.flask_db, args.orthanc_db, args.backup_dir)
    
    try:
        if args.action == 'validate':
            print("🔍 Validating databases...")
            result = migrator.validate_databases()
            print(json.dumps(result, indent=2))
            
        elif args.action == 'backup':
            print("💾 Creating backup...")
            backup_id = migrator.create_backup("Manual backup")
            print(f"✅ Backup created: {backup_id}")
            
        elif args.action == 'migrate':
            print("🚀 Starting full migration...")
            result = migrator.execute_full_migration()
            
            if result['success']:
                print("✅ Migration completed successfully!")
                print(f"📊 Statistics:")
                print(f"  - Users migrated: {result['statistics']['users_migrated']}")
                print(f"  - Healthcare professionals migrated: {result['statistics']['healthcare_professionals_migrated']}")
                print(f"  - Patients migrated: {result['statistics']['patients_migrated']}")
                print(f"  - Audit logs migrated: {result['statistics']['audit_logs_migrated']}")
                print(f"  - Duration: {result['duration_seconds']:.2f} seconds")
                print(f"  - Backup ID: {result['backup_id']}")
            else:
                print("❌ Migration completed with errors!")
                print(f"  - Total errors: {result['total_errors']}")
                print(f"  - Total warnings: {result['total_warnings']}")
                print(f"  - Backup ID: {result['backup_id']}")
                
    except Exception as e:
        print(f"💥 Migration failed: {e}")
        logger.error(f"Migration execution failed: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()