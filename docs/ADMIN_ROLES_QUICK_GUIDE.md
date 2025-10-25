# 🎭 Admin Role Management - Quick Guide

## 🔗 Access the Feature
```
URL: http://localhost:8080/admin
Tab: Click "🎭 Roles & Permissions"
```

---

## 📋 Quick Reference

### Creating a New Role

```
1. Click "+ Create Role" button (top-right)
   
2. Fill in the form:
   ├─ Role Name: "e.g., Pathologist, Lab Tech"
   ├─ Description: "Optional details about the role"
   └─ Permissions: Check the permissions this role needs
   
3. Click "Save Role"

4. Success! ✅ Role appears in the grid
```

**Permission Categories**:
- 🖼️ **Images**: View, Upload, Edit, Delete
- 📄 **Reports**: View, Create, Edit, Approve  
- 👥 **Patients**: View, Create, Edit
- ⚙️ **Admin**: Users, Roles, Audit Logs
- ☁️ **Data**: Export to Cloud, Share Studies

---

### Editing an Existing Role

```
1. Find the role card in the grid

2. Click the "✏️ Edit" button

3. Modal opens with current permissions

4. Change any field:
   ├─ Role Name
   ├─ Description
   └─ Permissions (check/uncheck as needed)

5. Click "Save Role"

6. Success! ✅ Changes saved
```

---

### Deleting a Role

```
1. Find the role card in the grid

2. Click the "🗑️ Delete" button

3. Confirmation dialog appears:
   "Are you sure you want to delete...?"

4. Click "OK" to confirm deletion
   (or "Cancel" to keep the role)

5. Success! ✅ Role removed
```

---

## 💡 Usage Examples

### Example 1: Create "Pathologist" Role
```
Name: Pathologist
Description: Medical doctor specializing in pathology

Permissions:
✓ View Images
✓ View Reports
✓ Create Reports (pathology reports)
✓ Edit Reports
✓ View Patients
✓ Export to Cloud
```

### Example 2: Create "Lab Technician" Role
```
Name: Lab Technician
Description: Laboratory technical staff

Permissions:
✓ View Images
✓ Upload Images
✓ View Patients
✓ Create Patients
```

### Example 3: Create "Report Reviewer" Role
```
Name: Report Reviewer
Description: Quality assurance reviewer

Permissions:
✓ View Images
✓ View Reports
✓ Approve Reports
✓ View Audit Logs
```

---

## 🎛️ Permission Quick Lookup

| Permission | Purpose | Typical Users |
|-----------|---------|---------------|
| View Images | Can view medical images in PACS | All clinical roles |
| Upload Images | Can upload new medical images | Technicians, Radiologists |
| Edit Images | Can modify image metadata | Radiologists, Technicians |
| Delete Images | Can delete images from system | Radiologists, Admins |
| View Reports | Can read written reports | All clinical roles |
| Create Reports | Can write new reports | Radiologists, Pathologists |
| Edit Reports | Can modify draft reports | Radiologists, Typists |
| Approve Reports | Can finalize/approve reports | Senior Radiologists, Admins |
| View Patients | Can see patient records | All clinical roles |
| Create Patients | Can add new patients | Technicians, Admins |
| Edit Patients | Can update patient info | Technicians, Admins |
| Manage Users | Can add/remove/edit users | Admins only |
| Manage Roles | Can create/edit/delete roles | Admins only |
| View Audit Logs | Can see activity logs | Admins, Compliance |
| Export to Cloud | Can backup to cloud storage | Admins, IT Staff |
| Share Studies | Can share cases with others | All clinical roles |

---

## ✨ Features

### ✅ What You Can Do
- [x] Create unlimited roles
- [x] Assign granular permissions
- [x] Edit roles anytime
- [x] Delete unused roles
- [x] See all roles at a glance
- [x] Preview permissions on cards
- [x] Quick edit/delete buttons
- [x] Confirmation dialogs for safety
- [x] Real-time updates
- [x] Error notifications

### ⚠️ Important Notes
- Only **Admins** can manage roles
- Deleting a role **cannot be undone**
- Users keep their current permissions until role is changed
- System roles may be protected from deletion
- Changes take effect immediately

---

## 🔍 Troubleshooting

### "Failed to save role" Error
**Solution**: 
- Check if you're logged in as Admin
- Verify role name doesn't already exist
- Check browser console for details

### Role doesn't appear after creation
**Solution**:
- Refresh the page (F5)
- Click the "Roles & Permissions" tab again
- Check if a success notification appeared

### Cannot delete a role
**Solution**:
- System roles cannot be deleted
- Try editing instead of deleting
- Check if users are still assigned to role

### Permissions not saving
**Solution**:
- Check internet connection
- Verify you're clicking "Save Role"
- Try again or refresh page

---

## 🆘 Support

For additional help:
1. Check the documentation in the Admin UI
2. Review the system logs
3. Contact system administrator
4. Check the troubleshooting guide

---

## 📊 Typical Workflow

```
Setup Phase:
├─ Create core roles (Admin, Radiologist, Technician)
├─ Define permissions for each role
└─ Test role-based access

Ongoing Management:
├─ Add new roles as needed
├─ Update permissions for changing needs
├─ Assign roles to users
└─ Monitor and adjust as needed

Maintenance:
├─ Remove unused roles
├─ Review role permissions quarterly
├─ Update based on user feedback
└─ Document role purpose and permissions
```

---

## 🎓 Best Practices

1. **Principle of Least Privilege**: Only grant necessary permissions
2. **Clear Naming**: Use descriptive role names (e.g., "Senior Radiologist" not "User2")
3. **Documentation**: Add detailed descriptions for each role
4. **Regular Review**: Audit roles and permissions quarterly
5. **Testing**: Test role permissions before deploying to users
6. **Backup**: Keep records of role configurations
7. **Consistency**: Use standard permission sets across roles

---

**Version**: 1.0  
**Last Updated**: 2025-10-21  
**Status**: ✅ Production Ready

