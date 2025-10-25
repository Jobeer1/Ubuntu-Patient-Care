$password = 'CH@R!$M@'
$cred = New-Object System.Management.Automation.PSCredential ('admin', (ConvertTo-SecureString $password -AsPlainText -Force))

Write-Host "Testing NAS connection to \\155.235.81.155\Image Archiving"
Write-Host "Username: admin"
Write-Host ""

try {
    New-PSDrive -Name Z -PSProvider FileSystem -Root '\\155.235.81.155\Image Archiving' -Credential $cred -ErrorAction Stop
    Write-Host "SUCCESS: Connected to NAS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Files in the share:"
    Get-ChildItem Z: | Select-Object -First 10 | Format-Table Name, Length, LastWriteTime
    Write-Host ""
    Write-Host "Disconnecting..."
    Remove-PSDrive Z
    Write-Host "Disconnected successfully"
} catch {
    Write-Host "FAILED: Could not connect to NAS" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}
