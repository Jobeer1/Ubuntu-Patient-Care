"""SIIM Hackathon ingest routes
==============================
Exposes HTTP endpoints to trigger or query the SIIM 2026 Hackathon
patient-data ingest pipeline (FHIR + DICOMweb).

Registered at  /api/sdoh/siim  in flask_app.py.

Routes
------
POST /api/sdoh/siim/ingest
    Start a full background ingest (FHIR + DICOMweb metadata + DICOM download).
    Accepts optional JSON body: {"dicom_download": true|false}
    Returns 202 with job state immediately.

GET  /api/sdoh/siim/ingest/status
    Poll current ingest job state.

GET  /api/sdoh/siim/sources
    List the SIIM source registrations from the local registry.

GET  /api/sdoh/siim/patients
    List all patients that were ingested from the SIIM Hackathon sources.

GET  /api/sdoh/siim/studies
    List all imaging studies ingested from SIIM sources.

Security
--------
* Admin-only: requires `admin` role or user_id == 0768193339.
* The API key is never returned in any response payload.
"""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

from backend.auth_utils import require_auth
from backend.siim_hackathon import (
    SIIMHackathonIngest,
    get_ingest_state,
    start_ingest_job,
)
from backend.pacs_registry import PACSContinuityRegistry

siim_bp = Blueprint("siim", __name__)

_WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_ADMIN_USER_IDS = {"0768193339"}


def _is_admin(current_user) -> bool:
    if getattr(current_user, "user_role", None) == "admin":
        return True
    uid = str(getattr(current_user, "user_id", "") or "")
    return uid in _ADMIN_USER_IDS


# ---------------------------------------------------------------------------
# POST /ingest  — start background ingest
# ---------------------------------------------------------------------------

@siim_bp.route("/ingest", methods=["POST"])
@require_auth
def trigger_ingest(current_user):
    if not _is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    result = start_ingest_job()
    status_code = 202 if result.get("status") == "started" else 200
    return jsonify(result), status_code


# ---------------------------------------------------------------------------
# GET /ingest/status  — poll job progress
# ---------------------------------------------------------------------------

@siim_bp.route("/ingest/status", methods=["GET"])
@require_auth
def ingest_status(current_user):
    if not _is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    state = get_ingest_state()
    # Strip the full report on non-completed states to keep payload small.
    if state.get("status") != "completed":
        state.pop("report", None)
    return jsonify(state), 200


# ---------------------------------------------------------------------------
# GET /sources  — list registered SIIM sources in the local registry
# ---------------------------------------------------------------------------

@siim_bp.route("/sources", methods=["GET"])
@require_auth
def list_sources(current_user):
    if not _is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    registry = PACSContinuityRegistry(workspace_path=_WORKSPACE)
    sources = registry.discover_sources()
    siim_sources = [
        {
            "source_type": s.get("source_type"),
            "source_label": s.get("source_label"),
            "source_location": s.get("source_location"),
            "data_class": s.get("data_class"),
        }
        for s in sources
        if "siim" in (s.get("source_tag") or "").lower()
        or "siim" in (s.get("source_label") or "").lower()
    ]
    return jsonify({"sources": siim_sources}), 200


# ---------------------------------------------------------------------------
# GET /patients  — patients ingested from SIIM sources
# ---------------------------------------------------------------------------

@siim_bp.route("/patients", methods=["GET"])
@require_auth
def list_patients(current_user):
    if not _is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    registry = PACSContinuityRegistry(workspace_path=_WORKSPACE)
    siim_locations = {"https://hackathon.siim.org/fhir", "https://hackathon.siim.org/dicomweb"}

    try:
        import sqlite3
        conn = sqlite3.connect(registry.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT DISTINCT ep.empi_id, ep.patient_name, ep.birth_date,
                            ep.national_id, ep.issuer_patient_id, ep.created_at
            FROM empi_patients ep
            JOIN source_identity_links sil ON ep.empi_id = sil.empi_id
            WHERE sil.source_location IN ({})
            ORDER BY ep.patient_name
            """.format(",".join("?" for _ in siim_locations)),
            tuple(siim_locations),
        ).fetchall()
        conn.close()
        patients = [dict(r) for r in rows]
    except Exception as exc:
        patients = []

    return jsonify({"count": len(patients), "patients": patients}), 200


# ---------------------------------------------------------------------------
# GET /studies  — imaging studies ingested from SIIM sources
# ---------------------------------------------------------------------------

@siim_bp.route("/studies", methods=["GET"])
@require_auth
def list_studies(current_user):
    if not _is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403

    registry = PACSContinuityRegistry(workspace_path=_WORKSPACE)
    siim_locations = {"https://hackathon.siim.org/fhir", "https://hackathon.siim.org/dicomweb"}

    try:
        import sqlite3
        conn = sqlite3.connect(registry.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT study_instance_uid, empi_id, modality, study_date,
                   study_description, accession_number, body_part,
                   series_count, instance_count, storage_tier, source_type
            FROM imaging_studies
            WHERE source_location IN ({})
            ORDER BY study_date DESC
            """.format(",".join("?" for _ in siim_locations)),
            tuple(siim_locations),
        ).fetchall()
        conn.close()
        studies = [dict(r) for r in rows]
    except Exception as exc:
        studies = []

    return jsonify({"count": len(studies), "studies": studies}), 200
