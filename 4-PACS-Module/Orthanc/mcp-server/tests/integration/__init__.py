"""
Integration Tests for Patient Access System

This package contains end-to-end integration tests for the complete
patient access control system.

Test Suites:
- test_patient_access_e2e.py: Patient access workflow tests
- test_doctor_access_e2e.py: Doctor assignment and access tests
- test_family_access_e2e.py: Family member access tests

To run all integration tests:
    pytest tests/integration/ -v

To run a specific test suite:
    pytest tests/integration/test_patient_access_e2e.py -v

Requirements:
- MCP server running on http://localhost:8080
- PACS backend running on http://localhost:5000
- Test users created in database
- pytest and requests packages installed
"""

__version__ = "1.0.0"
