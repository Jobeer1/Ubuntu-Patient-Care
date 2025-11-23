# Admin Dashboard Guide

## 🎨 Beautiful User-Friendly Admin Interface

The MCP Server includes a **gorgeous, intuitive admin dashboard** for managing users, roles, and access controls.

---

## 🚀 Access the Dashboard

**URL:** http://localhost:8080/admin

**Requirements:**
- MCP Server running (`python run.py`)
- Modern web browser

---

## ✨ Features

### 1. User Management Tab 👥

#### View All Users
- **User statistics** at a glance
  - Total users
  - Active users
  - Radiologists count
  - Referring doctors count
- **Searchable table** with all user details
- **Real-time filtering** by name or email

#### Add New User
1. Click **"➕ Add New User"** button
2. Fill in the form:
   - **Email** (required) - User's email address
   - **Full Name** (required) - Display name
   - **Role** (required) - Select from dropdown:
     - 👑 Admin - Full system access
     - 🩺 Radiologist - Medical imaging specialist
     - 🔧 Technician - Technical staff
     - ⌨️ Typist - Report transcription
     - 👨‍⚕️ Referring Doctor - External doctor (read-only)
   - **HPCSA Number** (optional) - South African medical license
   - **Language Preference** - English, Afrikaans, Zulu, Xhosa
3. Click **"Save User"**

#### Edit Existing User
1. Find user in the table
2. Click **"Edit"** button
3. Modify role or details
4. Click **"Save User"**

#### View User Activity
1. Find user in the table
2. Click **"Audit"** button
3. See all user's actions and access history

---

### 2. Roles & Permissions Tab 🎭

View detailed information about each role:

#### 👑 Admin
- **Full system access**
- Permissions:
  - View All
  - Edit All
  - Delete All
  - Manage Users
  - View Audit Logs
  - Manage System Settings

#### 🩺 Radiologist
- **Medical imaging specialist with reporting**
- Permissions:
  - View DICOM Images
  - Create Medical Reports
  - Edit Reports
  - Approve Studies
  - View Patient Data

#### 🔧 Technician
- **Technical staff with limited access**
- Permissions:
  - View Images
  - Upload Images
  - View Assigned Studies

#### ⌨️ Typist
- **Report transcription specialist**
- Permissions:
  - View Reports
  - Edit Draft Reports
  - Transcribe Dictations

#### 👨‍⚕️ Referring Doctor
- **External doctor with read-only access**
- Permissions:
  - View Patient Studies (assigned to them)
  - View Reports

---

### 3. Audit Logs Tab 📋

**Complete compliance tracking:**

#### View All Activity
- See all user actions
- Filter by user, action, or date
- Export for compliance reports

#### Track:
- User logins/logouts
- PACS access
- Report creation/editing
- Patient data access
- Failed authentication attempts

#### Compliance Features
- **POPIA compliant** - South African data protection
- **HIPAA aligned** - Healthcare data security
- **Immutable logs** - Cannot be deleted or modified
- **Timestamp tracking** - Exact date/time of actions
- **IP address logging** - Track access location

---

## 🎯 Common Tasks

### Assign a Referring Doctor

**Scenario:** External doctor needs access to view patient studies

1. Go to **Admin Dashboard** → **Users Tab**
2. Click **"➕ Add New User"**
3. Fill in:
   - Email: `dr.external@hospital.com`
   - Name: `Dr. External Specialist`
   - Role: **👨‍⚕️ Referring Doctor**
4. Click **"Save User"**
5. Done! They can now login with Google/Microsoft SSO

**What they can do:**
- ✅ View assigned patient studies
- ✅ View radiology reports
- ❌ Cannot edit or delete anything
- ❌ Cannot access other patients' data

---

### Change User Role

**Scenario:** Technician promoted to Radiologist

1. Go to **Admin Dashboard** → **Users Tab**
2. Find the user in the table
3. Click **"Edit"** button
4. Change **Role** from "Technician" to "Radiologist"
5. Click **"Save User"**
6. Done! User now has Radiologist permissions

---

### View User Activity History

**Scenario:** Audit what a user accessed

1. Go to **Admin Dashboard** → **Users Tab**
2. Find the user in the table
3. Click **"Audit"** button
4. View complete activity history:
   - Login times
   - Studies accessed
   - Reports created
   - All actions with timestamps

---

### Search for Users

**Quick search:**
1. Go to **Users Tab**
2. Type in the search box:
   - Search by name: "Dr. Smith"
   - Search by email: "smith@clinic.org"
3. Table filters automatically

---

## 🔐 Access Control Examples

### Example 1: Radiologist Access
**User:** Dr. Sarah Johnson  
**Role:** Radiologist  
**Can do:**
- ✅ View all DICOM images in PACS
- ✅ Create and edit radiology reports
- ✅ Approve completed studies
- ✅ Access patient medical history
- ✅ Use AI dictation tools

