# ✅ Correct Folder Structure

## Current Workspace Structure

```
Ubuntu-Patient-Care/
│
├── 1-RIS-Module/              ✅ USE THIS (RIS Module)
│   ├── openemr/               ✅ OpenEMR EHR/EMR
│   ├── sa-ris-backend/        ✅ Backend API
│   └── sa-ris-frontend/       ✅ Frontend UI
│
├── 2-Medical-Billing/         ✅ USE THIS (Billing Module)
│   └── README.md              (References mcp-medical-server)
│
├── 3-Dictation-Reporting/     ✅ USE THIS (Reporting Module)
│   └── README.md              (References reporting components)
│
├── 4-PACS-Module/             ✅ USE THIS (PACS Module)
│   ├── offline-dicom-viewer/  ✅ Offline viewer
│   └── Orthanc/               (Duplicate - can be removed)
│
├── mcp-medical-server/        ✅ Medical billing server
├── Orthanc/                   ✅ Main PACS server
│
├── RIS/                       ❌ OLD - DO NOT USE
│   ├── sa-ris-backend/        (Duplicate - locked)
│   └── sa-ris-frontend/       (Duplicate - locked)
│
└── Medical-Billing/           ❌ OLD - DO NOT USE
    └── openemr/               (Duplicate - locked)
```

## What to Do

### Immediate Solution
**Use the correct paths with the numbers:**

```bash
# ✅ CORRECT
cd 1-RIS-Module\sa-ris-backend
npm install
npm start
```

### Long-term Solution
**Delete the old folders when possible:**

1. Close all terminals
2. Stop all Node.js processes  
3. Run: `CLEANUP_OLD_FOLDERS.bat`

## Quick Commands

### Start RIS Backend (CORRECT)
```bash
cd 1-RIS-Module\sa-ris-backend
npm install
npm start
```

### Start RIS Frontend (CORRECT)
```bash
cd 1-RIS-Module\sa-ris-frontend
npm install
npm start
```

### Start OpenEMR (CORRECT)
```bash
cd 1-RIS-Module\openemr
docker-compose up -d
```

## Or Use the Helper Script
```bash
START_RIS_CORRECTLY.bat
```

This will automatically use the correct paths!

## Why This Happened

During the reorganization:
1. Files were moved to new numbered folders
2. Old folders couldn't be deleted (processes using them)
3. You tried to use the old path by mistake

## The Fix

Simply use the **numbered folders** going forward:
- `1-RIS-Module/` instead of `RIS/`
- `2-Medical-Billing/` instead of `Medical-Billing/`

All the code, databases, and configuration are intact in the new locations!
