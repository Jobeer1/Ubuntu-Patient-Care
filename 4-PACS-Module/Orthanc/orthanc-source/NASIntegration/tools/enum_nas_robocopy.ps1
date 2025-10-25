param(
    [string]$NasPath = "\\155.235.81.155\Image Archiving",
    [string]$OutputFile = "nas_dicom_files_robo.txt",
    [int]$SampleLimit = 0
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$tempDir = Join-Path $scriptRoot "temp_dummy"
$fullOutputPath = Join-Path $scriptRoot $OutputFile

# Robocopy needs a destination directory, even for list-only mode.
if (-not (Test-Path $tempDir)) {
    New-Item -Path $tempDir -ItemType Directory | Out-Null
}

Write-Host "Starting fast enumeration with robocopy..."
Write-Host "Source: $NasPath"
Write-Host "Output: $fullOutputPath"

# /L      - List only.
# /S      - Subdirectories.
# /FP     - Full Pathnames.
# /NJH    - No Job Header.
# /NJS    - No Job Summary.
# /NS     - No file Sizes.
# /NC     - No file Classes.
# /NDL    - No Directory List.
# /XF     - Exclude dummy file itself
# /BYTES  - Print sizes as bytes.
# The output is redirected to the log file.
$RoboArgs = @(
    $NasPath,
    $tempDir,
    "/L", "/S", "/FP", "/NJH", "/NJS", "/NS", "/NC", "/NDL", "/XF", "$tempDir\\*", "/BYTES"
)
robocopy @RoboArgs > $fullOutputPath

# Robocopy's output includes extra whitespace which we need to trim.
$filePaths = Get-Content $fullOutputPath | ForEach-Object { $_.Trim() } | Where-Object { $_ }

if ($SampleLimit -gt 0) {
    $filePaths = $filePaths | Select-Object -First $SampleLimit
}

$filePaths | Set-Content -Path $fullOutputPath -Encoding UTF8

$fileCount = ($filePaths).Count
Write-Host "✅ Robocopy enumeration complete. Found $fileCount files."

# Clean up the temporary directory and log file
Remove-Item -Path $tempDir -Recurse -Force
Remove-Item -Path $logFile -Force
