"""
SDOH Patient-Side Document Indexer
====================================
Scans patient-owned local folders for DICOM files, PDF reports, text reports,
referral letters, and medication scripts.

All data stays on the patient's device only — no cloud upload, no server-side
storage of actual file content.  The index stores metadata + short text
previews (≤400 chars) so the agent can surface the right documents when the
patient is preparing for a scan or specialist visit.

Dependencies (all optional — degrades gracefully if absent):
  - pydicom  : for reading DICOM headers
  - pdfminer : for PDF text extraction  (pip install pdfminer.six)
  - pypdf    : PDF fallback              (pip install pypdf)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Clinical vocabulary maps
# ---------------------------------------------------------------------------

MODALITY_LABELS: Dict[str, str] = {
    "CT": "CT Scan",
    "MR": "MRI",
    "CR": "X-Ray",
    "DX": "Digital X-Ray",
    "US": "Ultrasound",
    "PT": "PET Scan",
    "NM": "Nuclear Medicine Scan",
    "MG": "Mammogram",
    "RF": "Fluoroscopy",
    "XA": "Angiography",
    "SR": "Structured Report",
    "ECG": "ECG",
    "OT": "Other",
}

BODY_PART_KEYWORDS: Dict[str, List[str]] = {
    "chest": ["chest", "thorax", "thoracic", "lung", "lungs", "pulmonary", "heart", "cardiac", "mediastin", "pleura"],
    "abdomen": ["abdomen", "abdominal", "liver", "kidney", "renal", "bowel", "colon", "spleen", "pancreas", "gallbladder", "hepatic"],
    "brain": ["brain", "head", "neuro", "cerebral", "cranial", "skull", "intracranial", "cerebellum", "cortex"],
    "spine": ["spine", "vertebra", "vertebral", "cervical spine", "lumbar", "thoracic spine", "sacral", "spinal cord", "disc", "disk"],
    "pelvis": ["pelvis", "pelvic", "hip", "bladder", "prostate", "ovary", "uterus", "endometrium", "rectum"],
    "breast": ["breast", "mammogram", "mammography", "axilla"],
    "neck": ["neck", "thyroid", "cervical", "parathyroid", "carotid"],
    "extremity": ["arm", "leg", "knee", "shoulder", "elbow", "wrist", "ankle", "foot", "hand", "femur", "tibia", "fibula", "humerus"],
}

CLINICAL_PLAIN_LANGUAGE: Dict[str, str] = {
    "lesion": "an area that looks different from normal tissue and needs monitoring",
    "nodule": "a small lump or growth that may need follow-up",
    "mass": "a growth larger than a nodule — the doctor will want to investigate further",
    "opacity": "an area that appears lighter than expected on the scan, sometimes caused by fluid or infection",
    "effusion": "fluid that has built up where it should not be",
    "calcification": "calcium deposits — these can be completely normal or may need monitoring depending on where they are",
    "pneumonia": "a lung infection that causes part of the lung to look cloudy or filled with fluid",
    "atelectasis": "a small area of the lung that has partially collapsed — often temporary",
    "cardiomegaly": "the heart appears larger than normal on the image",
    "hepatomegaly": "the liver appears larger than normal",
    "splenomegaly": "the spleen appears larger than normal",
    "bilateral": "affecting both sides of the body",
    "unilateral": "affecting only one side of the body",
    "acute": "this is happening suddenly or has started recently",
    "chronic": "this is an ongoing or long-standing condition",
    "benign": "not cancerous — no immediate danger",
    "malignant": "cancerous or suspected to be cancerous — requires urgent follow-up",
    "metastasis": "cancer that has spread from where it originally started",
    "metastases": "multiple areas where cancer has spread",
    "edema": "swelling caused by fluid building up in the tissues",
    "stenosis": "a narrowing that restricts normal flow (blood, fluid, etc.)",
    "occlusion": "a complete blockage",
    "infarct": "tissue that has died due to lack of blood supply",
    "fracture": "a break or crack in a bone",
    "consolidation": "part of the lung is filled with something (like fluid or infection) instead of air",
    "infiltrate": "an abnormal substance has entered the lung tissue",
    "thickening": "a lining or wall is thicker than normal",
    "adenopathy": "lymph nodes are swollen or enlarged",
    "lymphadenopathy": "multiple lymph nodes are swollen — the body may be fighting an infection or something else",
    "atherosclerosis": "build-up of fatty deposits in the walls of blood vessels — can narrow them over time",
    "fibrosis": "scar tissue has formed in the organ",
    "cirrhosis": "the liver has significant scarring — often from long-term damage",
    "hernia": "part of an organ or tissue has pushed through a weak spot in the surrounding muscle or tissue",
    "cyst": "a sac filled with fluid — often harmless but may need monitoring",
    "abscess": "a collection of pus caused by infection",
    "haematoma": "a collection of blood outside the blood vessels, usually from injury",
    "contusion": "bruising of the tissue or organ",
    "perfusion": "the flow of blood through an organ",
    "ischaemia": "reduced blood supply to a part of the body",
}

# DICOM tag names → index field names
DICOM_TAG_MAP: Dict[str, str] = {
    "PatientName": "patient_name",
    "PatientID": "patient_id",
    "PatientBirthDate": "dob",
    "StudyDate": "study_date",
    "StudyDescription": "study_description",
    "SeriesDescription": "series_description",
    "Modality": "modality",
    "BodyPartExamined": "body_part",
    "InstitutionName": "institution",
    "ReferringPhysicianName": "referring_physician",
    "AccessionNumber": "accession_number",
    "StudyInstanceUID": "study_uid",
    "NumberOfSeriesRelatedInstances": "num_images",
}


# ---------------------------------------------------------------------------
# Windows network drive helpers
# ---------------------------------------------------------------------------

_DRIVE_UNC_CACHE: dict = {}

def _resolve_drive_unc(path_str: str) -> str:
    """Resolve a Windows drive-letter path to its UNC path via 'net use'.
    
    On Windows, mapped network drives (X:\\, Y:\\, …) are session-scoped and
    invisible to elevated processes.  'net use' enumerates all sessions and CAN
    return the mapping even from an elevated process — allowing the caller to
    retry the path using the raw UNC form (\\\\server\\share\\...).

    Returns the original path unchanged if the drive letter is not a network
    mapping or if 'net use' is unavailable.
    """
    if sys.platform != 'win32' or len(path_str) < 2 or path_str[1] != ':':
        return path_str
    drive_letter = path_str[0].upper()
    if drive_letter in _DRIVE_UNC_CACHE:
        unc_root = _DRIVE_UNC_CACHE[drive_letter]
        return (unc_root.rstrip('\\') + path_str[2:]) if unc_root else path_str
    try:
        import subprocess, re as _re
        result = subprocess.run(
            ['net', 'use', f'{drive_letter}:'],
            capture_output=True, text=True, timeout=5, creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        # Match 'Remote name   \\server\share name with spaces' to end of line
        m = _re.search(r'Remote name\s+(\\\\[^\r\n]+)', result.stdout)
        if not m:
            # Fallback: any double-backslash UNC path
            m = _re.search(r'(\\\\\\S[^\r\n]*)', result.stdout)
        if m:
            unc_root = m.group(1).strip()
            _DRIVE_UNC_CACHE[drive_letter] = unc_root
            return unc_root.rstrip('\\') + path_str[2:]
    except Exception:
        pass
    _DRIVE_UNC_CACHE[drive_letter] = None  # negative cache
    return path_str

def _win_isdir(path_str: str) -> bool:
    """Check whether *path_str* is an accessible directory on Windows.
    
    On Windows, ``os.path.isdir`` / ``Path.exists`` can silently return False
    for mapped network drives (X:, Y: …) when called from a subprocess that
    doesn't inherit the parent session's drive mappings.  This function first
    tries GetFileAttributesW (fast, works when the drive IS mapped), and if
    that fails for a drive-letter path it tries again via the UNC path obtained
    from ``net use`` (works even for elevated processes).
    """
    if sys.platform == 'win32':
        try:
            import ctypes
            _GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
            _GetFileAttributesW.restype = ctypes.c_uint32  # ensure unsigned 32-bit
            INVALID = 0xFFFFFFFF
            attrs = _GetFileAttributesW(str(path_str))
            FILE_ATTRIBUTE_DIRECTORY = 0x10
            if attrs != INVALID:
                return bool(attrs & FILE_ATTRIBUTE_DIRECTORY)
            # INVALID_FILE_ATTRIBUTES — path not accessible as-is.
            # Try UNC fallback for unmapped drive letters.
            unc_path = _resolve_drive_unc(path_str)
            if unc_path != path_str:
                attrs2 = _GetFileAttributesW(str(unc_path))
                if attrs2 != INVALID:
                    return bool(attrs2 & FILE_ATTRIBUTE_DIRECTORY)
            return False
        except Exception:
            pass
    return os.path.isdir(path_str)


def _win_probe_dir(path_str: str, timeout_sec: float = 5.0) -> Dict[str, Any]:
    """Probe a directory for accessibility with timeout.
    
    Returns a dict with:
      - accessible: bool
      - error: str or None
      - file_count: int (if accessible)
    """
    result = {"accessible": False, "error": None, "file_count": 0}
    
    def _probe():
        try:
            if _win_isdir(path_str):
                count = 0
                for _ in os.scandir(path_str):
                    count += 1
                    if count > 100:
                        break
                result["accessible"] = True
                result["file_count"] = count
            else:
                result["error"] = f"Path not accessible: {path_str}"
        except Exception as e:
            result["error"] = str(e)
    
    thread = threading.Thread(target=_probe, daemon=True)
    thread.start()
    thread.join(timeout=timeout_sec)
    
    if thread.is_alive():
        result["error"] = f"Directory probe timed out after {timeout_sec}s"
    
    return result


# ---------------------------------------------------------------------------
# Indexer
# ---------------------------------------------------------------------------

class PatientDocumentIndexer:
    """
    Indexes patient-owned medical documents from local folders.

    Usage
    -----
    indexer = PatientDocumentIndexer()
    indexer.scan_folder('/home/user/medical_records')
    results = indexer.search_for_visit('I need a CT scan of my chest')
    pack = indexer.build_history_pack('Jane', 'CT chest visit')
    """

    DEFAULT_SCAN_DIRS: List[str] = [
        os.path.expanduser("~/sdoh_medical_records"),
        os.path.expanduser("~/Desktop/medical_records"),
        os.path.expanduser("~/Documents/medical_records"),
        os.path.expanduser("~/Documents/Medical Records"),
        os.path.expanduser("~/Downloads"),
    ]

    DEFAULT_INDEX_PATH: str = os.path.expanduser("~/.sdoh_patient_index.json")

    SUPPORTED_EXTENSIONS: frozenset = frozenset({
        ".dcm", ".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png", ".jp2", ".j2k"
    })

    def __init__(
        self,
        scan_dirs: Optional[List[str]] = None,
        index_path: Optional[str] = None,
    ) -> None:
        self.scan_dirs: List[str] = scan_dirs or self.DEFAULT_SCAN_DIRS
        self.index_path: str = index_path or self.DEFAULT_INDEX_PATH
        self._index: List[Dict[str, Any]] = []
        self.db = None
        self.db_path: str = r'C:\Users\Admin\.openclaw\vault\index\master_health_graph.db'
        self._load_index()
        self._init_sqlite()

    # ------------------------------------------------------------------
    # Index persistence
    # ------------------------------------------------------------------

    def _load_index(self) -> None:
        try:
            if os.path.exists(self.index_path):
                with open(self.index_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        self._index = data
        except Exception:
            self._index = []

    def _save_index(self) -> None:
        try:
            parent = os.path.dirname(self.index_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.index_path, "w", encoding="utf-8") as fh:
                json.dump(self._index, fh, indent=2, default=str)
        except Exception:
            pass

    def _init_sqlite(self) -> None:
        """Initialize SQLite database for new metadata entries"""
        try:
            # Import from the same directory (backend folder)
            import sys
            import os
            backend_dir = os.path.dirname(__file__)
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            
            from health_graph_schema import HealthGraphSchema
            if os.path.exists(self.db_path):
                print(f"[_init_sqlite] Initializing SQLite at {self.db_path}")
                self.db = HealthGraphSchema(self.db_path)
                print(f"[_init_sqlite] Database initialized successfully")
            else:
                print(f"[_init_sqlite] SQLite database not found: {self.db_path}")
                self.db = None
        except ImportError as e:
            print(f"[_init_sqlite] SQLite import error: {e}")
            self.db = None
        except Exception as e:
            print(f"[_init_sqlite] SQLite initialization error: {e}")
            self.db = None

    def _write_to_sqlite(self, entry: Dict[str, Any]) -> None:
        """Write metadata entry to SQLite database"""
        if not self.db:
            print(f"[_write_to_sqlite] No database connection (db={self.db})")
            return
        
        try:
            patient_id = entry.get('patient_id')
            study_uid = entry.get('study_uid')
            file_path = entry.get('file_path')
            
            # All three required for proper indexing
            if not all([patient_id, study_uid, file_path]):
                missing = []
                if not patient_id: missing.append('patient_id')
                if not study_uid: missing.append('study_uid')
                if not file_path: missing.append('file_path')
                print(f"[_write_to_sqlite] Skipping {file_path}: missing {missing}")
                return
            
            # Insert patient first
            self.db.insert_patient(patient_id, entry)
            
            # Insert study
            self.db.insert_study(entry)
            
            # Insert series if has series_uid
            series_uid = entry.get('series_uid')
            if series_uid:
                self.db.insert_series(entry)
            
            # Insert file
            self.db.insert_file(entry)
            
            # Add keywords for search
            keywords = entry.get('relevance_keywords', [])
            if isinstance(keywords, str):
                keywords = keywords.split()
            for kw in keywords:
                if kw:
                    self.db.add_search_keyword(patient_id, kw.lower())
            
            # Add essential metadata
            for key, value in [
                ('institution', entry.get('institution')),
                ('dob', entry.get('dob')),
                ('modality', entry.get('modality')),
                ('body_part', entry.get('body_part_normalized')),
            ]:
                if value:
                    try:
                        self.db.insert_metadata(patient_id, key, value)
                    except:
                        pass
            
            # Update patient counts
            self.db.update_patient_counts(patient_id)
        
        except Exception as e:
            print(f"[_write_to_sqlite] Error writing entry: {e}")
            pass

    def query_health_graph_db(self, query: str = '') -> Dict[str, Any]:
        """Query the SQLite health graph database with intelligent intent detection"""
        if not self.db:
            return {'error': 'Database not initialized', 'patients': 0, 'studies': 0}
        
        try:
            stats = self.db.get_stats()
            query_lower = (query or '').lower().strip()
            
            print(f"[QUERY DEBUG] Processing: {query_lower[:60]}")
            
            import re
            
            # ===== PRIORITY 0: CHECK FOR SIIM QUERIES FIRST =====
            # But first check if asking about a SPECIFIC patient within SIIM
            is_asking_for_siim = any(word in query_lower for word in ['siim', 'hackathon'])
            
            # ===== PRIORITY 1: CHECK FOR EXPLICIT SEARCHES (surname, name, etc.) =====
            is_explicit_name_search = any(phrase in query_lower for phrase in [
                'surname', 'last name', 'first name', 'named', 'with surname'
            ])
            
            # Check if this is asking about a specific patient
            # "Tell me more about patient X", "give me details of X Y", "Tell me about X Y", etc.
            is_patient_about_query = re.search(r'(?:tell|show|what|about|more|details|give|please|provide|explain|find).*?(?:patient\s+)?(\w+(?:\s+\w+)?)', query_lower)
            
            print(f"[QUERY DEBUG]   is_explicit_name_search={is_explicit_name_search}, is_patient_about_query={is_patient_about_query is not None}, is_asking_for_siim={is_asking_for_siim}")
            
            # If this is a SIIM query AND asking about a specific patient (e.g., "Show me more about SIIM Ravi")
            # we should search for that patient in SIIM registry, not just list all SIIM patients
            siim_specific_patient_mode = False
            
            if is_explicit_name_search or is_patient_about_query:
                search_first_name = None
                search_last_name = None
                
                # Try pattern: "surname Strauss" or "named Smith" or "first name John" or "last name Smith"
                surname_match = re.search(r'(?:surname|last name)\s+(\w+)', query_lower)
                firstname_match = re.search(r'(?:first name)\s+(\w+)', query_lower)
                
                if surname_match:
                    search_last_name = surname_match.group(1).capitalize()
                if firstname_match:
                    search_first_name = firstname_match.group(1).capitalize()
                
                # Try pattern: "named John" (could be first or last)
                if not search_last_name and not search_first_name:
                    named_match = re.search(r'\bnamed\s+(\w+)', query_lower)
                    if named_match:
                        search_last_name = named_match.group(1).capitalize()
                
                # If not found, try extracting proper names (capitalized in original query)
                # Look for two consecutive capitalized words in the original query (before .lower())
                if not search_first_name and not search_last_name:
                    # Find capital letter sequences in original query
                    capital_words = re.findall(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b', query)
                    if capital_words:
                        search_first_name = capital_words[0][0]
                        search_last_name = capital_words[0][1]
                        print(f"[QUERY DEBUG]   → Found capitalized names from original query: {search_first_name} {search_last_name}")
                    else:
                        # Fallback: look for any two words after "about" or "patient"
                        # "Tell me more about juwan strauss" - extract juwan strauss
                        match = re.search(r'(?:about|patient|for)\s+(\w+)\s+(\w+)', query_lower)
                        if match:
                            search_first_name = match.group(1).capitalize()
                            search_last_name = match.group(2).capitalize()
                        elif is_asking_for_siim:
                            siim_match = re.search(r'siim\s+(\w+)', query_lower)
                            if siim_match and siim_match.group(1) not in ['patients', 'patient', 'hackathon', 'ingest', 'status', 'registry']:
                                search_first_name = siim_match.group(1).capitalize()
                                search_last_name = "Siim"
                
                print(f"[QUERY DEBUG]   → Name search: firstname={search_first_name}, lastname={search_last_name}")
                
                # Search for matching patients
                patients = []
                if search_first_name and search_last_name:
                    # Full name search - look for "LASTNAME^FIRSTNAME" pattern in patient_name
                    # Database stores names in DICOM format: "LASTNAME^FIRSTNAME"
                    try:
                        cursor = self.db.conn.cursor()
                        # Search for lastname^firstname pattern
                        pattern = f'{search_last_name.upper()}^{search_first_name.upper()}%'
                        cursor.execute('''
                            SELECT * FROM patients 
                            WHERE UPPER(patient_name) LIKE ?
                            LIMIT 20
                        ''', (pattern,))
                        rows = cursor.fetchall()
                        patients = [dict(row) for row in rows]
                        print(f"[QUERY DEBUG]   → Full name search found {len(patients)} patients with pattern '{pattern}'")
                    except Exception as e:
                        print(f"[QUERY DEBUG]   → Full name search error: {e}")
                    
                    # If no exact match, fall back to both names anywhere in string
                    if not patients:
                        all_patients = self.db.search_patients(search_last_name, limit=50)
                        for p in all_patients:
                            patient_name = (p.get('patient_name') or '').upper()
                            if search_first_name.upper() in patient_name:
                                patients.append(p)
                        print(f"[QUERY DEBUG]   → Fallback search found {len(patients)} patients")
                    
                elif search_last_name:
                    # Last name only search
                    patients = self.db.search_patients(search_last_name, limit=20)
                    print(f"[QUERY DEBUG]   → Last name search for '{search_last_name}' found {len(patients)} patients")
                    
                elif search_first_name:
                    # First name only search
                    patients = self.db.search_patients(search_first_name, limit=20)
                    print(f"[QUERY DEBUG]   → First name search for '{search_first_name}' found {len(patients)} patients")
                
                if patients:
                    print(f"[QUERY DEBUG]   → Found {len(patients)} patients total")
                    patient_list = []
                    for p in patients:
                        patient_list.append({
                            'patient_id': p.get('patient_id'),
                            'patient_name': p.get('patient_name'),
                            'dob': p.get('dob'),
                            'total_studies': p.get('total_studies', 0),
                        })
                    
                    # If this is a SIIM query for a specific patient, mark it as such
                    filter_type = 'siim_patient' if is_asking_for_siim else 'patient_name'
                    
                    return {
                        'success': True,
                        'query': query,
                        'filter_type': filter_type,
                        'search_firstname': search_first_name,
                        'search_lastname': search_last_name,
                        'filtered_patients': patient_list,
                        'total_found': len(patients),
                    }
                elif search_first_name or search_last_name:
                    print(f"[QUERY DEBUG]   → No patients found for firstname={search_first_name}, lastname={search_last_name}")
                    # Return "not found" result - don't fall through to other logic
                    return {
                        'success': False,
                        'filter_type': 'patient_name',
                        'search_firstname': search_first_name,
                        'search_lastname': search_last_name,
                        'filtered_patients': [],
                        'total_found': 0,
                    }
                else:
                    print(f"[QUERY DEBUG]   → No names extracted, falling through...")
                    pass
            
            # ===== PRIORITY 1.5: If only SIIM keyword without specific patient name, show all SIIM patients =====
            if is_asking_for_siim:
                print(f"[QUERY DEBUG]   → SIIM query detected (no specific patient)")
                return {'success': False, 'filter_type': 'siim_ingest'}
            
            # ===== PRIORITY 2: INTENT DETECTION FOR HEALTH GRAPH QUERIES =====
            is_asking_for_summary = any(word in query_lower for word in [
                'how many', 'total', 'summary', 'overview', 'what documents',
                'show me', 'list', 'give me', 'what do i have'
            ])
            
            print(f"[QUERY DEBUG]   is_summary={is_asking_for_summary}")
            
            # Extract year from query (for studies done in year OR birth year)
            filter_year = None
            filter_birth_year = None
            
            # Check if asking about birth year/DOB
            is_birth_year_query = any(phrase in query_lower for phrase in [
                'born in', 'dob', 'birth year', 'born', 'birthdate', 'date of birth',
                'age', 'aged', 'year old'
            ])
            
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query_lower)
            if year_match:
                year = year_match.group(1)
                if is_birth_year_query:
                    filter_birth_year = year
                    print(f"[QUERY DEBUG]   → Birth year filter: {year}")
                else:
                    filter_year = year
                    print(f"[QUERY DEBUG]   → Date filter: year {year}")
            
            # If asking for summary with birth year, filter patients by DOB year
            if is_asking_for_summary and filter_birth_year:
                # Get all patients and filter by birth year
                all_patients = self.db.search_patients('', limit=100000)
                filtered_patients = []
                
                for p in all_patients:
                    dob = (p.get('dob') or '').strip()
                    # DOB format is typically YYYYMMDD
                    if dob.startswith(filter_birth_year):
                        filtered_patients.append(p)
                
                print(f"[QUERY DEBUG]   → Found {len(filtered_patients)} patients born in {filter_birth_year}")
                
                if filtered_patients:
                    patient_list = []
                    for p in filtered_patients[:20]:
                        patient_list.append({
                            'patient_id': p.get('patient_id'),
                            'patient_name': p.get('patient_name'),
                            'dob': p.get('dob'),
                            'total_studies': p.get('total_studies', 0),
                        })
                    
                    return {
                        'success': True,
                        'query': query,
                        'filter_type': 'birth_year_filter',
                        'filter_birth_year': filter_birth_year,
                        'filtered_patients': patient_list,
                        'total_found': len(filtered_patients),
                    }
                else:
                    print(f"[QUERY DEBUG]   → No patients found born in {filter_birth_year}")
            
            # If asking for summary with study year, filter studies by year
            if is_asking_for_summary and filter_year:
                # Query with date range to get all studies from that year
                start_date = f"{filter_year}0101"
                end_date = f"{filter_year}1231"
                studies = self.db.search_studies(start_date=start_date, end_date=end_date, limit=50000)
                
                patients_dict = {}
                for study in studies:
                    pid = study.get('patient_id')
                    if pid not in patients_dict:
                        patients_dict[pid] = {'patient': None, 'studies': []}
                    patients_dict[pid]['studies'].append(study)
                
                for pid in list(patients_dict.keys())[:20]:
                    p = self.db.get_patient(pid)
                    if p:
                        patients_dict[pid]['patient'] = p
                
                return {
                    'success': True,
                    'query': query,
                    'filter_type': 'year_filter',
                    'filter_year': filter_year,
                    'filtered_patients': [
                        {
                            'patient_id': v['patient'].get('patient_id') if v['patient'] else pid,
                            'patient_name': v['patient'].get('patient_name') if v['patient'] else 'Unknown',
                            'total_studies': len(v['studies']),
                            'studies': v['studies'][:3],
                        } for pid, v in list(patients_dict.items())[:10]
                    ],
                    'total_studies_found': len(studies),
                }
            
            # If asking for summary/overview (without year), return generic stats
            if is_asking_for_summary:
                patients = self.db.search_patients('', limit=20)
                patient_list = []
                for p in patients:
                    patient_list.append({
                        'patient_id': p.get('patient_id'),
                        'patient_name': p.get('patient_name'),
                        'total_studies': p.get('total_studies', 0),
                    })
                
                return {
                    'success': True,
                    'filter_type': 'summary',
                    'stats': stats,
                    'patients': patient_list,
                    'total_patients': stats.get('patients', 0),
                    'total_studies': stats.get('studies', 0),
                    'total_files': stats.get('files', 0),
                }
            
            # Extract modality from query
            modality_map = {
                'ct': 'CT', 'mri': 'MR', 'xray': 'CR', 'x-ray': 'CR', 
                'ultrasound': 'US', 'mammogram': 'MG', 'fluoroscopy': 'RF',
                'ct scan': 'CT', 'ct scans': 'CT', 'mri scan': 'MR'
            }
            filter_modality = None
            for term, mod in modality_map.items():
                if term in query_lower:
                    filter_modality = mod
                    break
            
            # Extract body part
            body_parts = ['chest', 'abdomen', 'brain', 'spine', 'pelvis', 'breast', 'knee', 'shoulder', 'head']
            filter_body_part = None
            for bp in body_parts:
                if bp in query_lower:
                    filter_body_part = bp
                    break
            
            # If asking for modality or body part, search studies
            if filter_modality or filter_body_part:
                studies = self.db.search_studies(
                    modality=filter_modality,
                    body_part=filter_body_part,
                    limit=1000
                )
                
                if studies:
                    patients_dict = {}
                    for study in studies:
                        pid = study.get('patient_id')
                        if pid not in patients_dict:
                            patients_dict[pid] = {'patient': None, 'studies': []}
                        patients_dict[pid]['studies'].append(study)
                    
                    for pid in list(patients_dict.keys())[:20]:
                        p = self.db.get_patient(pid)
                        if p:
                            patients_dict[pid]['patient'] = p
                    
                    return {
                        'success': True,
                        'query': query,
                        'filter_type': 'modality_or_bodypart',
                        'filter_modality': filter_modality,
                        'filter_body_part': filter_body_part,
                        'filtered_patients': [
                            {
                                'patient_id': v['patient'].get('patient_id') if v['patient'] else pid,
                                'patient_name': v['patient'].get('patient_name') if v['patient'] else 'Unknown',
                                'total_studies': len(v['studies']),
                                'studies': v['studies'][:5],
                            } for pid, v in list(patients_dict.items())[:10]
                        ],
                        'total_studies_found': len(studies),
                    }
            
            # Default: return generic summary
            patients = self.db.search_patients('', limit=20)
            patient_list = []
            for p in patients:
                patient_list.append({
                    'patient_id': p.get('patient_id'),
                    'patient_name': p.get('patient_name'),
                    'total_studies': p.get('total_studies', 0),
                })
            
            return {
                'success': True,
                'filter_type': 'summary',
                'stats': stats,
                'patients': patient_list,
                'total_patients': stats.get('patients', 0),
                'total_studies': stats.get('studies', 0),
                'total_files': stats.get('files', 0),
            }
        except Exception as e:
            return {'error': str(e), 'patients': 0}

    # ------------------------------------------------------------------
    # DICOM detection (extensionless files)
    # ------------------------------------------------------------------

    def _is_dicom_file(self, file_path: str) -> bool:
        """
        Check if a file is a DICOM file by reading magic bytes.
        
        DICOM files start with:
        - 128 bytes of preamble (zeros or arbitrary)
        - Then 'DICM' at offset 128
        
        This allows detection of DICOM files without .dcm extension.
        """
        try:
            with open(file_path, "rb") as fh:
                # Check for DICM signature at offset 128
                fh.seek(128)
                signature = fh.read(4)
                return signature == b'DICM'
        except Exception:
            return False

    # ------------------------------------------------------------------
    # DICOM parsing
    # ------------------------------------------------------------------

    def _parse_dicom(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a DICOM file, returning metadata entry. Falls back to raw-byte sniff."""
        try:
            import pydicom
            import warnings
            warnings.filterwarnings('ignore', category=UserWarning, module='pydicom')
            
            _result = [None]
            _done = threading.Event()
            
            def _read():
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)
                    entry: Dict[str, Any] = {
                        "file_path": file_path,
                        "file_type": "dicom",
                        "indexed_at": datetime.utcnow().isoformat(),
                    }
                    for tag_name, field in DICOM_TAG_MAP.items():
                        try:
                            value = getattr(ds, tag_name, None)
                            if value is not None:
                                entry[field] = str(value).strip()
                        except Exception:
                            pass

                    # Additional DICOM fields
                    try:
                        if hasattr(ds, 'PatientAge') and ds.PatientAge:
                            entry['patient_age'] = str(ds.PatientAge).strip()
                        if hasattr(ds, 'PatientSex') and ds.PatientSex:
                            entry['patient_sex'] = str(ds.PatientSex).strip()
                        if hasattr(ds, 'StudyTime') and ds.StudyTime:
                            entry['study_time'] = str(ds.StudyTime).strip()
                        if hasattr(ds, 'SeriesTime') and ds.SeriesTime:
                            entry['series_time'] = str(ds.SeriesTime).strip()
                        if hasattr(ds, 'Manufacturer') and ds.Manufacturer:
                            entry['manufacturer'] = str(ds.Manufacturer).strip()
                        if hasattr(ds, 'ManufacturerModelName') and ds.ManufacturerModelName:
                            entry['equipment_model'] = str(ds.ManufacturerModelName).strip()
                        if hasattr(ds, 'NumberOfFrames') and ds.NumberOfFrames:
                            entry['number_of_frames'] = str(ds.NumberOfFrames).strip()
                        if hasattr(ds, 'Rows') and ds.Rows:
                            entry['image_height'] = int(ds.Rows)
                        if hasattr(ds, 'Columns') and ds.Columns:
                            entry['image_width'] = int(ds.Columns)
                    except Exception:
                        pass

                    # Normalise study date
                    raw_date = entry.get("study_date", "")
                    if re.match(r"^\d{8}$", raw_date):
                        entry["study_date_display"] = (
                            f"{raw_date[6:8]}/{raw_date[4:6]}/{raw_date[0:4]}"
                        )

                    raw_mod = entry.get("modality", "").upper()
                    entry["modality_label"] = MODALITY_LABELS.get(raw_mod, raw_mod)

                    body_hint = (
                        (entry.get("body_part", "") or "")
                        + " "
                        + (entry.get("study_description", "") or "")
                        + " "
                        + (entry.get("series_description", "") or "")
                    )
                    entry["body_part_normalized"] = self._normalize_body_part(body_hint)
                    entry["summary"] = self._dicom_summary(entry)
                    entry["relevance_keywords"] = self._keywords_from_dicom(entry)
                    _result[0] = entry
                    _done.set()
                except Exception as e:
                    print(f'[_parse_dicom] pydicom read failed for {file_path}: {e}, using fallback')
                    _result[0] = self._parse_dicom_fallback(file_path)
                    _done.set()

            _t = threading.Thread(target=_read, daemon=True)
            _t.start()
            _t.join(timeout=8)

            if _done.is_set():
                result = _result[0] if _result[0] is not None else self._parse_dicom_fallback(file_path)
                if result:
                    patient_id = result.get('patient_id')
                    study_uid = result.get('study_uid')
                    print(f"[_parse_dicom] Parsed {os.path.basename(file_path)}: patient_id={patient_id}, study_uid={study_uid}")
                return result

            print(f'[_parse_dicom] timed out for {file_path}, using fallback')
            return self._parse_dicom_fallback(file_path)

        except ImportError:
            return self._parse_dicom_fallback(file_path)
        except Exception:
            return self._parse_dicom_fallback(file_path)

    def _parse_dicom_fallback(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract basic info from DICOM without pydicom by reading raw bytes."""
        try:
            with open(file_path, "rb") as fh:
                raw = fh.read(8192)
            text_parts = re.findall(rb"[ -~]{4,}", raw)
            readable = [p.decode("ascii", errors="ignore").strip() for p in text_parts]
            readable = [r for r in readable if len(r) >= 4]

            entry: Dict[str, Any] = {
                "file_path": file_path,
                "file_type": "dicom",
                "indexed_at": datetime.utcnow().isoformat(),
                "summary": "DICOM medical imaging study",
                "relevance_keywords": ["dicom", "medical image"],
            }

            for hint in readable:
                h = hint.upper()
                for mod_code, mod_label in MODALITY_LABELS.items():
                    if mod_code in h:
                        entry["modality"] = mod_code
                        entry["modality_label"] = mod_label
                        break

            return entry
        except Exception:
            return None

    # ------------------------------------------------------------------
    # JP2 parsing
    # ------------------------------------------------------------------

    def _parse_jp2(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a JPEG2000 (JP2) file and extract metadata."""
        try:
            base_name = os.path.basename(file_path)
            for ext in ['.rst.jp2', '.rst.j2k', '.jp2', '.j2k']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break

            dir_name = os.path.dirname(file_path)

            # Search for companion DICOM
            potential_dicom_paths = [
                os.path.join(dir_name, 'DICOM', base_name + '.dcm'),
                os.path.join(dir_name, base_name + '.dcm'),
                os.path.join(dir_name, '..', 'DICOM', base_name + '.dcm'),
                os.path.join(dir_name, 'dcm', base_name + '.dcm'),
            ]

            for dcm_path in potential_dicom_paths:
                if os.path.exists(dcm_path):
                    entry = self._parse_dicom(dcm_path)
                    if entry:
                        entry['file_path'] = file_path
                        entry['file_type'] = 'image'
                        entry['original_dicom'] = dcm_path
                        if entry.get('summary'):
                            entry['summary'] = entry['summary'].replace('DICOM', 'JPEG2000 (DICOM-sourced)')
                        else:
                            entry['summary'] = 'JPEG2000 medical image (DICOM-sourced)'
                        if 'relevance_keywords' not in entry:
                            entry['relevance_keywords'] = []
                        entry['relevance_keywords'].extend(['image', 'jpeg2000', 'jp2', 'lossless', 'reversible'])
                        return entry

            # Parse JP2 header directly
            entry = self._parse_jp2_header(file_path)
            if entry:
                return entry

            # Final fallback
            stat = os.stat(file_path)
            return {
                'file_path': file_path,
                'file_type': 'image',
                'indexed_at': datetime.utcnow().isoformat(),
                'study_date_display': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d'),
                'summary': 'JPEG2000 medical image',
                'relevance_keywords': ['image', 'jpeg2000', 'jp2', 'scan', 'medical image'],
            }
        except Exception as e:
            import sys
            print(f'[SDOH] JP2 parse error for {file_path}: {e}', file=sys.stderr)
            return {
                'file_path': file_path,
                'file_type': 'image',
                'indexed_at': datetime.utcnow().isoformat(),
                'summary': 'JPEG2000 medical image (parse error)',
                'relevance_keywords': ['image', 'jpeg2000', 'jp2'],
            }

    def _parse_jp2_header(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract basic metadata from JP2 file header without external library."""
        try:
            import struct
            
            with open(file_path, 'rb') as f:
                header = f.read(12)
                if header[:4] != b'\x00\x00\x00\x0c' or header[4:8] != b'jP  ':
                    return None

                entry = {
                    'file_path': file_path,
                    'file_type': 'image',
                    'indexed_at': datetime.utcnow().isoformat(),
                    'modality': 'OT',
                    'modality_label': 'Optical/JPEG2000 Image',
                    'summary': 'JPEG2000 medical image',
                    'relevance_keywords': ['image', 'jpeg2000', 'jp2', 'scan'],
                }

                f.seek(0)
                data = f.read(65536)

                i = 12
                while i < len(data) - 8:
                    box_len_bytes = data[i:i+4]
                    box_type = data[i+4:i+8]

                    if len(box_len_bytes) < 4:
                        break

                    box_len = struct.unpack('>I', box_len_bytes)[0]
                    if box_len == 0:
                        box_len = len(data) - i
                    if box_len < 8 or box_len > 1000000:
                        i += 8
                        continue

                    if box_type == b'ihdr':
                        if i + 14 < len(data):
                            height, width = struct.unpack('>II', data[i+8:i+16])
                            entry['image_height'] = height
                            entry['image_width'] = width
                            entry['summary'] = f"JPEG2000 image ({width}x{height}px)"

                    elif box_type == b'colr':
                        if i + 11 < len(data):
                            colr_data = data[i+8:min(i+box_len, len(data))]
                            if len(colr_data) >= 3:
                                cs = struct.unpack('>I', b'\x00' + colr_data[1:4])[0]
                                cs_names = {0: 'sRGB', 1: 'Greyscale', 2: 'sYCC', 3: 'esRGB', 4: 'ROMMRGB', 5: 'Profiled', 6: 'Enumerated'}
                                entry['colorspace'] = cs_names.get(cs, f'CS{cs}')

                    i += box_len

                stat = os.stat(file_path)
                entry['study_date_display'] = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')

                return entry
        except Exception:
            return None

    # ------------------------------------------------------------------
    # PDF / text parsing
    # ------------------------------------------------------------------

    def _parse_pdf(self, file_path: str) -> Optional[Dict[str, Any]]:
        text = ""
        try:
            # pyrefly: ignore [missing-import]
            import pdfminer.high_level
            text = pdfminer.high_level.extract_text(file_path) or ""
        except (ImportError, Exception):
            pass

        if not text:
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                pass

        if not text:
            return {
                "file_path": file_path,
                "file_type": "pdf",
                "indexed_at": datetime.utcnow().isoformat(),
                "summary": "PDF medical document (text extraction unavailable — install pdfminer.six)",
                "document_type": "pdf",
                "relevance_keywords": ["document", "pdf"],
            }

        return self._build_text_entry(file_path, "pdf", text)

    def _parse_text(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            return self._build_text_entry(file_path, "text", text)
        except Exception:
            return None

    def _build_text_entry(
        self, file_path: str, file_type: str, text: str
    ) -> Dict[str, Any]:
        text_lower = text.lower()
        entry: Dict[str, Any] = {
            "file_path": file_path,
            "file_type": file_type,
            "indexed_at": datetime.utcnow().isoformat(),
            "text_preview": text[:400].strip(),
        }

        # Date detection
        date_match = re.search(
            r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})\b", text
        )
        if date_match:
            entry["study_date_display"] = date_match.group(0)

        # Modality detection
        for mod_code, mod_label in MODALITY_LABELS.items():
            if mod_code.lower() in text_lower or mod_label.lower() in text_lower:
                entry["modality"] = mod_code
                entry["modality_label"] = mod_label
                break
        if "modality" not in entry:
            for term, mod in [
                ("x-ray", "CR"), ("xray", "CR"), ("ultrasound", "US"),
                ("computed tomography", "CT"), ("magnetic resonance", "MR"),
                ("pet scan", "PT"), ("nuclear medicine", "NM"),
                ("mammograph", "MG"), ("fluoroscop", "RF"),
            ]:
                if term in text_lower:
                    entry["modality"] = mod
                    entry["modality_label"] = MODALITY_LABELS.get(mod, mod)
                    break

        # Body part
        entry["body_part_normalized"] = self._normalize_body_part(text)

        # Document type
        doc_type = "report"
        if any(
            w in text_lower
            for w in ["prescribed", "dispense", "tablet", "capsule", " mg ", "dosage", "medication", "script", "prescription"]
        ):
            doc_type = "script"
        elif any(
            w in text_lower
            for w in ["referred", "referral", "please see", "please assess", "kindly see", "review this patient", "for specialist"]
        ):
            doc_type = "referral"
        elif any(
            w in text_lower
            for w in ["discharge", "admitted", "ward", "theatre", "surgery", "post-operative", "operation"]
        ):
            doc_type = "discharge_summary"
        elif any(
            w in text_lower
            for w in [
                "haemoglobin", "haematocrit", "wbc", "rbc", "platelet",
                "creatinine", "sodium", "potassium", "glucose", "cholesterol",
                "urea", "albumin", "bilirubin", "alt ", "ast ", "ggt",
            ]
        ):
            doc_type = "lab_results"
        entry["document_type"] = doc_type

        # Clinical term extraction
        found_terms = [
            term for term in CLINICAL_PLAIN_LANGUAGE if term in text_lower
        ]
        entry["clinical_terms"] = found_terms[:10]

        # Plain-language summary
        entry["summary"] = self._text_summary(entry)
        entry["relevance_keywords"] = self._keywords_from_text(entry, text)
        return entry

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize_body_part(self, text: str) -> Optional[str]:
        text_lower = (text or "").lower()
        for part, terms in BODY_PART_KEYWORDS.items():
            if any(t in text_lower for t in terms):
                return part
        return None

    def _dicom_summary(self, entry: Dict[str, Any]) -> str:
        parts = []
        if entry.get("modality_label"):
            parts.append(entry["modality_label"])
        if entry.get("body_part_normalized"):
            parts.append(f"of the {entry['body_part_normalized']}")
        elif entry.get("body_part"):
            parts.append(f"({entry['body_part']})")
        if entry.get("study_date_display"):
            parts.append(f"dated {entry['study_date_display']}")
        if entry.get("institution"):
            parts.append(f"from {entry['institution']}")
        return " ".join(parts) if parts else "DICOM medical imaging study"

    def _text_summary(self, entry: Dict[str, Any]) -> str:
        label_map = {
            "script": "Medication script",
            "referral": "Referral letter",
            "discharge_summary": "Discharge summary",
            "lab_results": "Laboratory results",
            "report": "Medical report",
        }
        label = label_map.get(entry.get("document_type", ""), "Medical document")
        parts = [label]
        if entry.get("modality_label"):
            parts.append(f"— {entry['modality_label']}")
        if entry.get("body_part_normalized"):
            parts.append(f"({entry['body_part_normalized']})")
        if entry.get("study_date_display"):
            parts.append(f"dated {entry['study_date_display']}")
        return " ".join(parts)

    def _keywords_from_dicom(self, entry: Dict[str, Any]) -> List[str]:
        kw = []
        for field in ["modality", "body_part", "study_description", "series_description"]:
            v = (entry.get(field) or "").lower().strip()
            if v:
                kw.extend(v.split())
        return list(set(kw))

    def _keywords_from_text(self, entry: Dict[str, Any], text: str) -> List[str]:
        kw = list(entry.get("clinical_terms") or [])
        if entry.get("body_part_normalized"):
            kw.append(entry["body_part_normalized"])
        if entry.get("modality"):
            kw.append(entry["modality"].lower())
        if entry.get("document_type"):
            kw.append(entry["document_type"])
        return list(set(kw))

    # ------------------------------------------------------------------
    # Quick sample files (for large PACS archives)
    # ------------------------------------------------------------------

    def quick_sample_files(
        self,
        folder_path: str,
        max_files: int = 20,
        timeout_sec: int = 25,
        extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Quickly sample files from a large PACS archive using DFS traversal.
        
        This method uses os.scandir for fast directory traversal and returns
        the first N files found, even on very large network shares.
        
        Returns a dict with:
          - files: list of file info dicts
          - count: number of files found
          - elapsed_sec: time taken
          - method: 'dfs-scandir'
          - error: error message if any
        """
        start_time = time.time()
        files_found: List[Dict[str, Any]] = []
        ext_filter = set(extensions) if extensions else self.SUPPORTED_EXTENSIONS
        
        def _dfs_scan(path: str, depth: int = 0) -> None:
            if len(files_found) >= max_files:
                return
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        if len(files_found) >= max_files:
                            return
                        try:
                            if entry.is_file():
                                ext = os.path.splitext(entry.name)[1].lower()
                                # Check for known extensions
                                if ext in ext_filter:
                                    try:
                                        stat = entry.stat()
                                        files_found.append({
                                            "FullName": entry.path,
                                            "Extension": ext,
                                            "Length": stat.st_size,
                                            "Name": entry.name,
                                        })
                                    except Exception:
                                        pass
                                # Check for extensionless DICOM files
                                elif ext == "" and self._is_dicom_file(entry.path):
                                    try:
                                        stat = entry.stat()
                                        files_found.append({
                                            "FullName": entry.path,
                                            "Extension": ".dcm",  # Treat as DICOM
                                            "Length": stat.st_size,
                                            "Name": entry.name,
                                        })
                                    except Exception:
                                        pass
                            elif entry.is_dir() and depth < 20:
                                _dfs_scan(entry.path, depth + 1)
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                pass

        # Check if directory is accessible
        if not _win_isdir(folder_path):
            return {
                "files": [],
                "count": 0,
                "elapsed_sec": time.time() - start_time,
                "method": "dfs-scandir",
                "error": f"Directory not accessible: {folder_path}",
            }

        try:
            _dfs_scan(folder_path)
        except Exception as e:
            return {
                "files": [],
                "count": 0,
                "elapsed_sec": time.time() - start_time,
                "method": "dfs-scandir",
                "error": f"Scan failed: {str(e)}",
            }

        return {
            "files": files_found,
            "count": len(files_found),
            "elapsed_sec": time.time() - start_time,
            "method": "dfs-scandir",
        }

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan_folder(self, folder_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Recursively scan *folder_path* and add all new medical files to the
        local index.  Returns a summary: scanned / new / total counts.
        
        Args:
            folder_path: Path to folder to scan
            progress_callback: Optional callable that receives (scanned, new_entries, current_path) for progress updates
        """
        # Resolve drive-letter to UNC if the path isn't accessible as-is.
        # This handles the case where run.py runs in an elevated/service context
        # that can't see session-mapped drives like X:\ but CAN access the
        # underlying UNC path (\\\\server\\share\\...).
        resolved_path = _resolve_drive_unc(folder_path) if sys.platform == 'win32' else folder_path
        if resolved_path != folder_path:
            print(f"[scan_folder] Resolved {folder_path!r} -> {resolved_path!r} via net use")
        else:
            resolved_path = folder_path

        # Use Windows-aware check for network drives
        print(f"[DEBUG scan_folder] Checking folder: {resolved_path}")
        if not _win_isdir(resolved_path):
            print(f"[DEBUG scan_folder] _win_isdir failed for {resolved_path}")
            return {
                "scanned": 0,
                "new": 0,
                "error": f"[WinError 3] The system cannot find the path specified: {folder_path!r}",
            }
        print(f"[DEBUG scan_folder] _win_isdir passed, starting scan...")
        folder_path = resolved_path  # use the resolved path for actual I/O


        existing_paths = {e["file_path"] for e in self._index}
        scanned = 0
        new_entries = 0
        last_progress_report = 0

        max_depth = 20  # Allow deep PACS directory structures (year/month/day/patient/DICOM)
        skipped_no_ext = 0
        def _dfs_scan(path: str, depth: int = 0) -> None:
            nonlocal scanned, new_entries, skipped_no_ext, last_progress_report
            if depth > max_depth:
                print(f"[DEBUG] Max depth {max_depth} reached at {path}")
                return
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        try:
                            if entry.is_file():
                                ext = os.path.splitext(entry.name)[1].lower()
                                fp_str = entry.path
                                
                                # Check if file has known extension
                                if ext in self.SUPPORTED_EXTENSIONS:
                                    scanned += 1
                                    # Report progress every 50 files
                                    if progress_callback and scanned - last_progress_report >= 50:
                                        progress_callback(scanned, new_entries, path)
                                        last_progress_report = scanned
                                    if fp_str not in existing_paths:
                                        parsed_entry = None
                                        if ext == ".dcm":
                                            parsed_entry = self._parse_dicom(fp_str)
                                        elif ext == ".pdf":
                                            parsed_entry = self._parse_pdf(fp_str)
                                        elif ext in {".txt", ".md"}:
                                            parsed_entry = self._parse_text(fp_str)
                                        elif ext in {".jp2", ".j2k"}:
                                            parsed_entry = self._parse_jp2(fp_str)
                                        elif ext in {".jpg", ".jpeg", ".png"}:
                                            parsed_entry = {
                                                "file_path": fp_str,
                                                "file_type": "image",
                                                "indexed_at": datetime.utcnow().isoformat(),
                                                "summary": f"Scanned image — {entry.name}",
                                                "relevance_keywords": ["image", "scan", "document"],
                                            }
                                        if parsed_entry:
                                            self._index.append(parsed_entry)
                                            self._write_to_sqlite(parsed_entry)
                                            new_entries += 1
                                # Check for extensionless DICOM files (no extension or unknown extension)
                                elif ext == "" and fp_str not in existing_paths:
                                    # Try to detect DICOM by magic bytes
                                    if self._is_dicom_file(fp_str):
                                        scanned += 1
                                        parsed_entry = self._parse_dicom(fp_str)
                                        if parsed_entry:
                                            self._index.append(parsed_entry)
                                            self._write_to_sqlite(parsed_entry)
                                            new_entries += 1
                            elif entry.is_dir():
                                _dfs_scan(entry.path, depth + 1)
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError) as e:
                if depth == 0:
                    raise e

        start_time = time.time()
        root_error = None
        try:
            _dfs_scan(folder_path)
        except (PermissionError, OSError) as e:
            root_error = str(e)
            
        elapsed = time.time() - start_time
        self._save_index()
        
        print(f"[scan_folder DEBUG] Scan complete: scanned={scanned}, new_entries={new_entries}, total_indexed={len(self._index)}, elapsed={elapsed:.2f}s")
        
        return {
            "folder": folder_path,
            "scanned": scanned,
            "new": new_entries,
            "total_indexed": len(self._index),
            "skipped_no_ext": skipped_no_ext,
            "truncated": False,
            "error": root_error,
            "dicom_dir_count": 0,
            "empty_dicom_dir_count": 0,
            "dicom_dir_samples": [],
            "elapsed_sec": elapsed,
        }

    def scan_all_default_dirs(self) -> Dict[str, Any]:
        """Scan every directory in self.scan_dirs that actually exists."""
        total_scanned = 0
        total_new = 0
        scanned_dirs: List[str] = []
        for d in self.scan_dirs:
            if os.path.isdir(d):
                result = self.scan_folder(d)
                total_scanned += result.get("scanned", 0)
                total_new += result.get("new", 0)
                scanned_dirs.append(d)
        return {
            "scanned_dirs": scanned_dirs,
            "total_scanned": total_scanned,
            "total_new": total_new,
            "total_indexed": len(self._index),
        }

    # ------------------------------------------------------------------
    # Search / Retrieval
    # ------------------------------------------------------------------

    def search(
        self,
        modality: Optional[str] = None,
        body_part: Optional[str] = None,
        doc_type: Optional[str] = None,
        text_query: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Score every indexed entry against the supplied filters and return the
        top *limit* results sorted by score then by recency.
        """
        query_lower = (text_query or "").lower()
        results: List[Dict[str, Any]] = []

        for entry in self._index:
            score = 0

            if modality:
                entry_mod = (entry.get("modality") or "").upper()
                if entry_mod == modality.upper():
                    score += 10
                elif modality.upper() in (entry.get("modality_label") or "").upper():
                    score += 6

            if body_part:
                entry_bp = (entry.get("body_part_normalized") or "").lower()
                if entry_bp == body_part.lower():
                    score += 10
                elif body_part.lower() in (entry.get("body_part") or "").lower():
                    score += 6

            if doc_type:
                if (entry.get("document_type") or "").lower() == doc_type.lower():
                    score += 8

            if query_lower:
                for field in ["summary", "text_preview", "study_description", "series_description"]:
                    if query_lower in (entry.get(field) or "").lower():
                        score += 5
                for kw in (entry.get("relevance_keywords") or []):
                    if kw and kw in query_lower:
                        score += 3

            # Include the entry if any filter matched (score > 0) or no filter given
            if score > 0 or not any([modality, body_part, doc_type, text_query]):
                results.append({**entry, "_score": score})

        results.sort(
            key=lambda x: (x.get("_score", 0), x.get("study_date", "9999")),
            reverse=True,
        )
        return results[:limit]

    def search_for_visit(self, visit_description: str) -> Dict[str, Any]:
        """
        Given a plain-language visit description such as
        'I need a CT scan of my chest', return a ranked list of local
        documents the patient should bring plus context for the agent.
        """
        text_lower = visit_description.lower()

        # Detect modality
        modality: Optional[str] = None
        for mod_code, mod_label in MODALITY_LABELS.items():
            if mod_code.lower() in text_lower or mod_label.lower() in text_lower:
                modality = mod_code
                break
        if not modality:
            for term, mod in [
                ("x-ray", "CR"),
                ("xray", "CR"),
                ("ultrasound", "US"),
                ("computed tomography", "CT"),
                ("ct scan", "CT"),
                ("mri", "MR"),
                ("magnetic resonance", "MR"),
                ("pet scan", "PT"),
                ("nuclear medicine", "NM"),
                ("mammog", "MG"),
            ]:
                if term in text_lower:
                    modality = mod
                    break

        # Detect body part
        body_part: Optional[str] = None
        for part, terms in BODY_PART_KEYWORDS.items():
            if any(t in text_lower for t in terms):
                body_part = part
                break

        # Detect specialist type → preferred document types
        preferred_doc_types: List[str] = []
        if any(w in text_lower for w in ["cardiolog", "heart", "cardiac"]):
            preferred_doc_types = ["report", "lab_results", "discharge_summary"]
        elif any(w in text_lower for w in ["oncolog", "cancer", "chemotherapy", "radiation"]):
            preferred_doc_types = ["report", "lab_results", "referral"]
        elif any(w in text_lower for w in ["orthop", "bone", "fracture", "joint"]):
            preferred_doc_types = ["report", "referral"]
        elif any(w in text_lower for w in ["surgeon", "surgery", "operation", "procedure"]):
            preferred_doc_types = ["report", "discharge_summary", "lab_results", "referral"]
        elif any(w in text_lower for w in ["gp", "general practitioner", "family doctor"]):
            preferred_doc_types = ["report", "lab_results", "script"]
        else:
            preferred_doc_types = ["report", "lab_results"]

        all_matches: List[Dict[str, Any]] = []
        seen_paths: set = set()

        def _add_if_new(entries: List[Dict[str, Any]]) -> None:
            for e in entries:
                fp = e.get("file_path", "")
                if fp not in seen_paths:
                    all_matches.append(e)
                    seen_paths.add(fp)

        # 1. Direct modality match
        if modality:
            _add_if_new(self.search(modality=modality, limit=5))

        # 2. Body part match
        if body_part:
            _add_if_new(self.search(body_part=body_part, limit=5))

        # 3. Preferred document types for this visit
        for dt in preferred_doc_types:
            _add_if_new(self.search(doc_type=dt, limit=3))

        # 4. Always include current medication scripts (always relevant)
        scripts = self.search(doc_type="script", limit=2)
        for s in scripts:
            s["_always_relevant"] = True
            fp = s.get("file_path", "")
            if fp not in seen_paths:
                all_matches.append(s)
                seen_paths.add(fp)

        # 5. Always include recent referrals
        referrals = self.search(doc_type="referral", limit=2)
        _add_if_new(referrals)

        all_matches.sort(key=lambda x: x.get("_score", 0), reverse=True)

        return {
            "visit_description": visit_description,
            "detected_modality": modality,
            "detected_body_part": body_part,
            "matched_documents": all_matches[:8],
            "total_indexed": len(self._index),
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        if not self._index:
            return {
                "total": 0,
                "by_type": {},
                "by_modality": {},
                "by_body_part": {},
                "last_indexed": "never",
            }
        by_type: Dict[str, int] = {}
        by_modality: Dict[str, int] = {}
        by_body_part: Dict[str, int] = {}
        for entry in self._index:
            ft = entry.get("file_type", "unknown")
            by_type[ft] = by_type.get(ft, 0) + 1
            mod = entry.get("modality_label") or entry.get("modality")
            if mod:
                by_modality[mod] = by_modality.get(mod, 0) + 1
            bp = entry.get("body_part_normalized")
            if bp:
                by_body_part[bp] = by_body_part.get(bp, 0) + 1
        last_indexed = max(
            (e.get("indexed_at", "") for e in self._index), default="never"
        )
        return {
            "total": len(self._index),
            "by_type": by_type,
            "by_modality": by_modality,
            "by_body_part": by_body_part,
            "last_indexed": last_indexed,
        }

    # ------------------------------------------------------------------
    # History pack (practice-facing export)
    # ------------------------------------------------------------------

    def build_history_pack(
        self,
        user_alias: str,
        visit_description: str,
        approved_file_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build a patient-approved history pack for sharing with a practice.

        If *approved_file_paths* is supplied, only those files are included.
        Otherwise, the top matches for *visit_description* are used.

        Returns a dict with:
          - history_pack_markdown : the full document as Markdown text
          - filename              : suggested filename
          - document_count        : number of documents included
          - entries               : list of index entries included
        """
        if approved_file_paths:
            approved_set = set(approved_file_paths)
            entries = [e for e in self._index if e.get("file_path") in approved_set]
        else:
            result = self.search_for_visit(visit_description)
            entries = result.get("matched_documents", [])

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        lines = [
            "# PATIENT HISTORY PACK",
            f"**Patient alias:** {user_alias}",
            f"**Prepared for:** {visit_description}",
            f"**Generated:** {now} UTC",
            f"**Data source:** Patient-owned local storage — no cloud upload.",
            "",
            "---",
            "",
            "## Documents Included",
            "",
        ]

        if not entries:
            lines.append("*No indexed documents found for this visit. "
                         "Ask the patient to add their medical files to their "
                         "local medical records folder and re-index.*")
        else:
            for i, entry in enumerate(entries, 1):
                lines.append(f"### {i}. {entry.get('summary', 'Medical document')}")
                lines.append(f"- **File:** `{os.path.basename(entry.get('file_path', 'unknown'))}`")
                if entry.get("study_date_display"):
                    lines.append(f"- **Date:** {entry['study_date_display']}")
                if entry.get("modality_label"):
                    lines.append(f"- **Type:** {entry['modality_label']}")
                if entry.get("body_part_normalized"):
                    lines.append(f"- **Body area:** {entry['body_part_normalized'].capitalize()}")
                if entry.get("document_type"):
                    label = entry["document_type"].replace("_", " ").capitalize()
                    lines.append(f"- **Document type:** {label}")
                if entry.get("institution"):
                    lines.append(f"- **Source:** {entry['institution']}")
                if entry.get("referring_physician"):
                    lines.append(f"- **Clinician:** {entry['referring_physician']}")
                if entry.get("text_preview"):
                    lines.append(f"- **Preview:** {entry['text_preview'][:200]}…")
                if entry.get("clinical_terms"):
                    terms = ", ".join(entry["clinical_terms"][:5])
                    lines.append(f"- **Clinical terms:** {terms}")
                lines.append("")

        lines += [
            "---",
            "",
            "## Interoperability Notes",
            "- Each document maps to a FHIR **DiagnosticReport** or **DocumentReference**.",
            "- DICOM studies map to **ImagingStudy** with AccessionNumber as identifier.",
            "- Medication scripts map to **MedicationRequest**.",
            "- Referral letters map to **ServiceRequest**.",
            "- This pack is local-first. Export to FHIR JSON only on explicit patient approval.",
            "",
            "---",
            "*This document was prepared by the SDOH Patient Continuity Agent.*",
        ]

        return {
            "history_pack_markdown": "\n".join(lines),
            "filename": "PATIENT_HISTORY_PACK.md",
            "document_count": len(entries),
            "entries": entries,
        }

    # ------------------------------------------------------------------
    # Clinical plain-language helper (used by agent)
    # ------------------------------------------------------------------

    @staticmethod
    def explain_clinical_terms(text: str) -> Dict[str, str]:
        """
        Return plain-language explanations for any clinical terms found in
        *text*.  Used by the agent when interpreting a pasted report.
        """
        text_lower = (text or "").lower()
        found: Dict[str, str] = {}
        for term, explanation in CLINICAL_PLAIN_LANGUAGE.items():
            if term in text_lower:
                found[term] = explanation
        return found