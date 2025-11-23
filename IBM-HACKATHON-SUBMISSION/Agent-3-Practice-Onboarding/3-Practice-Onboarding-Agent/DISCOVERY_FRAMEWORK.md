# Practice Onboarding Agent - Safe Discovery Framework

**Non-Destructive Infrastructure Mapping & Credential Identification**

---

## Core Principles

### The Zero-Damage Guarantee

**Every discovery operation is:**
- ✅ Read-only (no writes to production)
- ✅ Non-invasive (no systems restarted)
- ✅ Documented (all queries logged)
- ✅ Reversible (no permanent changes)
- ✅ Observable (no hidden operations)
- ✅ Compliant (healthcare regulations)

**If it modifies production, it doesn't belong in discovery.**

---

## Tier 1: Passive Information Gathering

### 1.1 Configuration File Analysis

**Windows Systems:**

```python
# Safe Registry Queries (Read-Only)
Registry Keys to Query:
├── HKLM\Software\Microsoft\Windows\CurrentVersion
│   └── Installed applications, Windows version
├── HKLM\System\CurrentControlSet\Services
│   └── Running services, service dependencies
├── HKLM\Software\Microsoft\NetworkProvider
│   └── Network providers, shared drive mappings
├── HKLM\Software\Microsoft\Windows NT
│   └── System services configuration
└── HKLM\Software (Software directory)
    └── Application-specific settings

Query Method:
- Use: reg query (Windows built-in)
- Effect: READ ONLY, no modifications
- Risk: NONE
- Data: Registry values only, no system changes
```

**Linux Systems:**

```bash
# Safe Configuration File Reading (Read-Only)
Configuration Files:
├── /etc/hosts
│   └── Hostname mappings
├── /etc/passwd (non-shadow)
│   └── User information
├── /etc/network/interfaces
│   └── Network configuration
├── /etc/fstab
│   └── Mount points and storage
├── /etc/services
│   └── Service port mappings
├── /etc/resolv.conf
│   └── DNS configuration
└── /var/log/syslog
    └── System events

Query Method:
- Use: cat, grep (built-in Unix tools)
- Effect: READ ONLY, no modifications
- Risk: NONE
- Data: Configuration content only
```

### 1.2 File System Enumeration

**Windows File System Discovery:**

```python
Safe Discovery:
├── Directory Structure Scan
│   ├── Program Files locations
│   ├── Application data directories
│   ├── Database file locations
│   ├── Backup directories
│   └── Shared drive mappings
├── File Identification
│   ├── Database files (.mdf, .db, etc.)
│   ├── Configuration files
│   ├── Backup files
│   ├── Log files
│   └── Documentation files
└── Mount Point Discovery
    ├── Local drives
    ├── Network shares
    ├── NAS connections
    └── Storage devices

Query Method:
- Use: dir, tree commands
- Effect: READ ONLY directory listings
- Risk: NONE
- Data: Directory structure, file names only
```

**Linux File System Discovery:**

```bash
Safe Discovery:
├── Filesystem Scan
│   ├── mount command (storage mapping)
│   ├── df command (disk usage)
│   ├── lsblk command (block devices)
│   └── ls -la (directory contents)
├── Application Locations
│   ├── /opt (application data)
│   ├── /home (user data)
│   ├── /var (variable data)
│   └── /srv (service data)
└── Database Discovery
    ├── Common database paths
    ├── Data directory locations
    └── Backup locations

Query Method:
- Use: standard Unix tools (ls, mount, df)
- Effect: READ ONLY listings
- Risk: NONE
- Data: Directory structure only
```

### 1.3 Application Inventory

**Windows Application Discovery:**

```python
Installed Applications:
├── WMI Query: Win32_Product
│   └── All installed applications
├── Registry: HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall
│   └── Application registry entries
├── File System: Program Files
│   └── Application directories
└── Services: Service registry
    └── Running application services

Identified Applications:
├── EHR Systems
│   ├── MediNova
│   ├── CompuCare
│   ├── Practice Manager
│   └── Other systems
├── Database Systems
│   ├── SQL Server
│   ├── MySQL
│   ├── PostgreSQL
│   └── Oracle
├── Imaging Systems
│   ├── PACS systems
│   ├── Imaging viewers
│   └── Imaging storage
├── Backup Software
│   ├── Backup Exec
│   ├── Acronis
│   ├── Native backups
│   └── Cloud backup
└── Other Critical Software
    ├── Email systems
    ├── VPN systems
    ├── Firewalls
    └── Antivirus

Query Method:
- Use: WMI, Registry queries, file system scan
- Effect: READ ONLY enumeration
- Risk: NONE
- Data: Software names, versions, locations
```

**Linux Application Discovery:**

