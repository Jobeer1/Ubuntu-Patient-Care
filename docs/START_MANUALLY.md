# 🚀 Manual Startup Guide

**Follow these steps in order**

---

## Step 1: Open 3 PowerShell Windows

Right-click on PowerShell → "Run as Administrator" (do this 3 times)

---

## Step 2: Terminal 1 - MCP Server

```powershell
cd C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\mcp-medical-server
python server.py
```

**Wait for:**
```
✅ Database initialized
MCP Server started
```

**✅ Leave this window open!**

---

## Step 3: Terminal 2 - Backend API

```powershell
cd C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\sa-ris-backend
npm start
```

**Wait for:**
```
🚀 Backend Server running on port 3001
```

**✅ Leave this window open!**

---

## Step 4: Terminal 3 - Frontend Dev Server

```powershell
cd C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\sa-ris-frontend
npm start
```

**Wait for:**
```
Compiled successfully!
Local: http://localhost:3000
```

**Browser will open automatically!**

**✅ Leave this window open!**

---

## Step 5: Test the UI

1. **Browser opens at:** http://localhost:3000
2. **You should see:** Full SA-RIS Dashboard with sidebar
3. **Click:** "Medical Authorization" in left sidebar
4. **You should see:** Medical Authorization Panel with form

---

## ✅ Success Checklist

- [ ] Terminal 1: MCP Server running (no errors)
- [ ] Terminal 2: Backend running on port 3001
- [ ] Terminal 3: Frontend running on port 3000
- [ ] Browser shows full dashboard (not placeholder)
- [ ] Medical Authorization menu item visible
- [ ] Can click and see the form

---

## 🧪 Quick Test

**In the Medical Authorization panel:**

1. **Medical Scheme:** Select "Discovery Health"
2. **Member Number:** Type "1234567890"
3. **Patient ID:** Type "TEST-001"

**Expected result:**
- ✅ Green message: "Valid member: JOHN SMITH"
- ✅ Plan code auto-fills: "EXECUTIVE"

4. **Procedure:** Select "3011 - CT Head without contrast"

**Expected result:**
- ⚠️ Orange message: "Pre-Authorization Required"
- 💰 Cost estimate appears on right side
- Shows: Patient portion R185.00

---

## 🛑 To Stop

Press **Ctrl+C** in each terminal window (all 3)

---

## ❌ Common Issues

### Issue: "Port 3000 already in use"

**Solution:**
```powershell
netstat -ano | findstr :3000
taskkill /PID <PID_NUMBER> /F
```

### Issue: "Module not found"

**Solution:**
```powershell
cd sa-ris-frontend
npm install
```

### Issue: Still seeing placeholder page

**Problem:** You're looking at http://localhost:3001 instead of http://localhost:3000

**Solution:** Go to http://localhost:3000 (Frontend Dev Server)

---

## 📊 Port Summary

| Service | Port | URL |
|---------|------|-----|
| MCP Server | stdio | (internal) |
| Backend API | 3001 | http://localhost:3001 |
| Frontend UI | 3000 | http://localhost:3000 ← **Use this!** |

---

## 🎯 What You Should See

### At http://localhost:3000

```
┌─────────────────────────────────────────┐
│  SA-RIS Dashboard                       │
├─────────────────────────────────────────┤
│  Sidebar:                               │
│  • Dashboard                            │
│  • Medical Authorization ← Click here!  │
│  • Patients                             │
│  • Studies                              │
│                                         │
│  Main Area:                             │
│  • Statistics cards                     │
│  • Urgent cases                         │
│  • Radiologist workload                 │
└─────────────────────────────────────────┘
```

### After clicking "Medical Authorization"

```
┌─────────────────────────────────────────┐
│  Medical Scheme Authorization           │
├─────────────────────────────────────────┤
│  Form (Left):                           │
│  • Patient ID                           │
│  • Medical Scheme dropdown              │
│  • Member Number                        │
│  • Procedure selection                  │
│  • Clinical indication                  │
│                                         │
│  Info (Right):                          │
│  • Cost Estimate card                   │
│  • Pending Pre-Auths list               │
└─────────────────────────────────────────┘
```

---

**That's it! You should now see the full UI! 🎉**
