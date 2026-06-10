"""Patient Data Tools — real database queries for the SDOH agent
================================================================
Wraps the local PACS continuity registry (instance/pacs_continuity_registry.db)
to provide honest, deterministic lookups for:
  - Patient identity by SA national ID or name
  - Imaging studies for a matched patient
  - Account statements / billing (placeholder — wired when billing system is connected)
  - Appointments (placeholder — wired when appointments system is connected)

Safety: all reads are read-only. Nothing is written back to the registry from here.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "instance", "pacs_continuity_registry.db"
)


def _normalize_id(value: str) -> str:
    """Strip spaces and non-alphanumeric chars from an identifier."""
    return re.sub(r"[^a-zA-Z0-9]", "", (value or "").strip())


def _is_sa_national_id(text: str) -> bool:
    """Return True if text looks like a 13-digit SA national ID number."""
    digits = re.sub(r"\D", "", text)
    return len(digits) == 13


def _extract_sa_national_id(text: str) -> Optional[str]:
    """Find and return the first 13-digit run of digits in text, or None."""
    # Search in original text first (word boundaries work with spaces present)
    match = re.search(r"(?<!\d)(\d{13})(?!\d)", (text or ""))
    return match.group(1) if match else None


class PatientDataTools:
    """
    Read-only query layer over the local PACS continuity registry.

    Usage
    -----
    tools = PatientDataTools()
    result = tools.lookup_patient("8602170080084")
    studies = tools.get_studies_for_patient(result["empi_id"])
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _DEFAULT_DB_PATH

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _db_available(self) -> bool:
        return os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0

    # ------------------------------------------------------------------
    # Patient lookup
    # ------------------------------------------------------------------

    def lookup_patient_by_national_id(self, national_id: str) -> Optional[Dict[str, Any]]:
        """
        Look up a patient by SA national ID.
        Returns a dict with patient info, or None if not found.
        """
        if not self._db_available():
            return None
        normalized = _normalize_id(national_id)
        try:
            with self._conn() as conn:
                # Exact match first
                row = conn.execute(
                    "SELECT * FROM empi_patients WHERE REPLACE(REPLACE(national_id,' ',''),'-','') = ? LIMIT 1",
                    (normalized,),
                ).fetchone()
                if row:
                    return dict(row)
                # Partial match: national_id ends with the digits (handles older records stored with prefixes)
                row = conn.execute(
                    "SELECT * FROM empi_patients WHERE national_id LIKE ? LIMIT 1",
                    (f"%{normalized}%",),
                ).fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    def lookup_patient_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Fuzzy name lookup — returns up to 5 candidates ordered by name similarity.
        Uses LIKE on the stored DICOM name (LAST^FIRST format).
        """
        if not self._db_available():
            return []
        parts = re.sub(r"[^a-zA-Z ]", "", name).upper().split()
        if not parts:
            return []
        try:
            with self._conn() as conn:
                candidates = []
                for part in parts:
                    if len(part) >= 3:
                        rows = conn.execute(
                            "SELECT * FROM empi_patients WHERE patient_name LIKE ? LIMIT 5",
                            (f"%{part}%",),
                        ).fetchall()
                        for row in rows:
                            r = dict(row)
                            if r not in candidates:
                                candidates.append(r)
                return candidates[:5]
        except Exception:
            return []

    def lookup_patient(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Smart lookup: tries national ID first, then name.
        Returns first matched patient dict, or None.
        """
        national_id = _extract_sa_national_id(query)
        if national_id:
            result = self.lookup_patient_by_national_id(national_id)
            if result:
                return result
        # Try name search
        candidates = self.lookup_patient_by_name(query)
        return candidates[0] if candidates else None

    # ------------------------------------------------------------------
    # Studies
    # ------------------------------------------------------------------

    def get_studies_for_patient(self, empi_id: str) -> List[Dict[str, Any]]:
        """Return all imaging studies registered for a patient."""
        if not self._db_available():
            return []
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT study_instance_uid, modality, study_date, study_description,
                              accession_number, body_part, series_count, instance_count,
                              source_type, source_location
                         FROM imaging_studies
                        WHERE empi_id = ?
                        ORDER BY study_date DESC""",
                    (empi_id,),
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def get_study_asset_path(self, study_instance_uid: str) -> Optional[str]:
        """Return the local file path for a study if available in storage_assets."""
        if not self._db_available():
            return None
        try:
            with self._conn() as conn:
                row = conn.execute(
                    """SELECT sa.asset_path, sa.source_location
                         FROM storage_assets sa
                        WHERE sa.asset_path LIKE ?
                           OR sa.details_json LIKE ?
                        LIMIT 1""",
                    (f"%{study_instance_uid}%", f"%{study_instance_uid}%"),
                ).fetchone()
                return row["asset_path"] if row else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Formatted response helpers
    # ------------------------------------------------------------------

    def format_patient_summary(self, patient: Dict[str, Any]) -> str:
        """Return a brief patient identity summary for chat display."""
        name_raw = patient.get("patient_name", "Unknown")
        # DICOM stores LAST^FIRST^MIDDLE — convert to readable
        parts = name_raw.replace("^", " ").title().split()
        name = " ".join(p for p in parts if p not in {"N", "Nn", "Mn", "Mr", "Miss", "Mrs", "Ms"})
        dob = patient.get("birth_date", "")
        return f"{name.strip()} (DOB: {dob})" if dob else name.strip()

    def format_studies_list(self, studies: List[Dict[str, Any]]) -> str:
        """Return a numbered list of studies for chat display."""
        if not studies:
            return "No imaging studies found in our local registry for this patient."
        lines = []
        for i, s in enumerate(studies, 1):
            modality = s.get("modality", "?")
            desc = s.get("study_description", "Study")
            date = s.get("study_date", "Unknown date")
            location = s.get("source_location", "")
            accessible = os.path.exists(location) if location else False
            status = "✓ drive accessible" if accessible else "⚠ drive offline"
            lines.append(f"{i}. {modality} — {desc} ({date}) [{status}]")
        return "\n".join(lines)

    def check_drive_accessible(self, source_location: str) -> bool:
        """Return True if the NAS drive path is currently accessible."""
        if not source_location:
            return False
        try:
            return os.path.exists(source_location)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Billing statements (placeholder — connect your billing system here)
    # ------------------------------------------------------------------

    def get_account_statement(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder for billing system integration.
        Returns a status dict indicating which system needs to be connected.

        TO CONNECT: Replace this method body with a query to your billing
        system (GoodX, Elixir, Healthbridge, etc.) using the patient's
        account number or national ID.
        """
        return {
            "status": "not_connected",
            "message": (
                "Account statement retrieval is not yet connected to our billing system. "
                "Please contact the practice directly for a statement, or ask the administrator "
                "to connect the billing integration."
            ),
            "patient_name": self.format_patient_summary(patient),
            "billing_system": "pending_integration",
        }

    # ------------------------------------------------------------------
    # Appointments (placeholder — connect your appointments system here)
    # ------------------------------------------------------------------

    def get_appointments(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Placeholder for appointments system integration.

        TO CONNECT: Replace this method body with a query to your appointments
        system (same as billing, or Google Calendar, or a custom DB).
        """
        return {
            "status": "not_connected",
            "message": (
                "Appointment retrieval is not yet connected to our scheduling system. "
                "Please phone the practice to confirm your appointments, or ask the administrator "
                "to connect the scheduling integration."
            ),
            "patient_name": self.format_patient_summary(patient),
            "scheduling_system": "pending_integration",
        }


# Module-level singleton — reused across requests
_tools_instance: Optional[PatientDataTools] = None


def get_tools() -> PatientDataTools:
    global _tools_instance
    if _tools_instance is None:
        _tools_instance = PatientDataTools()
    return _tools_instance
