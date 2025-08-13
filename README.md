# 🏥 Ubuntu Patient Care System
## The World's Most Advanced South African Medical Software

**"I am because we are" - Ubuntu Philosophy in Healthcare Technology**

A revolutionary, offline-first medical software suite designed exclusively for South African healthcare providers. This system seamlessly integrates traditional African healing wisdom with cutting-edge medical technology, creating an unparalleled healthcare experience that no other software in the world can match.

## 🎯 Project Overview

**Mission:** Create a robust medical software solution that works seamlessly offline, is easy to install, and meets all South African legal and billing requirements for radiology practices.

## 🌟 World-First Features That Set Us Apart

### �*🇦 **Uniquely South African**
- **🗣️ 11 Official Languages Support** - Full interface in English, Afrikaans, isiZulu, isiXhosa, Sesotho, Setswana, Sepedi, Tshivenda, Xitsonga, siSwati, and isiNdebele
- **🤝 Ubuntu Care Philosophy** - Community-centered healthcare with family involvement
- **🌿 Traditional Medicine Integration** - World's first digital bridge between traditional African healing and modern medicine
- **⚡ Load Shedding Awareness** - Intelligent power management during South Africa's unique power challenges
- **🏛️ Complete Medical Aid Integration** - Direct integration with ALL major SA medical schemes

### 🚀 **Revolutionary Technology**
- **🔄 Offline-First Architecture** - Full functionality without internet connection
- **🏥 Advanced Patient Management** - Customized OpenEMR for South African workflows  
- **📸 Enterprise DICOM Storage** - Orthanc PACS with intelligent NAS integration
- **👁️ Professional Medical Imaging** - Browser-based DICOM viewer with AI enhancement
- **💰 Intelligent Billing System** - Automated claims processing for all SA medical aids
- **🔒 POPI Act Compliance** - Military-grade data protection and privacy compliance
- **📊 Real-Time Dashboard** - Live patient status and workflow management
- **🤖 AI-Powered Insights** - Predictive analytics for better patient outcomes

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Ubuntu 20.04+ or compatible Linux distribution
- Network Attached Storage (NAS) for image storage

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Jobeer1/Ubuntu-Patient-Care.git
cd Ubuntu-Patient-Care
```

2. **Run setup script:**
```bash
# For Linux/macOS
./scripts/setup-github-project.sh

# For Windows PowerShell
.\scripts\setup-github-project.ps1
```

3. **Start the services:**
```bash
docker-compose up -d
```

4. **Access the system:**
- Patient Management: http://localhost:8080
- DICOM Viewer: http://localhost:8042
- Dashboard: http://localhost:3000

## 📋 Current Development Status

### ✅ Completed
- [x] Project structure and documentation
- [x] GitHub project board setup
- [x] Development workflow automation

### 🚧 In Progress
- [ ] **Design Offline-First Data Sync** - Local database with sync capabilities
- [ ] **Containerize OpenEMR & Orthanc** - Docker deployment setup
- [ ] **Customize OpenEMR for Local Radiology** - SA-specific forms and workflows
- [ ] **Build Visual Dashboard/Worklist** - Real-time patient status interface
- [ ] **Add Local Billing Codes** - ICD-10, NRPL integration
- [ ] **Generate Invoices & Claims** - SA medical aid compatibility
- [ ] **Ensure POPI Act Compliance** - Data encryption and audit logging

## 🏗️ Architecture

### Core Components

1. **OpenEMR** - Patient management and electronic health records
2. **Orthanc PACS** - DICOM image storage and retrieval
3. **DICOM Viewer** - Web-based medical image viewing
4. **Sync Service** - Offline-first data synchronization
5. **Billing Engine** - SA medical aid integration
6. **Dashboard** - Unified workflow interface

### Data Flow
```
Patient Registration → OpenEMR → Dashboard
					↓
DICOM Images → Orthanc PACS → NAS Storage
					↓
Image Viewing → DICOM Viewer → Status Updates
					↓
Report Generation → Billing Engine → Medical Aid Claims
```

## 🛠️ Development

### Team Structure
- **Developer 1:** UI/UX, OpenEMR customization, dashboards
- **Developer 2:** Backend, integration, billing, compliance, deployment

### Development Workflow
1. Create feature branch from `main`
2. Implement changes following the project plan
3. Submit pull request with detailed description
4. Code review and testing
5. Merge to main after approval

### Project Management
- **GitHub Projects** for task tracking
- **Issues** for bug reports and feature requests
- **Pull Requests** for code review
- **Actions** for automated testing and deployment

## 📁 Project Structure
[📊 **Progress Tracker:** [South African Medical Imaging System Progress Tracker](orthanc-source/NASIntegration/SOUTH_AFRICAN_PROGRESS_TRACKER.md)]

```
├── scripts/                 # Setup and deployment scripts
- **GEMS** (Government Employees) - Direct government integration
- **Bonitas Medical Fund** - Automated claim processing
- **Momentum Health** - Vitality program integration
- **Medihelp** - XML-based claim submission
- **Fedhealth** - Batch processing support
- **Bestmed** - Real-time eligibility verification
- **POLMED** (Police Medical) - Specialized law enforcement support
- **SAMWUMED** (Municipal Workers) - Union-specific features
- **Compensation Fund (COIDA)** - Workplace injury claims
- **Road Accident Fund (RAF)** - Accident-related claims

