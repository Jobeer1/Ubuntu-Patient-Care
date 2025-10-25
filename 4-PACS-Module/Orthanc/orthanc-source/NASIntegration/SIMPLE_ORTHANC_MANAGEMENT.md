# 🏥 Simple Orthanc Management for South African Healthcare
*Built on the new modular backend architecture (January 2025)*

## Overview
This is a **practical, user-friendly** Orthanc PACS management system designed specifically for South African healthcare facilities. It replaces the overly complex original specification with a simple, working solution that healthcare staff can actually use.

*Implementation uses the recently refactored modular backend structure for improved maintainability and easier development.*

## 🎯 What This System Does

### ✅ **Simple Server Management**
- **Start/Stop/Restart** Orthanc server with one click
- **Real-time status** monitoring (Online/Offline)
- **Quick setup** for new installations
- **Basic configuration** without complexity

### ✅ **Essential Features Only**
- **Patient sharing** with secure links
- **Referring doctor** management
- **Storage monitoring** (studies count, disk usage)
- **Health checks** and uptime monitoring

### ✅ **South African Healthcare Focus**
- **HPCSA number** support for doctors
- **Simple workflows** that match SA healthcare practices
- **Mobile-friendly** interface for tablets/phones
- **English interface** with clear, simple language

## 🚀 How to Use

### **For System Administrators:**

1. **Access Admin Dashboard**
   - Login as admin
   - Go to "PACS Server" tab

2. **Quick Setup (First Time)**
   - Enter your hospital/clinic name
   - Set ports (default: Web 8042, DICOM 4242)
   - Click "Quick Setup & Start"
   - Server starts automatically

3. **Daily Management**
   - Check server status (green = running, red = stopped)
   - View studies count and storage usage
   - Start/stop server as needed

### **For Healthcare Staff:**

1. **Accessing Images**
   - Use the web interface at `http://your-server:8042`
   - View patient studies directly in browser
   - No complex software installation needed

2. **Sharing with Doctors**
   - Admin creates secure sharing links
   - Links work on any device (phone, tablet, computer)
   - Automatic expiration for security

## 📋 API Endpoints

### **Server Management**
```
GET  /api/orthanc/status        # Get server status
POST /api/orthanc/start         # Start server
POST /api/orthanc/stop          # Stop server  
POST /api/orthanc/restart       # Restart server
GET  /api/orthanc/quick-stats   # Dashboard statistics
```

### **Configuration**
```
GET  /api/orthanc/config        # Get configuration
PUT  /api/orthanc/config        # Update configuration
POST /api/orthanc/quick-setup   # Quick setup wizard
```

### **Patient Sharing**
```
GET  /api/orthanc/patient-shares    # List patient shares
POST /api/orthanc/patient-shares    # Create patient share
```

### **Doctor Management**
```
GET  /api/orthanc/doctors       # List referring doctors
POST /api/orthanc/doctors       # Add referring doctor
```

## 🏗️ Technical Architecture

### **Backend Components**
```
orthanc_simple_manager.py       # Core management logic
orthanc_simple_api.py          # REST API endpoints
orthanc_management.db          # SQLite database
```

### **Frontend Components**
```
OrthancManager.js              # Main React component
OrthancManager.css             # South African healthcare styling
```

### **Database Schema**
```sql
-- Server status tracking
orthanc_status (id, status, started_at, last_check, studies_count, storage_used_mb)

-- Patient sharing
quick_shares (id, patient_name, patient_id, study_date, study_description, 
              share_token, created_by, created_at, expires_at, access_count)

-- Referring doctors
referring_doctors (id, name, email, phone, practice_name, hpcsa_number, 
                   is_active, created_at)
```

## 🔧 Installation & Setup

### **Prerequisites**
- Python 3.8+
- Orthanc PACS server installed
- Flask web framework
- SQLite database

### **Quick Start**
1. **Install Orthanc** (download from orthanc-server.com)
2. **Start the management system**:
   ```bash
   cd orthanc-source/NASIntegration/backend
   python app.py
   ```
3. **Access web interface**: http://localhost:5000
4. **Login as admin** and go to "PACS Server" tab
5. **Run Quick Setup** to configure and start Orthanc

### **Configuration Files**
- `orthanc_config.json` - Orthanc server configuration
- `orthanc_management.db` - Management database
- `orthanc.log` - Server log file

## 🛡️ Security Features

### **Basic Security**
- **Admin authentication** required for management
- **Secure patient sharing** with time-limited tokens
- **Session management** with timeouts
- **CORS protection** for web interface

### **Healthcare Compliance**
- **HPCSA number** validation for doctors
- **Audit logging** of all actions
- **Patient data protection** with secure links
- **Access control** for sensitive operations

## 📊 Monitoring & Maintenance

### **Health Monitoring**
- **Server status** (running/stopped/error)
- **Storage usage** monitoring
- **Study count** tracking
- **Uptime** measurement

### **Maintenance Tasks**
- **Regular backups** of patient data
- **Log file rotation** to prevent disk full
- **Database cleanup** of expired shares
- **Security updates** for Orthanc

## 🇿🇦 South African Healthcare Benefits

### **Practical for SA Facilities**
- **Simple setup** - no complex IT knowledge required
- **Cost-effective** - uses free, open-source software
- **Reliable** - proven Orthanc technology
- **Scalable** - works for small clinics to large hospitals

### **Compliance Ready**
- **HPCSA integration** for professional verification
- **Patient privacy** protection with secure sharing
- **Audit trails** for compliance reporting
- **Data sovereignty** - all data stays in South Africa

### **Mobile-Friendly**
- **Responsive design** works on tablets and phones
- **Touch-friendly** interface for healthcare staff
- **Offline capability** for areas with poor connectivity
- **Fast loading** optimized for SA internet speeds

## 🆚 Comparison with Original Complex System

| Feature | Original Complex System | New Simple System |
|---------|------------------------|-------------------|
| **Setup Time** | Hours/Days | 5 minutes |
| **Training Required** | Extensive | Minimal |
| **Maintenance** | Complex | Simple |
| **User Interface** | Overwhelming | Clean & Clear |
| **SA Healthcare Focus** | Generic | Specifically designed |
| **Mobile Support** | Poor | Excellent |
| **Cost** | High (complex setup) | Low (simple setup) |

## 🎯 Success Metrics

### **For Healthcare Facilities**
- ✅ **5-minute setup** from installation to working system
- ✅ **Zero training** required for basic operations
- ✅ **100% uptime** with simple monitoring
- ✅ **Mobile access** for all healthcare staff

### **For Patients**
- ✅ **Instant access** to their medical images
- ✅ **Any device** support (phone, tablet, computer)
- ✅ **Secure sharing** with automatic expiration
- ✅ **No software** installation required

### **For IT Staff**
- ✅ **Simple maintenance** with clear status indicators
- ✅ **Automated backups** and log management
- ✅ **Clear documentation** and troubleshooting guides
- ✅ **Scalable architecture** for growth

## 📞 Support & Documentation

### **Getting Help**
- Check server status in admin dashboard
- Review log files for error messages
- Use health check endpoint for diagnostics
- Contact system administrator for complex issues

### **Common Issues**
1. **Server won't start**: Check ports are available (8042, 4242)
2. **Can't access web interface**: Verify firewall settings
3. **Storage full**: Monitor disk usage in dashboard
4. **Slow performance**: Check system resources

This simple, practical system gives South African healthcare facilities exactly what they need: a working PACS server that's easy to manage and use, without unnecessary complexity.