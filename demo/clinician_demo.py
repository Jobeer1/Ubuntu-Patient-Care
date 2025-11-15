"""
Clinician demo for Phase 1 (simple, safe, no external services).

What it does:
- Registers a sample patient in the PatientIDAdapter
- Creates a sample report (dictionary)
- Finalizes the report using ReportFinalizer (writes to a local demo ledger file)
- Prints the audit stamp and verifies it
- Shows tamper detection example

Run (PowerShell):
    python .\demo\clinician_demo.py

This script is intended for clinicians to see the high-level flow and outputs.
"""

import json
import os
from pprint import pprint

# Make imports work when running script from repo root
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from fhir_adapter.adapters.patient_id_adapter import PatientIDAdapter, ExternalID, ExternalIDType
from audit.report_finalizer import ReportFinalizer

LEDGER_PATH = str(repo_root / "demo_audit.ledger")


def run_demo():
    print("\n=== Phase 1 Clinician Demo ===\n")

    # 1) Register a patient
    adapter = PatientIDAdapter(auto_generate_uuid=True)
    openemr_id = "PAT-CLIN-001"
    print(f"Registering patient with OpenEMR ID: {openemr_id}")
    fhir_uuid = adapter.register_mapping(
        openemr_id,
        external_ids=[
            ExternalID(ExternalIDType.SSN, "999-88-7777"),
            ExternalID(ExternalIDType.INSURANCE, "INS-DEMO-001")
        ]
    )
    print(f"Mapped to FHIR UUID: {fhir_uuid}\n")

    # 2) Create a sample report
    report_id = "REPORT-CLIN-001"
    report_content = {
        "patient_openemr_id": openemr_id,
        "patient_fhir_uuid": fhir_uuid,
        "study": "XR-LEFT-KNEE",
        "findings": "No acute osseous abnormality.",
        "impression": "Normal left knee x-ray."
    }

    print("Sample report content:")
    pprint(report_content)
    print("")

    # 3) Finalize report and write audit entry
    finalizer = ReportFinalizer(ledger_path=LEDGER_PATH)
    print(f"Finalizing report {report_id} and recording audit entry in ledger: {LEDGER_PATH}")
    stamp = finalizer.finalize_report(
        report_id=report_id,
        content=report_content,
        practitioner_id="DR-ALICE-01",
        signature="clinician-demo-signature"
    )

    print("\nAudit stamp created:")
    pprint(stamp.to_dict())

    # 4) Verify stamp (should be valid)
    is_valid = finalizer.verify_report_stamp(report_id, report_content, stamp)
    print(f"\nVerification of audit stamp: {'VALID' if is_valid else 'INVALID'}")

    # 5) Show audit trail entries for this report
    trail = finalizer.get_audit_trail(report_id)
    print(f"\nAudit trail entries found for {report_id}: {len(trail)}")
    if trail:
        print("Most recent audit entry:")
        pprint(trail[-1])

    # 6) Tamper demonstration: modify report and verify fails
    tampered = dict(report_content)
    tampered['impression'] = "Subtle fracture suspected."  # tamper
    tamper_valid = finalizer.verify_report_stamp(report_id, tampered, stamp)
    print(f"\nAfter tampering, verification: {'VALID' if tamper_valid else 'INVALID (tamper detected)'}")

    print("\n=== Demo complete ===\n")


if __name__ == '__main__':
    run_demo()
