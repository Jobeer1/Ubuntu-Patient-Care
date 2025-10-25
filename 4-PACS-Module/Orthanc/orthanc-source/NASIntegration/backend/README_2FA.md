# Orthanc 2FA Integration

This module provides configurable Two-Factor Authentication (2FA) for the Orthanc NAS integration system. It allows administrators to enforce 2FA for admin users, regular users, or both, with support for multiple authentication methods.

## Features

- **Configurable 2FA Requirements**: Admin can enable/disable 2FA system-wide and set requirements per user role
- **Multiple Authentication Methods**:
  - TOTP (Time-based One-Time Password) - Compatible with Google Authenticator, Authy, etc.
  - Backup Codes - Static codes for emergency access
  - SMS (placeholder for future implementation)
  - Email (placeholder for future implementation)
- **Security Features**:
  - Failed attempt tracking and account lockout
  - Session timeout for 2FA verification
  - Secure backup code generation and storage
- **Admin Dashboard**: Statistics and user management for 2FA
- **Seamless Integration**: Works with existing authentication system

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Copy the configuration example:
```bash
cp config_example.py config.py
```

3. Edit `config.py` to match your environment settings.

## Quick Start

### 1. Initialize the Flask Application

```python
from flask import Flask
from orthanc_2fa_integration import create_2fa_middleware

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Initialize 2FA integration
two_factor_integration = create_2fa_middleware(app)

# Your existing routes...
```

### 2. Enable 2FA System-Wide

```python
# Via API call (admin only)
POST /api/2fa/config
{
    "enabled": true,
    "required_for_admin": true,
    "required_for_users": false
}
```

### 3. User 2FA Setup Flow

1. **Setup TOTP**:
   ```bash
   POST /api/2fa/setup/totp
   # Returns QR code and manual entry key
   ```

2. **Verify Setup**:
   ```bash
   POST /api/2fa/setup/totp/verify
   {
       "code": "123456"
   }
   ```

3. **Generate Backup Codes**:
   ```bash
   POST /api/2fa/backup-codes/generate
   # Returns 10 backup codes
   ```

### 4. Authentication Flow

1. **Regular Login**:
   ```bash
   POST /api/login
   {
       "username": "admin",
       "password": "password"
   }
   # Returns 2fa_requirements in response
   ```

2. **2FA Verification** (if required):
   ```bash
   POST /api/2fa/verify
   {
       "code": "123456",
       "method": "totp"
   }
   ```

## API Endpoints

### Configuration (Admin Only)

- `GET /api/2fa/config` - Get current 2FA configuration
- `POST /api/2fa/config` - Update 2FA configuration

### User Setup

- `POST /api/2fa/setup/totp` - Setup TOTP for current user
- `POST /api/2fa/setup/totp/verify` - Verify TOTP setup
- `POST /api/2fa/backup-codes/generate` - Generate backup codes
- `GET /api/2fa/status` - Get user's 2FA status

### Authentication

- `POST /api/2fa/verify` - Verify 2FA code
- `POST /api/2fa/disable` - Disable 2FA for current user

### Admin Management

- `POST /api/2fa/admin/disable-user` - Disable 2FA for any user
- `GET /api/2fa/admin/stats` - Get 2FA usage statistics
- `GET /api/2fa/admin/users` - Get 2FA status for all users

## Configuration Options

```python
TWO_FACTOR_CONFIG = {
    'enabled': False,                    # Enable/disable 2FA system-wide
    'required_for_admin': True,          # Require 2FA for admin users
    'required_for_users': False,         # Require 2FA for regular users
    'allowed_methods': ['totp', 'backup_codes'],  # Available methods
    'totp_issuer': 'Orthanc NAS',       # Name in authenticator apps
    'code_validity_seconds': 300,        # Code validity (5 minutes)
    'backup_codes_count': 10,           # Number of backup codes
    'max_failed_attempts': 3,           # Max failures before lockout
    'lockout_duration_minutes': 15      # Lockout duration
}
```

## Integration with Existing Code

### Protect Routes with 2FA

```python
@app.route('/api/admin/sensitive-action', methods=['POST'])
@two_factor_integration.require_2fa
def sensitive_admin_action():
    # This route now requires 2FA if enabled for admin users
    return jsonify({'success': True})
```

### Check 2FA Requirements

```python
user_id = session.get('user_id')
user_role = session.get('role')
requirements = two_factor_integration.get_user_2fa_requirements(user_id, user_role)

if requirements['needs_setup']:
    # Redirect user to 2FA setup
    pass
elif requirements['needs_verification']:
    # Redirect user to 2FA verification
    pass
```

## Database Schema

The system creates three tables:

1. **user_2fa**: Stores user 2FA settings and secrets
2. **auth_attempts**: Tracks authentication attempts for security
3. **system_2fa_config**: Stores system-wide 2FA configuration

## Security Considerations

1. **Secret Storage**: TOTP secrets are stored securely in the database
2. **Backup Codes**: Stored as SHA-256 hashes and consumed after use
3. **Rate Limiting**: Failed attempts are tracked and users are locked out
4. **Session Management**: 2FA verification expires after 8 hours
5. **Audit Trail**: All authentication attempts are logged

## Frontend Integration

The system provides JSON responses that can be easily integrated with any frontend:

```javascript
// Check if 2FA is required after login
const loginResponse = await fetch('/api/login', {
    method: 'POST',
    body: JSON.stringify({username, password})
});

const data = await loginResponse.json();
if (data['2fa_requirements']?.needs_setup) {
    // Redirect to 2FA setup page
} else if (data['2fa_requirements']?.needs_verification) {
    // Redirect to 2FA verification page
}
```

## Testing

Run the application in development mode:

```bash
python app.py
```

Test endpoints with curl:

```bash
# Enable 2FA (as admin)
curl -X POST http://localhost:5000/api/2fa/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "required_for_admin": true}'

# Setup TOTP
curl -X POST http://localhost:5000/api/2fa/setup/totp \
  -H "Content-Type: application/json"
```

## Troubleshooting

### Common Issues

1. **QR Code Not Displaying**: Check that Pillow is installed correctly
2. **TOTP Codes Not Working**: Verify system time is synchronized
3. **Session Issues**: Ensure Flask secret key is set and consistent
4. **Database Errors**: Check database permissions and path

### Debug Mode

Enable debug logging by setting `LOG_LEVEL = 'DEBUG'` in config.py.

## Future Enhancements

- SMS integration with Twilio/AWS SNS
- Email-based 2FA codes
- Hardware token support (FIDO2/WebAuthn)
- Integration with LDAP/Active Directory
- Mobile app push notifications

## License

This module is part of the Orthanc NAS integration project and follows the same licensing terms.