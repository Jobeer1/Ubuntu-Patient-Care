# Simple Orthanc health check
param(
    [string]$Url = $(if ($env:ORTHANC_URL) { $env:ORTHANC_URL } else { 'http://localhost:8042' })
)

try {
    $resp = Invoke-RestMethod -Uri "$Url/system" -Method Get -TimeoutSec 5
    Write-Host "Orthanc OK: Version = $($resp.Version)"
    $resp | ConvertTo-Json -Depth 5
    exit 0
} catch {
    Write-Error "Orthanc not reachable at $Url. Error: $_"
    exit 2
}
