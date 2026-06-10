import ctypes
import configparser
import hashlib
import json
import os
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime
from urllib.parse import urljoin

try:
    import requests
except ImportError:  # pragma: no cover - requests is listed in requirements
    requests = None

try:
    import pydicom
except ImportError:  # pragma: no cover - optional at runtime
    pydicom = None


def _now_utc_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _clean_text(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text in {"", "None", "UNKNOWN", "Unknown"}:
        return ""
    return re.sub(r"\s+", " ", text)


def _normalize_identifier(value):
    text = _clean_text(value)
    return text or None


def _normalize_date(value):
    text = _clean_text(value)
    if not text:
        return None
    if re.fullmatch(r"\d{8}", text):
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    return text


def _soundex(value):
    text = _clean_text(value).upper()
    if not text:
        return ""

    letters = re.sub(r"[^A-Z]", "", text)
    if not letters:
        return ""

    first_letter = letters[0]
    mapping = {
        "B": "1", "F": "1", "P": "1", "V": "1",
        "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
        "D": "3", "T": "3",
        "L": "4",
        "M": "5", "N": "5",
        "R": "6",
    }

    encoded = [first_letter]
    previous_code = mapping.get(first_letter, "")
    for letter in letters[1:]:
        code = mapping.get(letter, "")
        if code != previous_code and code:
            encoded.append(code)
        previous_code = code

    return ("".join(encoded) + "000")[:4]


def _stable_hash(*parts):
    digest = hashlib.sha1("|".join(_clean_text(part) for part in parts).encode("utf-8")).hexdigest()
    return digest[:16].upper()


def _json_value(value):
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=True)


