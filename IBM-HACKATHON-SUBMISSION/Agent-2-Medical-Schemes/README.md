# Agent 2: 📋 Medical Schemes Integration

**Purpose:** Insurance/medical scheme validation and claims processing

## Quick Start

```bash
# Navigate to Agent 2
cd Agent-2-Medical-Schemes

# Use the shared Granite model from Agent 1
# This agent provides scheme validation endpoints to main API
```

## Features

✅ **Multi-Scheme Support** - Government + private medical schemes
✅ **Real-time Eligibility** - Check patient coverage instantly
✅ **Claims Processing** - Automated submission & reimbursement
✅ **Scheme Validation** - Insurance plan verification
✅ **Cost Calculations** - Exact member out-of-pocket costs
✅ **Document Management** - Claims history & receipts

## Architecture

- **Scheme Database:** PostgreSQL (coverage rules, rates)
- **Validation Engine:** Real-time eligibility checks
- **Processing Pipeline:** Claim submission workflow
- **External APIs:** Insurance provider integrations
- **Cache:** Redis for scheme lookups

## Key Endpoints

- `GET /schemes/list` - Available medical schemes
- `POST /schemes/validate` - Check patient eligibility
- `POST /claims/submit` - Submit insurance claim
- `GET /claims/status/{id}` - Track claim processing
- `POST /schemes/calculate` - Reimbursement calculation

## Supported Schemes

```
🏥 Government:
  • National Health Insurance (NHI)
  • Government Employee Medical Scheme (GEMS)
  • Department of Health schemes

💼 Private:
  • Discovery Health
  • Medshield
  • Momentum Health
  • Bonitas
```

## Data Flow

```
Patient Request
    ↓
Check Coverage Rules
    ↓
Verify Eligibility
    ↓
Calculate Costs
    ↓
Process Claim
    ↓
Track Reimbursement
```

## Configuration

Database tables for:
- `schemes` - Medical insurance plans
- `coverage_rules` - Coverage details per scheme
- `claims` - Submitted claims
- `reimbursements` - Payment tracking

## Integration Points

- **Agent 1:** Patient authentication via RBAC
- **Agent 3:** Credential verification for claims
- **Main API:** REST endpoints for frontend

## Compliance

✅ HIPAA medical record privacy
✅ Insurance regulation compliance
✅ Audit trail for all claims
✅ Encryption of sensitive data

---

See main README for system-wide architecture.
