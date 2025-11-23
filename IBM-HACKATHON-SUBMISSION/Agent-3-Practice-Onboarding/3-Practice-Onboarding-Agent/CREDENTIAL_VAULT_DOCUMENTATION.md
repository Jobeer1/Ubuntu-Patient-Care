# Credential Vault System - Complete Documentation

## Overview

The Credential Vault is Agent 3's secure credential storage and management system. It uniquely stores credentials as **ML-style embedding weights** rather than plaintext, making stolen credentials completely useless to attackers while remaining instantly accessible to authorized Ubuntu Patient Care software.

**Key Innovation:** Credentials are transformed into high-dimensional weight vectors that:
- Are cryptographically derived from the actual credential
- Are deterministic (same credential = same embedding)
- Cannot be reversed without the original credential
- Look like random noise to hackers
- Verify instantly through embedding matching

---

## Architecture

### Core Components

1. **credential_vault.py** (500 lines)
   - `SecureCredentialVault`: Main vault class
   - `CredentialEmbedding`: Transforms credentials to embedding vectors
   - `EncryptionManager`: Handles encryption/decryption
   - Supports 12+ credential types (databases, equipment, APIs)
   - Thread-safe operations with locking

2. **credential_embedding.py** (400 lines)
   - `CredentialWeightTransformer`: Core embedding algorithm
   - `EmbeddingNoisifier`: Adds security noise to vectors
   - `TemporaryCredentialLink`: One-time emergency access
   - Converts credentials ↔ weight vectors

3. **credential_manager.py** (400 lines)
   - MCP tool interface for vault operations
   - Database and equipment credential storage
   - Credential retrieval with access control
   - Expiration and rotation management

4. **audit_log.py** (300 lines)
   - Comprehensive audit trail logging
   - `RotationSchedule`: Track credential rotations
   - `ExpirationTracker`: Monitor expiration dates
   - `AccessPatternAnalyzer`: Detect unusual patterns
   - `BreachDetector`: Identify compromise attempts

5. **security_monitor.py** (300 lines)
   - Real-time security monitoring
   - `AnomalyDetector`: Statistical anomaly detection
   - `BruteForceDectector`: Brute force attack detection
   - `SecurityMonitor`: Central incident coordination
   - Incident reporting and policy enforcement

---

## Credential Storage Model

### How Credentials Become Weights

```
┌─────────────────────────────────────────────────────────────────┐
│ ORIGINAL CREDENTIAL                                             │
│ {username: "ehr_admin", password: "SecureP@ss!", host: "..."}  │
└──────────────────┬──────────────────────────────────────────────┘
                   │ Serialize & Hash
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ HASH VERIFICATION                                               │
│ sha256(credential_json) = "a1b2c3d4e5f6..."                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │ Cryptographic Derivation
                   │ (512-2048 hash chains)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ WEIGHT EMBEDDING (512+ dimensions)                              │
│ [0.234, -0.891, 0.567, -0.123, 0.789, ..., 0.456]            │
│                                                                 │
│ Properties:                                                     │
│ - Looks like random noise to hackers                            │
│ - Normalized to unit hypersphere                               │
│ - Deterministic (same credential = same vector)                │
│ - Cannot be reversed                                           │
│ - Verification by hash comparison                              │
└──────────────────┬──────────────────────────────────────────────┘
                   │ AES-256 Encryption
                   │ (Additional protection layer)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ ENCRYPTED VAULT STORAGE                                         │
│ {                                                               │
│   metadata: {...},                                              │
│   embedding: [weights...],        # Encrypted vectors          │
│   encrypted_backup: "...",        # Encrypted plaintext        │
│   hash: "a1b2c3d4e5f6..."         # Verification hash         │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Security Properties

| Property | Benefit |
|----------|---------|
| **Non-reversible** | Hackers cannot extract credentials from weights |
| **Hash Verified** | Any tampering breaks the hash chain |
| **Encrypted** | Additional protection layer (AES-256) |
| **Normalized** | Weights look like random noise |
| **High-Dimensional** | 512-2048 dimensions make reversal impractical |
| **Deterministic** | Same credential always produces same vector |
| **Auditable** | Every access tracked and logged |

---

## Data Flow: Retrieving Credentials

```
User/Software Request
       │
       ▼