```bash
Installed Packages:
├── Package Manager Query
│   ├── dpkg -l (Debian)
│   ├── rpm -qa (Red Hat)
│   └── yum list (Fedora)
├── Running Services
│   ├── systemctl list-units
│   ├── service --status-all
│   └── ps aux
├── Listening Ports
│   ├── netstat -tlnp
│   ├── ss -tlnp
│   └── lsof -i
└── Installed Software
    ├── Application directories
    ├── Custom installations
    └── Development tools

Query Method:
- Use: package management, system tools
- Effect: READ ONLY queries
- Risk: NONE
- Data: Package names, versions, ports
```

---

## Tier 2: Safe System Queries

### 2.1 Database Discovery (Read-Only Queries)

**EHR System Database:**

```sql
-- Safe Read-Only Queries (NO DATA ACCESS)

-- Identify database system
SELECT @@version;  -- Database version, NO CHANGES

-- List databases (system information only)
SELECT name FROM sys.databases;

-- List tables (schema information only)
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES;

-- List users (security information only)
SELECT name FROM sys.sysusers WHERE islogin = 1;

-- Backup information (metadata only)
SELECT name, backup_finish_date FROM msdb.dbo.backupset;

-- Configuration (no data access)
SELECT name, value FROM sys.configurations;

CONSTRAINTS:
- NO SELECT from medical records
- NO access to patient data
- NO modifications
- NO data extraction
- Information gathering ONLY
```

**Database Connectivity Test:**

```python
# Test connection WITHOUT accessing data
def test_database_connectivity():
    Try connection:
    ├── Server: <hostname>
    ├── Port: <port>
    ├── Database: <name>
    └── Result: SUCCESS/FAILURE

    On success:
    ├── Document connectivity
    ├── Note database location
    ├── Identify database type
    ├── Record version
    └── DISCONNECT (no data access)

    Risk: NONE
    Data Access: NONE
    Changes: NONE
```

### 2.2 Network Discovery

**SNMP Queries (Read-Only):**

```python
SNMP Discovery (UDP 161, read-only community string):
├── System Information
│   ├── sysUpTime (device uptime)
│   ├── sysDescr (device description)
│   ├── sysObjectID (device type)
│   └── sysServices (services offered)
├── Interface Information
│   ├── ifNumber (number of interfaces)
│   ├── ifDescr (interface descriptions)
│   ├── ifSpeed (interface speed)
│   ├── ifOperStatus (operational status)
│   └── ifPhysAddress (MAC address)
├── Route Information
│   ├── ipRouteTable (routing table)
│   ├── ipRouteNextHop (gateway)
│   └── ipRouteMask (network mask)
└── ARP Information
    ├── ipNetToMediaPhysAddress (MAC mappings)
    └── ipNetToMediaNetAddress (IP mappings)

Query Method:
- Use: snmpwalk (read-only tool)
- Community: 'public' (read-only)
- Port: 161 (SNMP default)
- Risk: NONE
- Changes: NONE
- Data: Device information only
```

**DNS Queries (Informational):**

```bash
# Non-invasive DNS discovery
Safe Queries:
├── nslookup (forward/reverse lookup)
├── dig (DNS query tool)
├── host (host lookup)
└── nbtstat (NetBIOS lookup)

Information Gathered:
├── Hostname to IP mapping
├── Service records (SRV)
├── Mail exchange records (MX)
├── Name server records (NS)
├── Text records (TXT)
└── CNAME records

Risk: NONE
Changes: NONE
Data: DNS records only
```

**DHCP Queries (With Permission):**

```python
DHCP Discovery:
├── DHCP Server Query
│   ├── Active leases
│   ├── Reserved addresses
│   ├── IP pool information
│   └── Client list
├── Device Information
│   ├── Hostname
│   ├── IP address
│   ├── MAC address
│   └── Last activity
└── Scope Information
    ├── Subnet mask
    ├── Default gateway
    ├── DNS servers
    └── DHCP server address

Query Method:
- Windows: netsh dhcp show (admin access)
- Linux: dhcp-server-logs (log analysis)
- Risk: NONE (read-only)
- Changes: NONE
- Data: DHCP configuration only
```

### 2.3 Service & Process Discovery

**Windows Services:**

```python
Safe Service Discovery:
├── Service Enumeration
│   ├── Service name
│   ├── Service status (running/stopped)
│   ├── Service type (system/user)
│   ├── Startup type (auto/manual)
│   ├── Executable path
│   └── Dependencies
├── Service Information
│   ├── Service description
│   ├── Service version
│   ├── Service account
│   └── Last start time
└── Critical Services
    ├── Database services
    ├── Backup services
    ├── Network services
    └── Security services

Query Method:
- Use: sc query (Windows service controller)
- PowerShell: Get-Service
- WMI: Win32_Service
- Risk: NONE (read-only)
- Changes: NONE
```

