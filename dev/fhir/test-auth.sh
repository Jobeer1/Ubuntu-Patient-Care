#!/bin/bash
# Test script for OAuth2 auth stub

set -e

AUTH_URL="http://localhost:5000"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Testing OAuth2 Auth Stub..."
echo "=============================="
echo ""

# Test 1: Get token
echo "Test 1: Getting access token..."
TOKEN_RESPONSE=$(curl -s -X POST ${AUTH_URL}/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"dev"}')

TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✓ Token received: ${TOKEN:0:30}...${NC}"
else
    echo -e "${RED}✗ Failed to get token${NC}"
    exit 1
fi

# Test 2: Validate token
echo ""
echo "Test 2: Validating token..."
VALIDATE_RESPONSE=$(curl -s -X POST ${AUTH_URL}/auth/validate \
  -H "Authorization: Bearer ${TOKEN}")

if echo "$VALIDATE_RESPONSE" | grep -q '"valid":true'; then
    echo -e "${GREEN}✓ Token is valid${NC}"
else
    echo -e "${RED}✗ Token validation failed${NC}"
    exit 1
fi

# Test 3: List tokens
echo ""
echo "Test 3: Listing active tokens..."
LIST_RESPONSE=$(curl -s ${AUTH_URL}/auth/tokens)

if echo "$LIST_RESPONSE" | grep -q '"active_tokens"'; then
    echo -e "${GREEN}✓ Token list retrieved${NC}"
else
    echo -e "${RED}✗ Failed to list tokens${NC}"
    exit 1
fi

# Test 4: Use token with FHIR server (if running)
echo ""
echo "Test 4: Using token with FHIR server..."
if curl -s -f http://localhost:8080/fhir/metadata > /dev/null 2>&1; then
    FHIR_RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
      http://localhost:8080/fhir/Patient?_count=1)
    
    if echo "$FHIR_RESPONSE" | grep -q '"resourceType"'; then
        echo -e "${GREEN}✓ FHIR request with token successful${NC}"
    else
        echo -e "${RED}✗ FHIR request failed${NC}"
    fi
else
    echo "⚠️  FHIR server not running (skipping)"
fi

# Test 5: Revoke token
echo ""
echo "Test 5: Revoking token..."
REVOKE_RESPONSE=$(curl -s -X POST ${AUTH_URL}/auth/revoke \
  -H "Authorization: Bearer ${TOKEN}")

if echo "$REVOKE_RESPONSE" | grep -q '"message":"Token revoked"'; then
    echo -e "${GREEN}✓ Token revoked${NC}"
else
    echo -e "${RED}✗ Token revocation failed${NC}"
    exit 1
fi

# Test 6: Validate revoked token (should fail)
echo ""
echo "Test 6: Validating revoked token (should fail)..."
VALIDATE_REVOKED=$(curl -s -X POST ${AUTH_URL}/auth/validate \
  -H "Authorization: Bearer ${TOKEN}")

if echo "$VALIDATE_REVOKED" | grep -q '"valid":false'; then
    echo -e "${GREEN}✓ Revoked token correctly rejected${NC}"
else
    echo -e "${RED}✗ Revoked token still valid (error!)${NC}"
    exit 1
fi

echo ""
echo "=============================="
echo -e "${GREEN}All tests passed!${NC}"
echo ""
echo "Auth stub is working correctly."
echo "Token: ${TOKEN:0:30}..."
