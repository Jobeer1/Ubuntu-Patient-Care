$ErrorActionPreference = 'SilentlyContinue'

# RIS Module files
$risFiles = @(
    "QUICK_START_RIS.md",
    "RIS_COMPLETE_FEATURES.md",
    "RIS_FRONTEND_FIXES.md",
    "RIS_FRONTEND_REDESIGN.md",
    "RIS_TRANSFORMATION_SUMMARY.md",
    "START_YOUR_COMPLETE_RIS.md"
)

# PACS Module files  
$pacsFiles = @(
    "PATIENT_IMAGE_ACCESS_PLAN.md",
    "PATIENT_RECOGNITION_SYSTEM.md",
    "PATIENT_ACCESS_IMPLEMENTATION_TASKS.md",
    "PATIENT_ACCESS_QUICK_START.md",
    "PATIENT_ACCESS_SUMMARY.md"
)

# OAuth/Auth files -> docs/
$authFiles = @(
    "OAUTH_COMPLETE_SUMMARY.md",
    "OAUTH_FLOW_DIAGRAM.md",
    "OAUTH_IMPLEMENTATION_SUMMARY.md",
    "OAUTH_INDEX.md",
    "OAUTH_LOGIN_PAGE_PREVIEW.md",
    "OAUTH_QUICK_START.md",
    "OAUTH_SETUP_GUIDE.md",
    "README_OAUTH.md",
    "README_MEDICAL_AUTH.md",
    "QUICK_START_MCP_AUTH.md",
    "MCP_EXECUTIVE_SUMMARY.md",
    "MCP_INTEGRATION_COMPLETE.md",
    "MCP_INTEGRATION_FIXED.md",
    "MCP_LOGIN_INTEGRATION_GUIDE.md",
    "MCP_MOCK_IMPLEMENTATION.md",
    "MCP_SECURITY_AND_AUTH_SOLUTION.md",
    "MCP_SERVER_PLAN.md",
    "MCP_SSO_FIXED.md",
    "SESSION_COMPLETE_SUMMARY.md",
    "SESSION_FIX.md",
    "SESSION_REFACTORING_SUMMARY.md",
    "SESSION_SUMMARY_ERROR_FIXES.md",
    "SECRET_KEY_FIX.md",
    "ADMIN_ROLES_QUICK_GUIDE.md",
    "ROLES_MANAGEMENT_IMPLEMENTATION.md",
    "TEST_MEDICAL_AUTH_UI.md"
)

# OneDrive/Cloud files -> docs/
$cloudFiles = @(
    "ONEDRIVE_COMPLETE.md",
    "ONEDRIVE_FIX_SUMMARY.md",
    "ONEDRIVE_FLOW_DIAGRAM.md",
    "ONEDRIVE_READY_TO_USE.md",
    "ONEDRIVE_SETUP_GUIDE.md",
    "ONEDRIVE_VISUAL_GUIDE.md",
    "QUICK_FIX_ONEDRIVE.md",
    "CLOUD_STORAGE_COMPLETE.md",
    "CLOUD_STORAGE_READY.md",
    "CLOUD_STORAGE_VISUAL.md",
    "COMPLETE_ONEDRIVE_SETUP.md",
    "AZURE_SECRET_VISUAL_GUIDE.md",
    "GOOGLE_DRIVE_SETUP.md",
    "GOOGLE_OAUTH_EXPLAINED.md"
)

