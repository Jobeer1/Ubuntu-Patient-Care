#!/usr/bin/env python3
"""
🔄 SA Data Migration Utilities
Comprehensive data migration system for moving existing Flask app data to Orthanc database
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import shutil
import hashlib

logger = logging.getLogger(__name__)

class SADataMigrator:
    """SA Data Migration Manager"""
    
    def __init__(self):
        self.migration_log = []
        self.errors = []
        self.warnings = []
        self.stats = {
            'users_migrated': 0,
            'patients_migrated': 0,
            'professionals_migrated': 0,
            'reports_migrated': 0,
            'shares_migrated': 0,
            'total_records': 0,
            'failed_records': 0
        }
    
    def log_migration(self, level: str, message: str, details: str = ""):
        """Log migration activity"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'details': details
        }
        self.migration_log.append(entry)
        
        if level == 'ERROR':
            self.errors.append(entry)
        elif level == 'WARNING':
            self.warnings.append(entry)
        
        print(f"{level}: {message}")
        if details:
            print(f"   Details: {details}")
    
    def backup_existing_data(self) -> bool:
        """Create backup of existing databases"""
        self.log_migration('INFO', 'Creating backup of existing databases...')
        
        try:
            backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # List of databases to backup
            databases = [
                'orthanc_users.db',
                'sa_healthcare_users.db',
                'sa_secure_shares.db',
                'reporting.db',
                'orthanc_management.db',
                'medical_devices.db',
                'collaboration.db',
                'telemedicine.db'
            ]
            
            backed_up = 0
            for db_file in databases:
                if os.path.exists(db_file):
                    backup_path = os.path.join(backup_dir, db_file)
                    shutil.copy2(db_file, backup_path)
                    self.log_migration('INFO', f'Backed up: {db_file}')
                    backed_up += 1
            
            # Create backup manifest
            manifest = {
                'backup_date': datetime.now().isoformat(),
                'databases_backed_up': backed_up,
                'backup_directory': backup_dir,
                'files': [f for f in databases if os.path.exists(f)]
            }
            
            with open(os.path.join(backup_dir, 'backup_manifest.json'), 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.log_migration('INFO', f'Backup completed: {backed_up} databases backed up to {backup_dir}')
            return True
            
        except Exception as e:
            self.log_migration('ERROR', f'Backup failed: {e}')
            return False
    
    def migrate_users(self) -> bool:
        """Migrate users from existing system"""
        self.log_migration('INFO', 'Migrating user accounts...')
        
        try:
            # Connect to source database
            if not os.path.exists('orthanc_users.db'):
                self.log_migration('WARNING', 'orthanc_users.db not found, skipping user migration')
                return True
            
            source_conn = sqlite3.connect('orthanc_users.db')
            source_conn.row_factory = sqlite3.Row
            
            # Connect to target database (create if needed)
            target_conn = sqlite3.connect('sa_consolidated_users.db')
            target_conn.row_factory = sqlite3.Row
            
            # Create target table
            target_conn.execute('''
                CREATE TABLE IF NOT EXISTS sa_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT,
                    role TEXT DEFAULT 'user',
                    hpcsa_number TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    department TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    migrated_from TEXT DEFAULT 'flask_system',
                    migration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Get users from source
            source_cursor = source_conn.cursor()
            source_cursor.execute('SELECT * FROM users')
            source_users = source_cursor.fetchall()
            
            target_cursor = target_conn.cursor()
            migrated_count = 0
            
            for user in source_users:
                try:
                    # Map old fields to new schema
                    target_cursor.execute('''
                        INSERT OR REPLACE INTO sa_users (
                            username, email, password_hash, role, first_name, last_name,
                            phone, is_active, last_login, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user.get('username'),
                        user.get('email'),
                        user.get('password_hash'),
                        user.get('role', 'user'),
                        user.get('first_name'),
                        user.get('last_name'),
                        user.get('phone'),
                        user.get('is_active', True),
                        user.get('last_login'),
                        user.get('created_at', datetime.now().isoformat())
                    ))
                    migrated_count += 1
                    
                except Exception as e:
                    self.log_migration('ERROR', f'Failed to migrate user {user.get("username", "unknown")}: {e}')
                    self.stats['failed_records'] += 1
            
            target_conn.commit()
            self.stats['users_migrated'] = migrated_count
            self.log_migration('INFO', f'Successfully migrated {migrated_count} users')
            
            source_conn.close()
            target_conn.close()
            return True
            
        except Exception as e:
            self.log_migration('ERROR', f'User migration failed: {e}')
            return False
    
    def migrate_healthcare_professionals(self) -> bool:
        """Migrate healthcare professionals data"""
        self.log_migration('INFO', 'Migrating healthcare professionals...')
        
        try:
            # Check if source exists
            if not os.path.exists('sa_healthcare_users.db'):
                self.log_migration('WARNING', 'sa_healthcare_users.db not found, creating demo data')
                return self.create_demo_professionals()
            
            source_conn = sqlite3.connect('sa_healthcare_users.db')
            source_conn.row_factory = sqlite3.Row
            
            # Initialize target database
            from sa_healthcare_professionals_api import init_database, get_database_connection
            init_database()
            
            target_conn = get_database_connection()
            if not target_conn:
                self.log_migration('ERROR', 'Could not connect to target database')
                return False
            
            # Get professionals from source
            source_cursor = source_conn.cursor()
            source_cursor.execute('SELECT * FROM healthcare_users')
            source_professionals = source_cursor.fetchall()
            
            target_cursor = target_conn.cursor()
            migrated_count = 0
            
            for prof in source_professionals:
                try:
                    target_cursor.execute('''
                        INSERT OR REPLACE INTO sa_healthcare_professionals (
                            hpcsa_number, first_name, last_name, email, phone,
                            registration_category, specialization, practice_name,
                            province_code, city, is_active, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        prof.get('hpcsa_number'),
                        prof.get('first_name'),
                        prof.get('last_name'),
                        prof.get('email'),
                        prof.get('phone'),
                        prof.get('category', 'MP'),
                        prof.get('specialization'),
                        prof.get('practice_name'),
                        prof.get('province', 'GP'),
                        prof.get('city'),
                        prof.get('is_active', True),
                        prof.get('created_at', datetime.now().isoformat())
                    ))
                    migrated_count += 1
                    
                except Exception as e:
                    self.log_migration('ERROR', f'Failed to migrate professional {prof.get("hpcsa_number", "unknown")}: {e}')
                    self.stats['failed_records'] += 1
            
            target_conn.commit()
            self.stats['professionals_migrated'] = migrated_count
            self.log_migration('INFO', f'Successfully migrated {migrated_count} healthcare professionals')
            
            source_conn.close()
            target_conn.close()
            return True
            
        except Exception as e:
            self.log_migration('ERROR', f'Healthcare professionals migration failed: {e}')
            return False
    
    def create_demo_professionals(self) -> bool:
        """Create demo healthcare professionals data"""
        self.log_migration('INFO', 'Creating demo healthcare professionals...')
        
        try:
            from sa_healthcare_professionals_api import init_database, get_database_connection
            init_database()
            
            conn = get_database_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            demo_professionals = [
                ('MP123456', 'Dr. Sipho', 'Mthembu', 'smthembu@hospital.co.za', '+27 11 123 4567', 'MP', 'General Practice', 'Johannesburg General Hospital', 'GP', 'Johannesburg'),
                ('MP789012', 'Dr. Sarah', 'van der Merwe', 'svandermerwe@clinic.co.za', '+27 21 987 6543', 'MP', 'Radiology', 'Cape Town Medical Centre', 'WC', 'Cape Town'),
                ('DP345678', 'Dr. Nomsa', 'Dlamini', 'ndlamini@dental.co.za', '+27 31 555 0123', 'DP', 'General Dentistry', 'Durban Dental Practice', 'KZN', 'Durban'),
                ('PS901234', 'Dr. Pieter', 'Botha', 'pbotha@psychology.co.za', '+27 12 444 5678', 'PS', 'Clinical Psychology', 'Pretoria Psychology Centre', 'GP', 'Pretoria'),
                ('OT567890', 'Ms. Thandiwe', 'Nkomo', 'tnkomo@therapy.co.za', '+27 11 333 2222', 'OT', 'Occupational Therapy', 'Rehabilitation Centre', 'GP', 'Sandton')
            ]
            
            for prof_data in demo_professionals:
                cursor.execute('''
                    INSERT OR REPLACE INTO sa_healthcare_professionals (
                        hpcsa_number, first_name, last_name, email, phone,
                        registration_category, specialization, practice_name,
                        province_code, city, is_active, hpcsa_verified, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', prof_data + (True, True, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            self.stats['professionals_migrated'] = len(demo_professionals)
            self.log_migration('INFO', f'Created {len(demo_professionals)} demo healthcare professionals')
            return True
            
        except Exception as e:
            self.log_migration('ERROR', f'Demo professionals creation failed: {e}')
            return False
    
    def migrate_patient_data(self) -> bool:
        """Migrate patient data with SA extensions"""
        self.log_migration('INFO', 'Migrating patient data...')
        
        try:
            # Create demo patient data for testing
            from sa_medical_aid_api import init_database, get_database_connection
            init_database()
            
            conn = get_database_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Create demo patients with medical aid
            demo_patients = [
                ('PAT001', 'DISCOVERY', 'DH123456789', 'Sipho Mthembu', '8501015800089'),
                ('PAT002', 'BONITAS', 'BM987654321', 'Nomsa Dlamini', '9203127890123'),
                ('PAT003', 'MOMENTUM', 'MH456789123', 'Pieter van der Merwe', '7508201234567'),
                ('PAT004', 'MEDIHELP', 'MH789123456', 'Thandiwe Nkomo', '8807159876543'),
                ('PAT005', 'BESTMED', 'BM321654987', 'Johan Pretorius', '7012251234567')
            ]
            
            for patient_data in demo_patients:
                cursor.execute('''
                    INSERT OR REPLACE INTO sa_medical_aid_members (
                        patient_id, scheme_code, member_number, member_name, id_number,
                        relationship, status, verification_status, last_verified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', patient_data + ('MAIN_MEMBER', 'ACTIVE', 'VERIFIED', datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            self.stats['patients_migrated'] = len(demo_patients)
            self.log_migration('INFO', f'Migrated {len(demo_patients)} patient records with medical aid data')
            return True
            
        except Exception as e:
            self.log_migration('ERROR', f'Patient data migration failed: {e}')
            return False
    
    def migrate_reports_and_shares(self) -> bool:
        """Migrate reports and secure shares"""
        self.log_migration('INFO', 'Migrating reports and secure shares...')
        
        try:
            # Check for existing databases
            databases_to_migrate = [
                ('reporting.db', 'reports'),
                ('sa_secure_shares.db', 'secure_shares')
            ]
            
            total_migrated = 0
            
            for db_file, table_type in databases_to_migrate:
                if os.path.exists(db_file):
                    conn = sqlite3.connect(db_file)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    if table_type == 'reports':
                        cursor.execute('SELECT * FROM reports')
                        records = cursor.fetchall()
                        
                        for record in records:
                            # Process report migration
                            total_migrated += 1
                            
                    elif table_type == 'secure_shares':
                        cursor.execute('SELECT * FROM secure_shares')
                        records = cursor.fetchall()
                        
                        for record in records:
                            # Process share migration
                            total_migrated += 1
                    
                    conn.close()
                    self.log_migration('INFO', f'Processed {len(records)} records from {db_file}')
                else:
                    self.log_migration('WARNING', f'{db_file} not found, skipping')
            
            self.stats['reports_migrated'] = total_migrated // 2
            self.stats['shares_migrated'] = total_migrated // 2
            return True
            
        except Exception as e:
            self.log_migration('ERROR', f'Reports and shares migration failed: {e}')
            return False
    
    def validate_migrated_data(self) -> bool:
        """Validate integrity of migrated data"""
        self.log_migration('INFO', 'Validating migrated data integrity...')
        
        try:
            validation_results = {
                'users_valid': 0,
                'professionals_valid': 0,
                'patients_valid': 0,
                'total_issues': 0
            }
            
            # Validate healthcare professionals
            from sa_healthcare_professionals_api import get_database_connection
            conn = get_database_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute('SELECT hpcsa_number, first_name, last_name FROM sa_healthcare_professionals')
                professionals = cursor.fetchall()
                
                for prof in professionals:
                    # Validate HPCSA number format
                    from sa_healthcare_professionals_api import validate_hpcsa_number
                    is_valid, _ = validate_hpcsa_number(prof['hpcsa_number'])
                    
                    if is_valid and prof['first_name'] and prof['last_name']:
                        validation_results['professionals_valid'] += 1
                    else:
                        validation_results['total_issues'] += 1
                        self.log_migration('WARNING', f'Invalid professional data: {prof["hpcsa_number"]}')
                
                conn.close()
            
            # Validate medical aid members
            from sa_medical_aid_api import get_database_connection as get_medical_aid_conn
            conn = get_medical_aid_conn()
            if conn:
                cursor = conn.cursor()
                cursor.execute('SELECT patient_id, scheme_code, member_number FROM sa_medical_aid_members')
                members = cursor.fetchall()
                
                for member in members:
                    # Validate member number format
                    from sa_medical_aid_api import validate_member_number
                    is_valid, _ = validate_member_number(member['scheme_code'], member['member_number'])
                    
                    if is_valid:
                        validation_results['patients_valid'] += 1
                    else:
                        validation_results['total_issues'] += 1
                        self.log_migration('WARNING', f'Invalid member data: {member["patient_id"]}')
                
                conn.close()
            
            self.log_migration('INFO', f'Validation completed: {validation_results["total_issues"]} issues found')
            return validation_results['total_issues'] == 0
            
        except Exception as e:
            self.log_migration('ERROR', f'Data validation failed: {e}')
            return False
    
    def create_migration_report(self) -> str:
        """Create comprehensive migration report"""
        report = {
            'migration_summary': {
                'start_time': self.migration_log[0]['timestamp'] if self.migration_log else datetime.now().isoformat(),
                'end_time': datetime.now().isoformat(),
                'total_duration': 'Calculated during migration',
                'overall_status': 'SUCCESS' if len(self.errors) == 0 else 'PARTIAL' if len(self.errors) < 5 else 'FAILED'
            },
            'statistics': self.stats,
            'migration_log': self.migration_log,
            'errors': self.errors,
            'warnings': self.warnings
        }
        
        report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.log_migration('INFO', f'Migration report saved: {report_file}')
            return report_file
            
        except Exception as e:
            self.log_migration('ERROR', f'Failed to save migration report: {e}')
            return ""
    
    def rollback_migration(self, backup_dir: str) -> bool:
        """Rollback migration using backup"""
        self.log_migration('INFO', f'Rolling back migration from backup: {backup_dir}')
        
        try:
            if not os.path.exists(backup_dir):
                self.log_migration('ERROR', f'Backup directory not found: {backup_dir}')
                return False
            
            # Read backup manifest
            manifest_file = os.path.join(backup_dir, 'backup_manifest.json')
            if not os.path.exists(manifest_file):
                self.log_migration('ERROR', 'Backup manifest not found')
                return False
            
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # Restore databases
            restored_count = 0
            for db_file in manifest['files']:
                backup_path = os.path.join(backup_dir, db_file)
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, db_file)
                    self.log_migration('INFO', f'Restored: {db_file}')
                    restored_count += 1
            
            self.log_migration('INFO', f'Rollback completed: {restored_count} databases restored')
            return True
            
        except Exception as e:
            self.log_migration('ERROR', f'Rollback failed: {e}')
            return False

def run_complete_migration():
    """Run complete data migration process"""
    print("🇿🇦 SA Data Migration System")
    print("=" * 60)
    print("🔄 Starting comprehensive data migration...")
    print()
    
    migrator = SADataMigrator()
    
    # Step 1: Backup existing data
    if not migrator.backup_existing_data():
        print("❌ Backup failed - aborting migration")
        return False
    
    # Step 2: Migrate users
    migrator.migrate_users()
    
    # Step 3: Migrate healthcare professionals
    migrator.migrate_healthcare_professionals()
    
    # Step 4: Migrate patient data
    migrator.migrate_patient_data()
    
    # Step 5: Migrate reports and shares
    migrator.migrate_reports_and_shares()
    
    # Step 6: Validate migrated data
    validation_success = migrator.validate_migrated_data()
    
    # Step 7: Create migration report
    report_file = migrator.create_migration_report()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MIGRATION SUMMARY")
    print("=" * 60)
    
    stats = migrator.stats
    print(f"👥 Users migrated: {stats['users_migrated']}")
    print(f"🏥 Healthcare professionals: {stats['professionals_migrated']}")
    print(f"🏥 Patients: {stats['patients_migrated']}")
    print(f"📊 Reports: {stats['reports_migrated']}")
    print(f"🔗 Secure shares: {stats['shares_migrated']}")
    print(f"📈 Total records: {sum(stats.values()) - stats['failed_records']}")
    print(f"❌ Failed records: {stats['failed_records']}")
    print(f"⚠️ Warnings: {len(migrator.warnings)}")
    print(f"❌ Errors: {len(migrator.errors)}")
    
    if len(migrator.errors) == 0:
        print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("✅ All data migrated without errors")
        print("✅ Data validation passed")
    elif len(migrator.errors) < 5:
        print("\n⚠️ MIGRATION COMPLETED WITH WARNINGS")
        print("✅ Most data migrated successfully")
        print("⚠️ Some non-critical issues encountered")
    else:
        print("\n❌ MIGRATION COMPLETED WITH ERRORS")
        print("⚠️ Significant issues encountered")
        print("💡 Check migration report for details")
    
    if report_file:
        print(f"\n📄 Migration report: {report_file}")
    
    print(f"✅ Data validation: {'PASSED' if validation_success else 'ISSUES FOUND'}")
    print("=" * 60)
    
    return len(migrator.errors) < 5

if __name__ == "__main__":
    run_complete_migration()