param(
    [string]$NasPath = "\\155.235.81.155\Image Archiving",
    [string]$DriveLetter = "Z:",
    [string]$OutputFile = "nas_dicom_files_fast.txt",
    [int]$SampleLimit = 0
)

$ErrorActionPreference = 'Stop'

# Step 1: Map the NAS to a drive letter for faster access
Write-Host "Mapping NAS to drive $DriveLetter..."
try {
    # Check if drive is already mapped
    if (Test-Path $DriveLetter) {
        Write-Host "Drive $DriveLetter already mapped, removing..."
        net use $DriveLetter /delete /y | Out-Null
    }
    net use $DriveLetter $NasPath /persistent:no | Out-Null
    Write-Host "✅ NAS mapped successfully to $DriveLetter"
} catch {
    Write-Error "❌ Failed to map NAS: $($_.Exception.Message)"
    exit 1
}

# Step 2: Use robocopy for fast enumeration
Write-Host "Starting fast enumeration with robocopy on mapped drive..."
$RoboArgs = @(
    $DriveLetter,
    "$env:TEMP\robocopy_dummy",
    "/L", "/S", "/FP", "/NJH", "/NJS", "/NS", "/NC", "/NDL"
)
robocopy @RoboArgs > $OutputFile

# Step 3: Filter for DICOM files and limit if specified
Write-Host "Filtering DICOM files..."
$filePaths = Get-Content $OutputFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -and ($_.EndsWith('.dcm') -or $_.EndsWith('.dicom') -or $_.EndsWith('.ima') -or -not $_.Contains('.')) }

if ($SampleLimit -gt 0) {
    $filePaths = $filePaths | Select-Object -First $SampleLimit
}

$filePaths | Set-Content -Path $OutputFile -Encoding UTF8

# Step 4: Clean up
Write-Host "Cleaning up mapped drive..."
net use $DriveLetter /delete /y | Out-Null

$fileCount = ($filePaths).Count
Write-Host "✅ Fast enumeration complete. Found $fileCount DICOM files in $OutputFile."
