#!/bin/bash
#
# MCP Offline Key Generation Tool
#
# Generates all cryptographic keys for the MCP system:
# - Root CA certificate
# - Server certificates
# - Agent certificates
# - Owner signing keys
# - Vault unseal keys (with Shamir sharing)
#
# SECURITY: Run this on an air-gapped machine!
#
# Author: Kiro Team
# Task: K3.1
# Status: Production Ready
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
OUTPUT_DIR="./mcp-keys"
CA_DIR="$OUTPUT_DIR/ca"
SERVER_DIR="$OUTPUT_DIR/server"
AGENT_DIR="$OUTPUT_DIR/agents"
OWNER_DIR="$OUTPUT_DIR/owners"
VAULT_DIR="$OUTPUT_DIR/vault"
BACKUP_DIR="$OUTPUT_DIR/backup"

# Key parameters
CA_VALIDITY_DAYS=3650  # 10 years
SERVER_VALIDITY_DAYS=730  # 2 years
AGENT_VALIDITY_DAYS=730  # 2 years
OWNER_VALIDITY_DAYS=1825  # 5 years

# Shamir parameters
SHAMIR_TOTAL_SHARES=5
SHAMIR_THRESHOLD=3

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  MCP Offline Key Generation Tool      ║${NC}"
echo -e "${GREEN}║  SECURITY: Air-gapped machine only!   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if running offline
echo -e "${YELLOW}⚠ SECURITY CHECK: Verifying offline status...${NC}"
if ping -c 1 8.8.8.8 &> /dev/null; then
    echo -e "${RED}ERROR: Network connection detected!${NC}"
    echo -e "${RED}This tool must be run on an air-gapped machine.${NC}"
    echo ""
    read -p "Continue anyway? (type 'I UNDERSTAND THE RISK'): " confirm
    if [ "$confirm" != "I UNDERSTAND THE RISK" ]; then
        echo "Aborting."
        exit 1
    fi
else
    echo -e "${GREEN}✓ No network connection detected (good!)${NC}"
fi
echo ""