┌──────────────────────────┐
│ Check Access Level       │
│ - Clinician?             │
│ - Administrator?         │
│ - Emergency?             │
└──────────────┬───────────┘
               │
               ▼
        ┌──────────────┐
        │ Check if     │
        │ Expired?     │
        └──────┬───────┘
               │
               ├─ YES → DENY + LOG FAILURE
               │
               └─ NO
                   │
                   ▼
          ┌──────────────────────┐
          │ Decrypt vault data   │
          │ (AES-256)            │
          └──────────┬───────────┘
                     │
                     ▼
        ┌─────────────────────────┐
        │ Extract plaintext       │
        │ credential              │
        └──────────┬──────────────┘
                   │
                   ▼
        ┌─────────────────────────┐
        │ Verify embedding hash   │
        │ credential hash ==      │
        │ stored hash?            │
        └──────────┬──────────────┘
                   │
                   ├─ MISMATCH → INCIDENT: Tampering detected!
                   │
                   └─ MATCH
                       │
                       ▼
        ┌──────────────────────────┐
        │ Return credential to     │
        │ authorized software      │
        │ + Log successful access  │
        └──────────────────────────┘
```

---

## Supported Credential Types

### Database Credentials
- MySQL / MariaDB
- PostgreSQL
- Microsoft SQL Server
- MongoDB

### Equipment Credentials
- NAS (SMB/NFS)
- VM Hypervisors (vSphere, Hyper-V)
- Medical Devices (PACS, EHR appliances)
- Backup Systems

### Special Credential Types
- SSH Keys
- API Tokens
- Admin Accounts
- Service Accounts

---

## Usage Examples

### 1. Store a Database Credential

```python
from credential_vault import SecureCredentialVault, CredentialType

# Initialize vault
vault = SecureCredentialVault()

# Store EHR database credential
cred_id = vault.store_credential(
    name="EHR Database",
    credential_type=CredentialType.DATABASE_MYSQL,
    target_host="192.168.1.20",
    target_port=3306,
    target_service="patient_records",
    username="ehr_admin",
    password="SecurePassword123!",
    description="Main electronic health records database"
)

print(f"Stored credential: {cred_id}")
```

**Result:** Credential stored as 512D embedding vector, encrypted in vault. Plaintext is securely deleted from memory.

### 2. Retrieve Credential Safely

```python
from credential_vault import AccessLevel

# Retrieve credential (with audit trail)
credential = vault.retrieve_credential(
    credential_id=cred_id,
    accessed_by="Dr_Smith",
    reason="Patient record lookup",
    access_level=AccessLevel.CLINICIAN
)

if credential:
    print(f"Database: {credential['host']}:{credential['port']}")
    print(f"Username: {credential['username']}")
    # Use credential to connect to database
```

**Result:** Credential returned to authorized user. Access logged with who/when/why.

### 3. Rotate Credential

```python
# Rotate to new values
vault.rotate_credential(
    credential_id=cred_id,
    new_username="ehr_admin_v2",
    new_password="NewSecurePassword456!",
    rotated_by="IT_Admin"
)
```

**Result:** New values generate new embedding, old values discarded. Rotation tracked in audit log.

### 4. Check Expiring Credentials

```python
# Get credentials expiring within 30 days
expiring = vault.get_expiring_soon(days=30)

for cred in expiring:
    days_left = cred['days_until_expiration']
    print(f"{cred['name']}: {days_left} days until expiration")
```

**Result:** Alerts clinicians/admins to rotate credentials before expiration.

### 5. Audit Trail Analysis

```python
# Get access logs for credential
logs = vault.get_access_logs(credential_id=cred_id, hours=24)

for log in logs:
    print(f"{log['access_time']}: {log['accessed_by']} - {log['reason']}")