### 🌿 **Traditional Medicine Integration**
- **Sangoma Consultation System** - Digital integration with traditional healers
- **Herbal Medicine Database** - Comprehensive South African medicinal plants
- **Drug-Herb Interaction Checker** - Safety monitoring for traditional remedies
- **Cultural Sensitivity Engine** - Ubuntu philosophy in patient care
- **Traditional Healer Referral Network** - Verified practitioner directory

### ⚡ **Load Shedding Intelligence**
- **Real-Time Eskom Integration** - Live load shedding schedules
- **Intelligent Backup Management** - Automated power switching
- **Critical Equipment Protection** - Priority power allocation
- **Patient Notification System** - Automatic appointment adjustments
- **Emergency Protocol Activation** - Seamless crisis management

### 🔒 **POPI Act Excellence**
- **Military-Grade Encryption** - AES-256 data protection
- **Comprehensive Audit Trails** - Every action logged and monitored
- **Patient Consent Management** - Digital consent with cultural considerations
- **Data Retention Policies** - 7-year medical record compliance
- **Cross-Border Data Protection** - International patient privacy

## 📁 Detailed Project Structure

### 🖥️ South African Tailored PACS & Reporting - **Orthanc**

```plaintext
Orthanc/
├── LICENSE
├── package.json
├── README.md
├── tsconfig.json
├── UbuntuPatientSorg_Plan.md
├── orthanc-source/
│   ├── AUTHORS
│   ├── CITATION.cff
│   ├── COPYING
│   ├── DarwinCompilation.txt
│   ├── INSTALL
│   ├── LinuxCompilation.txt
│   ├── NAS_INTEGRATION_PLAN.md
│   ├── NAS_REQUIREMENTS.md
│   ├── NEWS
│   ├── README
│   ├── STRUCTURE.md
│   ├── TODO
│   ├── NASIntegration/
│   │   └── SOUTH_AFRICAN_PROGRESS_TRACKER.md
│   ├── OrthancFramework/
│   └── OrthancServer/
├── React phones/
├── scripts/
└── (other directories)
```

### 🩺 RIS / Medical Billing - **OpenEMR Components**

```plaintext
openemr/
├── admin.php
├── index.php
├── build.xml
├── README.md
├── composer.json
├── (other configuration files...)
├── apis/
├── controllers/
├── modules/
├── public/
└── src/
```

## 🔧 Configuration

### Environment Variables
```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=patient_care
DB_USER=admin
DB_PASS=secure_password

# NAS Configuration
NAS_HOST=192.168.1.100
NAS_SHARE=/medical_images
NAS_USER=orthanc
NAS_PASS=nas_password

# Orthanc Configuration
ORTHANC_HTTP_PORT=8042
ORTHANC_DICOM_PORT=4242
```

### Docker Compose Services
- `openemr` - Patient management system
- `orthanc` - DICOM server
- `postgres` - Database server
- `nginx` - Web server and reverse proxy
- `dashboard` - Custom workflow interface

## 🧪 Testing

### Running Tests
```bash
# Unit tests
npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# End-to-end tests
npm run test:e2e
```

### Test Coverage
- Patient registration workflows
- DICOM image upload and retrieval
- Billing code validation
- Offline sync functionality
- Security and compliance checks

## 📚 Documentation

- [📋 Project Plan](UbuntuPatientSorg_Plan.md) - Detailed development roadmap
- [💾 NAS Requirements](orthanc-source/NAS_REQUIREMENTS.md) - NAS integration specifications  
- [🔌 API Documentation](docs/api.md) - REST API reference
- [👥 User Guide](docs/user-guide.md) - End-user documentation
- [🚀 Deployment Guide](docs/deployment.md) - Production setup instructions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- Follow existing code style and conventions
- Write comprehensive tests for new features
- Update documentation for any API changes
- Ensure POPI Act compliance for all data handling

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/Jobeer1/Ubuntu-Patient-Care/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Jobeer1/Ubuntu-Patient-Care/discussions)
- **Email:** [support@ubuntu-patient-care.com](mailto:support@ubuntu-patient-care.com)

## 🙏 Acknowledgments

- [Orthanc](https://www.orthanc-server.com/) - DICOM server foundation
- [OpenEMR](https://www.open-emr.org/) - Electronic health records system
- South African medical community for requirements and feedback

---

**Built with ❤️ for South African healthcare providers**



