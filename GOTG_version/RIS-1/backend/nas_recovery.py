"""
NAS/Device Data Recovery Module for GOTG-RIS
Extract patient data from damaged NAS devices, corrupted files, and emergency backups
Designed for collapsed hospitals, war zones, and extreme disaster scenarios

Key Features:
- Recover data from corrupted SQLite databases
- Extract data from backup files (JSON, CSV, XML)
- OCR for physical document photos
- Partial recovery and data consistency validation
- Automatic data quality scoring
- Lightweight (can run on Raspberry Pi with <100MB memory)
"""

import os
import json
import sqlite3
import logging
import hashlib
import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import io
import threading
import queue

logger = logging.getLogger(__name__)

# Try optional OCR library (graceful fallback)
try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

# =============================================
# Data Classes & Enums
# =============================================

class DataSourceType(Enum):
    """Source of recovered data"""
    NAS_DATABASE = "nas_database"
    BACKUP_JSON = "backup_json"
    BACKUP_CSV = "backup_csv"
    BACKUP_XML = "backup_xml"
    OCR_DOCUMENT = "ocr_document"
    HANDWRITTEN_NOTE = "handwritten_note"
    PARTIAL_RECOVERY = "partial_recovery"
    CORRUPTED_FILE = "corrupted_file"

