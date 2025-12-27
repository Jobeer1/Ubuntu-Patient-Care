# 🏥 Ubuntu Patient Care - Complete Package

This folder contains **all the files needed** to get Ubuntu Patient Care working immediately on your system, including:

✅ Whisper AI model weights (speech-to-text)  
✅ Configuration templates  
✅ Automatic deployment scripts  

## 📦 Folder Structure

```
Ubuntu-Patient-Care-Complete-Package/
├── weights/
│   └── base.pt              ← Whisper AI model (138 MB)
├── secrets/
│   └── .env.template        ← Configuration template
└── setup/
    ├── deploy.ps1           ← Windows setup script
    └── deploy.sh            ← Linux/Mac setup script
```

## 🚀 Quick Setup (3 Steps)

### Step 1: Extract the Main Repository
Download and extract the main `Ubuntu-Patient-Care` repository from GitHub:
```
https://github.com/Jobeer1/Ubuntu-Patient-Care
```

### Step 2: Extract This Complete Package
Extract this folder (`Ubuntu-Patient-Care-Complete-Package`) to the **same parent directory** as the main repository.

Your folder structure should look like:
```
Desktop/
├── Ubuntu-Patient-Care/
│   ├── 1-RIS-Module/
│   ├── 2-Medical-Billing/
│   ├── 3-Dictation-Reporting/
│   ├── 4-PACS-Module/
│   ├── docs/
│   ├── README.md
│   └── ... (other files)
│
└── Ubuntu-Patient-Care-Complete-Package/  ← You are here
    ├── weights/
    ├── secrets/
    └── setup/
```

### Step 3: Run the Setup Script

#### 🪟 Windows (PowerShell)
1. Open PowerShell
2. Navigate to: `Ubuntu-Patient-Care-Complete-Package/setup/`
3. Run:
   ```powershell
   .\deploy.ps1
   ```

#### 🐧 Linux/Mac (Bash)
1. Open Terminal
2. Navigate to: `Ubuntu-Patient-Care-Complete-Package/setup/`
3. Run:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

## ✅ What the Setup Script Does

The deployment script automatically:

1. **Copies Whisper model weights** to the dictation module
   - Source: `weights/base.pt`
   - Destination: `4-PACS-Module/Orthanc/medical-reporting-module/models/whisper/base.pt`

2. **Deploys configuration template**
   - Source: `secrets/.env.template`
   - Destination: `.env` (in project root)

3. **Verifies all files** are in the correct locations

4. **Creates .env file** if it doesn't exist

## 🔧 Configure Your Credentials

After setup, edit the `.env` file in the project root with your OAuth credentials:

```env
# Microsoft Azure
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret

# Google Cloud
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**Get credentials from:**
- Microsoft Azure: https://portal.azure.com
- Google Cloud: https://console.cloud.google.com

## 🏥 Start Using Ubuntu Patient Care

After setup:

1. Navigate to project root: `Ubuntu-Patient-Care/`
2. Follow the main README.md instructions
3. Start the MCP Server on port 8080
4. Access PACS dashboard at: http://localhost:5000/login
5. Login with Google or Microsoft credentials
6. Start using all 4 modules!

## 📋 File Details

### weights/base.pt
- **Size:** 138.53 MB
- **Purpose:** OpenAI Whisper speech-to-text model
- **Destination:** Dictation/Reporting module
- **Used for:** Converting doctor voice recordings to medical reports

### secrets/.env.template
- **Contains:** Configuration template with all required variables
- **Actions:** Used as a template to create .env file
- **Note:** Replace placeholder values with real credentials

## 🆘 Troubleshooting

### "Deploy script not found"
Make sure you extracted the Complete Package folder to the same parent directory as Ubuntu-Patient-Care

### "base.pt not copied"
Run the deploy script **after** you've extracted both folders to the correct locations

### "Permission denied" (Linux/Mac)
The script needs execute permissions:
```bash
chmod +x deploy.sh
./deploy.sh
```

### ".env file not created"
The script will create it automatically. If not, you can:
```bash
cp secrets/.env.template ../.env
# Then edit the .env file with your credentials
```

## 📞 Support

**System Documentation:**
- See `README.md` in the main Ubuntu-Patient-Care folder
- Full setup guide: https://github.com/Jobeer1/Ubuntu-Patient-Care

**Credentials Issues:**
- Microsoft: https://portal.azure.com (App registrations)
- Google: https://console.cloud.google.com (OAuth)

---

**You're ready to go!** 🚀  
Run the setup script and start using Ubuntu Patient Care on your clinician team today!