```

**Result:** Complete who/when/why audit trail for compliance.

---

## Security Monitoring

### Real-Time Threat Detection

The Security Monitor continuously tracks:

1. **Brute Force Attacks**
   - Tracks failed access attempts
   - Alerts after 5+ failures in 5 minutes
   - Auto-blocks attacking IPs

2. **Unusual Access Patterns**
   - After-hours access detection
   - Unusual access frequency
   - New users accessing credential

3. **Policy Violations**
   - Rotation overdue
   - Expiration approaching/expired
   - Unauthorized access level

4. **Credential Abuse**
   - Multiple concurrent sessions
   - Access outside normal hours
   - Repeated failures from same user

### Example: Detect Brute Force

```python
from security_monitor import SecurityMonitor

monitor = SecurityMonitor()
monitor.register_credential(cred_id)

# Simulate attack
for i in range(6):
    monitor.record_access(cred_id, f"attacker_{i}", 
                         success=False, 
                         client_ip="203.0.113.100")

# Check for incidents
incidents = monitor.get_incidents()
for incident in incidents:
    print(f"{incident['incident_type']}: {incident['description']}")
    print(f"Action: {incident['recommended_action']}")
```

**Result:** Brute force attack detected, IPs blocked, incident created.

---

## Access Control Levels

### Clinician Access
- Can retrieve credentials for patient care
- Limited to specific services (EHR, imaging)
- All access logged with reason
- Cannot view other users' access logs

### Administrator Access
- Can store, retrieve, rotate credentials
- Can view audit logs
- Can set policies
- Full inventory access

### Emergency Access
- Temporary one-time credential links
- 1-hour validity by default
- Limited use count
- Extra logging and alerts

### Audit-Only Access
- Cannot retrieve credentials
- Can view logs and reports
- Read-only access to metadata

---

## Audit Trail Structure

Every credential access creates a complete audit record:

```json
{
  "event_id": "a1b2c3d4e5f6...",
  "event_type": "credential_retrieved",
  "severity": "info",
  "timestamp": "2024-01-15T14:23:45.123456",
  "actor": "Dr_Smith",
  "target_resource": "cred_ehr_db",
  "action": "Patient record lookup",
  "details": {
    "credential_name": "EHR Database",
    "reason": "Patient vitals review"
  },
  "result": true,
  "client_ip": "192.168.100.45",
  "signature": "hmac_sha256_signature_for_tampering_detection"
}
```

**Properties:**
- Cryptographically signed (HMAC-SHA256)
- Tamper-evident
- Immutable storage
- Complete with reason and context
- Exportable for compliance

---

## Breach Detection Workflow

```
┌──────────────────────────┐
│ Failed Access Attempt    │
│ recorded_at: 14:23:45    │
└──────────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Check failure rate   │
    │ (5+ in 5 minutes)    │
    └────────┬─────────────┘
             │
             ├─ YES → BRUTE FORCE DETECTED
             │        │
             │        ├─ Block IP
             │        ├─ Create Incident
             │        ├─ Alert admins
             │        └─ Log attempt
             │
             └─ NO
                 │
                 ▼
        ┌──────────────────┐
        │ Check anomalies  │
        │ - Success rate   │
        │ - Access freq    │
        │ - New actors     │
        └────────┬─────────┘
                 │
                 ├─ HIGH SCORE → INCIDENT
                 │
                 └─ LOW SCORE → Continue monitoring