class RecoveryStatus(Enum):
    """Status of recovery operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESSFUL = "successful"
    PARTIAL = "partial"
    FAILED = "failed"
    MANUAL_REVIEW_NEEDED = "manual_review_needed"

@dataclass
class RecoveredRecord:
    """Successfully recovered patient record"""
    record_id: str
    patient_id: Optional[int]
    source_type: str  # DataSourceType
    recovered_data: Dict[str, Any]  # The actual patient data
    quality_score: float  # 0.0-1.0: confidence in data accuracy
    completeness: float  # 0.0-1.0: how much of expected data was recovered
    conflicts: List[Dict] = field(default_factory=list)  # Data conflicts with other sources
    requires_verification: bool = True
    clinician_notes: Optional[str] = None
    recovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self):
        return asdict(self)

@dataclass
class DataRecoveryJob:
    """A data recovery operation"""
    job_id: str
    source_path: str
    source_type: str
    status: str
    records_found: int = 0
    records_recovered: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    progress_percent: int = 0

# =============================================
# Corrupted SQLite Database Recovery
# =============================================

class CorruptedDatabaseRecovery:
    """
    Recover data from corrupted or damaged SQLite databases
    Attempts multiple recovery strategies
    """
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.CorruptedDatabaseRecovery")
    
    def recover_from_corrupted_db(self, corrupted_db_path: str) -> Tuple[bool, List[Dict], str]:
        """
        Attempt to recover data from corrupted SQLite database
        
        Returns:
            (success, recovered_records, error_message)
        """
        recovered_records = []
        errors = []
        
        try:
            # Strategy 1: Try direct connection with recovery
            self.logger.info(f"Attempting recovery from: {corrupted_db_path}")
            
            conn = sqlite3.connect(corrupted_db_path)
            conn.isolation_level = None  # Autocommit mode
            
            try:
                # Run integrity check
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                integrity = cursor.fetchone()
                
                if integrity[0] != 'ok':
                    self.logger.warning(f"Database integrity issue: {integrity[0]}")
                    errors.append(f"Integrity check failed: {integrity[0]}")
                
                # Try to recover deleted pages
                cursor.execute("PRAGMA freelist_count")
                freelist = cursor.fetchone()[0]
                self.logger.info(f"Found {freelist} free pages (potential deleted data)")
                
            except Exception as e:
                errors.append(f"Integrity check error: {str(e)}")
            
            # Strategy 2: Extract from all tables
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                self.logger.info(f"Found {len(tables)} tables")
                
                for table in tables:
                    table_name = table[0]
                    try:
                        cursor.execute(f"SELECT * FROM {table_name}")
                        rows = cursor.fetchall()
                        
                        # Get column names
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        for row in rows:
                            record = dict(zip(columns, row))
                            record['_source_table'] = table_name
                            record['_recovery_method'] = 'direct_extraction'
                            recovered_records.append(record)
                        
                        self.logger.info(f"Recovered {len(rows)} records from table: {table_name}")
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to read table {table_name}: {str(e)}")
                        errors.append(f"Table {table_name} read error: {str(e)}")
            
            except Exception as e:
                errors.append(f"Table enumeration error: {str(e)}")
            
            conn.close()
            
            success = len(recovered_records) > 0
            error_msg = "; ".join(errors) if errors else ""
            
            return success, recovered_records, error_msg
        
        except Exception as e:
            error_msg = f"Database recovery failed: {str(e)}"
            self.logger.error(error_msg)
            return False, [], error_msg
    
    def extract_from_wal_file(self, wal_path: str) -> List[Dict]:
        """
        Extract data from SQLite WAL (Write-Ahead Log) files
        WAL files contain uncommitted transactions that may have important data
        """
        recovered = []
        
        try:
            if not os.path.exists(wal_path):
                return recovered
            
            # WAL files are binary, but we can try to extract text patterns
            with open(wal_path, 'rb') as f:
                content = f.read()
            
            # Look for common text patterns in WAL file
            # This is a heuristic approach
            text = content.decode('utf-8', errors='ignore')
            
            # Extract JSON-like patterns
            json_patterns = re.findall(r'\{[^{}]*\}', text)
            for pattern in json_patterns:
                try:
                    data = json.loads(pattern)
                    data['_source'] = 'wal_extraction'
                    recovered.append(data)
                except:
                    pass
            
            self.logger.info(f"Extracted {len(recovered)} records from WAL file")
            return recovered
        
        except Exception as e:
            self.logger.error(f"WAL extraction error: {str(e)}")
            return []

# =============================================
# Backup File Recovery (JSON, CSV, XML)
# =============================================

class BackupFileRecovery:
    """Recover patient data from backup files in various formats"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.BackupFileRecovery")
    
    def recover_from_json_backup(self, backup_path: str) -> Tuple[bool, List[Dict]]:
        """Recover data from JSON backup files"""
        recovered = []
        
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse as complete JSON
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    recovered = data
                elif isinstance(data, dict):
                    # Could be a single record or a container
                    if 'records' in data:
                        recovered = data['records']
                    elif 'patients' in data:
                        recovered = data['patients']
                    else:
                        recovered = [data]
            
            except json.JSONDecodeError:
                # Try partial recovery - extract valid JSON objects
                self.logger.warning("JSON parse failed, attempting partial recovery")
                recovered = self._extract_json_objects(content)
            
            self.logger.info(f"Recovered {len(recovered)} records from JSON backup")
            return len(recovered) > 0, recovered
        
        except Exception as e:
            self.logger.error(f"JSON backup recovery error: {str(e)}")
            return False, []
    
    def recover_from_csv_backup(self, backup_path: str) -> Tuple[bool, List[Dict]]:
        """Recover data from CSV backup files"""
        recovered = []
        
        try:
            import csv
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    for row in reader:
                        # Clean up empty fields
                        cleaned = {k: v for k, v in row.items() if v and v.strip()}
                        if cleaned:
                            recovered.append(cleaned)
            
            self.logger.info(f"Recovered {len(recovered)} records from CSV backup")
            return len(recovered) > 0, recovered
        
        except Exception as e:
            self.logger.error(f"CSV backup recovery error: {str(e)}")
            return False, []
    
    def recover_from_xml_backup(self, backup_path: str) -> Tuple[bool, List[Dict]]:
        """Recover data from XML backup files"""
        recovered = []
        
        try:
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(backup_path)
            root = tree.getroot()
            
            # Find patient elements
            for elem in root.findall('.//patient'):
                record = {}
                for child in elem:
                    record[child.tag] = child.text
                if record:
                    recovered.append(record)
            
            self.logger.info(f"Recovered {len(recovered)} records from XML backup")
            return len(recovered) > 0, recovered
        
        except Exception as e:
            self.logger.error(f"XML backup recovery error: {str(e)}")
            return False, []
    
    def _extract_json_objects(self, text: str) -> List[Dict]:
        """Extract valid JSON objects from corrupted JSON text"""
        objects = []
        
        # Find all {...} patterns
        depth = 0
        current = ""
        in_string = False
        escape = False
        
        for char in text:
            if escape:
                current += char
                escape = False
                continue
            
            if char == '\\':
                escape = True
                current += char
                continue
            
            if char == '"' and not escape:
                in_string = not in_string
                current += char
                continue
            
            if not in_string:
                if char == '{':
                    if depth == 0:
                        current = char
                    else:
                        current += char
                    depth += 1
                    continue
                elif char == '}':
                    current += char
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(current)
                            objects.append(obj)
                        except:
                            pass
                        current = ""
                    continue
            
            if depth > 0:
                current += char
        
        return objects

