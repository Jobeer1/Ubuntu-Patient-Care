# SSO Admin Control Feature

## Overview
Administrators can now enable or disable Single Sign-On (SSO) authentication for all users through a simple toggle button on the dashboard.

## Features

### Admin Dashboard Control
- **Location**: Visible only to admin users on the main dashboard
- **Toggle Button**: One-click enable/disable SSO authentication
- **Real-time Status**: Shows current SSO status (Enabled/Disabled)
- **Visual Feedback**: Color-coded status badges and notifications

### How It Works

1. **Admin Login**: Log in as an admin user
2. **Dashboard Access**: Navigate to the main dashboard
3. **SSO Control Panel**: Located at the top of the dashboard (admin-only)
4. **Toggle SSO**: Click the button to enable or disable SSO

### User Experience

#### When SSO is Enabled (Default)
- Users see Microsoft and Google sign-in buttons on login page
- OAuth authentication flows work normally
- Info message: "✅ SSO Ready! Sign in with Microsoft, Google, or use local credentials."

#### When SSO is Disabled
- Microsoft and Google sign-in buttons are hidden
- Only local credential login is available
- Warning message: "⚠️ SSO Disabled: Single Sign-On is currently disabled. Please use local credentials."

## Technical Details

### Backend Implementation

**New API Endpoints:**
- `GET /api/auth/sso/status` - Get current SSO status
- `POST /api/auth/sso/toggle` - Toggle SSO (admin only)

**Configuration Storage:**
- SSO status stored in `backend/sso_config.json`
- Persists across server restarts
- Default: Enabled

**Security:**
- Admin authentication required for toggle endpoint
- Session validation on every request
- Audit logging of SSO status changes

### Frontend Implementation

**Dashboard (Admin Only):**
- SSO control panel with status display
- Toggle button with loading states
- Real-time notifications for status changes

**Login Page:**
- Dynamic SSO button visibility
- Status check on page load
- Automatic UI updates based on SSO status

## Usage Examples

### Enable SSO
```
1. Login as admin
2. Go to dashboard
3. Click "🔓 Enable SSO" button
4. Confirmation: "SSO enabled successfully"
```

### Disable SSO
```
1. Login as admin
2. Go to dashboard
3. Click "🔒 Disable SSO" button
4. Confirmation: "SSO disabled successfully"
```

## Testing

### Test as Admin
```bash
# Login credentials
Username: admin
Password: admin
User Type: admin
```

### Test SSO Toggle
1. Login as admin
2. Toggle SSO off
3. Logout and check login page (SSO buttons hidden)
4. Login as admin again
5. Toggle SSO on
6. Logout and check login page (SSO buttons visible)

## Configuration

### Environment Variables
```bash
# SSO enabled by default
SSO_ENABLED=true

# SSO config file location
SSO_CONFIG_FILE=backend/sso_config.json
```

### Manual Configuration
Edit `backend/sso_config.json`:
```json
{
  "enabled": true
}
```

## Security Considerations

1. **Admin-Only Access**: Only users with admin privileges can toggle SSO
2. **Session Validation**: All requests validate active admin session
3. **Audit Trail**: All SSO changes are logged with username and timestamp
4. **Graceful Degradation**: If SSO is disabled, local auth still works
5. **No User Disruption**: Existing sessions remain valid during toggle

## Future Enhancements

- [ ] Role-based SSO policies (enable for specific user types)
- [ ] Scheduled SSO maintenance windows
- [ ] SSO provider-specific toggles (Microsoft only, Google only)
- [ ] Email notifications to users when SSO status changes
- [ ] Audit log viewer in admin panel

## Troubleshooting

### SSO Toggle Not Visible
- Ensure you're logged in as admin user
- Check session: `user_type` should be 'admin'
- Clear browser cache and reload

### Toggle Not Working
- Check browser console for errors
- Verify admin session is active
- Check server logs for authentication errors

### SSO Buttons Still Showing After Disable
- Hard refresh the login page (Ctrl+F5)
- Clear browser cache
- Check `/api/auth/sso/status` endpoint response

## Support

For issues or questions:
1. Check server logs: `backend/logs/`
2. Verify SSO config: `backend/sso_config.json`
3. Test API endpoints directly
4. Review session data in browser DevTools
