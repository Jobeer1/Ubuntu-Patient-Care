# OpenEMR RIS - How to Run Locally 🏥

## Quick Start (Recommended)

### 1. **Install Dependencies First**
```bash
# Install server dependencies
cd openemr/server
npm install

# Install client dependencies  
cd ../client
npm install
```

### 2. **Setup Database and Demo Users**
```bash
# Run the setup script (Windows)
./FIXED_START.bat

# Or manually run these commands:
cd openemr/server
npx prisma db push
node create-demo-user.js
```

### 3. **Start the System**
Open **TWO separate terminals**:

**Terminal 1 - Backend Server:**
```bash
cd openemr/server
npm run dev
```

**Terminal 2 - Frontend Client:**
```bash
cd openemr/client
npm start
```

### 4. **Access the System**
- Open your browser and go to: **http://localhost:3000**
- Login with demo credentials:
  - **Email:** `demo@example.com`
  - **Password:** `demo123`

---

## System Features ✅

### **Fully Working Pages:**
- **Dashboard** - System overview and statistics
- **Patients** - Patient management with CRUD operations
- **Study Orders** - Radiology order management
- **Billing** - Invoice management and tracking
- **Claims** - Medical aid claims processing
- **Reports** - Generate, download, and print reports
- **Tasks** - Personal task management
- **Notes** - Note-taking system
- **Settings** - System configuration

### **All Button Functionality Fixed:**
- ✅ Create/Add buttons work with validation
- ✅ Update/Edit buttons work with confirmation
- ✅ Delete buttons work with confirmation dialogs
- ✅ View buttons open details
- ✅ Generate/Download/Print buttons functional
- ✅ Notification button shows alerts

---

## Login Credentials

### **Demo User:**
- Email: `demo@example.com`
- Password: `demo123`

### **Admin User:**
- Email: `admin@openemr.co.za`
- Password: `admin123`

---

## Technical Details

### **Tech Stack:**
- **Frontend:** React + TypeScript + Material-UI
- **Backend:** Node.js + Express + TypeScript
- **Database:** SQLite (development) / PostgreSQL (production)
- **ORM:** Prisma
- **Authentication:** JWT tokens

### **Ports:**
- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:3001
- **Database:** SQLite file (no port needed)

### **Project Structure:**
```
openemr/
├── client/          # React frontend
├── server/          # Node.js backend
├── server/prisma/   # Database schema and migrations
└── HOW_TO_RUN_LOCALLY.md
```

---

## Troubleshooting

### **If login fails:**
1. Make sure both server and client are running
2. Check that demo users exist: `cd server && node create-demo-user.js`
3. Verify server is accessible: http://localhost:3001/health

### **If buttons don't work:**
- All CRUD operations have been fixed and now work properly
- Forms include validation and user feedback
- Delete operations show confirmation dialogs

### **If ports are busy:**
- Server: Change PORT in `server/.env`
- Client: Change port when prompted or set REACT_APP_PORT

---

## Development Commands

### **Server Commands:**
```bash
cd openemr/server
npm run dev          # Start development server
npm run build        # Build for production
npx prisma studio    # Open database GUI
npx prisma db seed   # Seed database with demo data
```

### **Client Commands:**
```bash
cd openemr/client
npm start            # Start development server
npm run build        # Build for production
npm test             # Run tests
```

---

## System Status: ✅ FULLY WORKING

- ✅ Login system fixed
- ✅ All CRUD operations working
- ✅ Form validation implemented
- ✅ Button functionality restored
- ✅ User feedback and confirmations added
- ✅ Database seeded with demo data
- ✅ Authentication and authorization working

**The OpenEMR RIS system is now fully functional and ready for use!** 🎉

---

## 🚀 How to Add This Project to GitHub

### **Step 1: Prepare Your Project**
```bash
# Navigate to project root
cd openemr

# Delete node_modules (they will be recreated with npm install)
# Windows:
rmdir /s /q client\node_modules
rmdir /s /q server\node_modules

# Mac/Linux:
rm -rf client/node_modules
rm -rf server/node_modules
```

### **Step 2: Create .gitignore Files**
Create `openemr/.gitignore`:
```
# Dependencies
node_modules/
client/node_modules/
server/node_modules/

# Build outputs
client/build/
server/dist/

# Environment files
.env
.env.local
.env.production

# Database
server/dev.db
server/prisma/dev.db

# Logs
*.log
server/logs/

# OS generated files
.DS_Store
Thumbs.db
```

### **Step 3: Initialize Git Repository**
```bash
# In openemr directory
git init
git add .
git commit -m "Initial commit: OpenEMR RIS System with full CRUD functionality"
```

### **Step 4: Create GitHub Repository**
1. Go to [GitHub.com](https://github.com)
2. Click "New Repository"
3. Name it: `openemr-ris-system`
4. Description: `OpenEMR Radiology Information System - Full-stack React/Node.js application`
5. Keep it **Public** or **Private** (your choice)
6. **Don't** initialize with README (you already have one)

### **Step 5: Connect and Push to GitHub**
```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/openemr-ris-system.git
git branch -M main
git push -u origin main
```

### **Step 6: Update README for GitHub**
Add this to the top of your main README.md:
```markdown
# OpenEMR RIS - Radiology Information System

A full-stack web application for managing radiology operations including patient management, study orders, billing, and claims processing.

## 🚀 Quick Start
1. Clone the repository
2. Follow instructions in `HOW_TO_RUN_LOCALLY.md`
3. Login with demo@example.com / demo123

## ✨ Features
- Patient Management
- Study Orders & Scheduling  
- Billing & Invoicing
- Medical Aid Claims
- Reports & Analytics
- Real-time Notifications
```

### **Step 7: For Others to Use Your Project**
Anyone can now clone and run your project:
```bash
git clone https://github.com/YOUR_USERNAME/openemr-ris-system.git
cd openemr-ris-system
# Follow HOW_TO_RUN_LOCALLY.md instructions
```

---

## ⚠️ Important Notes About node_modules

### **Why We Delete node_modules:**
- **Size:** Can be 100MB+ per folder
- **Platform-specific:** Contains compiled binaries for your OS
- **Recreatable:** `npm install` rebuilds it from package.json
- **Best Practice:** Never commit node_modules to Git

### **What Happens When Deleted:**
- ✅ **Your code is safe** - only dependencies are removed
- ❌ **Project won't run** until you run `npm install`
- ✅ **Smaller repository** - faster to clone/download
- ✅ **No conflicts** - each person gets fresh dependencies

### **To Restore After Cloning:**
```bash
cd openemr/server && npm install
cd ../client && npm install
```

**The OpenEMR RIS system is now fully functional and ready for GitHub!** 🎉