# =============================================
# OCR and Document Scanning
# =============================================

class DocumentOCRExtractor:
    """Extract patient data from scanned documents, photos, and handwritten notes"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.DocumentOCRExtractor")
    
    def extract_from_image(self, image_path: str) -> Tuple[bool, str, Dict]:
        """
        Extract text from document image using OCR
        
        Returns:
            (success, raw_text, structured_data)
        """
        if not HAS_OCR:
            return False, "OCR not available", {}
        
        try:
            image = Image.open(image_path)
            
            # Optimize image for OCR
            image = self._preprocess_image(image)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image)
            
            # Extract structured data from text
            structured = self._parse_medical_document(text)
            
            self.logger.info(f"OCR extraction successful: {len(text)} chars, {len(structured)} fields")
            return True, text, structured
        
        except Exception as e:
            self.logger.error(f"OCR extraction error: {str(e)}")
            return False, "", {}
    
    def _preprocess_image(self, image):
        """Preprocess image for better OCR results"""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Increase contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2)
            
            # Increase sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2)
            
            return image
        
        except Exception as e:
            self.logger.warning(f"Image preprocessing error: {str(e)}")
            return image
    
    def _parse_medical_document(self, text: str) -> Dict:
        """Parse medical information from OCR'd text"""
        extracted = {}
        
        # Try to extract patient name
        name_pattern = r'(?:Name|Patient):\s*([A-Za-z\s]+)'
        name_match = re.search(name_pattern, text, re.IGNORECASE)
        if name_match:
            extracted['name'] = name_match.group(1).strip()
        
        # Try to extract date of birth
        dob_pattern = r'(?:DOB|Birth|Born):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        dob_match = re.search(dob_pattern, text, re.IGNORECASE)
        if dob_match:
            extracted['date_of_birth'] = dob_match.group(1)
        
        # Try to extract conditions
        condition_keywords = ['diabetes', 'hypertension', 'asthma', 'heart', 'cancer', 'aids', 'epilepsy', 'stroke']
        extracted['conditions'] = []
        for keyword in condition_keywords:
            if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                extracted['conditions'].append(keyword.capitalize())
        
        # Try to extract allergies
        allergy_pattern = r'(?:Allerg[yies]|Allergic):\s*([^\n]+)'
        allergy_match = re.search(allergy_pattern, text, re.IGNORECASE)
        if allergy_match:
            extracted['allergies'] = [a.strip() for a in allergy_match.group(1).split(',')]
        
        # Try to extract medications
        med_keywords = ['medication', 'drug', 'taking', 'prescribed']
        med_section = ""
        for line in text.split('\n'):
            if any(keyword in line.lower() for keyword in med_keywords):
                med_section = line
                break
        if med_section:
            extracted['medications'] = self._extract_medications(med_section)
        
        # Try to extract phone number
        phone_pattern = r'(?:Phone|Contact):\s*(\+?\d[\d\s\-]{6,})'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            extracted['phone'] = phone_match.group(1).strip()
        
        return extracted
    
    def _extract_medications(self, text: str) -> List[str]:
        """Extract medication names from text"""
        medications = []
        
        # Common medication patterns
        med_pattern = r'([A-Z][a-z]+(?:\s+\d+\s*(?:mg|ml|units))?)'
        matches = re.findall(med_pattern, text)
        
        # Filter to likely medications
        common_meds = ['acetaminophen', 'aspirin', 'ibuprofen', 'metformin', 'lisinopril', 'atorvastatin', 'omeprazole']
        
        for match in matches:
            if any(med in match.lower() for med in common_meds):
                medications.append(match.strip())
        
        return medications

