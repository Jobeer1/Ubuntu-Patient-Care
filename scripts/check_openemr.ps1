param(
    [string]$Url = $(if ($env:OPENEMR_BASE_URL) { $env:OPENEMR_BASE_URL } else { 'http://localhost:8080' })
)

try {
    $resp = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 5
    Write-Host "OpenEMR reachable: StatusCode = $($resp.StatusCode)"
    exit 0
} catch {
    Write-Error "OpenEMR not reachable at $Url. Error: $_"
    exit 2
}
