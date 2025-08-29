# Medical Reporting Module

A comprehensive, offline-first Flask application for medical image reporting, designed specifically for South African healthcare environments.

## Features

- **Offline-First Architecture**: Full functionality without internet connectivity
- **Voice Dictation**: Advanced speech-to-text with South African accent support
- **Customizable Layouts**: Drag-and-drop interface customization
- **Template Management**: Voice-activated template selection and customization
- **Seamless Integration**: Works with Orthanc DICOM servers, NAS storage, and RIS systems
- **Typist Workflow**: Quality assurance through professional typist review
- **Learning STT**: Speech-to-text that improves from corrections

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (for production) or SQLite (for development)
- Access to Orthanc DICOM server
- NAS storage (optional)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd medical-reporting-module
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
python app.py
```

6. Access the application:
```
http://localhost:5001
```

## Configuration

### Environment Variables

- `FLASK_ENV`: Set to 'production' for production deployment
- `DATABASE_URL`: Database connection string
- `ORTHANC_URL`: Orthanc DICOM server URL
- `SA_MEDICAL_SYSTEM_URL`: Main SA Medical System URL
- `NAS_MOUNT_POINT`: NAS storage mount point

### Integration Setup

1. **Orthanc Integration**: Configure Orthanc server credentials in settings
2. **NAS Storage**: Set up NAS mount point for file storage
3. **RIS Integration**: Configure RIS system endpoints (optional)
4. **Voice Engine**: Set up speech-to-text model path

## Architecture

```
medical-reporting-module/
├── app.py                      # Main Flask application
├── config/                     # Configuration files
├── core/                       # Core business logic
├── integrations/               # External system integrations
├── api/                        # REST API endpoints
├── models/                     # Data models
├── services/                   # Business services
├── utils/                      # Utility functions
├── frontend/                   # Web interface
└── tests/                      # Test suite
```

## API Endpoints

### Health Check
- `GET /health` - System health status

### Authentication
- `POST /api/auth/login` - User authentication
- `POST /api/auth/logout` - User logout
- `GET /api/auth/validate` - Validate session

### Reports
- `GET /api/reports` - List reports
- `POST /api/reports` - Create new report
- `GET /api/reports/{id}` - Get specific report
- `PUT /api/reports/{id}` - Update report
- `DELETE /api/reports/{id}` - Delete report

### Voice
- `POST /api/voice/start` - Start voice session
- `POST /api/voice/upload` - Upload voice recording
- `GET /api/voice/transcribe/{id}` - Get transcription
- `POST /api/voice/command` - Process voice command

### Templates
- `GET /api/templates` - List templates
- `POST /api/templates` - Create template
- `GET /api/templates/{id}` - Get template
- `PUT /api/templates/{id}` - Update template

### Layouts
- `GET /api/layouts` - List layouts
- `POST /api/layouts` - Save layout
- `GET /api/layouts/{id}` - Get layout
- `PUT /api/layouts/{id}` - Update layout

### Sync
- `GET /api/sync/status` - Sync status
- `POST /api/sync/trigger` - Trigger sync
- `GET /api/sync/conflicts` - List conflicts

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black .
flake8 .
```

### Database Migrations
```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade
```

## Deployment

### Docker Deployment
```bash
docker build -t medical-reporting-module .
docker run -p 5001:5001 medical-reporting-module
```

### Production Deployment
1. Set `FLASK_ENV=production`
2. Configure PostgreSQL database
3. Set up reverse proxy (nginx)
4. Configure SSL certificates
5. Set up monitoring and logging

## Integration with SA Medical System

The Medical Reporting Module integrates with the existing SA Medical System through:

1. **Authentication Bridge**: Shared authentication with main system
2. **Database Synchronization**: Seamless data sharing
3. **API Integration**: REST API communication
4. **File Storage**: Shared NAS storage access

## Offline Functionality

The module provides full offline capabilities:

- **Local Caching**: DICOM images and metadata cached locally
- **Offline Queue**: Actions queued for sync when online
- **Conflict Resolution**: Intelligent handling of data conflicts
- **Background Sync**: Automatic synchronization when connectivity returns

## Voice Features

Advanced voice dictation capabilities:

- **Real-time Transcription**: Live speech-to-text conversion
- **Voice Commands**: Template selection and navigation
- **Learning Engine**: Improves accuracy from corrections
- **SA Accent Support**: Optimized for South African English

## Support

For support and documentation:
- Check the `/docs` directory for detailed documentation
- Review the API documentation at `/api/docs`
- Contact the development team for technical support

## License

Copyright (c) 2024 SA Medical System. All rights reserved.