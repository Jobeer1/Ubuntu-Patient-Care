# MCP Server - Discovery Tools Quick Reference

**Practice Onboarding Agent - MCP Server for Network & Database Discovery**

---

## Overview

The MCP Server exposes discovery tools that the Granite-3.1 LLM can call to discover practice infrastructure:
- Network devices (servers, NAS, medical machines, PCs, network equipment)
- Database servers (SQL Server, MySQL, PostgreSQL, MongoDB)
- Device types and characteristics
- Complete infrastructure catalog generation

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Granite-3.1 LLM                    │
│                                                     │
│  "Discover all databases on this network"          │
│  "What medical devices did you find?"              │
│  "Generate startup procedure"                      │
└────────────────────┬────────────────────────────────┘
                     │
                     │ MCP Protocol
                     │
┌────────────────────▼────────────────────────────────┐
│              MCP Server (mcp_server.py)             │
│                                                     │
│  ├─ discover_network_range()                       │
│  ├─ discover_current_network()                     │
│  ├─ probe_database_servers()                       │
│  ├─ get_device_summary()                           │
│  ├─ get_database_summary()                         │
│  ├─ analyze_database()                             │
│  ├─ get_infrastructure_catalog()                   │
│  └─ export_discovery_results()                     │
└────────────────┬──────────────────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
    ┌────▼────┐     ┌───▼──────┐
    │ Network │     │ Database │
    │Discovery│     │Discovery │
    │ Tools   │     │  Tools   │
    └─────────┘     └──────────┘