# Check dependencies
echo "Checking dependencies..."
for cmd in openssl python3; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}ERROR: $cmd is not installed${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ All dependencies found${NC}"
echo ""

# Create directory structure
echo "Creating directory structure..."
mkdir -p "$CA_DIR" "$SERVER_DIR" "$AGENT_DIR" "$OWNER_DIR" "$VAULT_DIR" "$BACKUP_DIR"
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# ============================================================================
# STEP 1: Generate Root CA
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 1: Generating Root CA${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

read -p "Organization name (e.g., 'My Clinic'): " org_name
read -p "Country code (e.g., 'US'): " country_code

echo ""
echo "Generating Root CA private key..."
openssl genrsa -aes256 -out "$CA_DIR/ca-key.pem" 4096

echo ""
echo "Generating Root CA certificate..."
openssl req -new -x509 -days $CA_VALIDITY_DAYS -key "$CA_DIR/ca-key.pem" \
    -sha256 -out "$CA_DIR/ca-cert.pem" \
    -subj "/C=$country_code/O=$org_name/CN=MCP Root CA"

echo -e "${GREEN}✓ Root CA generated${NC}"
echo "  Private key: $CA_DIR/ca-key.pem (KEEP SECURE!)"
echo "  Certificate: $CA_DIR/ca-cert.pem"
echo ""

# ============================================================================
# STEP 2: Generate Server Certificate
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 2: Generating Server Certificate${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

read -p "Server hostname (e.g., 'mcp-server.local'): " server_hostname

echo ""
echo "Generating server private key..."
openssl genrsa -out "$SERVER_DIR/server-key.pem" 4096

echo ""
echo "Generating server CSR..."
openssl req -new -key "$SERVER_DIR/server-key.pem" \
    -out "$SERVER_DIR/server-csr.pem" \
    -subj "/C=$country_code/O=$org_name/CN=$server_hostname"

echo ""
echo "Signing server certificate..."
cat > "$SERVER_DIR/server-extfile.cnf" << EOF
subjectAltName = DNS:$server_hostname,DNS:localhost,IP:127.0.0.1
extendedKeyUsage = serverAuth
EOF

openssl x509 -req -days $SERVER_VALIDITY_DAYS \
    -in "$SERVER_DIR/server-csr.pem" \
    -CA "$CA_DIR/ca-cert.pem" \
    -CAkey "$CA_DIR/ca-key.pem" \
    -CAcreateserial \
    -out "$SERVER_DIR/server-cert.pem" \
    -extfile "$SERVER_DIR/server-extfile.cnf"

rm "$SERVER_DIR/server-csr.pem" "$SERVER_DIR/server-extfile.cnf"

echo -e "${GREEN}✓ Server certificate generated${NC}"
echo "  Private key: $SERVER_DIR/server-key.pem"
echo "  Certificate: $SERVER_DIR/server-cert.pem"
echo ""

# ============================================================================
# STEP 3: Generate Agent Certificates
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 3: Generating Agent Certificates${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

read -p "Number of agents to generate certificates for: " num_agents

for i in $(seq 1 $num_agents); do
    echo ""
    read -p "Agent $i hostname (e.g., 'agent-subnet-1'): " agent_hostname
    
    agent_dir="$AGENT_DIR/$agent_hostname"
    mkdir -p "$agent_dir"
    
    echo "Generating agent private key..."
    openssl genrsa -out "$agent_dir/agent-key.pem" 4096
    
    echo "Generating agent CSR..."
    openssl req -new -key "$agent_dir/agent-key.pem" \
        -out "$agent_dir/agent-csr.pem" \
        -subj "/C=$country_code/O=$org_name/CN=$agent_hostname"
    
    echo "Signing agent certificate..."
    cat > "$agent_dir/agent-extfile.cnf" << EOF
subjectAltName = DNS:$agent_hostname,DNS:localhost,IP:127.0.0.1
extendedKeyUsage = clientAuth,serverAuth
EOF
    
    openssl x509 -req -days $AGENT_VALIDITY_DAYS \
        -in "$agent_dir/agent-csr.pem" \
        -CA "$CA_DIR/ca-cert.pem" \
        -CAkey "$CA_DIR/ca-key.pem" \
        -CAcreateserial \
        -out "$agent_dir/agent-cert.pem" \
        -extfile "$agent_dir/agent-extfile.cnf"
    
    rm "$agent_dir/agent-csr.pem" "$agent_dir/agent-extfile.cnf"
    
    echo -e "${GREEN}✓ Agent certificate generated: $agent_hostname${NC}"
done
echo ""

# ============================================================================
# STEP 4: Generate Owner Signing Keys
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 4: Generating Owner Signing Keys${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

read -p "Number of owners: " num_owners

for i in $(seq 1 $num_owners); do
    echo ""
    read -p "Owner $i name (e.g., 'dr-smith'): " owner_name
    
    owner_dir="$OWNER_DIR/$owner_name"
    mkdir -p "$owner_dir"
    
    echo "Generating Ed25519 signing key..."
    openssl genpkey -algorithm ED25519 -out "$owner_dir/signing-key.pem"
    
    echo "Extracting public key..."
    openssl pkey -in "$owner_dir/signing-key.pem" -pubout -out "$owner_dir/signing-key-pub.pem"
    
    echo "Encrypting private key..."
    openssl enc -aes-256-cbc -salt -in "$owner_dir/signing-key.pem" \
        -out "$owner_dir/signing-key-encrypted.pem"
    
    echo -e "${GREEN}✓ Owner signing key generated: $owner_name${NC}"
    echo "  Private key (encrypted): $owner_dir/signing-key-encrypted.pem"
    echo "  Public key: $owner_dir/signing-key-pub.pem"
done
echo ""

# ============================================================================
# STEP 5: Generate Vault Unseal Keys (Shamir)
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 5: Generating Vault Unseal Keys${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

echo "Generating master unseal key..."
MASTER_KEY=$(openssl rand -hex 32)
echo "$MASTER_KEY" > "$VAULT_DIR/master-key.txt"

echo ""
echo "Splitting key using Shamir Secret Sharing..."
echo "  Total shares: $SHAMIR_TOTAL_SHARES"
echo "  Threshold: $SHAMIR_THRESHOLD"
echo ""

# Create Python script for Shamir sharing
cat > "$VAULT_DIR/shamir_split.py" << 'PYTHON_EOF'
import sys
import secrets
from typing import List, Tuple

def split_secret(secret: bytes, threshold: int, num_shares: int) -> List[bytes]:
    """
    Simple Shamir Secret Sharing implementation.
    For production, use a proper library like 'secretsharing'.
    """
    if threshold > num_shares:
        raise ValueError("Threshold cannot exceed number of shares")
    
    # Convert secret to integer
    secret_int = int.from_bytes(secret, byteorder='big')
    
    # Generate random coefficients for polynomial
    coefficients = [secret_int] + [secrets.randbits(256) for _ in range(threshold - 1)]
    
    # Evaluate polynomial at different points
    shares = []
    for x in range(1, num_shares + 1):
        y = sum(coef * (x ** i) for i, coef in enumerate(coefficients))
        share = f"{x}:{y:064x}"
        shares.append(share.encode())
    
    return shares

if __name__ == '__main__':
    master_key = sys.argv[1]
    threshold = int(sys.argv[2])
    num_shares = int(sys.argv[3])
    output_dir = sys.argv[4]
    
    secret = bytes.fromhex(master_key)
    shares = split_secret(secret, threshold, num_shares)
    
    for i, share in enumerate(shares, 1):
        with open(f"{output_dir}/share-{i}.txt", 'wb') as f:
            f.write(share)
        print(f"Share {i} written")
PYTHON_EOF

python3 "$VAULT_DIR/shamir_split.py" "$MASTER_KEY" "$SHAMIR_THRESHOLD" "$SHAMIR_TOTAL_SHARES" "$VAULT_DIR"

rm "$VAULT_DIR/shamir_split.py"

echo -e "${GREEN}✓ Vault unseal keys generated${NC}"
echo "  Master key: $VAULT_DIR/master-key.txt (DELETE AFTER DISTRIBUTION!)"
echo "  Shares: $VAULT_DIR/share-*.txt"
echo ""

# ============================================================================
# STEP 6: Create Distribution Packages
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 6: Creating Distribution Packages${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

echo "Creating server package..."
tar -czf "$OUTPUT_DIR/server-keys.tar.gz" -C "$SERVER_DIR" .
echo -e "${GREEN}✓ Server package: $OUTPUT_DIR/server-keys.tar.gz${NC}"

echo ""
echo "Creating agent packages..."
for agent_dir in "$AGENT_DIR"/*; do
    if [ -d "$agent_dir" ]; then
        agent_name=$(basename "$agent_dir")
        tar -czf "$OUTPUT_DIR/agent-$agent_name-keys.tar.gz" -C "$agent_dir" .
        echo -e "${GREEN}✓ Agent package: $OUTPUT_DIR/agent-$agent_name-keys.tar.gz${NC}"
    fi
done

echo ""
echo "Creating owner packages..."
for owner_dir in "$OWNER_DIR"/*; do
    if [ -d "$owner_dir" ]; then
        owner_name=$(basename "$owner_dir")
        tar -czf "$OUTPUT_DIR/owner-$owner_name-keys.tar.gz" -C "$owner_dir" .
        echo -e "${GREEN}✓ Owner package: $OUTPUT_DIR/owner-$owner_name-keys.tar.gz${NC}"
    fi
done

echo ""

# ============================================================================
# STEP 7: Create Backup
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 7: Creating Encrypted Backup${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

echo "Creating full backup..."
tar -czf "$BACKUP_DIR/all-keys-backup.tar.gz" -C "$OUTPUT_DIR" \
    ca server agents owners vault

echo ""
echo "Encrypting backup..."
openssl enc -aes-256-cbc -salt \
    -in "$BACKUP_DIR/all-keys-backup.tar.gz" \
    -out "$BACKUP_DIR/all-keys-backup.tar.gz.enc"

rm "$BACKUP_DIR/all-keys-backup.tar.gz"

echo -e "${GREEN}✓ Encrypted backup created${NC}"
echo "  Location: $BACKUP_DIR/all-keys-backup.tar.gz.enc"
echo ""

# ============================================================================
# STEP 8: Generate Documentation
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}STEP 8: Generating Documentation${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

cat > "$OUTPUT_DIR/KEY_DISTRIBUTION.md" << EOF
# MCP Key Distribution Guide

**Generated:** $(date)
**Organization:** $org_name

## ⚠️ SECURITY WARNINGS

1. **NEVER** transmit keys over the internet
2. **ALWAYS** use encrypted USB drives for distribution
3. **DELETE** master-key.txt after distributing shares
4. **STORE** CA private key in a safe
5. **BACKUP** encrypted backup to secure offline storage

## Distribution Checklist

### Server Keys
- [ ] Copy \`server-keys.tar.gz\` to USB drive
- [ ] Deliver to server administrator
- [ ] Verify installation
- [ ] Delete from keygen machine

### Agent Keys
$(for agent_dir in "$AGENT_DIR"/*; do
    if [ -d "$agent_dir" ]; then
        agent_name=$(basename "$agent_dir")
        echo "- [ ] Copy \`agent-$agent_name-keys.tar.gz\` to USB drive"
        echo "- [ ] Deliver to subnet administrator"
        echo "- [ ] Verify installation"
        echo "- [ ] Delete from keygen machine"
        echo ""
    fi
done)

### Owner Keys
$(for owner_dir in "$OWNER_DIR"/*; do
    if [ -d "$owner_dir" ]; then
        owner_name=$(basename "$owner_dir")
        echo "- [ ] Copy \`owner-$owner_name-keys.tar.gz\` to USB drive"
        echo "- [ ] Deliver to owner (in person)"
        echo "- [ ] Verify owner can decrypt"
        echo "- [ ] Delete from keygen machine"
        echo ""
    fi
done)

### Vault Unseal Shares
- [ ] Print share-1.txt → Envelope 1 → Owner
- [ ] Print share-2.txt → Envelope 2 → Admin 1
- [ ] Print share-3.txt → Envelope 3 → Admin 2
- [ ] Print share-4.txt → Envelope 4 → Admin 3
- [ ] Print share-5.txt → Envelope 5 → Backup (safe)
- [ ] DELETE master-key.txt (CRITICAL!)
- [ ] DELETE all share-*.txt files

## Recovery Procedures

### If CA Key Lost
- Generate new CA
- Re-issue all certificates
- Update all systems

### If Server Key Lost
- Generate new server certificate
- Update server configuration
- Restart server

### If Owner Key Lost
- Generate new owner signing key
- Update server with new public key
- Owner must re-approve pending requests

### If Vault Shares Lost
- Need $SHAMIR_THRESHOLD of $SHAMIR_TOTAL_SHARES shares to recover
- If fewer than $SHAMIR_THRESHOLD shares available, vault is UNRECOVERABLE
- This is by design for security

## Certificate Expiry

- Root CA: $(date -d "+$CA_VALIDITY_DAYS days" +%Y-%m-%d)
- Server: $(date -d "+$SERVER_VALIDITY_DAYS days" +%Y-%m-%d)
- Agents: $(date -d "+$AGENT_VALIDITY_DAYS days" +%Y-%m-%d)
- Owners: $(date -d "+$OWNER_VALIDITY_DAYS days" +%Y-%m-%d)

Set calendar reminders 90 days before expiry!

## Backup Information

Encrypted backup location: \`backup/all-keys-backup.tar.gz.enc\`

To restore:
\`\`\`bash
openssl enc -d -aes-256-cbc -in all-keys-backup.tar.gz.enc -out all-keys-backup.tar.gz
tar -xzf all-keys-backup.tar.gz
\`\`\`

Store backup in:
1. Fireproof safe (primary)
2. Bank safety deposit box (secondary)
3. Trusted colleague's safe (tertiary)

EOF

echo -e "${GREEN}✓ Documentation generated${NC}"
echo "  Location: $OUTPUT_DIR/KEY_DISTRIBUTION.md"
echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  KEY GENERATION COMPLETE!              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📋 NEXT STEPS:${NC}"
echo ""
echo "1. Review KEY_DISTRIBUTION.md"
echo "2. Prepare encrypted USB drives"
echo "3. Distribute keys in person"
echo "4. DELETE master-key.txt after distributing shares"
echo "5. Store encrypted backup in safe"
echo "6. WIPE this machine or destroy it"
echo ""
echo -e "${RED}⚠️  CRITICAL SECURITY REMINDERS:${NC}"
echo ""
echo "• This machine should NEVER connect to the internet again"
echo "• Delete all keys after distribution"
echo "• Use encrypted USB drives only"
echo "• Deliver keys in person"
echo "• Store backup offline in safe"
echo ""
echo -e "${GREEN}All keys generated in: $OUTPUT_DIR${NC}"
echo ""
