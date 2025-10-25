$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
cd $scriptRoot

Write-Host "--- FAST E2E Test: Mapped Drive + Robocopy Enumeration ---"
Write-Host "Script running from: $scriptRoot"

# --- Step 1: Fast Enumeration with Mapped Drive + Robocopy ---
Write-Host "[1/3] Starting FAST enumeration with mapped drive and robocopy..."
$fileListPath = Join-Path $scriptRoot "nas_dicom_files_fast.txt"
$enumeratorScriptPath = Join-Path $scriptRoot "enum_nas_fast.ps1"

try {
    $stopwatchEnum = [System.Diagnostics.Stopwatch]::StartNew()
    powershell -ExecutionPolicy Bypass -File $enumeratorScriptPath -OutputFile "nas_dicom_files_fast.txt" -SampleLimit 200
    $stopwatchEnum.Stop()
    
    $fileCount = (Get-Content $fileListPath).Count
    Write-Host "✅ [1/3] Success! Enumerated $fileCount files in $($stopwatchEnum.Elapsed.TotalSeconds.ToString('F2'))s."
} catch {
    Write-Error "❌ [1/3] FAILED to enumerate files. Error: $($_.Exception.Message)"
    exit 1
}

# --- Step 2: Concurrent Header Indexing ---
Write-Host "[2/3] Starting concurrent header indexing..."
$indexerScriptPath = Join-Path $scriptRoot "build_index.py"
$outputIndexPath = Join-Path $scriptRoot "index_fast.json"

try {
    $stopwatchIndex = [System.Diagnostics.Stopwatch]::StartNew()
    python $indexerScriptPath --list $fileListPath --out $outputIndexPath
    $stopwatchIndex.Stop()
    Write-Host "✅ [2/3] Success! Indexing complete in $($stopwatchIndex.Elapsed.TotalSeconds.ToString('F2'))s."
} catch {
    Write-Error "❌ [2/3] FAILED to run Python indexer. Error: $($_.Exception.Message)"
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
    Write-Error "❌ [3/3] FAILED: The indexer did not create the output file."
    exit 1
}

Write-Host "🎉 --- FAST TEST COMPLETE --- 🎉"
