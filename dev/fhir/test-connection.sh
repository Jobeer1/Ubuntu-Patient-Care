#!/bin/bash
# Quick test script for FHIR server connectivity
# Usage: ./test-connection.sh

set -e

FHIR_BASE="http://localhost:8080/fhir"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Testing FHIR Server Connection..."
echo "=================================="
echo ""

# Test 1: Metadata endpoint
echo "Test 1: Checking server metadata..."
if curl -s -f "${FHIR_BASE}/metadata" > /dev/null; then
    echo -e "${GREEN}✓ Server is responding${NC}"
else
    echo -e "${RED}✗ Server is not responding${NC}"
    echo "Make sure the server is running: docker-compose up -d"
    exit 1
fi

# Test 2: Create a test patient
echo ""
echo "Test 2: Creating test patient..."
PATIENT_RESPONSE=$(curl -s -X POST "${FHIR_BASE}/Patient" \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "Patient",
    "identifier": [{
      "system": "urn:test:pid",
      "value": "TEST-001"
    }],
    "name": [{
      "family": "TestPatient",
      "given": ["Dev"]
    }],
    "gender": "unknown",
    "birthDate": "2000-01-01"
  }')

if echo "$PATIENT_RESPONSE" | grep -q "\"resourceType\":\"Patient\""; then
    PATIENT_ID=$(echo "$PATIENT_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${GREEN}✓ Patient created successfully (ID: $PATIENT_ID)${NC}"
else
    echo -e "${RED}✗ Failed to create patient${NC}"
    echo "$PATIENT_RESPONSE"
    exit 1
fi

# Test 3: Read the patient back
echo ""
echo "Test 3: Reading patient back..."
if curl -s -f "${FHIR_BASE}/Patient/${PATIENT_ID}" > /dev/null; then
    echo -e "${GREEN}✓ Patient retrieved successfully${NC}"
else
    echo -e "${RED}✗ Failed to retrieve patient${NC}"
    exit 1
fi

# Test 4: Search for patient
echo ""
echo "Test 4: Searching for patient..."
SEARCH_RESPONSE=$(curl -s "${FHIR_BASE}/Patient?family=TestPatient")
if echo "$SEARCH_RESPONSE" | grep -q "TestPatient"; then
    echo -e "${GREEN}✓ Patient search working${NC}"
else
    echo -e "${RED}✗ Patient search failed${NC}"
    exit 1
fi

echo ""
echo "=================================="
echo -e "${GREEN}All tests passed! FHIR server is ready.${NC}"
echo ""
echo "Server URL: ${FHIR_BASE}"
echo "Test Patient ID: ${PATIENT_ID}"
echo ""
echo "Next steps:"
echo "  - Run smoke tests: pytest tests/test_fhir_smoke.py"
echo "  - View in browser: http://localhost:8080/fhir/Patient/${PATIENT_ID}"
