# OHIF Integration Setup Guide for SA Medical Imaging

## Overview

This guide explains how to integrate OHIF (Open Health Imaging Foundation) viewer for referring doctors in the South African Medical Imaging system.

## Why OHIF for Referring Doctors?

### ✅ **Advantages**
- **Medical-grade quality** - FDA cleared, used in hospitals worldwide
- **Zero-footprint** - Pure web-based, no installation required
- **Mobile-responsive** - Works perfectly on tablets and phones
- **Extensible** - Plugin architecture for SA customizations
- **Active development** - Large community, regular updates
- **DICOM compliance** - Full DICOM Web (DICOMweb) support

### 🇿🇦 **SA-Specific Optimizations**
- Network optimization for 3G/4G conditions
- Offline caching for unreliable connections
- Multi-language support (English, Afrikaans, isiZulu)
- HPCSA and POPIA compliance features
- Integration with secure link sharing system

## Installation Steps

### 1. Install OHIF Dependencies

```bash
cd orthanc-source/NASIntegration/web_viewer/ohif-integration

# Install OHIF core packages
npm install @ohif/core@3.7.0
npm install @ohif/viewer@3.7.0
npm install @ohif/extension-default@3.7.0
npm install @ohif/extension-cornerstone@3.7.0
npm install @ohif/extension-measurement-tracking@3.7.0
npm install @ohif/mode-longitudinal@3.7.0

# Install additional dependencies for SA optimizations
npm install react@18.2.0
npm install react-dom@18.2.0
npm install cornerstone-core@2.6.1
npm install cornerstone-tools@6.0.10
npm install dicom-parser@1.8.21
```

### 2. Configure OHIF for SA Medical Standards

Create the main configuration file:

```javascript
// ohif-config.js
import { createSAOHIFConfig } from './ohif-sa-config.js';

const config = createSAOHIFConfig({
    isReferringDoctor: true,
    isLowBandwidth: navigator.connection?.effectiveType === '2g' || navigator.connection?.effectiveType === '3g',
    isMobile: /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
    language: 'en-ZA'
});

export default config;
```

### 3. Set Up Data Sources

Configure DICOM Web endpoints for secure access:

```javascript
// data-sources.js
export const setupSADataSources = (secureToken) => {
    const baseURL = window.location.origin;
    
    return [
        {
            sourceName: 'sa-medical-dicomweb',
            type: 'dicomweb',
            wadoUriRoot: `${baseURL}/api/secure-dicom/wado`,
            qidoRoot: `${baseURL}/api/secure-dicom/qido`,
            wadoRoot: `${baseURL}/api/secure-dicom/wado`,
            
            requestOptions: {
                headers: {
                    'Authorization': `Bearer ${secureToken}`,
                    'X-SA-Referring-Doctor': 'true'
                }
            }
        }
    ];
};
```

### 4. Create Referring Doctor Entry Point

```javascript
// referring-doctor-app.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import ReferringDoctorViewer from './ReferringDoctorViewer.jsx';

const App = () => {
    // Extract parameters from URL
    const urlParams = new URLSearchParams(window.location.search);
    const studyUID = urlParams.get('study');
    const token = urlParams.get('token');
    const doctorInfo = JSON.parse(urlParams.get('doctor') || '{}');

    return (
        <BrowserRouter>
            <ReferringDoctorViewer
                studyInstanceUID={studyUID}
                secureToken={token}
                referringDoctorInfo={doctorInfo}
            />
        </BrowserRouter>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
```

### 5. Backend Integration

Add secure endpoints for DICOM Web access:

```python
# backend/secure_dicom_endpoints.py
from flask import Blueprint, request, jsonify, Response
from .secure_link_sharing import verify_secure_token
from .orthanc_connector import OrthancConnector

secure_dicom_bp = Blueprint('secure_dicom', __name__)

@secure_dicom_bp.route('/api/secure-dicom/studies/<study_uid>')
def get_secure_study(study_uid):
    """Get study metadata for referring doctor"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # Verify secure token
    token_data = verify_secure_token(token)
    if not token_data or not token_data.get('referring_doctor'):
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    # Get study from Orthanc
    orthanc = OrthancConnector()
    study_data = orthanc.get_study(study_uid)
    
    # Log access for audit
    log_referring_doctor_access(token_data, study_uid)
    
    return jsonify(study_data)

@secure_dicom_bp.route('/api/secure-dicom/wado')
def wado_proxy():
    """WADO proxy for secure image access"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # Verify token and proxy to Orthanc
    token_data = verify_secure_token(token)
    if not token_data:
        return jsonify({'error': 'Invalid token'}), 401
    
    # Proxy request to Orthanc WADO
    orthanc_url = f"http://localhost:8042/wado?{request.query_string.decode()}"
    response = requests.get(orthanc_url)
    
    return Response(
        response.content,
        status=response.status_code,
        headers=dict(response.headers)
    )
```

## Usage Examples

