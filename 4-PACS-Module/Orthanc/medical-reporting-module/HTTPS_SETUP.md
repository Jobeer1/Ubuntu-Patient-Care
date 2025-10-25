# HTTPS Setup for Medical Reporting Module

## Overview
The Medical Reporting Module now runs with HTTPS support to enable microphone access for Speech-to-Text (STT) functionality. Modern browsers require HTTPS for microphone access due to security policies.

## Quick Start

1. **Install dependencies** (if needed):
   ```bash
   python install_ssl_deps.py
   ```

2. **Run the application**:
   ```bash
   python app.py
   ```

3. **Access the application**:
   - Local: https://localhost:5443
   - Network: https://[your-ip]:5443

## SSL Certificate

The application automatically generates a self-signed SSL certificate on first run:
- Certificate: `certs/cert.pem`
- Private Key: `certs/key.pem`
- Valid for: 365 days
- Includes: localhost, 127.0.0.1, and your local IP

## Browser Security Warning

When you first access the HTTPS site, you'll see a security warning because it uses a self-signed certificate. This is normal for development:

1. Click "Advanced" or "Show details"
2. Click "Proceed to localhost (unsafe)" or similar
3. The site will load and microphone access will work

## Microphone Access

With HTTPS enabled:
- ✅ Microphone access will work in all modern browsers
- ✅ Speech-to-Text functionality will be available
- ✅ Real-time voice transcription will function properly

## Port Configuration

- Default HTTPS port: 5443
- You can change this by setting the `PORT` environment variable:
  ```bash
  set PORT=8443
  python app.py
  ```

## Production Deployment

For production, replace the self-signed certificate with a proper SSL certificate from a Certificate Authority (CA) like Let's Encrypt.

## Troubleshooting

### Certificate Issues
If you encounter certificate problems:
1. Delete the `certs/` folder
2. Restart the application to regenerate certificates

### Microphone Still Not Working
1. Ensure you're accessing via HTTPS (not HTTP)
2. Check browser permissions for microphone access
3. Verify Windows privacy settings allow microphone access
4. Try refreshing the page after granting permissions

### Port Already in Use
If port 5443 is busy, the app will show an error. Change the port:
```bash
set PORT=8443
python app.py
```