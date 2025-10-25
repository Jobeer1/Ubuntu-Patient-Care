# ===============================================
# SA RIS System - Production Deployment Guide
# Complete setup and deployment instructions
# ===============================================

## Overview

The South African Radiology Information System (SA RIS) is a comprehensive, production-ready radiology management platform specifically designed for the South African healthcare market. This system provides:

- **Advanced SA Medical Aid Integration**: Real-time billing with Discovery, Momentum, Bonitas, GEMS
- **POPI Act Compliance**: Full data protection and audit trail capabilities
- **AI-Powered Workflows**: Automated report generation and critical finding detection
- **DICOM Management**: Complete Orthanc integration with intelligent routing
- **Real-time Monitoring**: Live dashboards and performance analytics

## System Requirements

### Hardware Requirements

**Minimum Production Setup:**
- CPU: 8 cores (Intel Xeon or AMD EPYC)
- RAM: 32GB DDR4
- Storage: 1TB NVMe SSD + 10TB HDD for DICOM storage
- Network: Gigabit Ethernet
- GPU: NVIDIA GTX 1660 or better (for AI processing)

**Recommended Production Setup:**
- CPU: 16 cores (Intel Xeon Gold or AMD EPYC)
- RAM: 64GB DDR4
- Storage: 2TB NVMe SSD + 50TB enterprise storage array
- Network: 10 Gigabit Ethernet with redundancy
- GPU: NVIDIA RTX 4090 or Tesla V100 (for advanced AI)

### Software Requirements

- Ubuntu 22.04 LTS or Red Hat Enterprise Linux 9
- Docker Engine 24.0+
- Docker Compose v2.20+
- Nginx 1.24+
- SSL certificates (Let's Encrypt or commercial)

## Quick Start Deployment

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install NVIDIA Docker (for GPU support)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install -y nvidia-docker2
sudo systemctl restart docker
```

### 2. Download and Configure

```bash
# Clone the repository
git clone https://github.com/your-org/ubuntu-patient-care.git
cd ubuntu-patient-care/sa-ris-backend

# Copy environment configuration
cp .env.example .env

# Generate secure passwords and keys
openssl rand -base64 32  # Use for JWT_SECRET
openssl rand -base64 32  # Use for MYSQL_ROOT_PASSWORD
```

### 3. SSL Certificate Setup

```bash
# Create SSL directory
mkdir -p ssl_certificates

# Option A: Let's Encrypt (recommended)
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.co.za
sudo cp /etc/letsencrypt/live/your-domain.co.za/fullchain.pem ssl_certificates/certificate.crt
sudo cp /etc/letsencrypt/live/your-domain.co.za/privkey.pem ssl_certificates/private.key

# Option B: Self-signed for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl_certificates/private.key \
  -out ssl_certificates/certificate.crt
```

### 4. Configure Medical Aid Integration

Edit `.env` file with your medical aid credentials:

```bash
# Discovery Health Medical Scheme
DISCOVERY_CLIENT_ID=your_discovery_client_id
DISCOVERY_CLIENT_SECRET=your_discovery_client_secret

# Momentum Health
MOMENTUM_CLIENT_ID=your_momentum_client_id
MOMENTUM_CLIENT_SECRET=your_momentum_client_secret

# Add other medical aid configurations...
```

### 5. Deploy the System

```bash
# Create necessary directories
mkdir -p logs backups dicom_backups

# Start the system
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

## Configuration Details

### Database Configuration

The system uses MySQL 8.0 with optimized settings for radiology workloads:

```sql
-- Performance optimizations in my.cnf
innodb_buffer_pool_size = 16G
max_connections = 1000
query_cache_size = 512M
innodb_log_file_size = 1G
```

### DICOM Configuration

Orthanc is configured for high-performance DICOM handling:

```json
{
  "StorageCompression": false,
  "MaximumStorageSize": 0,
  "MaximumPatientCount": 0,
  "DicomAet": "SA_RIS_ORTHANC",
  "DicomPort": 4242,
  "DicomServerEnabled": true,
  "DicomAlwaysAllowEcho": true,
  "DicomAlwaysAllowFind": true,
  "DicomAlwaysAllowGet": true,
  "DicomAlwaysAllowMove": true,
  "DicomAlwaysAllowStore": true
}
```

### AI Model Setup

```bash
# Download pre-trained models
mkdir -p ai_models
cd ai_models

# Chest X-ray detection model
wget https://models.sa-ris.co.za/chest_xray_v2.h5

# CT head analysis model
wget https://models.sa-ris.co.za/ct_head_detection.onnx

# MRI brain analysis model
wget https://models.sa-ris.co.za/mri_brain_analysis.pt

cd ..
```

## South African Medical Aid Integration

### Discovery Health Medical Scheme

The system integrates with Discovery's real-time authorization API:

```php
// Real-time benefit check
$discoveryAPI = new DiscoveryHealthAPI([
    'client_id' => env('DISCOVERY_CLIENT_ID'),
    'client_secret' => env('DISCOVERY_CLIENT_SECRET'),
    'environment' => 'production'
]);

$benefitCheck = $discoveryAPI->checkBenefits([
    'member_number' => $memberNumber,
    'procedure_code' => $nrplCode,
    'provider_number' => $providerNumber
]);
```

### Momentum Health

Electronic claims submission with real-time status updates:

```php
// Submit claim electronically
$momentumAPI = new MomentumHealthAPI([
    'client_id' => env('MOMENTUM_CLIENT_ID'),
    'client_secret' => env('MOMENTUM_CLIENT_SECRET')
]);

$claimSubmission = $momentumAPI->submitClaim([
    'claim_data' => $claimXML,
    'attachments' => $supportingDocuments
]);
```

### NRPL Integration

Automatic updates of the National Reference Price List:

```bash
# Daily NRPL update cron job
0 2 * * * /usr/local/bin/php /var/www/html/artisan nrpl:update
```

## Monitoring and Analytics

### Grafana Dashboards

Access Grafana at `https://your-domain.co.za:3001`:

**Key Dashboards:**
- Radiology Workflow Performance
- Medical Aid Claims Status
- DICOM Storage Utilization
- AI Processing Metrics
- Financial Analytics

### ElasticSearch Logging

All system events are logged to ElasticSearch:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "workflow_engine",
  "patient_id": "12345",
  "event": "examination_completed",
  "duration_minutes": 45,
  "urgency": "routine"
}
```

### Performance Monitoring

Key performance indicators tracked:

- **Turnaround Time**: Average time from booking to report delivery
- **AI Accuracy**: Confidence scores and radiologist agreement rates
- **Claims Processing**: Success rates and payment timelines
- **System Utilization**: Equipment usage and workflow efficiency

## Security and Compliance

### POPI Act Compliance

The system implements comprehensive POPI Act compliance:

**Data Protection Measures:**
- End-to-end encryption for all patient data
- Audit trails for all data access and modifications
- Automated data retention policies
- Patient consent management
- Right to be forgotten implementation

**Audit Trail Example:**
```json
{
  "patient_id": "12345",
  "user_id": "radiologist_001",
  "action": "report_viewed",
  "timestamp": "2024-01-15T10:30:00Z",
  "ip_address": "192.168.1.100",
  "justification": "Report review for treatment planning"
}
```

### Security Features

- **Multi-factor Authentication**: TOTP-based 2FA for all users
- **Role-based Access Control**: Granular permissions system
- **API Rate Limiting**: Protection against abuse
- **SQL Injection Prevention**: Parameterized queries throughout
- **CSRF Protection**: Token-based protection for all forms

## Backup and Disaster Recovery

### Automated Backups

```bash
# Database backup script (runs daily)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec sa_ris_mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} sa_ris_db > backups/sa_ris_${DATE}.sql
gzip backups/sa_ris_${DATE}.sql

