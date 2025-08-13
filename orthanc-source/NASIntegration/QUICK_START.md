# 🇿🇦 South African Medical Imaging System - Quick Start

## 🏥 **NEW: Simple Orthanc PACS Management**

### **🚀 5-Minute PACS Setup**
1. **Install Orthanc** (download from orthanc-server.com)
2. **Start the system**: `python start_sa_system.py`
3. **Login as admin**: http://localhost:5000 (admin/admin123)
4. **Go to "PACS Server" tab**
5. **Click "Quick Setup & Start"** - Done! ✅

### **✨ What You Get Instantly**
- **Medical imaging server** running at http://localhost:8042
- **DICOM port** 4242 for medical devices
- **Patient sharing** with secure links
- **Mobile-friendly** interface for healthcare staff

---

## 🚀 **System Installation**

### **Option 1: Clean Install (Recommended)**
```bash
# Run the clean installer
python install_clean.py

# Start the system
python start_sa_system.py
```

### **Option 2: Manual Install**
```bash
# Install core dependencies
cd backend
pip install -r requirements-core.txt

# Optional: Install advanced features
pip install -r requirements-optional.txt

# Start the system
cd ..
python start_sa_system.py
```

## 🌐 **Access the System**

### **� PACS MFanagement (NEW)**
- **Admin Dashboard**: http://localhost:5000 → "PACS Server" tab
- **Orthanc Web Interface**: http://localhost:8042 (after setup)
- **DICOM Port**: 4242 (for medical devices)

### **📋 Other Interfaces**
- **Main Interface**: http://localhost:5000
- **System Status**: http://localhost:5000/system-status
- **User Management**: http://localhost:5000/user-management
- **NAS Configuration**: http://localhost:5000/nas-config

## 🔐 **Demo Credentials**

- **Admin**: `admin` / `admin123`
- **Doctor**: `doctor1` / `doctor123`

## � **PrACS Quick Start Guide**

### **For Healthcare Administrators:**
1. **Login** as admin at http://localhost:5000
2. **Click "PACS Server"** tab in admin dashboard
3. **Fill Quick Setup form**:
   - Hospital name: "Your Hospital Name"
   - Web port: 8042 (default)
   - DICOM port: 4242 (default)
   - AET title: "YOUR_HOSPITAL"
4. **Click "Quick Setup & Start"**
5. **Access Orthanc** at http://localhost:8042

### **For Healthcare Staff:**
1. **Open web browser** on any device (phone, tablet, computer)
2. **Go to** http://your-server:8042
3. **View patient studies** directly in browser
4. **No software installation** required

### **For Referring Doctors:**
1. **Receive secure link** from hospital admin
2. **Click link** on any device
3. **View patient images** instantly
4. **Link expires automatically** for security

## 💡 **Pro Tips**

### **PACS Management**
- **Green status** = Orthanc running perfectly
- **Red status** = Server stopped (click Start button)
- **Monitor storage** usage in dashboard
- **Create patient shares** for referring doctors

### **General System**
- Press `Ctrl+D` on login page for demo credentials
- Visit `/system-status` for comprehensive health check
- System works with core features even without optional packages
- All interfaces are mobile-responsive

## 🇿🇦 **Core Features (Always Available)**

### **🏥 PACS Server Management (NEW)**
- ✅ **One-click** Orthanc start/stop/restart
- ✅ **Real-time** server status monitoring
- ✅ **Quick setup** wizard for new installations
- ✅ **Patient sharing** with secure links
- ✅ **Doctor management** with HPCSA numbers
- ✅ **Mobile-friendly** interface

### **📋 System Management**
- ✅ User Management
- ✅ Web Interface
- ✅ Basic Authentication
- ✅ NAS Configuration
- ✅ System Monitoring

## 🎯 **Optional Features (Install requirements-optional.txt)**

- 🎤 Voice Recognition
- 🤖 AI Diagnosis
- 👁️ Face Recognition
- 🏥 Advanced DICOM Processing
- 📊 Advanced Analytics

## 🆘 **Troubleshooting**

### **PACS Server Issues**
```bash
# Check if Orthanc is installed
orthanc --version

# Check if ports are available
netstat -an | grep 8042
netstat -an | grep 4242

# Restart the management system
python start_sa_system.py
```

### **General Issues**
```bash
# Install missing dependencies
pip install -r backend/requirements-core.txt

# Install optional features
pip install -r backend/requirements-optional.txt
```

### **Port Already in Use**
- Change port in `start_sa_system.py` (line with `port=5000`)
- For Orthanc ports, use the Quick Setup form to change them

### **Can't Access Orthanc Web Interface**
1. **Check server status** in admin dashboard
2. **Click "Start Server"** if status is red
3. **Verify firewall** allows port 8042
4. **Try** http://localhost:8042 first, then your server IP

## 📞 **Support**

### **PACS Support**
- **Server status**: Admin Dashboard → PACS Server tab
- **Health check**: http://localhost:5000/api/orthanc/health-check
- **Test all features**: `python backend/test_orthanc_simple.py`

### **General Support**
- Check system status at: http://localhost:5000/system-status
- Review logs in the console output
- All warnings about optional features are normal

## 🎯 **Success Checklist**

### **✅ PACS Server Working**
- [ ] Admin dashboard shows "PACS Server" tab
- [ ] Server status shows "Online" (green)
- [ ] Can access http://localhost:8042
- [ ] Can create patient shares
- [ ] Mobile interface works on phone/tablet

### **✅ System Working**
- [ ] Can login with admin/admin123
- [ ] All dashboard tabs load
- [ ] System status shows healthy
- [ ] No critical errors in console

---

**🇿🇦 Ready to revolutionize South African healthcare with simple, practical PACS management!**

## 🏆 **What Makes This Special**

- **🚀 5-minute setup** vs. hours with complex systems
- **📱 Mobile-first** design for SA healthcare staff
- **🇿🇦 SA-specific** features (HPCSA numbers, etc.)
- **💰 Cost-effective** using free, open-source software
- **🛡️ Secure** patient sharing with automatic expiration
- **👥 User-friendly** - no technical training required