```

---

## File Structure

```
3-Practice-Onboarding-Agent/
├── mcp_server.py                    # Main MCP server
├── network_discovery_tools.py       # Network scanning & device identification
├── database_discovery_tools.py      # Database server detection
├── granite_service.py               # Granite-3.1 integration
├── agent_orchestrator.py            # Workflow orchestration
├── requirements.txt                 # Python dependencies
├── README.md                        # Main documentation
├── SANDBOX_PROCEDURES.md            # Testing procedures
├── ONBOARDING_WORKFLOWS.md          # Automated workflows
├── IMPLEMENTATION_STRATEGY.md       # Technical approach
├── DISCOVERY_FRAMEWORK.md           # Discovery methods
└── MCP_TOOLS_REFERENCE.md          # This file
```

---

## Tool Reference

### Tool 1: discover_network_range

**Purpose:** Discover all devices on a specific network range

**Granite Usage:**
```python
Granite: "I need to scan your network. What's your network range?"
Doctor: "192.168.1.0/24"
Granite: Calls discover_network_range(network_cidr="192.168.1.0/24")
```

**Input:**
```json
{
  "network_cidr": "192.168.1.0/24",
  "timeout": 5
}
```

**Output:**
```json
{
  "status": "COMPLETE",
  "network": "192.168.1.0/24",
  "devices_found": 25,
  "devices": {
    "192.168.1.10": {
      "ip": "192.168.1.10",
      "hostname": "nas-storage",
      "device_type": "Network Storage (NAS)",
      "is_nas": true,
      "open_ports": [21, 22, 445],
      "services": ["FTP", "SSH", "SMB/CIFS"],
      "description": "Network Attached Storage - likely contains backups or shared files"
    },
    "192.168.1.20": {
      "ip": "192.168.1.20",
      "hostname": "ehr-server",
      "device_type": "Database Server (MySQL)",
      "is_database": true,
      "open_ports": [22, 3306],
      "services": ["SSH", "MySQL"],
      "description": "Database server - stores patient data..."
    },
    ...
  }
}
```

**What it discovers:**
- ✅ NAS storage devices
- ✅ Database servers
- ✅ Medical imaging servers (DICOM/PACS)
- ✅ Application servers
- ✅ Virtual machine hosts
- ✅ Workstations and PCs
- ✅ Network equipment
- ✅ Medical devices
- ✅ Printers

---

### Tool 2: discover_current_network

**Purpose:** Auto-detect and discover the current network

**Granite Usage:**
```python
Granite: "Let me auto-detect your network and discover all devices..."
Granite: Calls discover_current_network()
```

**Input:**
```json
{}
```

**Output:**
```json
{
  "status": "COMPLETE",
  "network": "192.168.1.0/24",
  "devices_found": 25,
  "devices": {...}
}
```

**Benefit:** No need to know network range - discovers automatically

---

### Tool 3: probe_database_servers

**Purpose:** Probe specific IPs for database servers

**Granite Usage:**
```python
Granite: "I found these IPs. Let me check for databases..."
Granite: Calls probe_database_servers(ips=["192.168.1.20", "192.168.1.21"])
```

**Input:**
```json
{
  "ips": [
    "192.168.1.20",
    "192.168.1.21",
    "192.168.1.22"
  ]
}
```

**Output:**
```json
{
  "status": "COMPLETE",
  "databases_found": 3,
  "databases": {
    "192.168.1.20:3306": {
      "type": "MySQL",
      "ip": "192.168.1.20",
      "port": 3306,
      "status": "ACCESSIBLE",
      "version": "MySQL 5.7.33",
      "description": "MySQL database server - likely contains medical records or application data"
    },
    "192.168.1.21:5432": {
      "type": "PostgreSQL",
      "ip": "192.168.1.21",
      "port": 5432,
      "status": "ACCESSIBLE",
      "version": "PostgreSQL 12"
    },
    "192.168.1.22:1433": {
      "type": "SQL Server",
      "ip": "192.168.1.22",
      "port": 1433,
      "status": "ACCESSIBLE",
      "version": "SQL Server 2019"
    }
  }
}
```

**Detects:**
- ✅ MySQL (port 3306)
- ✅ PostgreSQL (port 5432)
- ✅ SQL Server (port 1433)
- ✅ MongoDB (port 27017)
- ✅ Other databases

---

### Tool 4: get_device_summary

**Purpose:** Get summary of discovered devices grouped by type

**Granite Usage:**
```python
Granite: "Let me summarize what I found..."
Granite: Calls get_device_summary()
```

**Input:**
```json
{}
```

**Output:**
```json
{
  "total_devices": 25,
  "nas_devices": 2,
  "database_servers": 3,
  "medical_devices": 4,
  "vm_hosts": 1,
  "web_servers": 5,
  "workstations": 8,
  "printers": 2,
  "network_equipment": 3,
  "unknown": 2,
  "devices_by_type": {
    "Network Storage (NAS)": [
      {
        "ip": "192.168.1.10",
        "hostname": "nas-storage",
        "description": "Network Attached Storage..."
      }
    ],
    "Database Server (MySQL)": [...],
    ...
  }
}
```

---

### Tool 5: get_database_summary

**Purpose:** Get summary of discovered databases

**Granite Usage:**
```python
Granite: "Let me show you all the databases I found..."
Granite: Calls get_database_summary()
```

**Input:**
```json
{}
```

**Output:**
```json
{
  "total_databases": 3,
  "mysql_instances": 1,
  "postgresql_instances": 1,
  "sqlserver_instances": 1,
  "mongodb_instances": 0,
  "accessible": 3,
  "by_type": {
    "MySQL": [
      {
        "ip": "192.168.1.20",
        "port": 3306,
        "status": "ACCESSIBLE",
        "version": "MySQL 5.7.33"
      }
    ],
    ...
  }
}
```

---

### Tool 6: analyze_database

**Purpose:** Analyze specific database for likely use and recommendations

**Granite Usage:**
```python
Granite: "Let me analyze this database to identify what it stores..."
Granite: Calls analyze_database(ip="192.168.1.20", port=3306, db_type="MySQL")
```

**Input:**
```json
{
  "ip": "192.168.1.20",
  "port": 3306,
  "db_type": "MySQL"
}
```

**Output:**
```json
{
  "database_info": {
    "ip": "192.168.1.20",
    "port": 3306,
    "type": "MySQL"
  },
  "likely_applications": [
    "OpenEMR - Patient Management System",
    "Medical Office Management Software",
    "Clinic Billing System"
  ],
  "risk_assessment": {
    "backup_priority": "MEDIUM",
    "data_criticality": "HIGH",
    "access_control_required": true
  },
  "recommendations": [
    "Determine database owner and backup schedule",
    "Verify backup procedures are working",
    "Document database access procedures",
    "Implement access control and monitoring"
  ]
}
```

---

### Tool 7: get_infrastructure_catalog

**Purpose:** Get complete infrastructure catalog from all discoveries

**Granite Usage:**
```python
Granite: "Let me compile everything into a complete infrastructure catalog..."
Granite: Calls get_infrastructure_catalog()
```

**Input:**
```json
{}
```

**Output:**
```json
{
  "catalog_generated": "2024-01-15T10:30:00",
  "devices": {...},
  "databases": {...},
  "device_summary": {...},
  "database_summary": {...}
}
```

**Contains:**
- All discovered devices with full details
- All discovered databases with credentials info
- Device summary statistics
- Database summary statistics
- Ready for procedure generation and documentation

---

### Tool 8: export_discovery_results

**Purpose:** Export all discovery results to JSON file

**Granite Usage:**
```python
Granite: "Let me save all this to a file for your records..."
Granite: Calls export_discovery_results(filename="discovery_results.json")
```

**Input:**
```json
{
  "filename": "discovery_results.json"
}
```

**Output:**
```json
{
  "status": "SUCCESS",
  "filename": "discovery_results.json",
  "message": "Discovery results saved to discovery_results.json"
}
```

**Exports:**
- Complete device inventory
- All discovered databases
- Configuration files (if accessible)
- Network topology
- Services running
- Ready for backup procedures and DR testing

---

## How Granite Uses These Tools

### Workflow Example: Complete Practice Discovery

```
Granite-3.1 Workflow:

