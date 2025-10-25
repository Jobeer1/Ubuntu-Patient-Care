# ⚠️ IMPORTANT: Use Correct Module Paths

## Problem
There are **duplicate folders** in your workspace:
- ❌ OLD: `RIS/` and `Medical-Billing/` (DO NOT USE)
- ✅ NEW: `1-RIS-Module/` and `2-Medical-Billing/` (USE THESE)

## Why This Happened
During reorganization, the old folders couldn't be deleted because they were in use by running processes.

## ✅ CORRECT PATHS TO USE

### RIS Backend
```bash
# ❌ WRONG (old path)
cd RIS\sa-ris-backend

# ✅ CORRECT (new path)
cd 1-RIS-Module\sa-ris-backend
```

### RIS Frontend
```bash
# ❌ WRONG (old path)
cd RIS\sa-ris-frontend

# ✅ CORRECT (new path)
cd 1-RIS-Module\sa-ris-frontend
```

### OpenEMR
```bash
# ❌ WRONG (old path)
cd Medical-Billing\openemr

# ✅ CORRECT (new path)
cd 1-RIS-Module\openemr
```

## How to Fix

### Option 1: Close All Processes and Delete Old Folders
1. Close all terminals and command prompts
2. Stop any running Node.js processes
3. Close VS Code or any IDE
4. Run this command:
```powershell
Remove-Item -Path "RIS" -Recurse -Force
Remove-Item -Path "Medical-Billing" -Recurse -Force
```

### Option 2: Just Use the Correct Paths
Simply use the new numbered folder paths going forward:
- `1-RIS-Module/`
- `2-Medical-Billing/`
- `3-Dictation-Reporting/`
- `4-PACS-Module/`

## Updated Startup Commands

### Start RIS Backend
```bash
cd 1-RIS-Module\sa-ris-backend
npm install
npm start
```

### Start RIS Frontend
```bash
cd 1-RIS-Module\sa-ris-frontend
npm install
npm start
```

### Start OpenEMR
```bash
cd 1-RIS-Module\openemr
docker-compose up -d
```

## Quick Reference

| Component | Correct Path |
|-----------|-------------|
| RIS Backend | `1-RIS-Module\sa-ris-backend` |
| RIS Frontend | `1-RIS-Module\sa-ris-frontend` |
| OpenEMR | `1-RIS-Module\openemr` |
| MCP Server | `mcp-medical-server` |
| Orthanc | `Orthanc` |
| Offline Viewer | `4-PACS-Module\offline-dicom-viewer` |

## Verification

Check if you're in the correct location:
```powershell
# Should show package.json
dir 1-RIS-Module\sa-ris-backend\package.json

# Should show docker-compose.yml
dir 1-RIS-Module\openemr\docker-compose.yml
```

## Why Keep Numbered Folders?

The numbered folders provide:
1. **Clear organization** - Easy to understand system structure
2. **Logical grouping** - Related components together
3. **Better documentation** - Each module has comprehensive README
4. **Future scalability** - Easy to add more modules

## Need Help?

See these files for more information:
- `MODULE_STRUCTURE.md` - Complete system architecture
- `REORGANIZATION_COMPLETE.md` - What changed and why
- `1-RIS-Module/README.md` - RIS module documentation
- `START_SYSTEM_CORRECTLY.md` - How to start all services