# General/Infrastructure files -> docs/
$generalFiles = @(
    "README_INTEGRATION.md",
    "README_THIS_SESSION.md",
    "SYSTEM_ARCHITECTURE.md",
    "SYSTEM_ARCHITECTURE_SPRINT3.md",
    "MODULE_STRUCTURE.md",
    "ARCHITECTURE_DIAGRAM.md",
    "COMMAND_REFERENCE.md",
    "QUICK_REFERENCE.md",
    "RUNNING.md",
    "START_MANUALLY.md",
    "START_SYSTEM_CORRECTLY.md",
    "START_MEDICAL_AUTH_SYSTEM.ps1",
    "HTML_UPDATE_GUIDE.md",
    "NEW_BUTTONS_GUIDE.md",
    "NEW_DASHBOARD_GUIDE.md",
    "IMPLEMENTATION_CHECKLIST.md",
    "IMPLEMENTATION_PROGRESS.md",
    "ACTION_CHECKLIST.md",
    "CRITICAL_TASKS_ROADMAP.md",
    "NEXT_STEPS_DECISION.md",
    "USE_CORRECT_PATHS.md",
    "TESTING_GUIDE.md",
    "TESTING_VERIFICATION_GUIDE.md",
    "VISUAL_GUIDE.md",
    "VISUAL_IMPLEMENTATION_SUMMARY.txt",
    "VISUAL_REFACTORING_SUMMARY.md",
    "DASHBOARD_ENHANCEMENTS_COMPLETE.md",
    "DOCUMENTATION_INDEX.md",
    "MAIN_README_UPDATE_SUMMARY.md",
    "GITHUB_PUSH_SUMMARY.md",
    "PUSH_FIX_TO_GITHUB_NOW.md",
    "REFACTORING_COMPLETE.md",
    "REFACTORING_QUICK_START.md",
    "REFACTORING_STATUS_FINAL.md",
    "REORGANIZATION_COMPLETE.md",
    "SOLUTION_DELIVERED.md",
    "PROJECT_COMPLETE.md",
    "INTEGRATION_COMPLETE.md",
    "ALL_INTEGRATIONS_COMPLETE.md",
    "FINALLY_WORKING.md",
    "FRONTEND_FIXED.md",
    "BLANK_SCREEN_FIXED.md",
    "FINAL_FIX_RESTART_REQUIRED.md",
    "FOLDER_STRUCTURE_FIXED.md",
    "FRONTEND_BACKEND_ERROR_FIXES.md",
    "LOGIN_FIX_SUMMARY.md",
    "ACTUAL_FIX_SAMESITE_LAX.md",
    "CRITICAL_USER_FIXES.md",
    "EXECUTIVE_SUMMARY_ERROR_FIXES.md",
    "WHAT_WENT_WRONG.md",
    "COMPLETE_STATUS_REPORT.md",
    "DEV2_COMPLETE_ALL_PROJECTS.md",
    "DEV2_DOCUMENTATION_INDEX.md",
    "DEV2_STATUS_SUMMARY_OCT23.md",
    "SPRINT_3_COMPLETION_REPORT.md",
    "SPRINT_3_DOCUMENTATION_INDEX.md",
    "SPRINT_3_KICKOFF.md",
    "SPRINT_3_FINAL_SUMMARY.txt",
    "SPRINT_3_VISUAL_SUMMARY.txt",
    "TASK_3_QUICK_REFERENCE.md",
    "TASK_4_COMPLETE_SUMMARY.md",
    "UbuntuPatientSorg_Plan.md"
)

# Create docs directory if it doesn't exist
if (-not (Test-Path "docs")) {
    New-Item -ItemType Directory -Name "docs" -Force | Out-Null
    Write-Host "Created docs/ folder"
}

# Move RIS files
Write-Host "Moving RIS files..."
foreach ($file in $risFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "1-RIS-Module/" -Force -ErrorAction SilentlyContinue
        Write-Host "  Moved $file"
    }
}

# Move PACS files
Write-Host "Moving PACS files..."
foreach ($file in $pacsFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "4-PACS-Module/" -Force -ErrorAction SilentlyContinue
        Write-Host "  Moved $file"
    }
}

# Move Auth files to docs/
Write-Host "Moving Auth files to docs/..."
foreach ($file in $authFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "docs/" -Force -ErrorAction SilentlyContinue
        Write-Host "  Moved $file"
    }
}

# Move Cloud files to docs/
Write-Host "Moving Cloud/OneDrive files to docs/..."
foreach ($file in $cloudFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "docs/" -Force -ErrorAction SilentlyContinue
        Write-Host "  Moved $file"
    }
}

# Move General files to docs/
Write-Host "Moving General/Infrastructure files to docs/..."
foreach ($file in $generalFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "docs/" -Force -ErrorAction SilentlyContinue
        Write-Host "  Moved $file"
    }
}

Write-Host "`nFile movement complete!"
Write-Host "Remaining .md files in root:"
Get-ChildItem -File -Filter "*.md" | Select-Object Name
