param(
    [string]$nasServer = '155.235.81.155',
    [string]$share = 'Image Archiving',
    [string]$username = 'admin',
    [string]$password = 'CH@R!$M@',
    [int]$sampleLimit = 0,
    [string]$outList = 'nas_dicom_files.txt',
    [string]$outIndex = 'index_sample.json'
)

# This script uses robocopy /L (list-only) which is fast and does not copy files.
# It writes a plain list of files to $outList, then runs build_index.py on that list.

$unc = "\\$nasServer\$share"
$tempDest = Join-Path $env:TEMP "nas_dummy_$(Get-Random)"
New-Item -ItemType Directory -Path $tempDest -Force | Out-Null

Write-Host "Generating file list from $unc (robocopy list-only)..."
$robocopyCmd = "robocopy `"$unc`" `"$tempDest`" /L /S /FP /NJH /NJS"
Write-Host "Running: $robocopyCmd"

# Run robocopy and capture stdout
$robOut = & robocopy $unc $tempDest /L /S /FP /NJH /NJS 2>&1

# Parse robocopy output: lines with full paths will contain the UNC path
$files = @()
foreach ($line in $robOut) {
    if ($line -and $line.Trim().StartsWith("\\$nasServer")) {
        $files += $line.Trim()
    }
}

if ($files.Count -eq 0) {
    Write-Host "No files found or robocopy produced no list entries. Capturing full output for debugging..."
    $robOut | Out-File -FilePath robocopy_debug.txt -Encoding UTF8
    Write-Host "Wrote robocopy_debug.txt"
    Remove-Item -Recurse -Force $tempDest
    exit 1
}

# Optionally filter to typical DICOM extensions or files without extension
$filterExts = @('.dcm','.dicom','.ima')
$filtered = $files | Where-Object { 
    $ext = [System.IO.Path]::GetExtension($_)
    ($filterExts -contains $ext.ToLower()) -or ([System.IO.Path]::GetFileName($_) -notmatch '\.')
}

if ($sampleLimit -gt 0) {
    $filtered = $filtered | Select-Object -First $sampleLimit
}

# Write out list as UTF8
$filtered | Out-File -FilePath $outList -Encoding UTF8
Write-Host "Wrote $($filtered.Count) paths to $outList"

# Run the indexer
$python = 'python'
$script = Join-Path (Get-Location) 'build_index.py'
Write-Host "Running indexer: $script -> $outIndex"
& $python $script --list $outList --out $outIndex --limit 0

Write-Host "Cleaning up temporary folder"
Remove-Item -Recurse -Force $tempDest
Write-Host "Done."