Step 1: Initial Greeting
  Granite: "Hi Dr. Smith! I'm helping with your practice infrastructure
           documentation. Let me discover your network setup.
           What's your network range? (or should I auto-detect?)"

Step 2: Network Discovery
  Doctor: "Auto-detect please"
  Granite: Calls discover_current_network()
  Result: 25 devices found

Step 3: Device Analysis
  Granite: Calls get_device_summary()
  Granite: "I found 25 devices including:
           - 2 NAS storage devices
           - 3 database servers
           - 4 medical imaging systems
           - 8 workstations
           Let me probe the servers for databases..."

Step 4: Database Discovery
  Granite: Calls probe_database_servers([IPs of servers])
  Result: 3 databases found

Step 5: Database Analysis
  For each database:
    Granite: Calls analyze_database()
    Result: MySQL storing patient records, PostgreSQL storing test results

Step 6: Infrastructure Catalog
  Granite: Calls get_infrastructure_catalog()
  Result: Complete catalog with all devices and databases

Step 7: Procedure Generation
  Granite: Uses catalog to generate:
    - Startup procedure
    - Shutdown procedure
    - Backup procedure
    - Recovery procedure
    - Emergency procedures

Step 8: Documentation Export
  Granite: Calls export_discovery_results()
  Result: All results saved to file

Final Output:
  ✅ Complete infrastructure map
  ✅ Device inventory (25 devices)
  ✅ Database inventory (3 databases)
  ✅ Startup/shutdown/backup/recovery procedures
  ✅ Emergency access procedures
  ✅ Compliance documentation
  ✅ Audit trail (complete)
```

---

## Integration with Agents 1 & 2

### Agent 1 (Chat/RBAC) Integration
```
Chat Interface -> Agent 3 Discovery:
- Doctor asks: "How do I access the database?"
- Agent 1 queries: "What databases are available?"
- Agent 1 calls Agent 3: discover_infrastructure()
- Agent 1 returns personalized answer
```

### Agent 2 (Medical Schemes) Integration
```
Scheme Automation -> Agent 3 Infrastructure:
- Agent 2 needs: "Where is medical scheme portal data stored?"
- Agent 2 calls Agent 3: probe_database_servers()
- Agent 2 uses results to automate portal integration
```

---

## Performance Considerations

### Discovery Time Estimates

| Operation | Time | Notes |
|-----------|------|-------|
| Network scan (/24) | 2-5 min | Depends on network size |
| Database probing | 30-60 sec | Quick port checks |
| Analysis | 1-2 min | Granite analysis |
| Export | 10-30 sec | File I/O |
| **Total** | **5-10 min** | Complete discovery |

### Resource Requirements

| Component | CPU | RAM | Disk | Network |
|-----------|-----|-----|------|---------|
| Discovery | Low | 50 MB | 1 GB | Full |
| Granite | High | 8+ GB | 15 GB | Minimal |
| Results | Low | 100 MB | 100 MB | Minimal |

### Optimization Tips

1. **Skip already-discovered networks:** Export results, reuse in next session
2. **Parallel probing:** Multiple threads for faster discovery
3. **Incremental discovery:** Discover one network segment at a time
4. **Caching:** Cache discovery results for 24 hours

---

## Error Handling

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Network unreachable" | Network not accessible | Check firewall, routing |
| "Timeout on all ports" | Device offline | Verify device is powered on |
| "Connection refused" | Service not running | Check service status |
| "Permission denied" | Insufficient privileges | Run with appropriate privileges |
| "Out of memory" | Large network scan | Break into smaller segments |

### Recovery Procedures

```
If discovery fails:

1. Verify network connectivity
   - Ping each IP manually first
   - Check firewall rules

2. Reduce network scope
   - Instead of /24, try /25
   - Or scan specific subnet

3. Check resource limits
   - Monitor CPU/RAM usage
   - Increase process limits if needed

4. Enable debug logging
   - Set log level to DEBUG
   - Review detailed error messages

5. Manual fallback
   - Document devices manually
   - Use discovery to verify and supplement
```

---

## Security Considerations

### Safe Operations
✅ All discovery is read-only (no modifications)
✅ Network probing only (no exploitation)
✅ No credentials required for discovery
✅ Results don't contain sensitive data
✅ Complete audit trail

### Credential Handling
⚠️ If credentials are needed for advanced discovery:
- Store in encrypted vault only
- Never log credentials
- Access only via MCP server
- Audit all credential access
- Rotate after each use

---

## Next Steps

1. **Start discovery:** Run `agent_orchestrator.py` with practice info
2. **Review results:** Check exported JSON file
3. **Verify findings:** Walk through with IT staff
4. **Generate procedures:** Use discovery results to generate procedures
5. **Test procedures:** Use Sandbox procedures for safe testing
6. **Document everything:** Export results for compliance

---

This MCP server provides the foundation for Agent 3's complete infrastructure discovery and documentation capabilities.
