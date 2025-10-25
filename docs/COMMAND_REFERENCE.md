# 🇿🇦 South African Radiology Information System - Command Reference

## 📋 Available Commands & Scripts

### 🚀 **Quick Start (Recommended)**
```bash
# Double-click this file to start everything
start_system.bat
```

---

## 🐳 **Docker Services**

### Start All Docker Services
```bash
# From sa-ris-backend directory
docker-compose up -d

# Or use the dedicated script
start_docker.bat
```

### Individual Services
```bash
# MySQL Database
docker-compose up -d mysql_ris

# Redis Cache
docker-compose up -d redis_cache

# Orthanc PACS
docker-compose up -d orthanc

# FHIR Server
docker-compose up -d fhir_server
```

### Docker Management
```bash
# Check running containers
docker ps

# View logs
docker logs sa-ris-backend
docker logs mysql_ris
docker logs orthanc

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart orthanc
```

---

## ⚙️ **Backend Server**

### Start Backend Server
```bash
cd sa-ris-backend

# Install dependencies (first time only)
npm install

# Start server
npm start

# Or use development mode with auto-restart
npm run dev

# Or use the batch file
start_backend.bat
```

### Backend API Endpoints
```
GET  /health                    - Health check
GET  /api/dicom/studies         - List DICOM studies
GET  /api/dicom/studies/:id     - Get specific study
POST /api/dicom/studies/:id/compliance - Upgrade to DICOM 2023
GET  /api/fhir/patients         - FHIR patient queries
POST /api/fhir/imaging-study    - Create ImagingStudy
POST /api/fhir/patient          - Create FHIR patient
GET  /api/workflow/dashboard    - Dashboard data
POST /api/workflow/report       - Create radiology report
GET  /api/billing/estimate      - Billing estimate
POST /api/billing/claim         - Submit billing claim
```

---

## 🌐 **Frontend Application**

### Start Frontend
```bash
cd sa-ris-frontend

# Install dependencies (first time only)
npm install

# Start development server
npm start

# Or use the batch file
start_frontend.bat
```

### Frontend URLs
- **Main Application**: http://localhost:3000
- **South African Dashboard**: Features flag colors, animations
- **Accessibility**: EN/AF/ZU language switcher
- **Real-time Updates**: Socket.io integration

---

## 🧪 **Testing Commands**

### Functional Tests
```bash
# Run comprehensive functional test
node functional_test.js

# Run basic integration test
node integration_test.js
```

### Manual Testing
```bash
# Test backend health
curl http://localhost:3001/health

# Test DICOM studies endpoint
curl http://localhost:3001/api/dicom/studies

# Test FHIR integration
curl http://localhost:3001/api/fhir/patients

# Check Orthanc PACS
curl http://localhost:8042/system
```

---

## 📊 **Database Commands**

### MySQL Database
```bash
# Connect to database
docker exec -it sa_ris_mysql mysql -u sa_ris_user -p sa_ris_db

# Import schema
docker exec -i sa_ris_mysql mysql -u sa_ris_user -p sa_ris_db < database_schema.sql

# Backup database
docker exec sa_ris_mysql mysqldump -u sa_ris_user -p sa_ris_db > backup.sql
```

### Redis Cache
```bash
# Connect to Redis
docker exec -it sa_ris_redis redis-cli

# Check cache status
docker exec -it sa_ris_redis redis-cli ping

# Clear cache
docker exec -it sa_ris_redis redis-cli FLUSHALL
```

---

## 🔧 **Development Commands**

### Backend Development
```bash
cd sa-ris-backend

# Run tests
npm test

# Lint code
npm run lint

# Development mode
npm run dev
```

### Frontend Development
```bash
cd sa-ris-frontend

# Run tests
npm test

# Build for production
npm run build

# Start production server
npm run serve
```

---

## 📁 **File Structure & Locations**

