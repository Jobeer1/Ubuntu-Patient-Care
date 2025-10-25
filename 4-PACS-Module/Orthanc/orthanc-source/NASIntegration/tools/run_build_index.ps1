param(
    [string]$nasServer = '155.235.81.155',
    [string]$share = 'Image Archiving',
    [string]$username = 'admin',
    [string]$password = 'CH@R!$M@',
    [int]$sampleLimit = 200,
    [int]$indexLimit = 0
)

$securePass = ConvertTo-SecureString $password -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ($username, $securePass)

Write-Host "Mounting \\$nasServer\$share as Z:"
New-PSDrive -Name Z -PSProvider FileSystem -Root "\\$nasServer\$share" -Credential $cred -ErrorAction Stop

try {
    # Export list of potential DICOM files
    $files = Get-ChildItem Z: -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in @('.dcm', '.dicom', '.ima') -or $_.Name -notmatch '\.' }
    $outList = Join-Path (Get-Location) 'nas_dicom_files.txt'
    $files | Select-Object -ExpandProperty FullName | Select-Object -First $sampleLimit | Out-File -FilePath $outList -Encoding UTF8
    Write-Host "Exported $($files.Count) total files; wrote $sampleLimit to $outList"

    # Run the indexer
    $python = 'python'
    $script = Join-Path (Get-Location) 'build_index.py'
    $outIndex = Join-Path (Get-Location) 'index_sample.json'
    Write-Host "Running indexer: $script -> $outIndex (limit=$indexLimit)"
    & $python $script --list $outList --out $outIndex --limit $indexLimit

} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
} finally {
    Write-Host 'Unmounting Z:'
    Remove-PSDrive Z -Force -ErrorAction SilentlyContinue
}
