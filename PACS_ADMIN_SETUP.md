# PACS Mentor Admin Setup & Enhancement

**Date:** May 24, 2026  
**Status:** Complete  
**Target User ID:** 0768193339 (Admin/Root)

---

## Summary

The PACS Mentor agent has been enhanced to support:
1. **Admin-only access** for user `0768193339` with full diagnostic capabilities
2. **Network troubleshooting** including subnet scanning, IP checks, and VM status
3. **Direct diagnostics** without additional authorization requirements for admin users
4. **Dual-prompt system** to toggle between restricted and unrestricted modes

---

## Changes Made

### 1. Admin User Setup Script
**File:** `setup_admin_user.py`

This script initializes `0768193339` as the **only admin/root user** on the system.

**What it does:**
- Creates user `0768193339` with `user_role='admin'` and `is_verified=True`
- Ensures this is the only admin account (downgrades any other admins)
- Creates database tables if they don't exist
- Provides user summary after setup

**Run it:**
```bash
python setup_admin_user.py
```

**Output:**
```
✓ Database tables initialized
✓ Created new admin user 0768193339
✅ Admin setup complete!
   User ID: 0768193339
   Role: admin
   Verified: True
   This is the ONLY admin account on the system.
```

---

### 2. PACS Mentor Dual-Prompt System
**File:** `backend/agent_pacs.py`

Added two role prompts:

#### **pacs_role_prompt** (Restricted)
- Requires admin proof before network topology exploration
- Redacts sensitive discovery results for unverified users
- Asks for authorization (device login, payslip, etc.)

#### **pacs_admin_role_prompt** (Unrestricted)
- Full access to all diagnostics
- Direct subnet scanning and ping sweeps
- No additional authorization needed
- Provides concrete results immediately

**The agent automatically switches prompts based on `is_admin_session` flag.**

---

### 3. Enhanced Network Diagnostics
**File:** `backend/agent_pacs.py`

Admin users can now perform:

#### **Subnet Scanning**
```
"find all VMs on the 155.235.81/28 subnet"
```
Returns all online hosts with resolved hostnames.

#### **Individual IP Checks**
```
"check if 155.235.81.94 is online"
```
Returns online/offline status with reason if unavailable.

#### **VM Health Checks**
```
"check all VMs for me"
```
Pings configured VMs from `config.ini` and reports status.

#### **Database Health**
```
"what database is down right now"
```
Checks registry sources and reports which are offline.

#### **LAN Inventory**
```
"give me our full network topology"
```
Lists all configured network equipment and their status.

---

### 4. Auth Route Enhancement
**File:** `backend/routes/pacs_mentor.py`

The `/pacs/chat` endpoint now:
- Detects if user has `user_role='admin'` or `user_id='0768193339'`
- Automatically sets `session_mentor.is_admin_session = True`
- Auto-verifies admin proof: `admin_proof_verified = True`
- Sets `admin_proof_basis = 'admin-user-account'`
- Returns `is_admin` flag in response

**Authentication Flow:**
```python
if getattr(current_user, 'user_role', '') == 'admin' or current_user.user_id == '0768193339':
    session_mentor.is_admin_session = True
    session_mentor.admin_proof_verified = True
    session_mentor.admin_proof_basis = 'admin-user-account'
```

---

### 5. Updated Gemini Intent Parsing
**File:** `backend/agent_pacs.py` - `_gemini_parse_pacs_request()`

- Now includes `subnet_scan` and `vm_health` as intent options
- Uses admin prompt when in admin session
- Recognizes network diagnostic requests
- Routes infrastructure queries directly to diagnostics

---

## Capabilities Enabled for Admin User (0768193339)

### **Direct Network Diagnostics**
✅ Subnet scanning with ICMP ping sweep  
✅ Individual IP status checks  
✅ VM inventory status checking  
✅ Hostname resolution  
✅ Network topology mapping  

### **Infrastructure Status**
✅ Database health checks  
✅ Mounted NAS/share status  
✅ VM online/offline reporting  
✅ Network equipment status  

### **PACS Operations**
✅ Registry indexing and sync  
✅ DICOM metadata preview  
✅ Patient timeline stitching  
✅ Read-only export (DOCX/PDF)  
✅ Study reconciliation  

### **Troubleshooting**
✅ Network path verification  
✅ Service availability checks  
✅ Infrastructure continuity planning  
✅ Read-only incident logging  

---

## Usage Examples

### For Admin User (0768193339)

**1. Subnet Scan**
```
User: "find all VMs on the 155.235.81/28 subnet, tell me how many you find"
Agent: "Swept 155.235.81/28 — found 12 online host(s) out of 14 usable address(es):
  - 155.235.81.1 (gateway)
  - 155.235.81.10 (pacs-vm01)
  - 155.235.81.20 (ris-db01)
  ..."
```

**2. IP Status Check**
```
User: "check if 155.235.81.94 is online"
Agent: "Checked 155.235.81.94 with read-only ping probe.
- 155.235.81.94: ONLINE"
```

