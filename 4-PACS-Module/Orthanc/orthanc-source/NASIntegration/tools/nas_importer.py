#!/usr/bin/env python3
"""
🇿🇦 South African Medical Imaging System - NAS Import/Indexing Tool

This tool scans a NAS for existing DICOM files and imports them into Orthanc,
building the metadata index for fast searching and retrieval.

Features:
- Recursive NAS directory scanning
- DICOM file validation and parsing
- Batch import with progress tracking
- Duplicate detection and handling
- South African medical context support
- Comprehensive logging and error handling
"""

import os
import sys
import json
import time
import logging
import hashlib
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import argparse
import uuid

# Third-party imports
try:
    import pydicom
    import requests
    from smbprotocol.connection import Connection
    from smbprotocol.session import Session
    from smbprotocol.tree import TreeConnect
    from smbprotocol.open import Open, CreateDisposition, FileAttributes
    from smbprotocol.file_info import FileStandardInformation
except ImportError as e:
    print(f"❌ Missing required dependencies: {e}")
    print("Install with: pip install pydicom requests smbprotocol")
    sys.exit(1)

# Configure logging with Windows-compatible encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nas_importer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NASImporter:
    """
    🏥 World-class NAS DICOM importer for South African healthcare
    """
    
    def __init__(self, config_file: str = "nas_import_config.json"):
        """Initialize the NAS importer with configuration"""
        self.config = self.load_config(config_file)
        self.stats = {
            'files_scanned': 0,
            'dicom_files_found': 0,
            'files_imported': 0,
            'files_skipped': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        self.imported_files_db = "imported_files.db"
        self.init_tracking_db()
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            "nas": {
                "server": "192.168.1.100",
                "share": "medical_images",
                "username": "admin",
                "password": "password",
                "domain": "WORKGROUP"
            },
            "orthanc": {
                "url": "http://localhost:8042",
                "username": "orthanc",
                "password": "orthanc"
            },
            "import_settings": {
                "scan_subdirectories": True,
                "file_extensions": [".dcm", ".dicom", ".ima", ""],
                "batch_size": 100,
                "max_file_size_mb": 500,
                "skip_duplicates": True,
                "verify_dicom": True
            },
            "south_african_context": {
                "medical_aid_mapping": True,
                "sa_patient_id_validation": True,
                "timezone": "Africa/Johannesburg",
                "default_language": "en-ZA"
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if subkey not in config[key]:
                                config[key][subkey] = subvalue
                return config
            else:
                # Create default config file
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info(f"📝 Created default config file: {config_file}")
                return default_config
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return default_config
    
    def init_tracking_db(self):
        """Initialize SQLite database for tracking imported files"""
        try:
            conn = sqlite3.connect(self.imported_files_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS imported_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT NOT NULL,
                    orthanc_instance_id TEXT,
                    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    patient_id TEXT,
                    study_date TEXT,
                    modality TEXT,
                    status TEXT DEFAULT 'imported'
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_file_hash ON imported_files(file_hash)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_patient_id ON imported_files(patient_id)
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Tracking database initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing tracking database: {e}")
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    def is_file_already_imported(self, file_hash: str) -> bool:
        """Check if file has already been imported"""
        try:
            conn = sqlite3.connect(self.imported_files_db)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM imported_files WHERE file_hash = ?', (file_hash,))
            result = cursor.fetchone()
            
            conn.close()
            return result is not None
            
        except Exception as e:
            logger.error(f"❌ Error checking import status: {e}")
            return False
    
    def record_imported_file(self, file_path: str, file_hash: str, file_content: bytes, 
                           orthanc_instance_id: str = None):
        """Record imported file in tracking database"""
        try:
            # Extract DICOM metadata if possible
            patient_id = None
            study_date = None
            modality = None
            
            try:
                ds = pydicom.dcmread(pydicom.filebase.DicomBytesIO(file_content))
                patient_id = getattr(ds, 'PatientID', None)
                study_date = getattr(ds, 'StudyDate', None)
                modality = getattr(ds, 'Modality', None)
            except:
                pass
            
            conn = sqlite3.connect(self.imported_files_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO imported_files 
                (file_path, file_hash, orthanc_instance_id, file_size, patient_id, study_date, modality)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (file_path, file_hash, orthanc_instance_id, len(file_content), 
                  patient_id, study_date, modality))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error recording imported file: {e}")
    
    def connect_to_nas(self) -> Tuple[Connection, Session, TreeConnect]:
        """Establish connection to NAS"""
        try:
            nas_config = self.config['nas']
            
            logger.info(f"🔗 Connecting to NAS: {nas_config['server']}")
            
            connection = Connection(uuid.uuid4(), nas_config['server'], 445)
            connection.connect()
            
            session = Session(connection, nas_config['username'], nas_config['password'], 
                            nas_config.get('domain', 'WORKGROUP'))
            session.connect()
            
            tree = TreeConnect(session, f"\\\\{nas_config['server']}\\{nas_config['share']}")
            tree.connect()
            
            logger.info("✅ Successfully connected to NAS")
            return connection, session, tree
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to NAS: {e}")
            raise
    
    def scan_nas_directory(self, tree: TreeConnect, path: str = "") -> List[str]:
        """Recursively scan NAS directory for DICOM files"""
        dicom_files = []
        
        try:
            # List directory contents
            query_info = tree.query_directory(path, "*")
            
            for file_info in query_info:
                if file_info.file_name in ['.', '..']:
                    continue
                
                file_path = os.path.join(path, file_info.file_name).replace('\\', '/')
                self.stats['files_scanned'] += 1
                
                # Check if it's a directory
                if file_info.file_attributes & FileAttributes.FILE_ATTRIBUTE_DIRECTORY:
                    if self.config['import_settings']['scan_subdirectories']:
                        logger.info(f"📁 Scanning directory: {file_path}")
                        dicom_files.extend(self.scan_nas_directory(tree, file_path))
                else:
                    # Check if it's a potential DICOM file
                    if self.is_potential_dicom_file(file_info.file_name):
                        dicom_files.append(file_path)
                        self.stats['dicom_files_found'] += 1
                        
                        if self.stats['files_scanned'] % 1000 == 0:
                            logger.info(f"📊 Scanned {self.stats['files_scanned']} files, "
                                      f"found {self.stats['dicom_files_found']} potential DICOM files")
        
        except Exception as e:
            logger.error(f"❌ Error scanning directory {path}: {e}")
        
        return dicom_files
    
    def is_potential_dicom_file(self, filename: str) -> bool:
        """Check if file might be a DICOM file based on extension"""
        extensions = self.config['import_settings']['file_extensions']
        
        # Check extensions
        for ext in extensions:
            if ext == "":  # Files without extension
                if '.' not in filename:
                    return True
            elif filename.lower().endswith(ext.lower()):
                return True
        
        return False
    
    def read_file_from_nas(self, tree: TreeConnect, file_path: str) -> Optional[bytes]:
        """Read file content from NAS"""
        try:
            file_open = Open(tree, file_path)
            file_open.create(CreateDisposition.FILE_OPEN, FileAttributes.FILE_ATTRIBUTE_NORMAL)
            
            # Get file size
            file_info = file_open.query_info(FileStandardInformation)
            file_size = file_info.end_of_file
            
            # Check file size limit
            max_size = self.config['import_settings']['max_file_size_mb'] * 1024 * 1024
            if file_size > max_size:
                logger.warning(f"⚠️ File too large, skipping: {file_path} ({file_size} bytes)")
                file_open.close()
                return None
            
            # Read file content
            content = file_open.read(0, file_size)
            file_open.close()
            
            return content
            
        except Exception as e:
            logger.error(f"❌ Error reading file {file_path}: {e}")
            return None
    
    def validate_dicom_file(self, content: bytes) -> bool:
        """Validate if content is a valid DICOM file"""
        if not self.config['import_settings']['verify_dicom']:
            return True
        
        try:
            ds = pydicom.dcmread(pydicom.filebase.DicomBytesIO(content))
            return True
        except:
            return False
    
    def import_to_orthanc(self, content: bytes, filename: str) -> Optional[str]:
        """Import DICOM file to Orthanc"""
        try:
            orthanc_config = self.config['orthanc']
            
            # Prepare request
            url = f"{orthanc_config['url']}/instances"
            auth = (orthanc_config['username'], orthanc_config['password'])
            
            # Send file to Orthanc
            response = requests.post(
                url,
                data=content,
                headers={'Content-Type': 'application/dicom'},
                auth=auth,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                instance_id = result.get('ID')
                logger.debug(f"✅ Imported {filename} -> {instance_id}")
                return instance_id
            else:
                logger.error(f"❌ Failed to import {filename}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error importing {filename} to Orthanc: {e}")
            return None
    
    def import_files(self, file_list: List[str], tree: TreeConnect):
        """Import list of DICOM files to Orthanc"""
        batch_size = self.config['import_settings']['batch_size']
        total_files = len(file_list)
        
        logger.info(f"🚀 Starting import of {total_files} files in batches of {batch_size}")
        
        for i in range(0, total_files, batch_size):
            batch = file_list[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_files + batch_size - 1) // batch_size
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
            
            for file_path in batch:
                try:
                    # Read file from NAS
                    content = self.read_file_from_nas(tree, file_path)
                    if content is None:
                        self.stats['errors'] += 1
                        continue
                    
                    # Calculate hash for duplicate detection
                    file_hash = self.calculate_file_hash(content)
                    
                    # Check if already imported
                    if (self.config['import_settings']['skip_duplicates'] and 
                        self.is_file_already_imported(file_hash)):
                        logger.debug(f"⏭️ Skipping duplicate: {file_path}")
                        self.stats['files_skipped'] += 1
                        continue
                    
                    # Validate DICOM
                    if not self.validate_dicom_file(content):
                        logger.warning(f"⚠️ Invalid DICOM file, skipping: {file_path}")
                        self.stats['errors'] += 1
                        continue
                    
                    # Import to Orthanc
                    instance_id = self.import_to_orthanc(content, file_path)
                    
                    if instance_id:
                        # Record successful import
                        self.record_imported_file(file_path, file_hash, content, instance_id)
                        self.stats['files_imported'] += 1
                        
                        if self.stats['files_imported'] % 50 == 0:
                            logger.info(f"📈 Progress: {self.stats['files_imported']}/{total_files} files imported")
                    else:
                        self.stats['errors'] += 1
                
                except Exception as e:
                    logger.error(f"❌ Error processing {file_path}: {e}")
                    self.stats['errors'] += 1
            
            # Small delay between batches to avoid overwhelming the system
            time.sleep(1)
    
    def generate_report(self) -> str:
        """Generate import summary report"""
        duration = 0
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        report = f"""
🇿🇦 SOUTH AFRICAN MEDICAL IMAGING SYSTEM - NAS IMPORT REPORT
================================================================

📊 IMPORT STATISTICS:
- Files Scanned: {self.stats['files_scanned']:,}
- DICOM Files Found: {self.stats['dicom_files_found']:,}
- Files Successfully Imported: {self.stats['files_imported']:,}
- Files Skipped (Duplicates): {self.stats['files_skipped']:,}
- Errors Encountered: {self.stats['errors']:,}

⏱️ PERFORMANCE:
- Total Duration: {duration:.2f} seconds
- Import Rate: {self.stats['files_imported'] / max(duration, 1):.2f} files/second

🏥 SYSTEM STATUS:
- NAS Connection: {'✅ Success' if self.stats['files_scanned'] > 0 else '❌ Failed'}
- Orthanc Integration: {'✅ Active' if self.stats['files_imported'] > 0 else '❌ Failed'}
- Duplicate Detection: {'✅ Enabled' if self.config['import_settings']['skip_duplicates'] else '⚠️ Disabled'}

📈 SUCCESS RATE: {(self.stats['files_imported'] / max(self.stats['dicom_files_found'], 1)) * 100:.1f}%

Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (South African Time)
"""
        return report
    
    def run_import(self):
        """Main import process"""
        try:
            self.stats['start_time'] = datetime.now()
            logger.info("🇿🇦 Starting South African Medical Imaging NAS Import")
            
            # Connect to NAS
            connection, session, tree = self.connect_to_nas()
            
            try:
                # Scan for DICOM files
                logger.info("🔍 Scanning NAS for DICOM files...")
                dicom_files = self.scan_nas_directory(tree)
                
                if not dicom_files:
                    logger.warning("⚠️ No DICOM files found on NAS")
                    return
                
                logger.info(f"📋 Found {len(dicom_files)} potential DICOM files")
                
                # Import files
                self.import_files(dicom_files, tree)
                
            finally:
                # Clean up connections
                tree.disconnect()
                session.disconnect()
                connection.disconnect()
                logger.info("🔌 Disconnected from NAS")
            
            self.stats['end_time'] = datetime.now()
            
            # Generate and display report
            report = self.generate_report()
            logger.info(report)
            
            # Save report to file
            with open(f"nas_import_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w') as f:
                f.write(report)
            
            logger.info("🎉 NAS import completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            raise

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="🇿🇦 South African Medical Imaging NAS Import Tool"
    )
    parser.add_argument(
        '--config', 
        default='nas_import_config.json',
        help='Configuration file path'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Scan only, do not import files'
    )
    
    args = parser.parse_args()
    
    try:
        importer = NASImporter(args.config)
        
        if args.dry_run:
            logger.info("🔍 Running in dry-run mode (scan only)")
            # TODO: Implement dry-run mode
        else:
            importer.run_import()
            
    except KeyboardInterrupt:
        logger.info("⏹️ Import cancelled by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()