# DICOM backup (runs hourly)
rsync -avz orthanc_storage/ dicom_backups/$(date +%Y%m%d_%H)/
```

### Disaster Recovery

**Recovery Time Objective (RTO):** 4 hours
**Recovery Point Objective (RPO):** 1 hour

**Recovery Steps:**
1. Restore latest database backup
2. Restore DICOM storage from backup
3. Verify data integrity
4. Resume operations

## Maintenance

### Regular Maintenance Tasks

```bash
# Weekly maintenance script
#!/bin/bash

# Update NRPL codes
docker exec sa_ris_backend php artisan nrpl:update

# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete

# Optimize database
docker exec sa_ris_mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "OPTIMIZE TABLE sa_ris_db.*"

# Clean old DICOM studies (archive after 5 years)
docker exec sa_ris_backend php artisan dicom:archive --older-than=5years

# Generate performance reports
docker exec sa_ris_backend php artisan reports:performance --period=weekly
```

### System Updates

```bash
# Update Docker images
docker-compose pull
docker-compose up -d

# Update AI models
docker exec sa_ris_ai python update_models.py

# Database migrations
docker exec sa_ris_backend php artisan migrate
```

## Troubleshooting

### Common Issues

**Issue: High memory usage**
```bash
# Check container memory usage
docker stats

# Optimize MySQL buffer pool
# Edit docker-compose.yml and increase --innodb-buffer-pool-size
```

**Issue: Slow DICOM transfers**
```bash
# Check network performance
iperf3 -c dicom-server-ip

# Optimize Orthanc configuration
# Increase concurrent transfer limits in orthanc.json
```

**Issue: Failed medical aid submissions**
```bash
# Check API credentials
docker exec sa_ris_backend php artisan medical-aid:test-connection discovery

# Review logs
docker logs sa_ris_backend | grep "medical_aid_error"
```

### Log Analysis

```bash
# Real-time log monitoring
docker-compose logs -f --tail=100

# Search for specific errors
docker logs sa_ris_backend 2>&1 | grep -i "error\|exception"

# Performance analysis
docker exec sa_ris_backend php artisan log:analyze --type=performance
```

## Support and Documentation

### API Documentation

Access the interactive API documentation at:
`https://your-domain.co.za/api/documentation`

### Training Resources

- **Administrator Guide**: `/docs/admin-guide.pdf`
- **User Manual**: `/docs/user-manual.pdf`
- **API Reference**: `/docs/api-reference.html`
- **Video Tutorials**: Available at training portal

### Support Contacts

- **Technical Support**: support@sa-ris.co.za
- **Medical Aid Integration**: billing@sa-ris.co.za
- **Emergency Support**: +27 11 123 4567 (24/7)

## License and Compliance

This system is licensed under the MIT License and complies with:

- **POPI Act (Protection of Personal Information Act)**
- **HPCSA Guidelines** (Health Professions Council of South Africa)
- **Medical Schemes Act**
- **DICOM Standards**
- **HL7 FHIR R4**

---

**© 2024 Ubuntu Patient Care - South African RIS System**
**Version 1.0.0 - Production Ready**
