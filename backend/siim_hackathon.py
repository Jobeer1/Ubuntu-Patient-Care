"""SIIM 2026 Hackathon — Patient Data Ingest
============================================
Fetches all patient data from the SIIM Hackathon servers (FHIR R4 + DICOMweb)
and stores everything in the local PACS Continuity Registry and vault.

Endpoints used
--------------
* FHIR:     https://hackathon.siim.org/fhir/<ResourceType>
* DICOMweb QIDO-RS:  https://hackathon.siim.org/dicomweb/studies
* DICOMweb WADO-RS:  https://hackathon.siim.org/dicomweb/studies/{uid}

Authentication
--------------
All requests carry the header  ``apikey: <key>``  as documented at
https://imaginginformatics.github.io/hackathon-docs/

Security notes
--------------
* The API key is read from config.ini and never logged or returned in
  responses.
* Downloaded DICOM files are stored under the local vault path only.
* No patient data is forwarded to any third party.
"""
from __future__ import annotations

import configparser
import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    import pydicom
except ImportError:  # pragma: no cover
    pydicom = None

from backend.pacs_registry import (
    PACSContinuityRegistry,
    _clean_text,
    _normalize_date,
    _normalize_identifier,
    _stable_hash,
)

_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config.ini"
)
_DEFAULT_VAULT_PATH = os.path.join(
    os.path.expanduser("~"), ".openclaw", "vault", "siim_hackathon"
)

_SECTION = "SIIM_HACKATHON"

# FHIR resource types to fetch (order matters — Patient first for cross-linking).
_DEFAULT_FHIR_RESOURCES = [
    "Patient",
    "Condition",
    "Observation",
    "Encounter",
    "DiagnosticReport",
    "ImagingStudy",
    "MedicationRequest",
    "Procedure",
    "AllergyIntolerance",
]

_TIMEOUT = 30  # seconds per HTTP request

# ---------------------------------------------------------------------------
# Module-level job state so callers can poll progress.
# ---------------------------------------------------------------------------
_ingest_lock = threading.Lock()
_STATE_FILE = os.path.join(
    os.path.expanduser("~"), ".openclaw", "vault", "siim_hackathon", "ingest_state.json"
)

def _load_ingest_state() -> Dict[str, Any]:
    """Load persisted ingest state from disk."""
    try:
        if os.path.exists(_STATE_FILE):
            with open(_STATE_FILE, 'r', encoding='utf-8') as f:
                st = json.load(f)
                if st.get("status") == "running":
                    st["status"] = "error"
                    if "errors" not in st:
                        st["errors"] = []
                    st["errors"].append("Job interrupted by server restart.")
                return st
    except Exception:
        pass
    return {
        "status": "idle",
        "started_at": None,
        "finished_at": None,
        "progress": {},
        "dicom": {
            "studies_found": 0,
            "instances_queued": 0,
            "instances_downloaded": 0,
            "instances_skipped": 0,
            "bytes_written": 0,
        },
        "errors": [],
        "report": None,
    }

def _save_ingest_state(state: Dict[str, Any]) -> None:
    """Persist ingest state to disk."""
    try:
        os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
        with open(_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, default=str)
    except Exception:
        pass

_ingest_state: Dict[str, Any] = _load_ingest_state()


def _set_ingest_resource_progress(resource_type: str, fetched: int, indexed: int, errors: Optional[List[str]] = None) -> None:
    with _ingest_lock:
        entry = {
            "fetched": fetched,
            "indexed": indexed,
        }
        if errors:
            entry["errors"] = errors
        _ingest_state["progress"][resource_type] = entry
        _save_ingest_state(_ingest_state)


def _initialize_ingest_progress(resource_types: List[str]) -> None:
    with _ingest_lock:
        _ingest_state["progress"] = {
            rt: {"fetched": 0, "indexed": 0}
            for rt in resource_types
        }
        _save_ingest_state(_ingest_state)


def get_ingest_state() -> Dict[str, Any]:
    """Return a snapshot of the current ingest job state (thread-safe)."""
    with _ingest_lock:
        return json.loads(json.dumps(_ingest_state, default=str))


# ---------------------------------------------------------------------------
# Helper: load config
# ---------------------------------------------------------------------------

def _load_config(config_path: Optional[str] = None) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    path = config_path or _DEFAULT_CONFIG_PATH
    if os.path.exists(path):
        parser.read(path)
    return parser


def _cfg(parser: configparser.ConfigParser, key: str, fallback: str = "") -> str:
    if parser.has_section(_SECTION) and parser.has_option(_SECTION, key):
        return parser.get(_SECTION, key).strip()
    return os.environ.get(f"SIIM_{key.upper()}", fallback)


# ---------------------------------------------------------------------------
# Core ingest class
# ---------------------------------------------------------------------------