**3. VM Health Check**
```
User: "check what VMs are offline now"
Agent: "I checked N VM target(s) with read-only ping probes.
- vm01.hospital.local: ONLINE
- vm02.hospital.local: OFFLINE (host unreachable)
- ..."
```

**4. Database Health**
```
User: "check for me what VMs and NAS devices are offline now"
Agent: "I checked N database source(s) in the local registry.
- FIREBIRD | /mnt/ris | ONLINE
- DICOM_ARCHIVE | /mnt/pacs | ONLINE
- MEDICAL_BILLING | \\\\nas01\\billing | OFFLINE
..."
```

---

## Configuration

### Setup Admin User (One-time)

```bash
cd "C:\Users\Admin\Documents\OneDrive - Dr CI Stoyanov Radiological Services Inc\Desktop\ELC\SDOH-chat\SDOH-chat01"
python setup_admin_user.py
```

### Configure VM Targets (Optional)

Edit `config.ini` to specify VMs to monitor:

```ini
[PACS_VM]
# Comma, semicolon, or newline separated hostnames/IPs
hosts = vm01, vm02, 10.10.10.5
hostnames = pacs-server, ris-db, archive-01

[PACS_NETWORK]
devices = firewall, switch01
equipment = nas01=192.168.1.100, backup-appliance=192.168.1.101
```

Or use environment variables:
```powershell
$env:PACS_VM_HOSTS = "vm01;vm02;10.10.10.5"
$env:PACS_NETWORK_HOSTS = "firewall;switch01"
```

---

## Security Notes

⚠️ **Admin Bypass for Testing/Development Only**

- User `0768193339` has full unrestricted access to all diagnostics
- Network scanning results are visible without redaction
- This is **read-only** - no modifications to source systems
- Audit logging captures all admin actions in `pacs_audit_log.jsonl`
- For production, implement additional access controls

✅ **Read-Only Operations Only**
- No destructive changes
- No modifications to databases or files
- No credential capture or exposure
- All operations logged

---

## Testing the Setup

### 1. Initialize Admin User
```bash
python setup_admin_user.py
```

### 2. Login as 0768193339
- Use the SDOH Chat app
- Register/Login with code: `0768193339`

### 3. Test Network Diagnostics
```
"find all VMs on 155.235.81/28"
"check if 155.235.81.94 is online"
"what is offline on our network right now"
```

### 4. Verify Admin Mode
- Agent should provide full detail (IPs, hostnames)
- No redaction of results
- Immediate response without asking for proof

---

## Troubleshooting

### Agent Still Asking for Proof
- **Solution:** Check that user_id is exactly `0768193339` and `user_role='admin'`
- Run `python setup_admin_user.py` again to verify setup

### Subnet Scan Returns Empty
- **Solution:** Ensure ICMP (ping) is not blocked at firewall
- Verify target subnet is reachable from this network segment

### No VMs Found in Health Check
- **Solution:** Configure VM hosts in `config.ini` or set `PACS_VM_HOSTS` env var
- Or provide explicit hostnames in the request

### Agent in Restricted Mode (Redacted Results)
- **Solution:** Check that `is_admin_session` is `True` in chat response
- Verify user is logged in as admin (check user_id and user_role in database)

---

## Files Modified

1. **Created:** `setup_admin_user.py`
   - Admin user initialization script

2. **Modified:** `backend/agent_pacs.py`
   - Added `pacs_admin_role_prompt` 
   - Added `is_admin_session` flag
   - Updated `_build_subnet_scan_response()` to check admin status
   - Updated `_build_admin_proof_request()` for admin bypass
   - Updated `_gemini_parse_pacs_request()` to use admin prompt

3. **Modified:** `backend/routes/pacs_mentor.py`
   - Updated `/pacs/chat` endpoint to detect admin users
   - Auto-set `is_admin_session` for admin accounts
   - Added `is_admin` flag to response

---

## Next Steps

1. **Run Setup:**
   ```bash
   python setup_admin_user.py
   ```

2. **Test Admin Access:**
   - Login with `0768193339`
   - Request: "find all VMs on the 155.235.81/28 subnet"

3. **Configure Targets (Optional):**
   - Add VM/network hosts to `config.ini`
   - Or set `PACS_VM_HOSTS` environment variable

4. **Monitor Usage:**
   - Check `instance/pacs_audit_log.jsonl` for all admin actions
   - Review audit logs for security compliance

---

## Reference

**Related Documentation:**
- [PACS Mentor Current Behavior](PACS_MENTOR_AGENT_CURRENT.md)
- [Architecture and Couplings](ARCHITECTURE_AND_COUPLINGS.md)
- [Infrastructure Recovery Log](INFRASTRUCTURE_RECOVERY_LOG.md)

**Admin User ID:** `0768193339`  
**Setup Status:** Ready for testing and development