class PACSContinuityRegistry:
    """Read-only local continuity registry for PACS, FHIR, DICOMweb, and NAS sources."""

    def __init__(self, workspace_path=None, db_path=None, config_path=None, timeout_seconds=10):
        self.workspace_path = workspace_path or os.getcwd()
        self.instance_path = os.path.join(self.workspace_path, "instance")
        self.db_path = db_path or os.path.join(self.instance_path, "pacs_continuity_registry.db")
        self.config_path = config_path or os.path.join(self.workspace_path, "config.ini")
        self.timeout_seconds = timeout_seconds
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registry_sources (
                    source_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_label TEXT NOT NULL,
                    source_location TEXT,
                    data_class TEXT NOT NULL,
                    last_scan_at TEXT,
                    last_status TEXT,
                    details_json TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS empi_patients (
                    empi_id TEXT PRIMARY KEY,
                    national_id TEXT UNIQUE,
                    issuer_patient_id TEXT,
                    issuer_of_identifier TEXT,
                    patient_name TEXT,
                    phonetic_name TEXT,
                    birth_date TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    match_rule TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_empi_patients_lookup ON empi_patients (phonetic_name, birth_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_empi_patients_name_birth ON empi_patients (patient_name, birth_date)")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS source_identity_links (
                    source_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_location TEXT,
                    source_patient_key TEXT NOT NULL,
                    empi_id TEXT NOT NULL,
                    patient_name TEXT,
                    birth_date TEXT,
                    national_id TEXT,
                    issuer_patient_id TEXT,
                    issuer_of_identifier TEXT,
                    match_rule TEXT,
                    metadata_json TEXT,
                    last_seen_at TEXT,
                    UNIQUE(source_type, source_location, source_patient_key)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS imaging_studies (
                    study_instance_uid TEXT PRIMARY KEY,
                    empi_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_location TEXT,
                    modality TEXT,
                    study_date TEXT,
                    study_description TEXT,
                    accession_number TEXT,
                    body_part TEXT,
                    series_count INTEGER DEFAULT 0,
                    instance_count INTEGER DEFAULT 0,
                    storage_tier TEXT,
                    source_patient_key TEXT,
                    metadata_json TEXT,
                    last_seen_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_imaging_studies_empi_date ON imaging_studies (empi_id, study_date DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_imaging_studies_source ON imaging_studies (source_type, source_location)")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS storage_assets (
                    asset_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_location TEXT,
                    asset_path TEXT NOT NULL,
                    asset_name TEXT,
                    asset_kind TEXT,
                    asset_family TEXT,
                    size_bytes INTEGER DEFAULT 0,
                    details_json TEXT,
                    last_seen_at TEXT,
                    UNIQUE(source_location, asset_path)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_storage_assets_family ON storage_assets (asset_family, asset_kind)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_storage_assets_source ON storage_assets (source_type, source_location)")
            conn.commit()

    def _config(self):
        parser = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            parser.read(self.config_path)
        return parser

    def _source_id(self, source):
        return _stable_hash(source.get("source_type"), source.get("source_location"), source.get("source_label"))

    def _safe_source_details(self, source):
        details = {}
        for key, value in source.items():
            if key.lower() in {"api_key", "token", "secret", "password", "authorization"}:
                continue
            details[key] = value
        return details

    def _mask_identifier(self, value, prefix="ID"):
        text = _normalize_identifier(value)
        if not text:
            return ""
        return f"{prefix}-{_stable_hash(prefix, text)}"

    def _mask_person_name(self, value):
        text = _clean_text(value)
        if not text:
            return ""
        initials = "".join(part[0].upper() for part in re.split(r"\s+", text) if part)
        initials = initials or "X"
        return f"{initials}-{_stable_hash('name', text)[:8]}"

    def _mask_date(self, value):
        text = _normalize_date(value)
        if not text:
            return ""
        if len(text) >= 4:
            return f"{text[:4]}-REDACTED"
        return "REDACTED"

    def _redact_registry_results(self, result):
        redacted = {
            "query": result.get("query"),
            "patient_hits": [],
            "study_hits": [],
            "asset_hits": [dict(hit) for hit in result.get("asset_hits", [])],
        }

        for hit in result.get("patient_hits", []):
            item = dict(hit)
            if item.get("patient_name"):
                item["patient_name"] = self._mask_person_name(item["patient_name"])
            if item.get("national_id"):
                item["national_id"] = self._mask_identifier(item["national_id"], prefix="NID")
            if item.get("issuer_patient_id"):
                item["issuer_patient_id"] = self._mask_identifier(item["issuer_patient_id"], prefix="IPP")
            if item.get("birth_date"):
                item["birth_date"] = self._mask_date(item["birth_date"])
            redacted["patient_hits"].append(item)

        for hit in result.get("study_hits", []):
            item = dict(hit)
            if item.get("accession_number"):
                item["accession_number"] = self._mask_identifier(item["accession_number"], prefix="ACC")
            redacted["study_hits"].append(item)

        return redacted

    def preview_dicom_metadata(self, file_path, redact=True):
        if pydicom is None:
            return {"status": "skipped", "notes": ["pydicom is not installed"], "file_path": file_path}

        if not file_path or not os.path.exists(file_path):
            return {"status": "skipped", "notes": [f"file not found: {file_path}"], "file_path": file_path}

        try:
            dataset = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)
        except Exception as exc:
            return {"status": "partial", "notes": [str(exc)], "file_path": file_path}

        safe_fields = [
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "SOPInstanceUID",
            "StudyDate",
            "SeriesDate",
            "AcquisitionDate",
            "ContentDate",
            "Modality",
            "StudyDescription",
            "SeriesDescription",
            "BodyPartExamined",
            "Manufacturer",
            "InstitutionName",
            "StationName",
        ]
        sensitive_fields = [
            "PatientName",
            "PatientID",
            "PatientBirthDate",
            "PatientSex",
            "IssuerOfPatientID",
            "AccessionNumber",
            "ReferringPhysicianName",
            "PerformingPhysicianName",
            "OperatorsName",
            "OtherPatientIDs",
            "OtherPatientNames",
        ]

        metadata = {}
        for field in safe_fields:
            value = _clean_text(getattr(dataset, field, None))
            if value:
                metadata[field] = value

        scrubbed_fields = []
        for field in sensitive_fields:
            value = getattr(dataset, field, None)
            if _clean_text(value):
                scrubbed_fields.append(field)
                if redact:
                    if field == "PatientName":
                        metadata[field] = self._mask_person_name(value)
                    elif field == "PatientBirthDate":
                        metadata[field] = self._mask_date(value)
                    else:
                        metadata[field] = self._mask_identifier(value, prefix=field[:4].upper())
                else:
                    metadata[field] = _clean_text(value)

        metadata["study_fingerprint"] = _stable_hash(file_path, metadata.get("StudyInstanceUID"), metadata.get("SeriesInstanceUID"), metadata.get("SOPInstanceUID"))

        return {
            "status": "success",
            "file_path": file_path,
            "redacted": redact,
            "metadata": metadata,
            "scrubbed_fields": scrubbed_fields,
            "notes": ["Preview only. The source DICOM file was not modified."],
        }

    def discover_sources(self, source_overrides=None, include_auto_discovery=True):
        sources = []
        seen_locations = set()
        parser = self._config()

        def add_source(source_type, source_label, source_location, data_class, extra=None):
            if not source_location:
                return
            normalized_location = source_location.rstrip("\\/").lower()
            source_key = (source_type.upper(), normalized_location)
            if source_key in seen_locations:
                return
            seen_locations.add(source_key)
            source = {
                "source_type": source_type,
                "source_label": source_label,
                "source_location": source_location,
                "data_class": data_class,
            }
            if extra:
                source.update(extra)
            sources.append(source)

        def section_value(section_names, option_names):
            for section_name in section_names:
                if parser.has_section(section_name):
                    for option_name in option_names:
                        if parser.has_option(section_name, option_name):
                            return parser.get(section_name, option_name)
            return None

        if include_auto_discovery:
            fhir_url = section_value(["PACS_FHIR", "FHIR"], ["base_url", "url", "endpoint"])
            if not fhir_url:
                fhir_url = os.environ.get("PACS_FHIR_BASE_URL") or os.environ.get("FHIR_BASE_URL")
            if fhir_url:
                add_source(
                    "FHIR",
                    "FHIR clinical metadata",
                    fhir_url.rstrip("/"),
                    "patient, encounter, and ImagingStudy metadata",
                    {
                        "patient_path": section_value(["PACS_FHIR", "FHIR"], ["patient_path"]) or "/Patient",
                        "imagingstudy_path": section_value(["PACS_FHIR", "FHIR"], ["imagingstudy_path"]) or "/ImagingStudy",
                        "api_key_header": section_value(["PACS_FHIR", "FHIR"], ["api_key_header"]) or os.environ.get("PACS_FHIR_API_KEY_HEADER") or "X-API-Key",
                        "api_key": section_value(["PACS_FHIR", "FHIR"], ["api_key"]) or os.environ.get("PACS_FHIR_API_KEY") or os.environ.get("FHIR_API_KEY"),
                        "bearer_token": section_value(["PACS_FHIR", "FHIR"], ["bearer_token", "token"]) or os.environ.get("PACS_FHIR_BEARER_TOKEN") or os.environ.get("FHIR_BEARER_TOKEN"),
                    },
                )

            dicomweb_url = section_value(["PACS_DICOMWEB", "DICOMWEB"], ["base_url", "url", "endpoint"])
            if not dicomweb_url:
                dicomweb_url = os.environ.get("PACS_DICOMWEB_BASE_URL") or os.environ.get("DICOMWEB_BASE_URL")
            if dicomweb_url:
                add_source(
                    "DICOMWEB",
                    "DICOMweb study metadata",
                    dicomweb_url.rstrip("/"),
                    "QIDO-RS study metadata and DICOM JSON tags",
                    {
                        "qido_path": section_value(["PACS_DICOMWEB", "DICOMWEB"], ["qido_path"]) or "/studies",
                        "api_key_header": section_value(["PACS_DICOMWEB", "DICOMWEB"], ["api_key_header"]) or os.environ.get("PACS_DICOMWEB_API_KEY_HEADER") or "X-API-Key",
                        "api_key": section_value(["PACS_DICOMWEB", "DICOMWEB"], ["api_key"]) or os.environ.get("PACS_DICOMWEB_API_KEY") or os.environ.get("DICOMWEB_API_KEY"),
                        "bearer_token": section_value(["PACS_DICOMWEB", "DICOMWEB"], ["bearer_token", "token"]) or os.environ.get("PACS_DICOMWEB_BEARER_TOKEN") or os.environ.get("DICOMWEB_BEARER_TOKEN"),
                    },
                )

            # SIIM Hackathon — auto-register both FHIR and DICOMweb endpoints
            # when the [SIIM_HACKATHON] section is present in config.ini.
            siim_fhir_url = section_value(["SIIM_HACKATHON"], ["fhir_base_url"])
            siim_dicomweb_url = section_value(["SIIM_HACKATHON"], ["dicomweb_base_url"])
            siim_api_key_header = section_value(["SIIM_HACKATHON"], ["api_key_header"]) or "apikey"
            siim_api_key = section_value(["SIIM_HACKATHON"], ["api_key"]) or os.environ.get("SIIM_API_KEY")
            if siim_fhir_url and siim_api_key:
                add_source(
                    "FHIR",
                    "SIIM Hackathon FHIR",
                    siim_fhir_url.rstrip("/"),
                    "SIIM patient, encounter, condition, and ImagingStudy metadata",
                    {
                        "patient_path": "/Patient",
                        "imagingstudy_path": "/ImagingStudy",
                        "api_key_header": siim_api_key_header,
                        "api_key": siim_api_key,
                        "source_tag": "siim_hackathon",
                    },
                )
            if siim_dicomweb_url and siim_api_key:
                add_source(
                    "DICOMWEB",
                    "SIIM Hackathon DICOMweb",
                    siim_dicomweb_url.rstrip("/"),
                    "SIIM QIDO-RS study metadata and WADO-RS DICOM images",
                    {
                        "qido_path": "/studies",
                        "api_key_header": siim_api_key_header,
                        "api_key": siim_api_key,
                        "source_tag": "siim_hackathon",
                    },
                )

            nas_paths = section_value(["PACS_NAS", "NAS"], ["mount_paths", "paths", "root_paths"])
            if not nas_paths:
                nas_paths = os.environ.get("PACS_NAS_MOUNTS") or os.environ.get("NAS_MOUNTS")
            for index, nas_path in enumerate(self._split_paths(nas_paths or ""), start=1):
                add_source(
                    "NAS",
                    f"Mounted NAS archive {index}",
                    nas_path,
                    "raw DICOM files from mounted storage",
                    {
                        "file_globs": ["*.dcm", "*.dicom"],
                        "auto_discovered": False,
                    },
                )

            for drive in self._windows_remote_drives():
                add_source(
                    "NAS",
                    drive.get("source_label") or f"Mounted network drive {drive['source_location']}",
                    drive["source_location"],
                    "mounted NAS share",
                    {
                        **drive,
                        "scan_mode": "sample-limited",
                    },
                )

        if source_overrides:
            for override in source_overrides:
                if override.get("source_type") and override.get("source_location"):
                    sources.append({
                        "source_type": override.get("source_type"),
                        "source_label": override.get("source_label") or f"{override.get('source_type')} override",
                        "source_location": override.get("source_location"),
                        "data_class": override.get("data_class") or "overridden source",
                        **{k: v for k, v in override.items() if k not in {"source_type", "source_label", "source_location", "data_class"}},
                    })

        return sources

    def _split_paths(self, value):
        if not value:
            return []
        return [path.strip() for path in re.split(r"[;,\n]+", value) if path.strip()]

    def _windows_remote_drives(self):
        if os.name != "nt":
            return []

        try:
            drive_mask = ctypes.windll.kernel32.GetLogicalDrives()
        except Exception:
            return []

        drives = []
        for index in range(26):
            if not (drive_mask & (1 << index)):
                continue

            root_path = f"{chr(65 + index)}:\\"
            try:
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root_path))
            except Exception:
                continue

            if drive_type != 4 or not os.path.isdir(root_path):
                continue

            drives.append({
                "source_type": "NAS",
                "source_label": self._drive_label(root_path) or f"Network drive {root_path[0]}",
                "source_location": root_path,
                "data_class": "mounted NAS share",
                "auto_discovered": True,
            })

        return drives

    def _drive_label(self, root_path):
        if os.name != "nt":
            return None

        volume_name = ctypes.create_unicode_buffer(260)
        file_system = ctypes.create_unicode_buffer(260)
        serial_number = ctypes.c_uint32()
        max_component_length = ctypes.c_uint32()
        flags = ctypes.c_uint32()

        try:
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(root_path),
                volume_name,
                len(volume_name),
                ctypes.byref(serial_number),
                ctypes.byref(max_component_length),
                ctypes.byref(flags),
                file_system,
                len(file_system),
            )
        except Exception:
            return None

        if not ok:
            return None

        return _clean_text(volume_name.value) or None

    def _iter_sample_paths(self, mount_path, max_depth=3, max_files=400):
        discovered = 0
        for root, dirs, files in os.walk(mount_path):
            relative_root = os.path.relpath(root, mount_path)
            depth = 0 if relative_root == "." else relative_root.count(os.sep) + 1
            if depth > max_depth:
                dirs[:] = []
                continue

            dirs[:] = [directory for directory in dirs if not directory.startswith("$")]
            for file_name in files:
                yield os.path.join(root, file_name)
                discovered += 1
                if discovered >= max_files:
                    return

    def _quick_sample_paths(self, mount_path, max_entries=50):
        discovered = 0
        try:
            with os.scandir(mount_path) as entries:
                for entry in entries:
                    yield entry.path
                    discovered += 1
                    if discovered >= max_entries:
                        return
                    if entry.is_dir(follow_symlinks=False):
                        try:
                            with os.scandir(entry.path) as child_entries:
                                for child_entry in child_entries:
                                    yield child_entry.path
                                    discovered += 1
                                    if discovered >= max_entries:
                                        return
                        except Exception:
                            continue
        except Exception:
            return

    def _looks_like_sqlite(self, file_path):
        try:
            with open(file_path, "rb") as handle:
                return handle.read(16).startswith(b"SQLite format 3")
        except Exception:
            return False

    def _inspect_sqlite_database(self, file_path, max_tables=25):
        connection = None
        try:
            connection = sqlite3.connect(f"file:{file_path}?mode=ro", uri=True)
            cursor = connection.cursor()
            rows = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name LIMIT ?",
                (max_tables,),
            ).fetchall()
            return [row[0] for row in rows]
        except Exception:
            return []
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _classify_storage_asset(self, file_path):
        file_name = os.path.basename(file_path)
        upper_name = file_name.upper()
        extension = os.path.splitext(file_name)[1].lower()
        size_bytes = 0
        try:
            size_bytes = os.path.getsize(file_path)
        except Exception:
            pass

        family = None
        kind = None
        details = {}

        if upper_name == "DICOMDIR":
            family = "DICOM archive"
            kind = "index"
        elif extension in {".sqlite", ".sqlite3", ".db"}:
            family = "SQLite database" if self._looks_like_sqlite(file_path) else "Application database"
            kind = "database"
            if family == "SQLite database":
                details["tables"] = self._inspect_sqlite_database(file_path)
        elif extension in {".fdb", ".gdb"}:
            family = "Firebird database"
            kind = "database"
        elif extension in {".mdf", ".ndf", ".ldf"}:
            family = "Microsoft SQL Server database"
            kind = "database"
        elif extension in {".ibd", ".myd", ".myi"}:
            family = "MySQL/MariaDB database"
            kind = "database"

        if family is None:
            return None

        return {
            "asset_id": "ASSET-" + _stable_hash(file_path, size_bytes, family, kind),
            "asset_path": file_path,
            "asset_name": file_name,
            "asset_kind": kind,
            "asset_family": family,
            "size_bytes": size_bytes,
            "details": details,
        }

    def _upsert_storage_asset(self, source, asset):
        now = _now_utc_iso()
        source_id = self._source_id(source)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO storage_assets (
                    asset_id, source_id, source_type, source_location, asset_path,
                    asset_name, asset_kind, asset_family, size_bytes, details_json, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_location, asset_path) DO UPDATE SET
                    source_id = excluded.source_id,
                    source_type = excluded.source_type,
                    asset_name = excluded.asset_name,
                    asset_kind = excluded.asset_kind,
                    asset_family = excluded.asset_family,
                    size_bytes = excluded.size_bytes,
                    details_json = excluded.details_json,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    asset["asset_id"],
                    source_id,
                    source.get("source_type"),
                    source.get("source_location"),
                    asset["asset_path"],
                    asset["asset_name"],
                    asset["asset_kind"],
                    asset["asset_family"],
                    asset["size_bytes"],
                    _json_value(asset.get("details", {})),
                    now,
                ),
            )
            conn.commit()

    def _summarize_nas_data_class(self, family_counts):
        if not family_counts:
            return "unknown NAS share"

        if family_counts.get("DICOM archive") and len(family_counts) == 1:
            return "DICOM archive"
        if family_counts.get("DICOM archive") and any("database" in name.lower() for name in family_counts.keys()):
            return "mixed DICOM and database archive"
        if family_counts.get("SQLite database") and len(family_counts) == 1:
            return "SQLite database share"
        if family_counts.get("Firebird database") and len(family_counts) == 1:
            return "Firebird database share"
        if family_counts.get("Microsoft SQL Server database") and len(family_counts) == 1:
            return "SQL Server database share"
        if family_counts.get("MySQL/MariaDB database") and len(family_counts) == 1:
            return "MySQL/MariaDB database share"

        return "mixed clinical archive"

    def _http_headers(self, source):
        headers = {
            "Accept": "application/json, application/fhir+json;q=0.9, application/dicom+json;q=0.8",
        }
        api_key = source.get("api_key")
        bearer_token = source.get("bearer_token")
        api_key_header = source.get("api_key_header") or "X-API-Key"
        if api_key:
            headers[api_key_header] = api_key
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        return headers

    def _fetch_json(self, url, source):
        if requests is None:
            raise RuntimeError("requests is not available")
        response = requests.get(url, headers=self._http_headers(source), timeout=self.timeout_seconds)
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    def _resources_from_payload(self, payload):
        if payload is None:
            return []
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if payload.get("resourceType") == "Bundle" and isinstance(payload.get("entry"), list):
                resources = []
                for entry in payload.get("entry", []):
                    resource = entry.get("resource") if isinstance(entry, dict) else None
                    if resource:
                        resources.append(resource)
                return resources
            if payload.get("resourceType"):
                return [payload]
        return []

    def _record_registry_source(self, source, status, notes, scan_stats=None):
        source_id = self._source_id(source)
        details = self._safe_source_details(source)
        if scan_stats:
            details.update(scan_stats)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO registry_sources (
                    source_id, source_type, source_label, source_location, data_class,
                    last_scan_at, last_status, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    source_type = excluded.source_type,
                    source_label = excluded.source_label,
                    source_location = excluded.source_location,
                    data_class = excluded.data_class,
                    last_scan_at = excluded.last_scan_at,
                    last_status = excluded.last_status,
                    details_json = excluded.details_json
            """, (
                source_id,
                source.get("source_type"),
                source.get("source_label"),
                source.get("source_location"),
                source.get("data_class"),
                _now_utc_iso(),
                status,
                _json_value({"notes": notes, **details}),
            ))
            conn.commit()

    def _source_patient_key(self, source_type, source_location, patient_name, birth_date, national_id=None, issuer_patient_id=None, source_identity=None):
        return "SRC-" + _stable_hash(source_type, source_location, national_id, issuer_patient_id, patient_name, birth_date, source_identity)

    def list_patients(self, limit=20):
        with self._connect() as conn:
            cursor = conn.cursor()
            rows = cursor.execute('''
                SELECT p.empi_id, p.patient_name, p.birth_date,
                       (SELECT COUNT(*) FROM imaging_studies s WHERE s.empi_id = p.empi_id) as study_count
                FROM empi_patients p
                ORDER BY p.created_at DESC
                LIMIT ?
            ''', (limit,)).fetchall()
            return [dict(row) for row in rows]

    def resolve_patient_identity(self, patient_name=None, birth_date=None, national_id=None, issuer_patient_id=None, issuer_of_identifier=None, source_type=None, source_location=None, source_patient_key=None, source_identity=None):
        normalized_name = _clean_text(patient_name)
        normalized_birth_date = _normalize_date(birth_date)
        normalized_national_id = _normalize_identifier(national_id)
        normalized_issuer_patient_id = _normalize_identifier(issuer_patient_id)
        normalized_issuer_of_identifier = _normalize_identifier(issuer_of_identifier)
        normalized_source_key = _normalize_identifier(source_patient_key)

        with self._connect() as conn:
            cursor = conn.cursor()

            if source_type and source_location and normalized_source_key:
                row = cursor.execute(
                    """
                    SELECT empi_id, match_rule
                    FROM source_identity_links
                    WHERE source_type = ? AND source_location = ? AND source_patient_key = ?
                    """,
                    (source_type, source_location, normalized_source_key),
                ).fetchone()
                if row:
                    return row["empi_id"], row["match_rule"] or "source_patient_key"

            if normalized_national_id:
                row = cursor.execute(
                    "SELECT empi_id FROM empi_patients WHERE national_id = ?",
                    (normalized_national_id,),
                ).fetchone()
                if row:
                    return row["empi_id"], "national_id"

            if source_type and source_location and normalized_issuer_patient_id:
                row = cursor.execute(
                    """
                    SELECT empi_id, match_rule
                    FROM source_identity_links
                    WHERE source_type = ? AND source_location = ? AND issuer_patient_id = ?
                    LIMIT 1
                    """,
                    (source_type, source_location, normalized_issuer_patient_id),
                ).fetchone()
                if row:
                    return row["empi_id"], row["match_rule"] or "issuer_patient_id"

            if normalized_name and normalized_birth_date:
                phonetic_name = _soundex(normalized_name)
                row = cursor.execute(
                    """
                    SELECT empi_id
                    FROM empi_patients
                    WHERE phonetic_name = ? AND birth_date = ?
                    """,
                    (phonetic_name, normalized_birth_date),
                ).fetchone()
                if row:
                    return row["empi_id"], "phonetic_name_birth_date"

            if normalized_name and normalized_birth_date:
                row = cursor.execute(
                    """
                    SELECT empi_id
                    FROM empi_patients
                    WHERE patient_name = ? AND birth_date = ?
                    """,
                    (normalized_name, normalized_birth_date),
                ).fetchone()
                if row:
                    return row["empi_id"], "exact_name_birth_date"

            empi_id = f"EMPI-{uuid.uuid4().hex[:12].upper()}"
            phonetic_name = _soundex(normalized_name)
            cursor.execute(
                """
                INSERT INTO empi_patients (
                    empi_id, national_id, issuer_patient_id, issuer_of_identifier,
                    patient_name, phonetic_name, birth_date, created_at, updated_at, match_rule
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    empi_id,
                    normalized_national_id,
                    normalized_issuer_patient_id,
                    normalized_issuer_of_identifier,
                    normalized_name,
                    phonetic_name,
                    normalized_birth_date,
                    _now_utc_iso(),
                    _now_utc_iso(),
                    "new_empi",
                ),
            )
            conn.commit()
            return empi_id, "new_empi"

    def _upsert_patient_profile(self, empi_id, patient_name=None, birth_date=None, national_id=None, issuer_patient_id=None, issuer_of_identifier=None, match_rule=None):
        normalized_name = _clean_text(patient_name)
        normalized_birth_date = _normalize_date(birth_date)
        normalized_national_id = _normalize_identifier(national_id)
        normalized_issuer_patient_id = _normalize_identifier(issuer_patient_id)
        normalized_issuer_of_identifier = _normalize_identifier(issuer_of_identifier)
        phonetic_name = _soundex(normalized_name)
        now = _now_utc_iso()

        with self._connect() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT empi_id FROM empi_patients WHERE empi_id = ?", (empi_id,)).fetchone()
            if row:
                cursor.execute(
                    """
                    UPDATE empi_patients
                    SET national_id = COALESCE(?, national_id),
                        issuer_patient_id = COALESCE(?, issuer_patient_id),
                        issuer_of_identifier = COALESCE(?, issuer_of_identifier),
                        patient_name = CASE WHEN ? != '' THEN ? ELSE patient_name END,
                        phonetic_name = CASE WHEN ? != '' THEN ? ELSE phonetic_name END,
                        birth_date = COALESCE(?, birth_date),
                        updated_at = ?,
                        match_rule = COALESCE(?, match_rule)
                    WHERE empi_id = ?
                    """,
                    (
                        normalized_national_id,
                        normalized_issuer_patient_id,
                        normalized_issuer_of_identifier,
                        normalized_name,
                        normalized_name,
                        phonetic_name,
                        phonetic_name,
                        normalized_birth_date,
                        now,
                        match_rule,
                        empi_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO empi_patients (
                        empi_id, national_id, issuer_patient_id, issuer_of_identifier,
                        patient_name, phonetic_name, birth_date, created_at, updated_at, match_rule
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        empi_id,
                        normalized_national_id,
                        normalized_issuer_patient_id,
                        normalized_issuer_of_identifier,
                        normalized_name,
                        phonetic_name,
                        normalized_birth_date,
                        now,
                        now,
                        match_rule,
                    ),
                )
            conn.commit()

    def _upsert_source_identity(self, source, source_patient_key, empi_id, patient_name=None, birth_date=None, national_id=None, issuer_patient_id=None, issuer_of_identifier=None, match_rule=None, metadata=None):
        source_id = _stable_hash(source.get("source_type"), source.get("source_location"), source_patient_key)
        now = _now_utc_iso()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO source_identity_links (
                    source_id, source_type, source_location, source_patient_key, empi_id,
                    patient_name, birth_date, national_id, issuer_patient_id, issuer_of_identifier,
                    match_rule, metadata_json, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_type, source_location, source_patient_key) DO UPDATE SET
                    source_id = excluded.source_id,
                    empi_id = excluded.empi_id,
                    patient_name = excluded.patient_name,
                    birth_date = excluded.birth_date,
                    national_id = excluded.national_id,
                    issuer_patient_id = excluded.issuer_patient_id,
                    issuer_of_identifier = excluded.issuer_of_identifier,
                    match_rule = excluded.match_rule,
                    metadata_json = excluded.metadata_json,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    source_id,
                    source.get("source_type"),
                    source.get("source_location"),
                    source_patient_key,
                    empi_id,
                    _clean_text(patient_name),
                    _normalize_date(birth_date),
                    _normalize_identifier(national_id),
                    _normalize_identifier(issuer_patient_id),
                    _normalize_identifier(issuer_of_identifier),
                    match_rule,
                    _json_value(metadata or {}),
                    now,
                ),
            )
            conn.commit()

    def _upsert_study(self, study_instance_uid, empi_id, source, modality=None, study_date=None, study_description=None, accession_number=None, body_part=None, series_count=0, instance_count=0, source_patient_key=None, storage_tier=None, metadata=None):
        now = _now_utc_iso()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO imaging_studies (
                    study_instance_uid, empi_id, source_type, source_location, modality,
                    study_date, study_description, accession_number, body_part,
                    series_count, instance_count, storage_tier, source_patient_key,
                    metadata_json, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(study_instance_uid) DO UPDATE SET
                    empi_id = excluded.empi_id,
                    modality = excluded.modality,
                    study_date = excluded.study_date,
                    study_description = excluded.study_description,
                    accession_number = excluded.accession_number,
                    body_part = excluded.body_part,
                    series_count = excluded.series_count,
                    instance_count = excluded.instance_count,
                    storage_tier = excluded.storage_tier,
                    source_patient_key = excluded.source_patient_key,
                    metadata_json = excluded.metadata_json,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    study_instance_uid,
                    empi_id,
                    source.get("source_type"),
                    source.get("source_location"),
                    _clean_text(modality),
                    _normalize_date(study_date),
                    _clean_text(study_description),
                    _clean_text(accession_number),
                    _clean_text(body_part),
                    int(series_count or 0),
                    int(instance_count or 0),
                    storage_tier or source.get("data_class"),
                    _clean_text(source_patient_key),
                    _json_value(metadata or {}),
                    now,
                ),
            )
            conn.commit()

    def _fhir_patient_name(self, resource):
        for name in resource.get("name", []):
            if not isinstance(name, dict):
                continue
            given = name.get("given") or []
            if isinstance(given, list):
                given_text = " ".join(_clean_text(item) for item in given if _clean_text(item))
            else:
                given_text = _clean_text(given)
            family = _clean_text(name.get("family"))
            combined = " ".join(part for part in [given_text, family] if part)
            if combined:
                return combined
        return _clean_text(resource.get("text", {}).get("div"))

    def _fhir_identifier(self, resource):
        identifiers = resource.get("identifier", []) if isinstance(resource.get("identifier"), list) else []
        for identifier in identifiers:
            if not isinstance(identifier, dict):
                continue
            value = _normalize_identifier(identifier.get("value"))
            if value:
                return value, _normalize_identifier(identifier.get("system"))
        return None, None

    def _index_fhir_source(self, source):
        if requests is None:
            return {"source_type": "FHIR", "status": "skipped", "notes": "requests is unavailable"}

        base_url = source.get("source_location", "").rstrip("/")
        patient_path = source.get("patient_path") or "/Patient"
        imagingstudy_path = source.get("imagingstudy_path") or "/ImagingStudy"
        patient_url = urljoin(base_url + "/", patient_path.lstrip("/"))
        imagingstudy_url = urljoin(base_url + "/", imagingstudy_path.lstrip("/"))
        report = {"source_type": "FHIR", "status": "success", "patients_indexed": 0, "studies_indexed": 0, "notes": []}
        patient_context = {}

        try:
            for payload in [self._fetch_json(patient_url, source), self._fetch_json(imagingstudy_url, source)]:
                resources = self._resources_from_payload(payload)
                for resource in resources:
                    resource_type = resource.get("resourceType")
                    if resource_type == "Patient":
                        patient_id = _normalize_identifier(resource.get("id")) or _normalize_identifier(resource.get("identifier", [{}])[0].get("value") if resource.get("identifier") else None)
                        patient_name = self._fhir_patient_name(resource)
                        birth_date = _normalize_date(resource.get("birthDate"))
                        national_id, issuer_of_identifier = self._fhir_identifier(resource)
                        source_patient_key = self._source_patient_key("FHIR", base_url, patient_name, birth_date, national_id, patient_id, patient_id or national_id)
                        empi_id, match_rule = self.resolve_patient_identity(
                            patient_name=patient_name,
                            birth_date=birth_date,
                            national_id=national_id,
                            issuer_patient_id=patient_id,
                            issuer_of_identifier=issuer_of_identifier,
                            source_type="FHIR",
                            source_location=base_url,
                            source_patient_key=source_patient_key,
                            source_identity=patient_id,
                        )
                        self._upsert_patient_profile(empi_id, patient_name, birth_date, national_id, patient_id, issuer_of_identifier, match_rule)
                        self._upsert_source_identity(source, source_patient_key, empi_id, patient_name, birth_date, national_id, patient_id, issuer_of_identifier, match_rule, resource)
                        patient_context[f"Patient/{patient_id}"] = {
                            "empi_id": empi_id,
                            "source_patient_key": source_patient_key,
                            "patient_name": patient_name,
                            "birth_date": birth_date,
                            "national_id": national_id,
                            "issuer_patient_id": patient_id,
                            "issuer_of_identifier": issuer_of_identifier,
                        }
                        report["patients_indexed"] += 1
                    elif resource_type == "ImagingStudy":
                        study_uid = _normalize_identifier(resource.get("id")) or _normalize_identifier(resource.get("identifier", [{}])[0].get("value") if resource.get("identifier") else None)
                        if not study_uid:
                            study_uid = "FHIR-" + _stable_hash(base_url, resource.get("subject", {}).get("reference"), resource.get("started"), resource.get("description"), resource.get("resourceType"), resource.get("id"))
                        subject_reference = _clean_text(resource.get("subject", {}).get("reference"))
                        patient_data = patient_context.get(subject_reference, {})
                        patient_name = patient_data.get("patient_name")
                        birth_date = patient_data.get("birth_date")
                        national_id = patient_data.get("national_id")
                        issuer_patient_id = patient_data.get("issuer_patient_id") or _clean_text(subject_reference)
                        source_patient_key = patient_data.get("source_patient_key") or self._source_patient_key("FHIR", base_url, patient_name, birth_date, national_id, issuer_patient_id, subject_reference)
                        empi_id, match_rule = self.resolve_patient_identity(
                            patient_name=patient_name,
                            birth_date=birth_date,
                            national_id=national_id,
                            issuer_patient_id=issuer_patient_id,
                            issuer_of_identifier=patient_data.get("issuer_of_identifier"),
                            source_type="FHIR",
                            source_location=base_url,
                            source_patient_key=source_patient_key,
                            source_identity=subject_reference,
                        )
                        self._upsert_patient_profile(empi_id, patient_name, birth_date, national_id, issuer_patient_id, patient_data.get("issuer_of_identifier"), match_rule)
                        self._upsert_source_identity(source, source_patient_key, empi_id, patient_name, birth_date, national_id, issuer_patient_id, patient_data.get("issuer_of_identifier"), match_rule, resource)
                        self._upsert_study(
                            study_uid,
                            empi_id,
                            source,
                            modality="FHIR",
                            study_date=resource.get("started") or resource.get("derivedFrom", [{}])[0].get("reference"),
                            study_description=resource.get("description") or "FHIR ImagingStudy",
                            accession_number=_clean_text(resource.get("identifier", [{}])[0].get("value") if resource.get("identifier") else None),
                            body_part=None,
                            series_count=len(resource.get("series", []) or []),
                            instance_count=0,
                            source_patient_key=source_patient_key,
                            storage_tier="FHIR",
                            metadata=resource,
                        )
                        report["studies_indexed"] += 1
            self._record_registry_source(source, "indexed", "FHIR source indexed", report)
        except Exception as exc:
            report["status"] = "partial"
            report["notes"].append(str(exc))
            self._record_registry_source(source, "partial", str(exc), report)

        return report

    def _dicom_json_value(self, item, tag):
        values = item.get(tag) if isinstance(item, dict) else None
        if not values or not isinstance(values, list):
            return None
        first = values[0] if values else None
        if isinstance(first, dict):
            if "Value" in first and isinstance(first["Value"], list) and first["Value"]:
                return first["Value"][0]
            if "Alphabetic" in first:
                return first["Alphabetic"]
            if "InlineBinary" in first:
                return first["InlineBinary"]
        return None

    def _index_dicomweb_source(self, source):
        if requests is None:
            return {"source_type": "DICOMWEB", "status": "skipped", "notes": "requests is unavailable"}

        base_url = source.get("source_location", "").rstrip("/")
        qido_path = source.get("qido_path") or "/studies"
        qido_url = urljoin(base_url + "/", qido_path.lstrip("/"))
        report = {"source_type": "DICOMWEB", "status": "success", "patients_indexed": 0, "studies_indexed": 0, "notes": []}

        try:
            payload = self._fetch_json(qido_url, source)
            studies = self._resources_from_payload(payload)
            for item in studies:
                if not isinstance(item, dict):
                    continue
                study_uid = self._dicom_json_value(item, "0020000D")
                if not study_uid:
                    study_uid = "QIDO-" + _stable_hash(base_url, self._dicom_json_value(item, "00100020"), self._dicom_json_value(item, "00080020"), self._dicom_json_value(item, "00081030"))
                patient_name = self._dicom_json_value(item, "00100010")
                birth_date = _normalize_date(self._dicom_json_value(item, "00100030"))
                national_id = _normalize_identifier(self._dicom_json_value(item, "00100020"))
                issuer_patient_id = _normalize_identifier(self._dicom_json_value(item, "00100021")) or national_id
                source_patient_key = self._source_patient_key("DICOMWEB", base_url, patient_name, birth_date, national_id, issuer_patient_id, study_uid)
                empi_id, match_rule = self.resolve_patient_identity(
                    patient_name=patient_name,
                    birth_date=birth_date,
                    national_id=national_id,
                    issuer_patient_id=issuer_patient_id,
                    issuer_of_identifier=_normalize_identifier(self._dicom_json_value(item, "00100021")),
                    source_type="DICOMWEB",
                    source_location=base_url,
                    source_patient_key=source_patient_key,
                    source_identity=study_uid,
                )
                self._upsert_patient_profile(empi_id, patient_name, birth_date, national_id, issuer_patient_id, _normalize_identifier(self._dicom_json_value(item, "00100021")), match_rule)
                self._upsert_source_identity(source, source_patient_key, empi_id, patient_name, birth_date, national_id, issuer_patient_id, _normalize_identifier(self._dicom_json_value(item, "00100021")), match_rule, item)
                self._upsert_study(
                    study_uid,
                    empi_id,
                    source,
                    modality=self._dicom_json_value(item, "00080060"),
                    study_date=self._dicom_json_value(item, "00080020"),
                    study_description=self._dicom_json_value(item, "00081030") or "DICOMweb study",
                    accession_number=self._dicom_json_value(item, "00080050"),
                    body_part=self._dicom_json_value(item, "00180015"),
                    series_count=len(item.get("00081115", []) or []),
                    instance_count=len(item.get("00081115", []) or []),
                    source_patient_key=source_patient_key,
                    storage_tier="DICOMWEB",
                    metadata=item,
                )
                report["studies_indexed"] += 1
            self._record_registry_source(source, "indexed", "DICOMweb source indexed", report)
        except Exception as exc:
            report["status"] = "partial"
            report["notes"].append(str(exc))
            self._record_registry_source(source, "partial", str(exc), report)

        return report

    def _study_uid_from_file(self, file_path):
        stat = os.stat(file_path)
        return "NAS-" + _stable_hash(file_path, stat.st_size, int(stat.st_mtime))

    def _index_nas_source(self, source):
        mount_path = source.get("source_location")
        if not mount_path or not os.path.isdir(mount_path):
            report = {"source_type": "NAS", "status": "skipped", "notes": [f"mount path unavailable: {mount_path}"], "studies_indexed": 0, "patients_indexed": 0}
            self._record_registry_source(source, "skipped", "NAS mount unavailable", report)
            return report

        report = {
            "source_type": "NAS",
            "status": "success",
            "patients_indexed": 0,
            "studies_indexed": 0,
            "database_assets_indexed": 0,
            "notes": [],
        }
        family_counts = Counter()
        sample_limit = 40 if source.get("auto_discovered") else 600
        scan_depth = 1 if source.get("auto_discovered") else 3

        if pydicom is None:
            report["notes"].append("pydicom is not installed; DICOM studies were skipped")

        try:
            sample_paths = self._quick_sample_paths(mount_path, max_entries=sample_limit) if source.get("auto_discovered") else self._iter_sample_paths(mount_path, max_depth=scan_depth, max_files=sample_limit)
            for file_path in sample_paths:
                file_name = os.path.basename(file_path)

                asset = self._classify_storage_asset(file_path)
                if asset:
                    self._upsert_storage_asset(source, asset)
                    report["database_assets_indexed"] += 1
                    family_counts[asset["asset_family"]] += 1

                if pydicom is None or not file_name.lower().endswith((".dcm", ".dicom", ".ima")):
                    continue

                try:
                    dataset = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)
                except Exception as exc:
                    report["notes"].append(f"{file_path}: {exc}")
                    continue

                patient_name = _clean_text(getattr(dataset, "PatientName", ""))
                birth_date = _normalize_date(getattr(dataset, "PatientBirthDate", None))
                national_id = _normalize_identifier(getattr(dataset, "PatientID", None))
                issuer_patient_id = _normalize_identifier(getattr(dataset, "IssuerOfPatientID", None))
                issuer_of_identifier = _normalize_identifier(getattr(dataset, "IssuerOfPatientID", None))
                source_patient_key = self._source_patient_key("NAS", mount_path, patient_name, birth_date, national_id, issuer_patient_id, file_path)
                empi_id, match_rule = self.resolve_patient_identity(
                    patient_name=patient_name,
                    birth_date=birth_date,
                    national_id=national_id,
                    issuer_patient_id=issuer_patient_id,
                    issuer_of_identifier=issuer_of_identifier,
                    source_type="NAS",
                    source_location=mount_path,
                    source_patient_key=source_patient_key,
                    source_identity=file_path,
                )
                self._upsert_patient_profile(empi_id, patient_name, birth_date, national_id, issuer_patient_id, issuer_of_identifier, match_rule)
                self._upsert_source_identity(source, source_patient_key, empi_id, patient_name, birth_date, national_id, issuer_patient_id, issuer_of_identifier, match_rule, {"file_path": file_path})
                study_uid = _normalize_identifier(getattr(dataset, "StudyInstanceUID", None)) or self._study_uid_from_file(file_path)
                self._upsert_study(
                    study_uid,
                    empi_id,
                    source,
                    modality=_clean_text(getattr(dataset, "Modality", "")),
                    study_date=getattr(dataset, "StudyDate", None),
                    study_description=_clean_text(getattr(dataset, "StudyDescription", "")) or "Raw DICOM file",
                    accession_number=_clean_text(getattr(dataset, "AccessionNumber", "")),
                    body_part=_clean_text(getattr(dataset, "BodyPartExamined", "")),
                    series_count=1,
                    instance_count=1,
                    source_patient_key=source_patient_key,
                    storage_tier="NAS",
                    metadata={
                        "file_path": file_path,
                        "study_uid": study_uid,
                        "modality": _clean_text(getattr(dataset, "Modality", "")),
                    },
                )
                report["studies_indexed"] += 1

            source["data_class"] = self._summarize_nas_data_class(family_counts)
            self._record_registry_source(source, "indexed", "NAS archive indexed", report)
        except Exception as exc:
            report["status"] = "partial"
            report["notes"].append(str(exc))
            self._record_registry_source(source, "partial", str(exc), report)

        return report

    def sync_registry(self, source_overrides=None, include_auto_discovery=True):
        sources = self.discover_sources(source_overrides=source_overrides, include_auto_discovery=include_auto_discovery)
        reports = []
        total_sources = len(sources)
        for index, source in enumerate(sources, start=1):
            source_type = source.get("source_type")
            if source_type == "FHIR":
                report = self._index_fhir_source(source)
            elif source_type == "DICOMWEB":
                report = self._index_dicomweb_source(source)
            elif source_type == "NAS":
                report = self._index_nas_source(source)
            else:
                report = {"source_type": source_type, "status": "skipped", "notes": ["unsupported source type"]}

            report["progress_percent"] = int(round((index / total_sources) * 100)) if total_sources else 100
            report["progress_step"] = f"{index}/{total_sources}" if total_sources else "0/0"
            report["current_step"] = f"{source_type} at {source.get('source_location')}"
            reports.append(report)

        snapshot = self.registry_snapshot()
        return {
            "status": "success" if any(report.get("status") == "success" for report in reports) or not reports else "idle",
            "sources_discovered": len(sources),
            "completed_sources": len(reports),
            "failed_sources": sum(1 for report in reports if report.get("status") == "partial"),
            "skipped_sources": sum(1 for report in reports if report.get("status") == "skipped"),
            "progress_percent": reports[-1]["progress_percent"] if reports else 100,
            "current_step": reports[-1]["current_step"] if reports else "No sources configured",
            "reports": reports,
            "snapshot": snapshot,
        }

    def registry_snapshot(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            source_rows = cursor.execute(
                "SELECT source_type, source_label, source_location, data_class, last_scan_at, last_status FROM registry_sources ORDER BY source_type, source_label"
            ).fetchall()
            patient_count = cursor.execute("SELECT COUNT(*) AS count FROM empi_patients").fetchone()["count"]
            study_count = cursor.execute("SELECT COUNT(*) AS count FROM imaging_studies").fetchone()["count"]
            asset_count = cursor.execute("SELECT COUNT(*) AS count FROM storage_assets").fetchone()["count"]
            modality_rows = cursor.execute(
                "SELECT modality, COUNT(*) AS count FROM imaging_studies GROUP BY modality ORDER BY count DESC, modality ASC"
            ).fetchall()
            asset_family_rows = cursor.execute(
                "SELECT asset_family, COUNT(*) AS count FROM storage_assets GROUP BY asset_family ORDER BY count DESC, asset_family ASC"
            ).fetchall()

        return {
            "source_count": len(source_rows),
            "patient_count": patient_count,
            "study_count": study_count,
            "asset_count": asset_count,
            "sources": [dict(row) for row in source_rows],
            "modality_counts": [dict(row) for row in modality_rows],
            "asset_family_counts": [dict(row) for row in asset_family_rows],
        }

    def search_registry(self, query, limit=25, redact=False):
        text = _clean_text(query)
        if not text:
            return {"query": text, "patient_hits": [], "study_hits": [], "asset_hits": []}

        terms = [term for term in re.split(r"\W+", text.lower()) if len(term) >= 3]
        if not terms:
            terms = [text.lower()]
        terms = terms[:6]

        def build_like_clause(fields):
            clause_parts = []
            params = []
            for term in terms:
                pattern = f"%{term}%"
                for field in fields:
                    clause_parts.append(f"lower(coalesce({field}, '')) LIKE ?")
                    params.append(pattern)
            return "(" + " OR ".join(clause_parts) + ")", params

        with self._connect() as conn:
            cursor = conn.cursor()

            patient_clause, patient_params = build_like_clause(["empi_id", "patient_name", "national_id", "issuer_patient_id", "birth_date"])
            patient_rows = cursor.execute(
                f"SELECT empi_id, patient_name, national_id, issuer_patient_id, birth_date, match_rule FROM empi_patients WHERE {patient_clause} ORDER BY updated_at DESC LIMIT ?",
                (*patient_params, limit),
            ).fetchall()

            study_clause, study_params = build_like_clause(["study_instance_uid", "modality", "study_date", "study_description", "accession_number", "body_part", "source_type", "source_location"])
            study_rows = cursor.execute(
                f"SELECT study_instance_uid, empi_id, source_type, source_location, modality, study_date, study_description, accession_number, body_part, storage_tier FROM imaging_studies WHERE {study_clause} ORDER BY study_date DESC, last_seen_at DESC LIMIT ?",
                (*study_params, limit),
            ).fetchall()

            asset_clause, asset_params = build_like_clause(["asset_path", "asset_name", "asset_family", "asset_kind", "source_type", "source_location"])
            asset_rows = cursor.execute(
                f"SELECT asset_id, asset_path, asset_name, asset_family, asset_kind, source_type, source_location, size_bytes FROM storage_assets WHERE {asset_clause} ORDER BY last_seen_at DESC LIMIT ?",
                (*asset_params, limit),
            ).fetchall()

        result = {
            "query": text,
            "patient_hits": [dict(row) for row in patient_rows],
            "study_hits": [dict(row) for row in study_rows],
            "asset_hits": [dict(row) for row in asset_rows],
        }

        if redact:
            return self._redact_registry_results(result)

        return result

    def get_patient_timeline(self, empi_id):
        with self._connect() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(
                """
                SELECT
                    study_instance_uid,
                    source_type,
                    source_location,
                    modality,
                    study_date,
                    study_description,
                    accession_number,
                    body_part,
                    storage_tier,
                    source_patient_key,
                    metadata_json,
                    last_seen_at
                FROM imaging_studies
                WHERE empi_id = ?
                ORDER BY study_date DESC, study_instance_uid DESC
                """,
                (empi_id,),
            ).fetchall()

            patient_row = cursor.execute(
                "SELECT empi_id, national_id, issuer_patient_id, patient_name, phonetic_name, birth_date, match_rule FROM empi_patients WHERE empi_id = ?",
                (empi_id,),
            ).fetchone()

        return {
            "patient": dict(patient_row) if patient_row else None,
            "timeline": [dict(row) for row in rows],
        }

    def describe_registry(self):
        snapshot = self.registry_snapshot()
        if snapshot["source_count"] == 0:
            return "No PACS continuity sources are configured yet. Add FHIR, DICOMweb, or NAS settings and run a registry sync."

        source_lines = []
        for source in snapshot["sources"]:
            source_lines.append(
                f"- {source['source_type']} at {source['source_location']} stores {source['data_class']} (last status: {source['last_status'] or 'unknown'})"
            )

        modality_lines = []
        for modality_row in snapshot["modality_counts"]:
            modality_label = modality_row.get("modality") or "UNKNOWN"
            modality_lines.append(f"{modality_label}: {modality_row['count']}")

        return (
            f"Continuity registry holds {snapshot['patient_count']} linked patients and {snapshot['study_count']} studies across {snapshot['source_count']} sources. "
            f"It treats FHIR as patient and encounter metadata, DICOMweb as study metadata, and NAS as raw DICOM file storage. "
            f"Source inventory: {'; '.join(source_lines)}. "
            f"Modality mix: {', '.join(modality_lines) if modality_lines else 'no studies indexed yet'}."
        )

    def format_timeline(self, empi_id):
        timeline = self.get_patient_timeline(empi_id)
        patient = timeline.get("patient")
        if not patient:
            return f"No local registry record exists for {empi_id}."

        if not timeline["timeline"]:
            return (
                f"EMPI {empi_id} is linked to {patient.get('patient_name') or 'an unnamed patient'}, but no studies have been indexed yet."
            )

        lines = [
            f"EMPI {empi_id} belongs to {patient.get('patient_name') or 'an unnamed patient'} and currently has {len(timeline['timeline'])} indexed studies:"
        ]
        for study in timeline["timeline"]:
            lines.append(
                f"- {study.get('study_date') or 'unknown date'} | {study.get('modality') or 'UNKNOWN'} | {study.get('study_description') or 'Study'} | {study.get('source_type')}"
            )
        return "\n".join(lines)