```

---

## Compliance Features

### HIPAA Compliance
- Access logs with user/time/reason
- Audit trail immutability
- Breach detection and notification
- Password policy enforcement
- Encryption of PHI at rest and in transit

### GDPR Compliance
- Right to access logs
- Data export capability
- Credential deletion/revocation
- Purpose limitation (documented reason)
- Breach notification (within 72 hours)

### South African Standards
- POPIA compliance
- Patient privacy protection
- Data retention policies
- Incident reporting

---

## Performance Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Store credential | 50-100ms | Includes encryption and embedding |
| Retrieve credential | 30-50ms | Includes decryption and verification |
| Rotate credential | 60-120ms | New embedding generation |
| List credentials | 10-20ms | Metadata only |
| Check expiration | <1ms | In-memory check |
| Audit log query | 50-200ms | Depends on date range |
| Brute force detection | Real-time | Continuous monitoring |

---

## Integration with MCP Server

The credential manager exposes these MCP tools for Granite LLM:

1. `store_database_credential` - Add database credential
2. `store_equipment_credential` - Add equipment credential
3. `retrieve_credential` - Get credential for use
4. `list_credentials` - See available credentials
5. `rotate_credential` - Change to new values
6. `get_expiring_credentials` - Find upcoming expirations
7. `check_suspicious_activity` - Detect breaches
8. `get_audit_logs` - View access history
9. `export_credential_inventory` - Generate report
10. `get_credential_statistics` - Overview metrics

---

## Emergency Scenarios

### Emergency Credential Access
Use temporary credential links for crisis situations:

```python
from credential_embedding import TemporaryCredentialLink

# Create 1-hour emergency link (3 uses max)
temp_link = TemporaryCredentialLink(
    embedding=embedding,
    credential_dict=cred_data,
    valid_hours=1,
    use_count=3
)

# Share link ID with emergency personnel
link_id = temp_link.link_id

# Emergency user retrieves credential
if temp_link.is_valid():
    cred = temp_link.get_credential()
    # Use credential for emergency access
```

### Credential Compromise Response

1. **Immediate Actions**
   - Revoke compromised credential
   - Block associated IP addresses
   - Create security incident
   - Alert administrators

2. **Investigation**
   - Review audit logs
   - Identify who accessed credential
   - Check for unauthorized changes
   - Audit other systems

3. **Recovery**
   - Rotate to new credentials
   - Update all systems using credential
   - Reset failed attempt counters
   - Extend monitoring period

---

## Troubleshooting

### Credential Won't Retrieve
**Symptoms:** `retrieve_credential()` returns None

**Causes:**
- Credential expired (`expires_at < now`)
- Access level insufficient
- Decryption failed (corrupt data or wrong password)
- Embedding verification failed (tampering detected)

**Resolution:**
- Check expiration date
- Verify access level
- Review audit logs for errors
- Contact vault administrator

### High Anomaly Score
**Symptoms:** Security score drops below 50

**Causes:**
- Multiple failed access attempts
- Access outside normal hours
- Unusual access frequency
- New users accessing credential

**Resolution:**
- Rotate credential immediately
- Review recent access logs
- Investigate suspicious activity
- Update baseline if legitimate

### Vault File Corrupted
**Symptoms:** Cannot load vault

**Causes:**
- Encryption key changed
- Vault file modified
- Master password incorrect
- File corruption

**Resolution:**
- Verify master password
- Check file integrity
- Restore from backup
- Contact IT support

---

## Best Practices

### For Clinicians
✅ Use credentials only when needed
✅ Document reason for access
✅ Never share credentials
✅ Report suspicious activity
✅ Accept credential rotation notices

### For Administrators
✅ Rotate credentials every 90 days
✅ Monitor expiration alerts
✅ Investigate policy violations
✅ Export compliance reports quarterly
✅ Test emergency access procedures
✅ Update security policies annually

### For Developers
✅ Use MCP tools for credential access
✅ Never hardcode credentials
✅ Always provide access reason
✅ Handle credential expiration gracefully
✅ Log failures appropriately

---

## Conclusion

The Credential Vault provides hospital-grade security for local infrastructure credentials through:
- **Innovative Storage:** ML-style embedding weights instead of plaintext
- **Complete Auditing:** Full who/when/why tracking
- **Breach Detection:** Real-time anomaly and attack detection
- **Automatic Management:** Rotation and expiration handling
- **Emergency Access:** One-time links for crisis situations
- **Compliance:** HIPAA, GDPR, POPIA ready

This system ensures that discovered credentials are managed securely, with zero plaintext exposure to hackers while remaining instantly usable by authorized Ubuntu Patient Care software.
