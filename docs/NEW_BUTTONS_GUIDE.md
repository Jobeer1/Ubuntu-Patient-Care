# Quick Guide: New Dashboard Buttons

## 🎯 Where to Find the New Buttons

### Main Dashboard (http://localhost:3000)

When you open the RIS Dashboard, you'll see a new **"Quick Actions"** panel right below the welcome header:

```
┌────────────────────────────────────────────────────────────┐
│  Welcome back, Admin!                                      │
│  South African Radiology Information System Dashboard      │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Quick Actions                                             │
├──────────────┬──────────────┬──────────────┬──────────────┤
│              │              │              │              │
│  👤 Register │  🔍 Advanced │  💳 Benefits │  🛡️ Auth    │
│    Patient   │    Search    │    Check     │   Request    │
│              │              │              │              │
│  [BLUE BTN]  │  [WHITE BTN] │  [WHITE BTN] │  [WHITE BTN] │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

## 📋 Button Functions

### 1. 👤 Register Patient (Blue Button)
**What it does**: Opens a form to register a new patient

**When to use**: 
- New patient arrives
- Need to add patient to system
- Before scheduling appointment

**What you'll enter**:
- First Name & Last Name
- SA ID Number
- Date of Birth
- Gender
- Phone Number
- Email (optional)
- Address
- Medical Aid (Discovery, Momentum, etc.)
- Medical Aid Number

---

### 2. 🔍 Advanced Search (White Button)
**What it does**: Search for existing patients using multiple criteria

**When to use**:
- Looking for a specific patient
- Can't remember exact patient ID
- Need to find patient by phone or medical aid number

**Search by**:
- First Name
- Last Name
- SA ID Number
- Medical Aid Number
- Phone Number
- Date of Birth

**Note**: Uses the same database as NAS integration!

---

### 3. 💳 Benefits Check (Green Border Button)
**What it does**: Verify patient's medical aid benefits

**When to use**:
- Before scheduling procedure
- To check if benefits are available
- Verify medical aid status

**What you'll enter**:
- Member Number
- Medical Scheme (dropdown)
- ID Number (optional)

**Result shows**:
- Member name
- Scheme name
- Status (Active/Inactive)
- Benefits available (Yes/No)

---

### 4. 🛡️ Authorization Request (Purple Border Button)
**What it does**: Submit pre-authorization request to medical aid

**When to use**:
- Before expensive procedures
- When medical aid requires pre-auth
- For CT, MRI, or specialized imaging

**What you'll enter**:
- Patient ID
- Member Number
- Medical Scheme
- Procedure Code (NRPL)
- Clinical Indication (why needed)
- ICD-10 Codes (diagnosis)
- Urgency (Routine/Urgent/Emergency)

**Result**:
- Request ID for tracking
- Status (Submitted)
- Notification when processed

---

## 🔔 Notification Settings (In Appointments)

### Where: Appointment Scheduling Page
**Button**: "Notification Settings" (next to "New Appointment")

### What it does:
Configure automatic notifications to patients

### Options:

**Notification Channels**:
- ✅ SMS (Recommended)
- ✅ Email
- ✅ WhatsApp (New!)

**Reminder Times**:
- 7 days before
- 3 days before
- 24 hours before
- 2 hours before
- 30 minutes before

**Automation**:
- Auto-send confirmation after booking
- Auto-send reminders
- Allow patient rescheduling via link

---

## 🚀 Quick Start Workflow

### Scenario 1: New Patient Appointment
1. Click **"Register Patient"**
2. Fill in patient details
3. Click **"Benefits Check"** (if has medical aid)
4. Go to **Appointments** tab
5. Click **"New Appointment"**
6. Notifications sent automatically!

### Scenario 2: Find Existing Patient
1. Click **"Advanced Search"**
2. Enter any known detail (name, ID, phone)
3. Click **"Search Patients"**
4. View results in Patient Management

### Scenario 3: Request Authorization
1. Click **"Authorization Request"**
2. Enter patient and procedure details
3. Add clinical indication
4. Submit request
5. Track using Request ID

---

## 💡 Tips

### For Patient Registration
- SA ID number auto-validates format
- Medical aid is optional
- All contact info helps with notifications

### For Advanced Search
- Can search with partial information
- Multiple fields narrow results
- Same database as NAS = no duplicates

### For Benefits Check
- Do this BEFORE scheduling
- Saves time and prevents issues
- Shows real-time status

### For Authorization Requests
- Include detailed clinical indication
- Add all relevant ICD-10 codes
- Mark urgency correctly
- Keep Request ID for follow-up

### For Notifications
- Enable SMS for best delivery
- Set multiple reminders
- Test with one appointment first
- Patients can reschedule via link

---

## 🎨 Visual Indicators

### Button Colors
- **Blue** = Primary action (Register Patient)
- **White with Blue Border** = Search/Query
- **White with Green Border** = Verification
- **White with Purple Border** = Authorization

### Status Tags
- **Green** = Active/Confirmed
- **Orange** = Pending/Scheduled
- **Red** = Urgent/Critical
- **Blue** = Information

---

## ❓ Troubleshooting

### Button doesn't respond
- Check backend is running (port 3001)
- Refresh the page
- Check browser console for errors

### Form won't submit
- Fill all required fields (marked with *)
- Check date formats
- Verify ID number format

### Search returns no results
- Try fewer search criteria
- Check spelling
- Try different field (phone vs name)

### Notifications not sending
- Check notification settings saved
- Verify patient has contact info
- Check notification channels enabled

---

## 📞 Need Help?

- **Documentation**: See `DASHBOARD_ENHANCEMENTS_COMPLETE.md`
- **System Guide**: See `MODULE_STRUCTURE.md`
- **API Details**: See `1-RIS-Module/README.md`

---

## ✅ Summary

**4 New Buttons on Dashboard**:
1. Register Patient
2. Advanced Search  
3. Benefits Check
4. Authorization Request

**Plus**: Notification Settings in Appointments

**All working and ready to use!** 🎉
