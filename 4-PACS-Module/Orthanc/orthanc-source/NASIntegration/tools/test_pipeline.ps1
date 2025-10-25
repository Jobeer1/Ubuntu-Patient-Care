$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
cd $scriptRoot

Write-Host "--- E2E Test: Fast Indexing Pipeline ---"
Write-Host "Script running from: $scriptRoot"

# --- Step 1: Fast File Enumeration (Sample of 200) ---
Write-Host "[1/3] Starting fast file enumeration from NAS..."
$fileListPath = Join-Path $scriptRoot "nas_dicom_files_sample.txt"
$nasPath = "\\155.235.81.155\Image Archiving"

try {
    $stopwatchEnum = [System.Diagnostics.Stopwatch]::StartNew()
    Get-ChildItem -Path $nasPath -Recurse -File -ErrorAction Stop |
        Where-Object { $_.Extension -in @('.dcm', '.dicom', '.ima') -or [string]::IsNullOrEmpty($_.Extension) } |
        Select-Object -First 200 |
        Select-Object -ExpandProperty FullName |
        Set-Content -Path $fileListPath -Encoding UTF8
    $stopwatchEnum.Stop()
    
    $fileCount = (Get-Content $fileListPath).Count
    Write-Host "✅ [1/3] Success! Enumerated $fileCount files in $($stopwatchEnum.Elapsed.TotalSeconds.ToString('F2'))s."
} catch {
    Write-Error "❌ [1/3] FAILED to enumerate files from NAS. Check credentials and path. Error: $($_.Exception.Message)"
    exit 1
}

# --- Step 2: Concurrent Header Indexing ---
Write-Host "[2/3] Starting concurrent header indexing..."
$indexerScriptPath = Join-Path $scriptRoot "build_index.py"
$outputIndexPath = Join-Path $scriptRoot "index_sample.json"

try {
    $stopwatchIndex = [System.Diagnostics.Stopwatch]::StartNew()
    # Ensure we use a python that is in the PATH
    python $indexerScriptPath --list $fileListPath --out $outputIndexPath
    $stopwatchIndex.Stop()
    Write-Host "✅ [2/3] Success! Indexing complete in $($stopwatchIndex.Elapsed.TotalSeconds.ToString('F2'))s."
} catch {
    Write-Error "❌ [2/3] FAILED to run Python indexer. Ensure Python and pydicom are installed. Error: $($_.Exception.Message)"
    exit 1
}

# --- Step 3: Verifying Index ---
Write-Host "[3/3] Verifying output index file..."
if (Test-Path $outputIndexPath) {
    $indexContent = Get-Content $outputIndexPath -Raw | ConvertFrom-Json
    if ($indexContent) {
        $seriesCount = $indexContent.Count
        Write-Host "✅ [3/3] Success! Created '$($outputIndexPath | Split-Path -Leaf)' with $seriesCount series."
        Write-Host "--- Sample Entry ---"
        $indexContent | Select-Object -First 1 | ConvertTo-Json -Depth 5
        Write-Host "--------------------"
    } else {
        Write-Error "❌ [3/3] FAILED: The index file is empty or invalid JSON."
        exit 1
    }
} else {
    Write-Error "❌ [3/3] FAILED: The indexer did not create the output file '$($outputIndexPath | Split-Path -Leaf)'."
    exit 1
}

Write-Host "🎉 --- TEST COMPLETE --- 🎉"
