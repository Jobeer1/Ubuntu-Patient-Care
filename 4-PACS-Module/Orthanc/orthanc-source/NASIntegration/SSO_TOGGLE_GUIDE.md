# SSO Toggle Button - Visual Guide

## What You'll See

### Admin Dashboard - SSO Control Panel

When you log in as an admin, you'll see a new control panel at the top of your dashboard:

```
┌─────────────────────────────────────────────────────────────┐
│ 🔐 SSO Authentication Control                               │
│ Enable or disable Single Sign-On for all users              │
│                                                              │
│ SSO Authentication: [🟢 Enabled]    [🔒 Disable SSO]       │
└─────────────────────────────────────────────────────────────┘
```

### When SSO is Enabled (Default State)

**Dashboard Control Panel:**
```
┌─────────────────────────────────────────────────────────────┐
│ 🔐 SSO Authentication Control                               │
│ Enable or disable Single Sign-On for all users              │
│                                                              │
│ SSO Authentication: [🟢 Enabled]    [🔒 Disable SSO]       │
└─────────────────────────────────────────────────────────────┘
```

**Login Page Shows:**
- ✅ Microsoft Sign-In Button
- ✅ Google Sign-In Button
- ✅ Local Credentials Form
- Info: "✅ SSO Ready! Sign in with Microsoft, Google, or use local credentials."

### When SSO is Disabled

**Dashboard Control Panel:**
```
┌─────────────────────────────────────────────────────────────┐
│ 🔐 SSO Authentication Control                               │
│ Enable or disable Single Sign-On for all users              │
│                                                              │
│ SSO Authentication: [🔴 Disabled]   [🔓 Enable SSO]        │
└─────────────────────────────────────────────────────────────┘
```

**Login Page Shows:**
- ❌ Microsoft Sign-In Button (Hidden)
- ❌ Google Sign-In Button (Hidden)
- ✅ Local Credentials Form (Still Available)
- Warning: "⚠️ SSO Disabled: Single Sign-On is currently disabled. Please use local credentials."

## How to Use

### Step 1: Login as Admin
```
Username: admin
Password: admin
User Type: admin
```

### Step 2: Navigate to Dashboard
After successful login, you'll be on the main dashboard.

### Step 3: Locate SSO Control Panel
Look for the gold-bordered panel at the top of the page with the 🔐 icon.

### Step 4: Toggle SSO
Click the button to change SSO status:
- **To Disable**: Click "🔒 Disable SSO"
- **To Enable**: Click "🔓 Enable SSO"

### Step 5: Confirmation
You'll see a notification in the top-right corner:
```
┌────────────────────────────────┐
│ ✓ SSO disabled successfully    │
└────────────────────────────────┘
```

## Button States

### Normal State (Enabled)
```
┌──────────────────┐
│ 🔒 Disable SSO   │  ← Red gradient button
└──────────────────┘
```

### Normal State (Disabled)
```
┌──────────────────┐
│ 🔓 Enable SSO    │  ← Green gradient button
└──────────────────┘
```

### Loading State
```
┌──────────────────┐
│ ⏳ Processing... │  ← Disabled, grayed out
└──────────────────┘
```

## Color Coding

### Status Badges
- **🟢 Enabled**: Green background, dark green text
- **🔴 Disabled**: Red background, dark red text

### Toggle Buttons
- **Disable Button**: Red gradient (when SSO is enabled)
- **Enable Button**: Green gradient (when SSO is disabled)

### Notifications
- **Success**: Green background with checkmark
- **Error**: Red background with X icon
- **Info**: Blue background with info icon

## Non-Admin Users

Non-admin users will NOT see the SSO control panel. Their dashboard will look normal without any SSO controls.

## Testing Checklist

- [ ] Login as admin
- [ ] Verify SSO control panel is visible
- [ ] Check initial status (should be "Enabled")
- [ ] Click "Disable SSO" button
- [ ] Verify notification appears
- [ ] Verify status changes to "Disabled"
- [ ] Logout
- [ ] Check login page (SSO buttons should be hidden)
- [ ] Login as admin again
- [ ] Click "Enable SSO" button
- [ ] Verify notification appears
- [ ] Verify status changes to "Enabled"
- [ ] Logout
- [ ] Check login page (SSO buttons should be visible)

## Quick Reference

| Action | Button Text | Result |
|--------|-------------|--------|
| Disable SSO | 🔒 Disable SSO | Hides SSO buttons on login page |
| Enable SSO | 🔓 Enable SSO | Shows SSO buttons on login page |
| Check Status | View badge | See current SSO state |

## Notes

- Changes take effect immediately
- No server restart required
- Existing user sessions remain active
- Only affects new login attempts
- Admin can always use local credentials
