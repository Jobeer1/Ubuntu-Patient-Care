# ✅ How to Start the System Correctly

## 🚨 Important: You Need 3 Separate Terminals

The system has 3 parts that must run separately:

1. **MCP Server** (Python) - Port: stdio
2. **Backend API** (Node.js) - Port: 3001
3. **Frontend Dev Server** (React) - Port: 3000

---

## 🚀 Correct Startup Procedure

### Terminal 1: MCP Server

```powershell
cd mcp-medical-server
python server.py
```

**Expected output:**
```
Initializing database...
✅ Database initialized
MCP Server started
```

**Leave this terminal running!**

---

### Terminal 2: Backend API

```powershell
cd sa-ris-backend
npm start
```

**Expected output:**
```
🚀 Backend Server running on port 3001
🌐 API URL: http://localhost:3001
```

**Leave this terminal running!**

---

### Terminal 3: Frontend Dev Server

```powershell
cd sa-ris-frontend
npm start
```

**Expected output:**
```
Compiled successfully!

You can now view sa-ris-frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

**Browser will open automatically at http://localhost:3000**

**Leave this terminal running!**

---

## ✅ What You Should See

### In Browser (http://localhost:3000)

You should see:
- ✅ Full SA-RIS Dashboard with sidebar
- ✅ Dashboard, Medical Authorization, Patients, Studies menu items
- ✅ South African flag colors
- ✅ Statistics cards
- ✅ Urgent cases list
- ✅ Radiologist workload

### Click "Medical Authorization"

You should see:
- ✅ Medical Authorization Panel
- ✅ Form with medical scheme dropdown
- ✅ Member number input
- ✅ Procedure selection
- ✅ Cost estimate card (when filled)
- ✅ Pending pre-auths list

---

## ❌ What Went Wrong Before

You were seeing:
```
"SA-RIS Dashboard (Development)
If you see this page, the frontend build succeeded.
Replace with the real UI files when available."
```

**Why?** The backend was serving the **production build** (`sa-ris-frontend/build`) which only has a placeholder HTML file.

**Solution:** Run the **React development server** separately on port 3000.

---

## 🔧 If You See Errors

### "Module not found" errors

```powershell
cd sa-ris-frontend
npm install
```

### "Port 3000 already in use"

```powershell
# Kill the process using port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### "Cannot connect to backend"

Make sure backend is running on port 3001:
```powershell
curl http://localhost:3001/health
```

---

## 🎯 Quick Test After Startup

1. **Open:** http://localhost:3000
2. **Click:** "Medical Authorization" in sidebar
3. **Enter:**
   - Medical Scheme: Discovery Health
   - Member Number: 1234567890
   - Patient ID: TEST-001
4. **See:** Green success message "✅ Valid member: JOHN SMITH"

---

## 📝 Summary

**Wrong way (what you did):**
```
npm start in sa-ris-backend
→ Serves production build from /build folder
→ Shows placeholder page
```

**Right way (what to do):**
```
Terminal 1: python server.py (MCP)
Terminal 2: npm start (Backend)
Terminal 3: npm start (Frontend) ← This was missing!
→ React dev server on port 3000
→ Shows full UI
```

---

## 🚀 Automated Startup (Updated)

I'll create a better startup script that opens 3 terminals correctly...
