# Mount NAS, export file list, run Python importer in dry-run for first 20 files, then unmount
param(
    [string]$nasServer = '155.235.81.155',
    [string]$share = 'Image Archiving',
    [string]$username = 'admin',
    [string]$password = 'CH@R!$M@',
    [int]$limit = 20
)

$securePass = ConvertTo-SecureString $password -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ($username, $securePass)

Write-Host "Mounting \\$nasServer\$share as Z:"
New-PSDrive -Name Z -PSProvider FileSystem -Root "\\$nasServer\$share" -Credential $cred -ErrorAction Stop

try {
    # Export list of potential DICOM files
    $files = Get-ChildItem Z: -Recurse -File | Where-Object { $_.Extension -in @('.dcm', '.dicom', '.ima') -or $_.Name -notmatch '\.' }
    $outFile = Join-Path (Get-Location) 'nas_dicom_files.txt'
    $files | Select-Object -ExpandProperty FullName | Out-File -FilePath $outFile -Encoding UTF8
    Write-Host "Exported $($files.Count) files to $outFile"

    # Run Python importer in dry-run mode
    $python = 'python'
    $script = Join-Path (Get-Location) 'import_from_list.py'
    Write-Host "Running importer dry-run (limit=$limit)"
    & $python $script --list $outFile --dry-run --limit $limit

} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
} finally {
    Write-Host 'Unmounting Z:'
    Remove-PSDrive Z -Force -ErrorAction SilentlyContinue
}
