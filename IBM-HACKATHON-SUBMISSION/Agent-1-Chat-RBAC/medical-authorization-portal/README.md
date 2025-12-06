# 🏥 Medical Authorization Portal

A professional Flask web application for managing medical authorizations with AI-powered decision support.

## 🌟 Features

- **🔐 Secure Authentication**: User registration and login with encrypted passwords
- **👥 Patient Management**: Search and manage patient medical records
- **📋 Pre-Authorization System**: Create, track, and manage medical pre-authorizations
- **🤖 AI Copilot Assistant**: Chat interface powered by GitHub Copilot for medical queries
- **💾 Data Persistence**: SQLite database for users, chat history, and authorizations
- **🎨 Professional UI**: Healthcare-themed interface matching PACS standards
- **📊 Dashboard**: Real-time overview of authorizations and patient data
- **🔍 Smart Search**: Find patients by ID, name, or member number

## 📋 System Requirements

- Python 3.8+
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Safari, Edge)

## 🚀 Quick Start

### 1. Installation

```bash
# Navigate to project directory
cd medical-authorization-portal

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Application

```bash
# Start the Flask server
python app.py
```

The application will be available at: **http://localhost:5000**

### 3. Access Portal

- **URL**: http://localhost:5000
- **Default Page**: Login page
- **Demo Credentials**: Create a new account via registration

## 📖 User Guide

### Creating an Account

1. Click "Register here" on the login page
2. Enter username (3-20 characters), email, role (Clinician/Admin), and password (8+ characters)
3. Click "Create Account"
4. Login with your credentials

### Dashboard Overview

The dashboard displays:
- **Total Authorizations**: Count of all pre-authorizations
- **Approved**: Number of approved authorizations
- **Pending Review**: Pending authorizations awaiting decision
- **Chat Messages**: Total messages with AI assistant
- **Recent Pre-Authorizations**: List of latest authorizations
- **Quick Actions**: Buttons for common tasks

### Patient Search

1. Go to "Patient Search" from sidebar
2. Enter member number or patient name
3. Click "Search"
4. Click "View Details" or "New Auth" on patient card

### Pre-Authorizations

1. Go to "Pre-Authorizations" from sidebar
2. Use filters to search by status, date, procedure, or patient
3. View authorization details or edit existing ones
4. Track AI confidence scores and approval status

### Chat with Copilot

1. Navigate to "Chat with Copilot"
2. Ask questions about:
   - Patient benefit verification
   - Procedure cost estimation
   - Pre-authorization requirements
   - Medical decision support
3. Use quick question buttons for common queries
4. View chat history with timestamps

## 🏗️ Project Structure

```
medical-authorization-portal/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── templates/                      # HTML templates
│   ├── base.html                  # Base layout with header/sidebar
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── dashboard.html             # Main dashboard
│   ├── chat.html                  # Copilot chat interface
│   ├── patients.html              # Patient search
│   ├── authorizations.html        # Pre-authorization list
│   ├── 404.html                   # Not found page
│   └── 500.html                   # Server error page
├── static/                         # Static files
│   ├── css/
│   │   └── style.css              # Global stylesheet
│   └── js/                        # JavaScript files (future)
└── users.db                        # SQLite database (auto-created)
```

## 🔑 Key Endpoints

### Authentication
- `POST /login` - Login with credentials
- `POST /register` - Create new account
- `POST /logout` - Logout and clear session

### Main Pages
- `GET /` - Home (redirects to login/dashboard)
- `GET /dashboard` - Dashboard view
- `GET /patients` - Patient search
- `GET /authorizations` - Pre-authorization list
- `GET /chat` - Copilot chat interface

### API Endpoints
- `POST /api/validate-member` - Validate member enrollment
- `POST /api/check-benefits` - Get patient benefits
- `POST /api/estimate-cost` - Calculate procedure costs
- `POST /api/create-preauth` - Create pre-authorization
- `POST /api/check-preauth-status` - Track authorization status
- `POST /api/patient-data` - Query patient data across modules
- `POST /api/ai-consult` - AI consultation query
- `GET /api/chat-history` - Retrieve chat history

## 💾 Database Schema

### users table
- `id`: Primary key
- `username`: Unique username
- `password_hash`: SHA-256 hashed password
- `email`: User email
- `role`: 'clinician' or 'admin'
- `created_at`: Registration timestamp
- `last_login`: Last login timestamp

### chat_history table
- `id`: Primary key
- `user_id`: Foreign key to users
- `message`: User message
- `response`: AI response
- `context`: Query context
- `created_at`: Message timestamp

### authorizations table
- `id`: Primary key
- `user_id`: Foreign key to users
- `patient_id`: Patient identifier
- `procedure`: Medical procedure code
- `status`: 'approved', 'pending', or 'rejected'
- `ai_confidence`: AI confidence score (0-100)
- `ai_notes`: AI reasoning notes
- `created_at`: Creation timestamp

## 🎨 Design System

### Color Scheme
- **Primary Blue**: `#1e3c72` → `#2a5298` (gradient)
- **Accent Blue**: `#4a90e2` (buttons, highlights)
- **Success Green**: `#28a745` → `#20c997`
- **Warning Orange**: `#ffc107`
- **Error Red**: `#dc3545`
- **Dark Background**: `#0f0f0f` (main), `#1a1a1a` (cards)

