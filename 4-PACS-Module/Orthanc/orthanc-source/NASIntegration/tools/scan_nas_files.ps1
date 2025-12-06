$password = 'CH@R!$M@'
$cred = New-Object System.Management.Automation.PSCredential ('admin', (ConvertTo-SecureString $password -AsPlainText -Force))

Write-Host "Scanning NAS for DICOM files..."
Write-Host ""

try {
    New-PSDrive -Name Z -PSProvider FileSystem -Root '\\155.235.81.155\Image Archiving' -Credential $cred -ErrorAction Stop
    Write-Host "Connected to NAS successfully!" -ForegroundColor Green

    # Get all files recursively
    $allFiles = Get-ChildItem Z: -Recurse -File | Where-Object {
        $_.Extension -in @('.dcm', '.dicom', '.ima') -or $_.Name -notmatch '\.'
    }

    Write-Host "Found $($allFiles.Count) potential DICOM files:" -ForegroundColor Cyan
    Write-Host ""

    # Export file list to CSV for Python importer
    $fileList = $allFiles | Select-Object @{Name='FullName';Expression={$_.FullName}}, @{Name='Name';Expression={$_.Name}}, Length, LastWriteTime
    $fileList | Export-Csv -Path "nas_files.csv" -NoTypeInformation

    # Show sample files
    $fileList | Select-Object -First 10 | Format-Table Name, Length, LastWriteTime -AutoSize

    if ($allFiles.Count -gt 10) {
        Write-Host "... and $($allFiles.Count - 10) more files" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "File list exported to nas_files.csv" -ForegroundColor Green

    Remove-PSDrive Z
    Write-Host "Disconnected from NAS"

} catch {
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
}