**Cannot do:**
- ❌ Add/remove users
- ❌ Change system settings
- ❌ Delete other users' reports

---

### Example 2: Referring Doctor Access
**User:** Dr. External Specialist  
**Role:** Referring Doctor  
**Can do:**
- ✅ View studies for their referred patients only
- ✅ Read radiology reports
- ✅ Download reports (if enabled)

**Cannot do:**
- ❌ View other patients' studies
- ❌ Edit or create reports
- ❌ Access PACS upload functions
- ❌ See system audit logs

---

### Example 3: Technician Access
**User:** John Tech  
**Role:** Technician  
**Can do:**
- ✅ Upload DICOM images from modalities
- ✅ View images they uploaded
- ✅ See assigned work queue

**Cannot do:**
- ❌ Create or edit reports
- ❌ Approve studies
- ❌ Access all patient data
- ❌ View other technicians' work

---

## 📊 Dashboard Statistics

The dashboard shows real-time statistics:

### Total Users
Count of all registered users in the system

### Active Users
Users who have logged in at least once

### Radiologists
Count of users with Radiologist role

### Referring Doctors
Count of external doctors with access

---

## 🎨 User Interface Features

### Beautiful Design
- Modern, clean interface
- Color-coded roles for easy identification
- Responsive design (works on tablets)
- Intuitive navigation

### Search & Filter
- Real-time search
- Filter by name or email
- Quick access to user details

### Status Indicators
- **Active/Inactive** badges
- **Last login** timestamps
- **Role** color coding

### Modal Forms
- Clean, focused data entry
- Form validation
- Clear error messages

---

## 🔧 Technical Details

### API Integration
The dashboard uses the MCP Server REST API:
- `GET /users` - List all users
- `POST /users` - Create new user
- `PUT /users/{id}` - Update user
- `GET /audit/logs` - View audit logs
- `GET /audit/user/{id}` - User-specific logs

### Security
- All API calls go through the MCP Server
- JWT validation on backend
- No direct database access
- Audit logging of all changes

### Browser Compatibility
- Chrome (recommended)
- Firefox
- Safari
- Edge

---

## 📝 Best Practices

### User Management
1. **Use descriptive names** - "Dr. John Smith" not "jsmith"
2. **Verify email addresses** - Users login with these
3. **Assign correct roles** - Determines access permissions
4. **Add HPCSA numbers** - For South African compliance
5. **Set language preferences** - For AI dictation accuracy

### Role Assignment
1. **Start with least privilege** - Assign minimum required role
2. **Review regularly** - Audit user roles quarterly
3. **Remove inactive users** - Disable accounts no longer needed
4. **Document changes** - Note why roles were changed

### Audit Logs
1. **Review regularly** - Check for suspicious activity
2. **Export for compliance** - Keep records for audits
3. **Investigate failures** - Failed logins may indicate issues
4. **Track access patterns** - Identify unusual behavior

---

## 🆘 Troubleshooting

### Dashboard won't load
```bash
# Check server is running
curl http://localhost:8080/health

# Restart server
python run.py
```

### Can't see users
- Check browser console for errors (F12)
- Verify API endpoint: http://localhost:8080/users
- Check server logs: `tail -f logs/mcp-server.log`

### Changes not saving
- Check network tab in browser (F12)
- Verify API is responding
- Check for validation errors in form

### Search not working
- Clear browser cache
- Refresh page (Ctrl+F5)
- Check JavaScript console for errors

---

## 🎓 Video Tutorial (Coming Soon)

We're creating video tutorials for:
1. Adding your first user
2. Assigning roles and permissions
3. Viewing audit logs
4. Managing referring doctors

---

## 💡 Tips & Tricks

### Quick Actions
- **Double-click** a user row to edit
- **Use search** instead of scrolling
- **Click role badges** to filter by role (coming soon)

### Keyboard Shortcuts
- **Ctrl+F** - Focus search box
- **Esc** - Close modal
- **Enter** - Submit form

### Workflow Tips
1. **Batch add users** - Add multiple users at once
2. **Use consistent naming** - Makes searching easier
3. **Set up referring doctors first** - Before they need access
4. **Check audit logs weekly** - Stay on top of activity

---

## 📞 Need Help?

### Documentation
- **Main README:** `mcp-server/README.md`
- **API Docs:** http://localhost:8080/docs
- **Testing Guide:** `mcp-server/TESTING.md`

### Support
- Check server logs: `tail -f logs/mcp-server.log`
- View API documentation: http://localhost:8080/docs
- Test API directly: Use `/docs` interactive interface

---

## 🎉 You're Ready!

The admin dashboard makes it **easy and intuitive** to:
- ✅ Add new users in seconds
- ✅ Assign roles with one click
- ✅ Track all user activity
- ✅ Manage referring doctors
- ✅ Maintain compliance

**Start managing users now:** http://localhost:8080/admin

---

**Version:** 1.0.0  
**Last Updated:** October 18, 2025  
**Status:** Production Ready ✅