### 1. Generate Secure Link for Referring Doctor

```python
# Generate secure viewing link
from .secure_link_sharing import generate_secure_link

link_data = generate_secure_link(
    study_uid='1.2.3.4.5.6.7.8.9',
    referring_doctor={
        'name': 'Dr. John Smith',
        'practice': 'Cape Town Family Practice',
        'hpcsa_number': 'MP123456'
    },
    expires_in_hours=48
)

# Create viewer URL
viewer_url = f"https://your-domain.co.za/referring-viewer?study={study_uid}&token={link_data['token']}&doctor={json.dumps(doctor_info)}"
```

### 2. Send Link to Referring Doctor

```python
# Email integration
from .email_service import send_secure_link_email

send_secure_link_email(
    to_email='doctor@practice.co.za',
    doctor_name='Dr. John Smith',
    patient_name='Jane Doe',
    study_description='Chest X-Ray',
    viewer_url=viewer_url,
    expires_at=link_data['expires_at']
)
```

### 3. Mobile-Optimized Access

The viewer automatically detects mobile devices and applies optimizations:

- Touch-friendly interface
- Gesture controls (pinch-to-zoom, pan, swipe)
- Simplified toolbar for small screens
- Network-aware image loading
- Offline caching for poor connectivity

## SA-Specific Features

### 1. HPCSA Compliance
- Complete audit logging of all access
- Patient privacy protection
- Secure data transmission
- Access control and authentication

### 2. POPIA Compliance
- Data minimization (only necessary data shared)
- Consent management
- Right to erasure
- Data protection measures

### 3. Network Optimizations
- Adaptive image quality based on connection speed
- Progressive image loading
- Intelligent caching
- Offline viewing capabilities

### 4. Multi-Language Support
- English (South African)
- Afrikaans
- isiZulu
- Extensible for additional languages

## Deployment

### 1. Build for Production

```bash
# Build OHIF viewer
npm run build:ohif-sa

# Copy built files to web server
cp -r dist/* /var/www/html/referring-viewer/
```

### 2. Configure Web Server

```nginx
# Nginx configuration
server {
    listen 443 ssl;
    server_name your-domain.co.za;
    
    location /referring-viewer {
        root /var/www/html;
        try_files $uri $uri/ /referring-viewer/index.html;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
    }
    
    location /api/secure-dicom {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. SSL Certificate

```bash
# Install SSL certificate for secure access
certbot --nginx -d your-domain.co.za
```

## Testing

### 1. Unit Tests

```javascript
// tests/referring-doctor-viewer.test.js
import { render, screen } from '@testing-library/react';
import ReferringDoctorViewer from '../ReferringDoctorViewer.jsx';

test('renders referring doctor viewer', () => {
    render(
        <ReferringDoctorViewer
            studyInstanceUID="1.2.3.4.5"
            secureToken="test-token"
            referringDoctorInfo={{ name: 'Dr. Test' }}
        />
    );
    
    expect(screen.getByText('SA Medical Imaging')).toBeInTheDocument();
});
```

### 2. Integration Tests

```python
# tests/test_secure_dicom_endpoints.py
def test_secure_study_access():
    """Test secure study access for referring doctors"""
    token = generate_test_token(referring_doctor=True)
    
    response = client.get(
        '/api/secure-dicom/studies/1.2.3.4.5',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    assert response.status_code == 200
    assert 'studyInstanceUID' in response.json
```

## Monitoring and Analytics

### 1. Usage Analytics

```python
# Track referring doctor usage
@secure_dicom_bp.after_request
def log_usage(response):
    if request.headers.get('X-SA-Referring-Doctor'):
        log_referring_doctor_usage({
            'doctor_info': get_doctor_from_token(),
            'study_uid': request.view_args.get('study_uid'),
            'action': request.endpoint,
            'timestamp': datetime.utcnow(),
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string
        })
    return response
```

### 2. Performance Monitoring

```javascript
// Monitor OHIF performance
const performanceObserver = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
        if (entry.name.includes('dicom-load')) {
            // Send performance metrics to analytics
            sendAnalytics('dicom-load-time', {
                duration: entry.duration,
                networkType: navigator.connection?.effectiveType,
                isMobile: /Mobile/.test(navigator.userAgent)
            });
        }
    }
});

performanceObserver.observe({ entryTypes: ['measure'] });
```

## Support and Maintenance

### 1. Update OHIF

```bash
# Update to latest OHIF version
npm update @ohif/viewer @ohif/core
npm run build:ohif-sa
```

### 2. Monitor Logs

```bash
# Monitor referring doctor access logs
tail -f /var/log/sa-medical/referring-doctor-access.log
```

### 3. Backup Configuration

```bash
# Backup OHIF configuration
cp ohif-sa-config.js /backup/ohif-config-$(date +%Y%m%d).js
```

This OHIF integration provides a world-class, web-based DICOM viewer specifically optimized for South African referring doctors, with full compliance to local medical standards and network conditions.