### Typography
- **Font Family**: Segoe UI, Tahoma, Geneva, Verdana, sans-serif
- **Header**: 28px, 700 weight
- **Title**: 24px, 600 weight
- **Body**: 14px, 400 weight
- **Small**: 12px, 400 weight

### Components
- **Cards**: 12px border-radius, dark background with border
- **Buttons**: 8px border-radius with gradient backgrounds
- **Modals**: Centered with backdrop blur
- **Forms**: Dark inputs with blue focus states
- **Tables**: Blue header with hover effects

## 🔒 Security Features

- **Password Hashing**: SHA-256 encryption for stored passwords
- **Session Management**: 24-hour session timeout
- **CSRF Protection**: Built-in Flask security
- **Role-Based Access**: Clinician and Admin roles
- **Input Validation**: Server-side validation on all inputs
- **SQL Injection Prevention**: Parameterized queries

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Use a different port
python app.py --port 5001
```

### Database Errors
```bash
# Delete existing database and restart
rm users.db
python app.py
```

### Module Import Errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Login Issues
- Clear browser cookies
- Check username/password spelling
- Ensure account was created successfully

## 🔄 API Integration

The application can integrate with external MCP (Model Context Protocol) servers:

```python
# In app.py, the MedicalAuthorizationEngine supports:
- CopilotAIBrain - AI consultation integration
- UniversalDatabaseConnector - Cross-module data queries
- QueryIntelligenceEngine - Intelligent query routing
```

## 📚 Additional Resources

- Flask Documentation: https://flask.palletsprojects.com/
- PACS Standards: DICOM medical imaging standards
- Healthcare Integration: MCP server protocol

## 👥 User Roles

### Clinician
- View dashboard and statistics
- Search and manage patients
- Create and track pre-authorizations
- Chat with AI assistant
- View own chat history

### Administrator
- All clinician permissions
- Access to admin settings
- User management (coming soon)
- System monitoring (coming soon)

## 🚀 Future Enhancements

- [ ] Real-time WebSocket chat streaming
- [ ] Multi-language support
- [ ] Advanced data visualization
- [ ] Integration with EHR systems
- [ ] Mobile native applications
- [ ] API rate limiting
- [ ] Advanced audit logging
- [ ] Two-factor authentication
- [ ] DICOM image viewer integration
- [ ] PDF report generation

## 📝 License

Copyright © 2024. All rights reserved.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Check application logs in console

---

**Version**: 1.0.0  
**Last Updated**: January 2024  
**Status**: Production Ready ✅
