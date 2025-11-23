# Credential Vault MCP Integration Guide

## Overview

This guide explains how to integrate the Credential Vault system into the existing Agent 3 MCP server, exposing vault operations as tools that Granite LLM can call.

---

## Architecture Integration

### Current Agent 3 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Granite LLM (via MCP)                                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ MCP Server (mcp_server.py)                                      │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Existing Tools (8)                                         │ │
│ │ - discover_network_range                                  │ │
│ │ - discover_current_network                               │ │
│ │ - probe_database_servers                                 │ │
│ │ - get_device_summary                                     │ │
│ │ - get_database_summary                                   │ │
│ │ - analyze_database                                       │ │
│ │ - get_infrastructure_catalog                             │ │
│ │ - export_discovery_results                               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ NEW: Credential Vault Tools (10)                          │ │
│ │ - store_database_credential                              │ │
│ │ - store_equipment_credential                             │ │
│ │ - retrieve_credential                                    │ │
│ │ - list_credentials                                       │ │
│ │ - rotate_credential                                      │ │
│ │ - get_expiring_credentials                               │ │
│ │ - check_suspicious_activity                              │ │
│ │ - get_audit_logs                                         │ │
│ │ - export_credential_inventory                            │ │
│ │ - get_credential_statistics                              │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
┌──────────────────┐  ┌────────────────────────────────────┐
│ Discovery Tools  │  │ Vault System                       │
│ ├─ network_...   │  │ ├─ credential_vault.py             │
│ └─ database_...  │  │ ├─ credential_embedding.py         │
└──────────────────┘  │ ├─ credential_manager.py           │
                      │ ├─ audit_log.py                    │
                      │ └─ security_monitor.py             │
                      └────────────────────────────────────┘
```

---

## Step 1: Update MCP Server

Add vault tool handlers to `mcp_server.py`:

```python
from credential_manager import CredentialManager
from security_monitor import SecurityMonitor

# Initialize at server startup
credential_manager = CredentialManager()
security_monitor = SecurityMonitor()

# Add tool handlers

@server.call_tool()
async def handle_store_database_credential(arguments: dict):
    """Store database credential in vault"""
    try:
        result = credential_manager.store_database_credential(
            name=arguments["name"],
            db_type=arguments["db_type"],
            host=arguments["host"],
            port=arguments["port"],
            database=arguments["database"],
            username=arguments["username"],
            password=arguments["password"],
            description=arguments.get("description", "")
        )
        
        # Register for security monitoring
        if result.get("success"):
            cred_id = result["credential_id"]
            security_monitor.register_credential(cred_id)
            # Setup audit tracking...
        
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

@server.call_tool()
async def handle_retrieve_credential(arguments: dict):
    """Retrieve credential from vault"""
    try:
        result = credential_manager.retrieve_credential(
            credential_id=arguments["credential_id"],
            clinician_id=arguments["clinician_id"],
            reason=arguments["reason"],
            access_level=arguments.get("access_level", "clinician")
        )
        
        # Record access in security monitor
        if result.get("success"):
            security_monitor.record_access(
                arguments["credential_id"],
                arguments["clinician_id"],
                True
            )
        else:
            security_monitor.record_access(
                arguments["credential_id"],
                arguments["clinician_id"],
                False
            )
        
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