```
sa-ris/
├── start_system.bat           # 🚀 Main startup script
├── start_docker.bat           # 🐳 Docker services only
├── functional_test.js         # 🧪 Functional testing
├── integration_test.js        # 🔗 Integration testing
│
├── sa-ris-backend/
│   ├── start_backend.bat      # ⚙️ Backend startup
│   ├── server.js              # 🚀 Main backend server
│   ├── package.json           # 📦 Backend dependencies
│   ├── .env                   # 🔐 Environment config
│   ├── docker-compose.yml     # 🐳 Docker services
│   ├── DICOM2023Compliance.php # 📊 DICOM 2023 standards
│   ├── FHIRRadiologyService.php # 🔬 HL7 FHIR integration
│   ├── OrthancConnector.php   # 🩺 PACS connection
│   ├── RISWorkflowEngine.php  # ⚡ Workflow management
│   └── SABillingEngine.php    # 💰 Medical billing
│
└── sa-ris-frontend/
    ├── start_frontend.bat     # 🌐 Frontend startup
    ├── package.json           # 📦 Frontend dependencies
    ├── src/
    │   ├── SARadiologyDashboard.js    # 📊 Main dashboard
    │   ├── components/
    │   │   └── AccessibilityContext.js # ♿ WCAG 2.1 AA
    │   └── styles/
    │       └── sa-eye-candy.css       # 🎨 South African theme
```

---

## 🚨 **Troubleshooting Commands**

### Check Service Status
```bash
# Check all Docker containers
docker ps -a

# Check backend logs
docker logs sa-ris-backend

# Check specific service logs
docker logs mysql_ris
docker logs orthanc
docker logs redis_cache

# Check backend health
curl http://localhost:3001/health
```

### Restart Services
```bash
# Restart all Docker services
docker-compose restart

# Restart specific service
docker-compose restart orthanc

# Restart backend
cd sa-ris-backend && npm restart
```

### Clean Restart
```bash
# Stop everything
docker-compose down

# Remove containers and volumes (WARNING: deletes data)
docker-compose down -v

# Clean npm cache
cd sa-ris-backend && rm -rf node_modules && npm install
cd ../sa-ris-frontend && rm -rf node_modules && npm install

# Start fresh
docker-compose up -d
```

---

## 🔐 **Environment Configuration**

### Backend Environment (.env)
```bash
# Server
NODE_ENV=development
PORT=3001

# Database
MYSQL_ROOT_PASSWORD=sa_ris_root_2025
MYSQL_USER=sa_ris_user
MYSQL_PASSWORD=sa_ris_pass_2025

# Orthanc PACS
ORTHANC_URL=http://localhost:8042

# FHIR
FHIR_BASE_URL=https://fhir.sacoronavirus.co.za/r4

# Security
JWT_SECRET=sa_ris_jwt_secret_2025_change_this_in_production
```

### Update Environment
```bash
# Edit environment file
notepad sa-ris-backend\.env

# Restart services after changes
docker-compose restart
cd sa-ris-backend && npm restart
```

---

## 📞 **Support & Monitoring**

### Log Locations
- **Backend Logs**: `sa-ris-backend/` terminal window
- **Frontend Logs**: Browser console (F12)
- **Docker Logs**: `docker logs [container_name]`
- **System Logs**: Windows Event Viewer

### Health Checks
```bash
# Backend health
curl http://localhost:3001/health

# Database connection
docker exec sa_ris_mysql mysqladmin ping

# Redis connection
docker exec sa_ris_redis redis-cli ping

# Orthanc status
curl http://localhost:8042/system
```

---

## 🎯 **Quick Reference**

### Start Everything
```bash
# One command to rule them all
start_system.bat
```

### Check Everything is Running
```bash
# Quick health check
curl http://localhost:3001/health && echo "✅ Backend OK"
curl http://localhost:8042/system && echo "✅ Orthanc OK"
```

### Stop Everything
```bash
# From sa-ris-backend directory
docker-compose down
```

---

**🇿🇦 Happy coding with South African Radiology Information System! 🇿🇦**