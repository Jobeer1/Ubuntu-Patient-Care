<#
.SYNOPSIS
    Enumerate DICOM files on NAS share without copying.
.DESCRIPTION
    Uses PowerShell Get-ChildItem to list recursively all DICOM files (.dcm, .dicom, .ima or no extension) under a UNC path.
    Outputs full paths to a text file with timing.
.PARAMETER root
    UNC path to NAS share (e.g. \\155.235.81.155\Image Archiving).
.PARAMETER out
    Output text file name (default: nas_dicom_files.txt).
.EXAMPLE
    .\enum_nas_getchild.ps1 -root "\\155.235.81.155\Image Archiving" -out nas_dicom_files.txt
#>
param(
    [Parameter(Mandatory = $false)]
    [string]$root = '\\155.235.81.155\Image Archiving',
    [Parameter(Mandatory = $false)]
    [string]$out = 'nas_dicom_files.txt'
)

Write-Host "Enumerating DICOM files in $root..."
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

try {
    Get-ChildItem -Path $root -Recurse -File -ErrorAction Stop |
        Where-Object { $_.Extension.ToLower() -in @('.dcm', '.dicom', '.ima') -or $_.Name -notmatch '\.' } |
        Select-Object -ExpandProperty FullName |
        Out-File -FilePath $out -Encoding UTF8

    $stopwatch.Stop()
    $count = (Get-Content $out).Count
    Write-Host "✅ Enumerated $count DICOM file(s) in $($stopwatch.Elapsed.TotalSeconds.ToString('F2')) seconds, saved to $out"
} catch {
    Write-Error "❌ FAILED to enumerate files from NAS. Error: $($_.Exception.Message)"
    exit 1
}
    Write-Error "❌ Failed to enumerate DICOM files: $_"
    exit 1
}