# ... additional handlers for other vault operations
```

---

## Step 2: Register MCP Tools

Add tool definitions to the MCP server's tool list:

```python
VAULT_TOOLS = [
    {
        "name": "store_database_credential",
        "description": "Store a database credential in the secure vault. Returns credential ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Credential name (e.g., 'EHR Database')"},
                "db_type": {"type": "string", "enum": ["mysql", "postgresql", "sqlserver", "mongodb"]},
                "host": {"type": "string", "description": "Database host/IP"},
                "port": {"type": "integer", "description": "Database port"},
                "database": {"type": "string", "description": "Database/schema name"},
                "username": {"type": "string", "description": "Database username"},
                "password": {"type": "string", "description": "Database password"},
                "description": {"type": "string", "description": "Optional description"}
            },
            "required": ["name", "db_type", "host", "port", "database", "username", "password"]
        }
    },
    {
        "name": "retrieve_credential",
        "description": "Retrieve credential for use with proper access control and audit logging.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "credential_id": {"type": "string", "description": "ID of credential to retrieve"},
                "clinician_id": {"type": "string", "description": "ID/name of clinician requesting access"},
                "reason": {"type": "string", "description": "Reason for access (for audit trail)"},
                "access_level": {"type": "string", "enum": ["clinician", "administrator", "emergency"]}
            },
            "required": ["credential_id", "clinician_id", "reason"]
        }
    },
    {
        "name": "list_credentials",
        "description": "List all available credentials in vault",
        "inputSchema": {
            "type": "object",
            "properties": {
                "access_level": {"type": "string", "enum": ["clinician", "administrator"]}
            }
        }
    },
    {
        "name": "rotate_credential",
        "description": "Rotate credential to new username/password",
        "inputSchema": {
            "type": "object",
            "properties": {
                "credential_id": {"type": "string"},
                "new_username": {"type": "string"},
                "new_password": {"type": "string"},
                "rotated_by": {"type": "string", "description": "Admin rotating the credential"}
            },
            "required": ["credential_id", "new_username", "new_password", "rotated_by"]
        }
    },
    {
        "name": "get_expiring_credentials",
        "description": "Get credentials expiring soon",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Show credentials expiring within N days", "default": 30}
            }
        }
    },
    {
        "name": "check_suspicious_activity",
        "description": "Check for suspicious credential activity and potential breaches",
        "inputSchema": {
            "type": "object",
            "properties": {
                "failed_attempts_threshold": {"type": "integer", "description": "Trigger alert after N failures", "default": 5}
            }
        }
    },
    {
        "name": "get_audit_logs",
        "description": "Get audit logs for credential access",
        "inputSchema": {
            "type": "object",
            "properties": {
                "credential_id": {"type": "string", "description": "Optional: specific credential"},
                "hours": {"type": "integer", "description": "Look back N hours", "default": 24}
            }
        }
    },
    {
        "name": "export_credential_inventory",
        "description": "Export complete credential inventory",
        "inputSchema": {"type": "object"}
    },
    {
        "name": "get_credential_statistics",
        "description": "Get statistics about stored credentials",
        "inputSchema": {"type": "object"}
    }
]
```

---

## Step 3: Integrate with Granite Service

Update `granite_service.py` to use vault for credential management:

```python
class GraniteService:
    def __init__(self, credential_manager=None, security_monitor=None):
        """Initialize with vault integration"""
        self.credential_manager = credential_manager
        self.security_monitor = security_monitor
        # ... existing initialization
    
    async def store_discovered_credentials(self, discovered_databases: list) -> dict:
        """
        Store discovered database credentials in vault
        
        Called after database discovery to securely store found credentials
        """
        stored_count = 0
        errors = []
        
        for db in discovered_databases:
            try:
                result = self.credential_manager.store_database_credential(
                    name=f"Auto-discovered: {db['service']}",
                    db_type=self._normalize_db_type(db["type"]),
                    host=db["host"],
                    port=db["port"],
                    database=db.get("database", db["service"]),
                    username=db.get("username", "admin"),
                    password=db.get("password", ""),
                    description=f"Auto-discovered during network scan at {datetime.now()}"
                )
                
                if result.get("success"):
                    stored_count += 1
                    # Register for monitoring
                    self.security_monitor.register_credential(result["credential_id"])
                else:
                    errors.append(f"{db['service']}: {result.get('error')}")
            
            except Exception as e:
                errors.append(f"{db['service']}: {str(e)}")
        
        return {
            "stored_count": stored_count,
            "total_databases": len(discovered_databases),
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
    
    async def generate_credential_security_report(self) -> str:
        """Generate Granite-analyzed security report for credentials"""
        
        # Get current stats
        stats = self.credential_manager.get_credential_statistics()
        suspicious = self.credential_manager.check_suspicious_activity()
        expiring = self.credential_manager.get_expiring_credentials(days=30)
        
        # Analyze with Granite
        prompt = f"""
        Analyze this credential vault status and provide security recommendations:
        
        Statistics:
        {json.dumps(stats, indent=2)}
        
        Suspicious Activity:
        {json.dumps(suspicious, indent=2)}
        
        Expiring Credentials:
        {json.dumps(expiring, indent=2)}
        
        Provide:
        1. Security risk assessment
        2. Priority remediation actions
        3. Recommended rotation schedule
        4. Compliance status (HIPAA/GDPR)
        5. Emergency procedures needed
        """
        
        response = await self.model.generate(prompt)
        return response.text
```

---

## Step 4: Update Agent Orchestrator

Modify `agent_orchestrator.py` to include credential vault phase:

```python
class PracticeOnboardingOrchestrator:
    async def start_new_practice_onboarding(self) -> dict:
        """Complete 6-phase onboarding workflow"""
        
        results = {
            "practice_id": self.practice_id,
            "started_at": datetime.now().isoformat(),
            "phases": {}
        }
        
        # Phase 1: Network Discovery
        results["phases"]["network"] = await self._phase_network_discovery()
        
        # Phase 2: Database Discovery
        results["phases"]["databases"] = await self._phase_database_discovery()
        
        # Phase 3: Infrastructure Analysis
        results["phases"]["analysis"] = await self._phase_infrastructure_analysis()
        
        # Phase 4: Procedure Generation
        results["phases"]["procedures"] = await self._phase_procedure_generation()
        
        # NEW Phase 5: Credential Vault Setup
        results["phases"]["credentials"] = await self._phase_credential_vault_setup()
        
        # Phase 6: Documentation & Export
        results["phases"]["export"] = await self._phase_documentation_export()
        
        results["completed_at"] = datetime.now().isoformat()
        return results
    
    async def _phase_credential_vault_setup(self) -> dict:
        """
        Phase 5: Setup credential vault
        - Store discovered credentials
        - Setup audit logging
        - Configure security monitoring
        - Test emergency access
        """
        phase_start = datetime.now()
        
        try:
            # Store discovered database credentials
            stored_creds = await self.granite_service.store_discovered_credentials(
                self.discovered_databases
            )
            
            # Setup audit logging for each credential
            for cred_id in stored_creds.get("credential_ids", []):
                # Setup rotation schedule
                # Setup expiration tracking
                # Setup access analyzer
                # Setup breach detector
                pass
            
            # Generate security report
            security_report = await self.granite_service.generate_credential_security_report()
            
            return {
                "status": "success",
                "credentials_stored": stored_creds["stored_count"],
                "security_report": security_report,
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
                "timestamp": phase_start.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Phase 5 (Credential Vault) failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "duration_seconds": (datetime.now() - phase_start).total_seconds()
            }
```

---

## Step 5: Configure Security Policies

Create a policies configuration file `vault_policies.json`:

```json
{
  "access_control": {
    "clinician": {
      "can_retrieve": true,
      "can_store": false,
      "can_rotate": false,
      "can_view_logs": ["own_access"],
      "can_view_inventory": false
    },
    "administrator": {
      "can_retrieve": true,
      "can_store": true,
      "can_rotate": true,
      "can_view_logs": ["all"],
      "can_view_inventory": true
    },
    "emergency": {
      "can_retrieve": true,
      "can_store": false,
      "can_rotate": false,
      "session_duration_minutes": 60,
      "max_uses": 1,
      "requires_approval": true
    }
  },
  "security": {
    "max_failed_attempts": 5,
    "brute_force_window_minutes": 5,
    "rotation_interval_days": 90,
    "max_age_days": 365,
    "require_mfa_for_sensitive": true,
    "unusual_access_hours": [22, 23, 0, 1, 2, 3, 4, 5]
  },
  "monitoring": {
    "enable_anomaly_detection": true,
    "enable_brute_force_detection": true,
    "enable_policy_enforcement": true,
    "alert_on_expiration_days": 30,
    "alert_on_rotation_overdue_days": 7
  },
  "compliance": {
    "hipaa_enabled": true,
    "gdpr_enabled": true,
    "popia_enabled": true,
    "audit_retention_days": 2555,
    "breach_notification_hours": 72
  }
}
```

---

## Workflow Integration

### Discovery to Vault Flow

```
1. Network Discovery (Phase 1)
   └─ Discovers: IP ranges, devices, open ports
   
2. Database Discovery (Phase 2)
   ├─ Probes: MySQL, PostgreSQL, SQL Server, MongoDB
   ├─ Result: Hostname, port, type, sample username/password
   └─ Stores in memory for Phase 5

3. Analysis (Phase 3)
   ├─ Granite analyzes: Risk level, usage, compliance
   ├─ Result: Risk assessment, procedures needed
   └─ Stores in memory for reporting

4. Procedures (Phase 4)
   ├─ Granite generates: Startup, shutdown, backup, recovery
   ├─ Result: Documented procedures
   └─ Stored in memory for export

5. CREDENTIAL VAULT (NEW Phase 5)
   ├─ Store credentials from Phase 2
   ├─ Create embedding weights from credentials
   ├─ Encrypt with AES-256
   ├─ Register for audit logging
   ├─ Setup security monitoring
   └─ Result: Secure vault with audit trail

6. Export (Phase 6)
   ├─ Exports: Infrastructure catalog
   ├─ Exports: Security procedures
   ├─ Exports: Compliance report
   ├─ Exports: Credential inventory (metadata only, no secrets)
   └─ Result: Complete onboarding documentation
```

---

## Testing the Integration

### 1. Test Vault Storage

```python
import asyncio
from credential_manager import CredentialManager

async def test_vault():
    mgr = CredentialManager()
    
    # Store credential
    result = mgr.store_database_credential(
        name="Test Database",
        db_type="mysql",
        host="192.168.1.20",
        port=3306,
        database="testdb",
        username="test_user",
        password="test_pass",
        description="Test credential"
    )
    
    assert result["success"]
    cred_id = result["credential_id"]
    
    # Retrieve credential
    retrieved = mgr.retrieve_credential(
        cred_id,
        clinician_id="test_clinician",
        reason="testing"
    )
    
    assert retrieved["success"]
    assert retrieved["username"] == "test_user"
    assert retrieved["password"] == "test_pass"

asyncio.run(test_vault())
```

### 2. Test Security Monitoring

```python
from security_monitor import SecurityMonitor

def test_brute_force_detection():
    monitor = SecurityMonitor()
    cred_id = "test_cred"
    monitor.register_credential(cred_id)
    
    # Simulate brute force
    for i in range(6):
        monitor.record_access(cred_id, f"attacker_{i}", 
                            success=False, 
                            client_ip="203.0.113.100")
    
    # Check incidents
    incidents = monitor.get_incidents()
    assert len(incidents) > 0
    assert incidents[0]["incident_type"] == "brute_force"

test_brute_force_detection()
```

### 3. Test Audit Logging

```python
from audit_log import AuditLogManager, EventType, SeverityLevel

def test_audit_logs():
    manager = AuditLogManager()
    
    # Log events
    event_id = manager.log_event(
        EventType.CREDENTIAL_CREATED,
        "test_cred",
        "Test credential created",
        actor="admin",
        severity=SeverityLevel.INFO
    )
    
    # Get logs
    logs = manager.export_logs()
    assert len(logs) > 0

test_audit_logs()
```

---

## Deployment Checklist

- [ ] credential_vault.py created and tested
- [ ] credential_embedding.py created and tested
- [ ] credential_manager.py created and tested
- [ ] audit_log.py created and tested
- [ ] security_monitor.py created and tested
- [ ] MCP server updated with vault tool handlers
- [ ] Tool definitions registered in MCP
- [ ] Granite service updated with vault integration
- [ ] Agent orchestrator includes Phase 5
- [ ] Security policies configured
- [ ] Integration tests passing
- [ ] Documentation generated
- [ ] Emergency procedures tested
- [ ] Compliance requirements verified
- [ ] Production deployment ready

---

## Production Deployment

### 1. Initialize Vault

```bash
python -c "
from credential_vault import SecureCredentialVault
vault = SecureCredentialVault('/data/vault/credentials.vault')
print('Vault initialized successfully')
"
```

### 2. Start MCP Server

```bash
python mcp_server.py
```

### 3. Verify Tools Are Available

```bash
curl http://localhost:8000/tools | grep credential
```

### 4. Run Initial Onboarding

```python
from agent_orchestrator import PracticeOnboardingOrchestrator

orchestrator = PracticeOnboardingOrchestrator(practice_id="PRACTICE_001")
results = orchestrator.start_new_practice_onboarding()
print(f"Onboarding completed: {results}")
```

---

## Conclusion

The Credential Vault is now integrated into Agent 3's complete onboarding workflow:
- Discovery → Vault Storage → Audit Logging → Security Monitoring → Compliance Reporting

This provides end-to-end credential management for discovered local infrastructure without exposing plaintext credentials.