**Linux Services:**

```bash
Safe Service Discovery:
├── Service Status
│   ├── systemctl list-units
│   ├── systemctl status <service>
│   └── service <service> status
├── Process Information
│   ├── ps aux (process list)
│   ├── top (process monitor)
│   ├── lsof (open files)
│   └── netstat (network connections)
├── Startup Services
│   ├── systemctl list-enabled
│   ├── /etc/rc.d/ (startup scripts)
│   └── systemd configuration
└── Service Dependencies
    ├── Service requirements
    ├── Service triggers
    └── Service ordering

Query Method:
- Use: systemctl, service, ps commands
- Risk: NONE (read-only)
- Changes: NONE
- Data: Service information only
```

---

## Tier 3: Connectivity Testing

### 3.1 Ping Connectivity

**Safe Connectivity Verification:**

```python
def test_connectivity():
    """Test system connectivity - completely safe"""
    
    Systems to Test:
    ├── Primary server
    ├── Backup server
    ├── Database server
    ├── Imaging server
    ├── NAS/Storage
    ├── Gateway/Router
    ├── DNS server
    └── Internet connectivity
    
    Test Method:
    - ping <hostname>
    - ICMP echo requests
    - Measure response time
    
    Result:
    ├── Reachable / Unreachable
    ├── Response time
    ├── Packet loss %
    └── Network path
    
    Risk: NONE
    Changes: NONE
    Data: Connectivity status only
```

### 3.2 Port Scanning (Information Only)

**Service Port Discovery:**

```python
def port_scan():
    """Identify running services by open ports"""
    
    Scanning Method:
    ├── nmap -sV (service version detection)
    ├── TCP port scan
    ├── UDP port scan
    └── Service identification
    
    Information Gathered:
    ├── Open ports
    ├── Service types
    ├── Service versions (if identifiable)
    ├── Firewall rules (inferred)
    └── Running services
    
    Common Ports Mapped:
    ├── 3306: MySQL
    ├── 5432: PostgreSQL
    ├── 1433: SQL Server
    ├── 445: SMB/File Sharing
    ├── 3389: Remote Desktop
    ├── 22: SSH
    ├── 80: HTTP
    └── 443: HTTPS
    
    Risk: NONE (information gathering only)
    Changes: NONE
    Impact: NONE
```

### 3.3 Credential Validation (No Data Access)

**Read-Only Connectivity Test:**

```python
def validate_credential_access():
    """Test credential works WITHOUT accessing data"""
    
    Database Test:
    ├── Attempt connection
    ├── If successful:
    │   ├── Execute: SELECT 1
    │   ├── Verify response
    │   ├── Record success
    │   └── DISCONNECT
    └── If failed:
        └── Record failure reason
    
    Server Test:
    ├── SSH/RDP connection attempt
    ├── If successful:
    │   ├── Execute: whoami
    │   ├── Verify identity
    │   ├── Record success
    │   └── DISCONNECT
    └── If failed:
        └── Record failure reason
    
    Share Test:
    ├── Network share connection
    ├── If successful:
    │   ├── List directory
    │   ├── Verify read access
    │   ├── Record success
    │   └── DISCONNECT
    └── If failed:
        └── Record failure reason
    
    Data Access: NONE
    Modifications: NONE
    Risk: NONE
```

---

## Tier 4: Safe Sandbox Operations

### 4.1 Backup Clone Testing

**Safe Testing Environment:**

```python
def create_sandbox_environment():
    """Create safe isolated testing environment"""
    
    Step 1: Identify Backup to Test
    ├── Select backup file
    ├── Verify backup integrity
    ├── Check backup date
    └── Confirm size/completeness
    
    Step 2: Clone to Isolated Storage
    ├── Copy backup file
    ├── Destination: Isolated storage
    ├── Network: NOT connected to production
    ├── Verification: Checksum validate
    └── Result: Complete isolated copy
    
    Step 3: Mount in Sandbox VM
    ├── Create VM (VMware/Hyper-V)
    ├── Attach cloned drive
    ├── Configure isolated network
    ├── Snapshot for revert capability
    └── Boot VM
    
    Step 4: Verification
    ├── System boots successfully
    ├── All drives accessible
    ├── Services start
    ├── Database accessible
    └── Applications functional
    
    Production Impact: NONE
    Reversibility: COMPLETE
```

### 4.2 Procedure Validation

**Safe Procedure Testing:**