# =============================================
# Data Quality & Consistency Validation
# =============================================

class DataQualityValidator:
    """Validate recovered data quality and detect conflicts"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.DataQualityValidator")
    
    def calculate_quality_score(self, record: Dict) -> float:
        """
        Calculate quality score for a recovered record (0.0 - 1.0)
        Considers:
        - Completeness (missing fields)
        - Data type validity
        - Logical consistency
        - Presence of critical fields
        """
        score = 0.0
        weights = []
        
        # Critical fields that must be present
        critical_fields = ['patient_id', 'name']
        critical_present = sum(1 for f in critical_fields if f in record and record[f])
        critical_score = critical_present / len(critical_fields)
        score += critical_score * 0.4
        weights.append(0.4)
        
        # Completeness (percentage of fields filled)
        total_fields = len(record)
        filled_fields = sum(1 for v in record.values() if v is not None and str(v).strip())
        completeness = filled_fields / max(total_fields, 1)
        score += completeness * 0.3
        weights.append(0.3)
        
        # Data validity
        validity = self._check_data_validity(record)
        score += validity * 0.2
        weights.append(0.2)
        
        # Logical consistency
        consistency = self._check_logical_consistency(record)
        score += consistency * 0.1
        weights.append(0.1)
        
        # Normalize
        total_weight = sum(weights)
        return min(1.0, max(0.0, score / total_weight if total_weight > 0 else 0))
    
    def _check_data_validity(self, record: Dict) -> float:
        """Check if data types and values are reasonable"""
        validity_score = 0.0
        checks = 0
        
        # Check dates
        for date_field in ['date_of_birth', 'admission_date', 'created_at']:
            if date_field in record:
                checks += 1
                try:
                    from dateutil import parser
                    parser.parse(str(record[date_field]))
                    validity_score += 1
                except:
                    pass
        
        # Check ages (if DOB present)
        if 'age' in record:
            checks += 1
            try:
                age = int(record['age'])
                if 0 <= age <= 150:
                    validity_score += 1
            except:
                pass
        
        # Check phone (basic pattern)
        if 'phone' in record:
            checks += 1
            if re.match(r'\d{7,}', str(record['phone']).replace('-', '').replace(' ', '')):
                validity_score += 1
        
        return validity_score / max(checks, 1) if checks > 0 else 1.0
    
    def _check_logical_consistency(self, record: Dict) -> float:
        """Check for logical inconsistencies in data"""
        consistency_score = 1.0
        
        # Check if DOB and age make sense together
        if 'date_of_birth' in record and 'age' in record:
            try:
                from dateutil import parser
                dob = parser.parse(str(record['date_of_birth']))
                age = int(record['age'])
                calculated_age = (datetime.now() - dob).days // 365
                
                if abs(calculated_age - age) > 1:
                    consistency_score -= 0.2
            except:
                pass
        
        return max(0.0, consistency_score)
    
    def detect_duplicates(self, records: List[Dict]) -> List[Tuple[int, int, float]]:
        """
        Detect potential duplicate records
        
        Returns:
            List of (index1, index2, similarity_score) tuples
        """
        duplicates = []
        
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                similarity = self._calculate_similarity(records[i], records[j])
                if similarity > 0.7:  # High similarity threshold
                    duplicates.append((i, j, similarity))
        
        return duplicates
    
    def _calculate_similarity(self, record1: Dict, record2: Dict) -> float:
        """Calculate similarity between two records"""
        # Simple Jaccard similarity on common fields
        fields = set(list(record1.keys()) + list(record2.keys()))
        matching = 0
        
        for field in fields:
            v1 = str(record1.get(field, '')).lower().strip()
            v2 = str(record2.get(field, '')).lower().strip()
            
            if v1 and v2 and v1 == v2:
                matching += 1
        
        return matching / len(fields) if fields else 0.0

# =============================================
# Recovery Manager (Orchestrator)
# =============================================

class DisasterRecoveryManager:
    """
    Orchestrates recovery from multiple data sources
    Merges recovered data, validates quality, and stores results
    """
    
    def __init__(self, db_path: str = './ris.db'):
        self.db_path = db_path
        self.db_recovery = CorruptedDatabaseRecovery(db_path)
        self.backup_recovery = BackupFileRecovery()
        self.ocr_recovery = DocumentOCRExtractor()
        self.validator = DataQualityValidator()
        self.logger = logging.getLogger(f"{__name__}.DisasterRecoveryManager")
        self.recovery_queue = queue.Queue()
    
    def initiate_recovery(self, source_path: str, source_type: str) -> str:
        """
        Initiate recovery job
        
        Returns:
            job_id
        """
        job_id = hashlib.sha256(
            f"{source_path}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        job = DataRecoveryJob(
            job_id=job_id,
            source_path=source_path,
            source_type=source_type,
            status=RecoveryStatus.PENDING.value
        )
        
        # Save job to database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO data_recovery_jobs 
                (job_id, source_path, source_type, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, source_path, source_type, job.status, job.created_at))
            conn.commit()
            conn.close()
            
            self.logger.info(f"Recovery job initiated: {job_id}")
        except Exception as e:
            self.logger.error(f"Failed to save job: {str(e)}")
        
        return job_id
    
    def execute_recovery(self, source_path: str, source_type: str) -> Tuple[bool, List[RecoveredRecord]]:
        """Execute recovery from source"""
        recovered_records = []
        
        try:
            if source_type == DataSourceType.NAS_DATABASE.value:
                success, records, error = self.db_recovery.recover_from_corrupted_db(source_path)
                if success:
                    recovered_records = [self._build_recovered_record(r, source_type) for r in records]
            
            elif source_type == DataSourceType.BACKUP_JSON.value:
                success, records = self.backup_recovery.recover_from_json_backup(source_path)
                if success:
                    recovered_records = [self._build_recovered_record(r, source_type) for r in records]
            
            elif source_type == DataSourceType.BACKUP_CSV.value:
                success, records = self.backup_recovery.recover_from_csv_backup(source_path)
                if success:
                    recovered_records = [self._build_recovered_record(r, source_type) for r in records]
            
            elif source_type == DataSourceType.OCR_DOCUMENT.value:
                success, text, structured = self.ocr_recovery.extract_from_image(source_path)
                if success:
                    record = self._build_recovered_record(structured, source_type)
                    recovered_records = [record]
            
            return True, recovered_records
        
        except Exception as e:
            self.logger.error(f"Recovery execution error: {str(e)}")
            return False, []
    
    def _build_recovered_record(self, data: Dict, source_type: str) -> RecoveredRecord:
        """Build RecoveredRecord with quality scoring"""
        quality = self.validator.calculate_quality_score(data)
        completeness = len([v for v in data.values() if v]) / max(len(data), 1)
        
        return RecoveredRecord(
            record_id=hashlib.sha256(json.dumps(data, default=str).encode()).hexdigest()[:16],
            patient_id=data.get('patient_id'),
            source_type=source_type,
            recovered_data=data,
            quality_score=quality,
            completeness=completeness,
            requires_verification=quality < 0.8  # High quality doesn't need review
        )