class SIIMHackathonIngest:
    """
    Fetches FHIR and DICOMweb data from the SIIM Hackathon servers
    and indexes it into the local PACSContinuityRegistry.

    Parameters
    ----------
    config_path : str, optional
        Path to config.ini.  Defaults to the project root config.ini.
    registry : PACSContinuityRegistry, optional
        Existing registry instance.  A new one is created if omitted.
    vault_path : str, optional
        Directory where DICOM instances are saved.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        registry: Optional[PACSContinuityRegistry] = None,
        vault_path: Optional[str] = None,
    ):
        self._parser = _load_config(config_path)
        self.fhir_base = _cfg(self._parser, "fhir_base_url", "https://hackathon.siim.org/fhir").rstrip("/")
        self.dicomweb_base = _cfg(self._parser, "dicomweb_base_url", "https://hackathon.siim.org/dicomweb").rstrip("/")
        self._api_key_header = _cfg(self._parser, "api_key_header", "apikey")
        self._api_key = _cfg(self._parser, "api_key", "")
        self._fhir_resources = [
            r.strip()
            for r in _cfg(self._parser, "fhir_resources", ",".join(_DEFAULT_FHIR_RESOURCES)).split(",")
            if r.strip()
        ]
        raw_max = _cfg(self._parser, "dicom_max_instances", "200")
        self._dicom_max_instances = int(raw_max) if raw_max.isdigit() else 200
        ssl_verify_raw = _cfg(self._parser, "ssl_verify", "true").strip().lower()
        self._ssl_verify: bool = ssl_verify_raw not in {"false", "0", "no", "off"}
        configured_vault = _cfg(self._parser, "dicom_vault_path", "")
        self.vault_path = vault_path or configured_vault or _DEFAULT_VAULT_PATH
        self.progress_callback = None
        self.registry = registry or PACSContinuityRegistry()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self, extra_accept: str = "") -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self._api_key:
            headers[self._api_key_header] = self._api_key
        if extra_accept:
            headers["Accept"] = extra_accept
        return headers

    def _get_json(self, url: str, params: Optional[Dict] = None, accept: Optional[str] = None) -> Optional[Any]:
        if requests is None:
            raise RuntimeError("requests library is not installed")
        if not self._ssl_verify:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        headers = self._headers(accept or "application/fhir+json, application/json;q=0.9")
        resp = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=_TIMEOUT,
            verify=self._ssl_verify,
        )
        resp.raise_for_status()
        if not resp.content:
            return None
        return resp.json()

    def _get_bytes(self, url: str, accept: str) -> Optional[bytes]:
        if requests is None:
            raise RuntimeError("requests library is not installed")
        if not self._ssl_verify:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(
            url,
            headers=self._headers(accept),
            timeout=_TIMEOUT,
            stream=True,
            verify=self._ssl_verify,
        )
        resp.raise_for_status()
        return resp.content

    # ------------------------------------------------------------------
    # FHIR helpers
    # ------------------------------------------------------------------

    def _fhir_url(self, resource_type: str) -> str:
        return f"{self.fhir_base}/{resource_type}"

    def _extract_bundle_entries(self, payload: Any) -> List[Dict]:
        if payload is None:
            return []
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []
        if payload.get("resourceType") == "Bundle":
            return [
                entry.get("resource")
                for entry in payload.get("entry", [])
                if isinstance(entry, dict) and entry.get("resource")
            ]
        if payload.get("resourceType"):
            return [payload]
        return []

    def _next_url(self, bundle: Any) -> Optional[str]:
        """Return the `next` link URL from a FHIR Bundle, or None.

        The SIIM Hackathon server returns pagination links that point to
        localhost:8080; we rewrite them to the configured FHIR base URL.
        """
        if not isinstance(bundle, dict):
            return None
        for link in bundle.get("link", []):
            if isinstance(link, dict) and link.get("relation") == "next":
                url = link.get("url")
                if not url:
                    return None
                parsed = urlparse(url)
                base_parsed = urlparse(self.fhir_base)
                # If the URL is relative, points to localhost, or has a different
                # host than our configured FHIR base, rewrite it.
                if not parsed.netloc or parsed.netloc in ("localhost:8080", "localhost"):
                    return f"{base_parsed.scheme}://{base_parsed.netloc}{parsed.path}{'?' if parsed.query else ''}{parsed.query}"
                return url
        return None

    def _fhir_patient_name(self, resource: Dict) -> str:
        for name in resource.get("name", []):
            if not isinstance(name, dict):
                continue
            given_parts = name.get("given") or []
            if isinstance(given_parts, list):
                given = " ".join(_clean_text(g) for g in given_parts if _clean_text(g))
            else:
                given = _clean_text(given_parts)
            family = _clean_text(name.get("family", ""))
            combined = " ".join(p for p in [given, family] if p)
            if combined:
                return combined
        return _clean_text(resource.get("text", {}).get("div", ""))

    def _fhir_patient_id(self, resource: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Return (patient_id_value, issuer_system) from the first identifier."""
        for ident in resource.get("identifier", []):
            if not isinstance(ident, dict):
                continue
            value = _normalize_identifier(ident.get("value"))
            if value:
                return value, _normalize_identifier(ident.get("system"))
        return None, None

    def _fhir_subject_ref(self, resource: Dict) -> str:
        """Return the Patient reference string from subject/patient fields."""
        for key in ("subject", "patient"):
            ref = resource.get(key)
            if isinstance(ref, dict):
                return _clean_text(ref.get("reference", ""))
        return ""

    # ------------------------------------------------------------------
    # FHIR ingest
    # ------------------------------------------------------------------

    def ingest_fhir(self) -> Dict[str, Any]:
        """
        Fetch all configured FHIR resource types and index them into
        the local registry.  Returns a per-resource-type report dict.
        """
        report: Dict[str, Any] = {}
        patient_context: Dict[str, Dict] = {}  # "Patient/{id}" -> identity dict

        fhir_source = {
            "source_type": "FHIR",
            "source_label": "SIIM Hackathon FHIR",
            "source_location": self.fhir_base,
            "data_class": "patient, encounter, and ImagingStudy metadata",
            "api_key_header": self._api_key_header,
            "api_key": self._api_key,
        }

        for resource_type in self._fhir_resources:
            fetched = 0
            indexed = 0
            errors: List[str] = []

            try:
                url: Optional[str] = self._fhir_url(resource_type)
                all_resources: List[Dict] = []

                # Follow pagination (FHIR Bundle `next` links).
                while url:
                    payload = self._get_json(url)
                    batch = self._extract_bundle_entries(payload)
                    fetched += len(batch)
                    all_resources.extend(batch)
                    url = self._next_url(payload) if isinstance(payload, dict) else None

                for resource in all_resources:
                    rt = resource.get("resourceType", resource_type)
                    try:
                        if rt == "Patient":
                            indexed += self._index_fhir_patient(resource, fhir_source, patient_context)
                        elif rt == "ImagingStudy":
                            indexed += self._index_fhir_imaging_study(resource, fhir_source, patient_context)
                        elif rt == "Condition":
                            indexed += self._index_fhir_clinical(resource, "Condition", fhir_source, patient_context)
                        elif rt == "Observation":
                            indexed += self._index_fhir_clinical(resource, "Observation", fhir_source, patient_context)
                        elif rt in ("Encounter", "DiagnosticReport", "MedicationRequest", "Procedure", "AllergyIntolerance"):
                            indexed += self._index_fhir_clinical(resource, rt, fhir_source, patient_context)
                        else:
                            indexed += self._index_fhir_clinical(resource, rt, fhir_source, patient_context)
                    except Exception as exc:
                        errors.append(f"row error: {exc}")

            except Exception as exc:
                errors.append(str(exc))

            report[resource_type] = {"fetched": fetched, "indexed": indexed, "errors": errors}
            _set_ingest_resource_progress(resource_type, fetched, indexed, errors=errors)

        # Record the FHIR source in registry_sources.
        notes = [f"{rt}: {v['fetched']} fetched / {v['indexed']} indexed" for rt, v in report.items()]
        self.registry._record_registry_source(fhir_source, "success", notes)

        return report

    def _index_fhir_patient(self, resource: Dict, source: Dict, context: Dict) -> int:
        patient_id = _normalize_identifier(resource.get("id"))
        name = self._fhir_patient_name(resource)
        birth_date = _normalize_date(resource.get("birthDate"))
        national_id, issuer_system = self._fhir_patient_id(resource)

        source_patient_key = self.registry._source_patient_key(
            "FHIR", source["source_location"], name, birth_date, national_id, patient_id, patient_id or national_id
        )
        empi_id, match_rule = self.registry.resolve_patient_identity(
            patient_name=name,
            birth_date=birth_date,
            national_id=national_id,
            issuer_patient_id=patient_id,
            issuer_of_identifier=issuer_system,
            source_type="FHIR",
            source_location=source["source_location"],
            source_patient_key=source_patient_key,
            source_identity=patient_id,
        )
        self.registry._upsert_patient_profile(empi_id, name, birth_date, national_id, patient_id, issuer_system, match_rule)
        self.registry._upsert_source_identity(source, source_patient_key, empi_id, name, birth_date, national_id, patient_id, issuer_system, match_rule, resource)

        # Stash context so ImagingStudy + clinical resources can cross-link.
        context[f"Patient/{patient_id}"] = {
            "empi_id": empi_id,
            "source_patient_key": source_patient_key,
            "patient_name": name,
            "birth_date": birth_date,
            "national_id": national_id,
            "issuer_patient_id": patient_id,
            "issuer_of_identifier": issuer_system,
        }
        return 1

    def _index_fhir_imaging_study(self, resource: Dict, source: Dict, context: Dict) -> int:
        subject_ref = self._fhir_subject_ref(resource)
        patient_data = context.get(subject_ref, {})

        # Study UID — prefer the DICOM UID stored in identifier.
        study_uid = None
        for ident in resource.get("identifier", []):
            if not isinstance(ident, dict):
                continue
            v = _normalize_identifier(ident.get("value"))
            if v:
                study_uid = v
                break
        if not study_uid:
            study_uid = _normalize_identifier(resource.get("id")) or f"FHIR-{id(resource)}"

        name = patient_data.get("patient_name")
        birth_date = patient_data.get("birth_date")
        national_id = patient_data.get("national_id")
        issuer_patient_id = patient_data.get("issuer_patient_id") or _clean_text(subject_ref)
        source_patient_key = patient_data.get("source_patient_key") or self.registry._source_patient_key(
            "FHIR", source["source_location"], name, birth_date, national_id, issuer_patient_id, subject_ref
        )
        empi_id, match_rule = self.registry.resolve_patient_identity(
            patient_name=name,
            birth_date=birth_date,
            national_id=national_id,
            issuer_patient_id=issuer_patient_id,
            source_type="FHIR",
            source_location=source["source_location"],
            source_patient_key=source_patient_key,
        )
        self.registry._upsert_patient_profile(empi_id, name, birth_date, national_id, issuer_patient_id, patient_data.get("issuer_of_identifier"), match_rule)
        self.registry._upsert_source_identity(source, source_patient_key, empi_id, name, birth_date, national_id, issuer_patient_id, patient_data.get("issuer_of_identifier"), match_rule, resource)

        # Extract modality from series[].modality.code
        modality_codes: List[str] = []
        for series in resource.get("series", []):
            if not isinstance(series, dict):
                continue
            m = series.get("modality")
            if isinstance(m, dict):
                code = _clean_text(m.get("code"))
                if code and code not in modality_codes:
                    modality_codes.append(code)
        modality = "/".join(modality_codes) if modality_codes else _clean_text(resource.get("modality", {}).get("code") if isinstance(resource.get("modality"), dict) else resource.get("modality"))

        self.registry._upsert_study(
            study_uid,
            empi_id,
            source,
            modality=modality,
            study_date=_normalize_date(resource.get("started")),
            study_description=_clean_text(resource.get("description")),
            accession_number=None,
            body_part=None,
            series_count=len(resource.get("series", [])),
            instance_count=sum(
                len(s.get("instance", [])) for s in resource.get("series", []) if isinstance(s, dict)
            ),
            source_patient_key=source_patient_key,
            storage_tier="fhir",
            metadata=resource,
        )
        return 1

    def _index_fhir_clinical(self, resource: Dict, resource_type: str, source: Dict, context: Dict) -> int:
        """
        Index clinical FHIR resources (Condition, Observation, etc.).
        These are attached to the patient EMPI via the subject/patient reference.
        Stored as metadata in the source_identity_links metadata_json for the patient.
        """
        subject_ref = self._fhir_subject_ref(resource)
        patient_data = context.get(subject_ref, {})
        empi_id = patient_data.get("empi_id")
        if not empi_id:
            # Unknown patient — still index under a synthetic patient record.
            empi_id = None

        # We attach the clinical resource as an imaging_studies entry with a
        # synthetic UID so that patient_data_tools can retrieve it.
        resource_id = _normalize_identifier(resource.get("id")) or f"{resource_type}-{id(resource)}"
        synthetic_uid = f"SIIM-{resource_type.upper()}-{resource_id}"

        if empi_id:
            self.registry._upsert_study(
                synthetic_uid,
                empi_id,
                source,
                modality=resource_type,
                study_date=_normalize_date(
                    resource.get("recordedDate") or resource.get("effectiveDateTime")
                    or resource.get("issued") or resource.get("period", {}).get("start")
                    or resource.get("authoredOn") or resource.get("performedDateTime")
                    or resource.get("onsetDateTime") or ""
                ),
                study_description=self._clinical_summary(resource, resource_type),
                accession_number=resource_id,
                body_part=None,
                series_count=0,
                instance_count=0,
                source_patient_key=patient_data.get("source_patient_key"),
                storage_tier=f"fhir-{resource_type.lower()}",
                metadata=resource,
            )
        return 1

    def _clinical_summary(self, resource: Dict, resource_type: str) -> str:
        """Extract a short human-readable summary from a clinical FHIR resource."""
        # Condition / DiagnosticReport
        cc = resource.get("code")
        if isinstance(cc, dict):
            text = _clean_text(cc.get("text"))
            if text:
                return f"{resource_type}: {text}"
            for coding in cc.get("coding", []):
                if isinstance(coding, dict):
                    display = _clean_text(coding.get("display"))
                    if display:
                        return f"{resource_type}: {display}"
        # Observation value
        if resource_type == "Observation":
            vq = resource.get("valueQuantity")
            if isinstance(vq, dict):
                val = _clean_text(vq.get("value"))
                unit = _clean_text(vq.get("unit"))
                return f"Observation: {val} {unit}".strip()
            vs = _clean_text(resource.get("valueString"))
            if vs:
                return f"Observation: {vs}"
        return resource_type

    # ------------------------------------------------------------------
    # DICOMweb QIDO-RS — study / series / instance metadata
    # ------------------------------------------------------------------

    def ingest_dicomweb_metadata(self) -> Dict[str, Any]:
        """
        Query QIDO-RS for all studies, iterate series and instances,
        and register each study in the local registry.
        Returns a summary report dict.
        """
        dicomweb_source = {
            "source_type": "DICOMWEB",
            "source_label": "SIIM Hackathon DICOMweb",
            "source_location": self.dicomweb_base,
            "data_class": "DICOM study metadata",
            "api_key_header": self._api_key_header,
            "api_key": self._api_key,
        }

        report: Dict[str, Any] = {
            "studies_found": 0,
            "studies_indexed": 0,
            "series_found": 0,
            "instances_found": 0,
            "errors": [],
        }

        try:
            studies_payload = self._get_json(f"{self.dicomweb_base}/studies", accept="application/dicom+json")
        except Exception as exc:
            report["errors"].append(f"QIDO studies fetch failed: {exc}")
            self.registry._record_registry_source(dicomweb_source, "error", [str(exc)])
            return report

        if not isinstance(studies_payload, list):
            studies_payload = []

        report["studies_found"] = len(studies_payload)

        for study_json in studies_payload:
            try:
                study_uid, study_meta = self._parse_dicom_json_study(study_json)
                if not study_uid:
                    continue

                # Fetch series-level metadata for instance count.
                series_list: List[Dict] = []
                try:
                    series_payload = self._get_json(f"{self.dicomweb_base}/studies/{study_uid}/series", accept="application/dicom+json")
                    if isinstance(series_payload, list):
                        series_list = series_payload
                except Exception:
                    pass

                report["series_found"] += len(series_list)

                instance_count = 0
                for series_json in series_list:
                    series_uid = _clean_text(self._dicom_tag(series_json, "0020000E"))
                    if not series_uid:
                        continue
                    try:
                        instances_payload = self._get_json(
                            f"{self.dicomweb_base}/studies/{study_uid}/series/{series_uid}/instances",
                            accept="application/dicom+json",
                        )
                        if isinstance(instances_payload, list):
                            instance_count += len(instances_payload)
                            report["instances_found"] += len(instances_payload)
                    except Exception:
                        pass

                # Resolve patient identity from DICOM tags.
                patient_name = study_meta.get("patient_name")
                birth_date = study_meta.get("birth_date")
                patient_id = study_meta.get("patient_id")
                issuer = study_meta.get("issuer_of_patient_id")

                empi_id, match_rule = self.registry.resolve_patient_identity(
                    patient_name=patient_name,
                    birth_date=birth_date,
                    national_id=None,
                    issuer_patient_id=patient_id,
                    issuer_of_identifier=issuer,
                    source_type="DICOMWEB",
                    source_location=self.dicomweb_base,
                    source_patient_key=f"DCMWEB-{study_uid}",
                )
                self.registry._upsert_patient_profile(empi_id, patient_name, birth_date, None, patient_id, issuer, match_rule)
                self.registry._upsert_source_identity(
                    dicomweb_source,
                    f"DCMWEB-{study_uid}",
                    empi_id,
                    patient_name, birth_date, None, patient_id, issuer, match_rule, study_json
                )

                self.registry._upsert_study(
                    study_uid,
                    empi_id,
                    dicomweb_source,
                    modality=study_meta.get("modality"),
                    study_date=study_meta.get("study_date"),
                    study_description=study_meta.get("study_description"),
                    accession_number=study_meta.get("accession_number"),
                    body_part=study_meta.get("body_part"),
                    series_count=len(series_list),
                    instance_count=instance_count,
                    source_patient_key=f"DCMWEB-{study_uid}",
                    storage_tier="dicomweb",
                    metadata=study_json,
                )
                report["studies_indexed"] += 1

            except Exception as exc:
                report["errors"].append(f"Study index error: {exc}")

        notes = [
            f"{report['studies_found']} studies found",
            f"{report['studies_indexed']} indexed",
            f"{report['series_found']} series",
            f"{report['instances_found']} instances",
        ]
        status = "error" if report["errors"] and report["studies_indexed"] == 0 else "success"
        self.registry._record_registry_source(dicomweb_source, status, notes)

        return report

    # ------------------------------------------------------------------
    # DICOMweb WADO-RS — DICOM instance download
    # ------------------------------------------------------------------

    def download_dicom_study(
        self,
        study_uid: str,
        max_instances: Optional[int] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Download all DICOM instances for *study_uid* via WADO-RS and save
        them under ``self.vault_path/{study_uid}/``.

        Parameters
        ----------
        study_uid : str
            DICOM Study Instance UID.
        max_instances : int, optional
            Cap on total instances to download.  Falls back to config value.
        progress_callback : callable(downloaded, total), optional
            Called after each successful instance download.

        Returns
        -------
        dict with keys: downloaded, skipped, bytes_written, vault_dir, errors
        """
        cap = max_instances if max_instances is not None else self._dicom_max_instances
        vault_dir = os.path.join(self.vault_path, _safe_uid(study_uid))
        os.makedirs(vault_dir, exist_ok=True)

        report: Dict[str, Any] = {
            "study_uid": study_uid,
            "vault_dir": vault_dir,
            "downloaded": 0,
            "skipped": 0,
            "bytes_written": 0,
            "errors": [],
        }

        # Enumerate series → instances.
        try:
            series_payload = self._get_json(f"{self.dicomweb_base}/studies/{study_uid}/series", accept="application/dicom+json")
        except Exception as exc:
            report["errors"].append(f"Series list failed: {exc}")
            return report

        if not isinstance(series_payload, list):
            report["errors"].append("Unexpected series payload format")
            return report

        for series_json in series_payload:
            series_uid = _clean_text(self._dicom_tag(series_json, "0020000E"))
            if not series_uid:
                continue

            try:
                instances_payload = self._get_json(
                    f"{self.dicomweb_base}/studies/{study_uid}/series/{series_uid}/instances",
                    accept="application/dicom+json",
                )
            except Exception as exc:
                report["errors"].append(f"Instance list failed for series {series_uid}: {exc}")
                continue

            if not isinstance(instances_payload, list):
                continue

            for instance_json in instances_payload:
                if cap > 0 and (report["downloaded"] + report["skipped"]) >= cap:
                    report["skipped"] += 1
                    continue

                sop_uid = _clean_text(self._dicom_tag(instance_json, "00080018"))
                if not sop_uid:
                    report["skipped"] += 1
                    continue

                out_path = os.path.join(vault_dir, f"{_safe_uid(sop_uid)}.dcm")
                if os.path.exists(out_path) and os.path.getsize(out_path) > 128:
                    # Already downloaded — skip.
                    report["skipped"] += 1
                    continue

                try:
                    instance_url = (
                        f"{self.dicomweb_base}/studies/{study_uid}"
                        f"/series/{series_uid}/instances/{sop_uid}"
                    )
                    data = self._get_bytes(instance_url, "multipart/related; type=application/dicom")
                    if data:
                        idx = data.find(b'\r\n\r\n')
                        if idx != -1:
                            data = data[idx+4:]
                            end_boundary = data.rfind(b'\r\n--')
                            if end_boundary != -1:
                                data = data[:end_boundary]
                        with open(out_path, "wb") as fh:
                            fh.write(data)
                        report["downloaded"] += 1
                        report["bytes_written"] += len(data)
                        if progress_callback:
                            progress_callback(report["downloaded"], cap or -1)
                    else:
                        report["skipped"] += 1
                except Exception as exc:
                    report["errors"].append(f"Instance {sop_uid} download failed: {exc}")
                    report["skipped"] += 1

        return report

    def download_all_studies(self) -> Dict[str, Any]:
        """
        List all studies from QIDO-RS and download each one via WADO-RS.
        Respects the ``dicom_max_instances`` cap across all studies.
        """
        report: Dict[str, Any] = {
            "studies": 0,
            "downloaded": 0,
            "skipped": 0,
            "bytes_written": 0,
            "errors": [],
        }
        remaining = self._dicom_max_instances

        try:
            studies_payload = self._get_json(f"{self.dicomweb_base}/studies", accept="application/dicom+json")
        except Exception as exc:
            report["errors"].append(f"QIDO failed: {exc}")
            return report

        if not isinstance(studies_payload, list):
            return report

        for study_json in studies_payload:
            study_uid, _ = self._parse_dicom_json_study(study_json)
            if not study_uid:
                continue

            study_cap = remaining if self._dicom_max_instances > 0 else 0
            r = self.download_dicom_study(study_uid, max_instances=study_cap)
            report["studies"] += 1
            report["downloaded"] += r["downloaded"]
            report["skipped"] += r["skipped"]
            report["bytes_written"] += r["bytes_written"]
            report["errors"].extend(r["errors"])

            if self.progress_callback:
                self.progress_callback(report["downloaded"], report["studies"] * 10, report["bytes_written"], report["studies"])

            if self._dicom_max_instances > 0:
                remaining -= r["downloaded"]
                if remaining <= 0:
                    break

        return report

    # ------------------------------------------------------------------
    # DICOMweb JSON helpers (DICOM JSON Model — PS3.18)
    # ------------------------------------------------------------------

    def _dicom_tag(self, json_obj: Dict, tag: str) -> Optional[str]:
        """Extract the Value[0] string from a DICOM JSON attribute."""
        attr = json_obj.get(tag)
        if not isinstance(attr, dict):
            return None
        values = attr.get("Value")
        if isinstance(values, list) and values:
            first = values[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                # PersonName
                alphabetic = first.get("Alphabetic") or first.get("alphabetic")
                if isinstance(alphabetic, dict):
                    parts = [_clean_text(alphabetic.get(k)) for k in ("FamilyName", "GivenName", "MiddleName") if alphabetic.get(k)]
                    return " ".join(p for p in parts if p)
                return str(first)
            return str(first)
        return None

    def _parse_dicom_json_study(self, study_json: Dict) -> Tuple[Optional[str], Dict]:
        """Parse a DICOM JSON study object and return (study_uid, meta_dict)."""
        # Tag reference: PS3.6 Table 6-1
        study_uid = _clean_text(self._dicom_tag(study_json, "0020000D"))
        meta: Dict[str, Any] = {
            "study_uid": study_uid,
            "patient_name": _clean_text(self._dicom_tag(study_json, "00100010")),
            "patient_id": _clean_text(self._dicom_tag(study_json, "00100020")),
            "issuer_of_patient_id": _clean_text(self._dicom_tag(study_json, "00100021")),
            "birth_date": _normalize_date(self._dicom_tag(study_json, "00100030") or ""),
            "study_date": _normalize_date(self._dicom_tag(study_json, "00080020") or ""),
            "study_description": _clean_text(self._dicom_tag(study_json, "00081030")),
            "accession_number": _clean_text(self._dicom_tag(study_json, "00080050")),
            "modality": _clean_text(self._dicom_tag(study_json, "00080060")),
            "body_part": _clean_text(self._dicom_tag(study_json, "00180015")),
        }
        return study_uid, meta

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def scan_local_vault(self) -> Dict[str, Any]:
        """
        Scan the local vault path for previously-downloaded DICOM files
        and index their metadata into the PACSContinuityRegistry.
        """
        report: Dict[str, Any] = {
            "files_scanned": 0,
            "studies_indexed": 0,
            "errors": [],
        }
        if pydicom is None:
            report["errors"].append("pydicom is not installed; skipping local vault scan")
            return report
        if not os.path.isdir(self.vault_path):
            report["errors"].append(f"Vault path does not exist: {self.vault_path}")
            return report

        dicomweb_source = {
            "source_type": "DICOMWEB",
            "source_label": "SIIM Hackathon DICOMweb",
            "source_location": self.dicomweb_base,
            "data_class": "DICOM study metadata",
            "api_key_header": self._api_key_header,
            "api_key": self._api_key,
        }

        for root, dirs, files in os.walk(self.vault_path):
            for file_name in files:
                if not file_name.lower().endswith((".dcm", ".dicom", ".ima")):
                    continue
                file_path = os.path.join(root, file_name)
                report["files_scanned"] += 1
                try:
                    dataset = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)
                except Exception as exc:
                    report["errors"].append(f"{file_path}: read error: {exc}")
                    continue

                patient_name = _clean_text(getattr(dataset, "PatientName", ""))
                birth_date = _normalize_date(getattr(dataset, "PatientBirthDate", None))
                national_id = _normalize_identifier(getattr(dataset, "PatientID", None))
                issuer_patient_id = _normalize_identifier(getattr(dataset, "IssuerOfPatientID", None))
                issuer_of_identifier = _normalize_identifier(getattr(dataset, "IssuerOfPatientID", None))
                study_uid = _normalize_identifier(getattr(dataset, "StudyInstanceUID", None))
                if not study_uid:
                    study_uid = "VAULT-" + _stable_hash(file_path)

                source_patient_key = self.registry._source_patient_key(
                    "DICOMWEB", self.dicomweb_base, patient_name, birth_date, national_id, issuer_patient_id, study_uid
                )
                empi_id, match_rule = self.registry.resolve_patient_identity(
                    patient_name=patient_name,
                    birth_date=birth_date,
                    national_id=national_id,
                    issuer_patient_id=issuer_patient_id,
                    issuer_of_identifier=issuer_of_identifier,
                    source_type="DICOMWEB",
                    source_location=self.dicomweb_base,
                    source_patient_key=source_patient_key,
                    source_identity=study_uid,
                )
                self.registry._upsert_patient_profile(
                    empi_id, patient_name, birth_date, national_id, issuer_patient_id, issuer_of_identifier, match_rule
                )
                self.registry._upsert_source_identity(
                    dicomweb_source,
                    source_patient_key,
                    empi_id,
                    patient_name,
                    birth_date,
                    national_id,
                    issuer_patient_id,
                    issuer_of_identifier,
                    match_rule,
                    {
                        "file_path": file_path,
                        "study_uid": study_uid,
                        "modality": _clean_text(getattr(dataset, "Modality", "")),
                        "series_uid": _normalize_identifier(getattr(dataset, "SeriesInstanceUID", None)),
                        "sop_uid": _normalize_identifier(getattr(dataset, "SOPInstanceUID", None)),
                        "study_date": getattr(dataset, "StudyDate", None),
                    },
                )
                self.registry._upsert_study(
                    study_uid,
                    empi_id,
                    dicomweb_source,
                    modality=_clean_text(getattr(dataset, "Modality", "")),
                    study_date=getattr(dataset, "StudyDate", None),
                    study_description=_clean_text(getattr(dataset, "StudyDescription", "")) or "DICOM vault file",
                    accession_number=_clean_text(getattr(dataset, "AccessionNumber", "")),
                    body_part=_clean_text(getattr(dataset, "BodyPartExamined", "")),
                    series_count=1,
                    instance_count=1,
                    source_patient_key=source_patient_key,
                    storage_tier="local_vault",
                    metadata={
                        "file_path": file_path,
                        "study_uid": study_uid,
                        "modality": _clean_text(getattr(dataset, "Modality", "")),
                    },
                )
                report["studies_indexed"] += 1

        return report

    def full_ingest(self) -> Dict[str, Any]:
        """
        Run the complete ingest pipeline:
        1. Fetch all FHIR resources and index them.
        2. Fetch all DICOMweb study metadata.
        3. Download DICOM instances into the vault.
        4. Scan the vault for existing DICOM files and index their metadata.

        Returns a combined report dict.
        """
        report: Dict[str, Any] = {
            "started_at": datetime.utcnow().isoformat() + "Z",
            "fhir": {},
            "dicomweb_metadata": {},
            "dicom_download": {},
            "vault_scan": {},
            "finished_at": None,
            "summary": "",
        }

        # Step 1 — FHIR
        try:
            report["fhir"] = self.ingest_fhir()
        except Exception as exc:
            report["fhir"] = {"error": str(exc)}

        # Step 2 — DICOMweb metadata
        try:
            report["dicomweb_metadata"] = self.ingest_dicomweb_metadata()
        except Exception as exc:
            report["dicomweb_metadata"] = {"error": str(exc)}

        # Step 3 — DICOM file download
        try:
            report["dicom_download"] = self.download_all_studies()
        except Exception as exc:
            report["dicom_download"] = {"error": str(exc)}

        # Step 4 — Index any DICOM files already present in the vault.
        try:
            report["vault_scan"] = self.scan_local_vault()
        except Exception as exc:
            report["vault_scan"] = {"error": str(exc)}

        report["finished_at"] = datetime.utcnow().isoformat() + "Z"

        # Human-readable summary.
        fhir = report["fhir"]
        dcm_meta = report["dicomweb_metadata"]
        dcm_dl = report["dicom_download"]
        total_fhir = sum(v.get("indexed", 0) for v in fhir.values() if isinstance(v, dict))
        vault = report.get("vault_scan", {})
        report["summary"] = (
            f"FHIR: {total_fhir} resources indexed across {len(fhir)} types. "
            f"DICOMweb: {dcm_meta.get('studies_indexed', 0)} studies / "
            f"{dcm_meta.get('instances_found', 0)} instances discovered. "
            f"Downloaded: {dcm_dl.get('downloaded', 0)} DICOM instances "
            f"({_human_bytes(dcm_dl.get('bytes_written', 0))}) "
            f"to {self.vault_path}. "
            f"Vault scan: {vault.get('files_scanned', 0)} files / {vault.get('studies_indexed', 0)} indexed."
        )
        return report


# ---------------------------------------------------------------------------
# Background job wrapper
# ---------------------------------------------------------------------------

def start_ingest_job(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Launch a full ingest in a background thread and return immediately
    with the current state snapshot.  Poll ``get_ingest_state()`` for progress.
    """
    with _ingest_lock:
        if _ingest_state["status"] == "running":
            started_at = _ingest_state.get("started_at")
            stale = False
            if started_at:
                try:
                    from datetime import timezone
                    started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    stale = (datetime.now(timezone.utc) - started_dt).total_seconds() > 3600
                except Exception:
                    stale = True
            if not stale:
                return {"status": "already_running", "state": get_ingest_state()}
            # Stale job — reset and restart.
            _ingest_state.update({
                "status": "idle",
                "started_at": None,
                "finished_at": None,
                "progress": {},
                "dicom": {k: 0 for k in _ingest_state["dicom"]},
                "errors": ["Previous run was stale (>1h); resetting and restarting."],
                "report": None,
            })
            _save_ingest_state(_ingest_state)
        _ingest_state.update({
            "status": "running",
            "started_at": datetime.utcnow().isoformat() + "Z",
            "finished_at": None,
            "progress": {},
            "dicom": {k: 0 for k in _ingest_state["dicom"]},
            "errors": [],
            "report": None,
        })

    progress_types = _DEFAULT_FHIR_RESOURCES
    try:
        ingest = SIIMHackathonIngest(config_path=config_path)
        progress_types = getattr(ingest, '_fhir_resources', progress_types)
    except Exception:
        pass
    _initialize_ingest_progress(progress_types)

    def _run():
        try:
            ingest = SIIMHackathonIngest(config_path=config_path)
            
            def cb(downloaded, total, b_written, st_found):
                with _ingest_lock:
                    _ingest_state["dicom"]["instances_downloaded"] = downloaded
                    _ingest_state["dicom"]["bytes_written"] = b_written
                    _ingest_state["dicom"]["studies_found"] = st_found
            ingest.progress_callback = cb
            
            report = ingest.full_ingest()

            # Also index vault DICOM files into PatientDocumentIndexer so
            # "show my records" and history packs can find them.
            try:
                from backend.sdoh_patient_index import PatientDocumentIndexer
                indexer = PatientDocumentIndexer()
                indexer.scan_folder(ingest.vault_path)
            except Exception as idx_exc:
                print(f"[SIIM] PatientDocumentIndexer scan failed: {idx_exc}")

            with _ingest_lock:
                _ingest_state["status"] = "completed"
                _ingest_state["finished_at"] = datetime.utcnow().isoformat() + "Z"
                _ingest_state["report"] = report
                # Surface FHIR progress counters.
                for rt, v in report.get("fhir", {}).items():
                    if isinstance(v, dict):
                        _ingest_state["progress"][rt] = v
                dl = report.get("dicom_download", {})
                _ingest_state["dicom"]["instances_downloaded"] = dl.get("downloaded", 0)
                _ingest_state["dicom"]["instances_skipped"] = dl.get("skipped", 0)
                _ingest_state["dicom"]["bytes_written"] = dl.get("bytes_written", 0)
                dcm_meta = report.get("dicomweb_metadata", {})
                _ingest_state["dicom"]["studies_found"] = dcm_meta.get("studies_found", 0)
                _ingest_state["dicom"]["instances_queued"] = dcm_meta.get("instances_found", 0)
                vault = report.get("vault_scan", {})
                _ingest_state["dicom"]["vault_files_scanned"] = vault.get("files_scanned", 0)
                _ingest_state["dicom"]["vault_studies_indexed"] = vault.get("studies_indexed", 0)
                _save_ingest_state(_ingest_state)
        except Exception as exc:
            with _ingest_lock:
                _ingest_state["status"] = "error"
                _ingest_state["errors"].append(str(exc))
                _ingest_state["finished_at"] = datetime.utcnow().isoformat() + "Z"
                _save_ingest_state(_ingest_state)

    thread = threading.Thread(target=_run, daemon=True, name="siim-ingest")
    thread.start()
    return {"status": "started", "state": get_ingest_state()}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_uid(uid: str) -> str:
    """Convert a DICOM UID to a safe filesystem filename."""
    return re.sub(r"[^\w.\-]", "_", uid)


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"