```python
def validate_procedure():
    """Test procedures safely in sandbox"""
    
    For Each Procedure:
    
    Step 1: Create Snapshot
    ├── Take VM snapshot
    ├── Current state saved
    ├── Revert capability enabled
    └── Testing can proceed
    
    Step 2: Execute Procedure
    ├── Follow documented steps
    ├── Execute in sandbox
    ├── Monitor progress
    ├── Record results
    └── Identify issues
    
    Step 3: Validate Results
    ├── Verify all steps worked
    ├── Check functionality
    ├── Measure performance
    ├── Document findings
    └── Identify improvements
    
    Step 4: Revert Snapshot
    ├── Revert to pre-test state
    ├── System restored
    ├── Test cleanup complete
    └── Ready for next test
    
    Procedures Tested:
    ├── Startup procedures
    ├── Shutdown procedures
    ├── Backup procedures
    ├── Restore procedures
    ├── Recovery procedures
    ├── Failover procedures
    └── Emergency procedures
    
    Production Impact: NONE
    Data Integrity: MAINTAINED
    Procedure Confidence: VERIFIED
```

### 4.3 Disaster Recovery Testing

**Safe DR Testing:**

```python
def test_disaster_recovery():
    """Test complete DR capability safely"""
    
    Environment: Isolated Sandbox VM
    
    Scenario 1: Database Failure
    ├── Create snapshot
    ├── Simulate database failure
    ├── Activate recovery procedure
    ├── Restore from backup
    ├── Verify data integrity
    ├── Measure recovery time
    ├── Document process
    └── Revert snapshot
    
    Scenario 2: Server Failure
    ├── Create snapshot
    ├── Simulate server failure
    ├── Boot from backup
    ├── Activate failover
    ├── Test service availability
    ├── Verify connectivity
    ├── Document procedure
    └── Revert snapshot
    
    Scenario 3: Partial Data Corruption
    ├── Create snapshot
    ├── Corrupt test data
    ├── Execute recovery procedure
    ├── Validate uncorrupted data
    ├── Verify recovery
    ├── Document procedures
    └── Revert snapshot
    
    Results:
    ├── Recovery procedures work
    ├── Recovery time documented
    ├── Success rate: 100%
    ├── Data integrity: verified
    ├── Staff confidence: high
    └── Compliance: achieved
    
    Production Impact: NONE
    Confidence Level: HIGH
```

---

## Discovery Checklist

### Phase 1: Setup & Safety Verification

- [ ] Obtain management approval
- [ ] Document practice infrastructure
- [ ] Identify critical systems
- [ ] Plan discovery windows
- [ ] Verify sandbox availability
- [ ] Confirm backup schedule
- [ ] Test discovery tools
- [ ] Establish rollback procedures

### Phase 2: Tier 1 Passive Discovery

- [ ] Scan Windows registry
- [ ] Scan Linux configuration
- [ ] Enumerate file systems
- [ ] Identify database locations
- [ ] Catalog applications
- [ ] Document shared drives
- [ ] Identify backup locations
- [ ] Compile initial infrastructure map

### Phase 3: Tier 2 Safe Queries

- [ ] Query database systems (read-only)
- [ ] Identify database users
- [ ] List backup history
- [ ] Query network devices (SNMP)
- [ ] Scan DNS records
- [ ] Check DHCP leases
- [ ] Enumerate services
- [ ] Identify processes

### Phase 4: Tier 3 Connectivity Testing

- [ ] Test server connectivity
- [ ] Verify DNS resolution
- [ ] Scan open ports
- [ ] Identify services
- [ ] Test backup accessibility
- [ ] Verify network paths
- [ ] Document routing
- [ ] Confirm gateway access

### Phase 5: Tier 4 Sandbox Testing

- [ ] Clone production backup
- [ ] Create sandbox VM
- [ ] Test system boot
- [ ] Validate database restore
- [ ] Test recovery procedures
- [ ] Document recovery time
- [ ] Verify data integrity
- [ ] Confirm all procedures

### Phase 6: Documentation & Catalog

- [ ] Create infrastructure map
- [ ] Document all systems
- [ ] List all credentials needed
- [ ] Create access matrix
- [ ] Document procedures
- [ ] Create emergency contact list
- [ ] Generate compliance report
- [ ] Prepare recommendations

---

## Safe Discovery Guarantees

### What WILL Happen
✅ Complete infrastructure mapping
✅ System inventory completed
✅ All applications identified
✅ Database locations documented
✅ Backup systems verified
✅ Network topology mapped
✅ Service dependencies identified
✅ Emergency procedures documented

### What WILL NOT Happen
❌ No production system changes
❌ No service interruptions
❌ No data access
❌ No data modifications
❌ No credential exposure
❌ No security vulnerabilities introduced
❌ No compliance violations
❌ No hidden operations

---

This framework ensures **complete infrastructure discovery** with **zero production impact** and **absolute safety guarantees**.
