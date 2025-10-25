# Start key services (Orthanc, MySQL, Redis, PHP backend) using Docker Compose
# Usage: .\start_services.ps1

param(
    [switch]$Detach
)

$composeFile = "./sa-ris-backend/docker-compose.yml"
if (-not (Test-Path $composeFile)) {
    Write-Error "docker-compose file not found at $composeFile"
    exit 1
}

function Invoke-Compose {
    param(
        [string[]]$Args
    )

    # Prefer `docker compose` plugin if available
    if (Get-Command 'docker' -ErrorAction SilentlyContinue) {
        try {
            docker compose @Args
            return $true
        } catch {
            # fallthrough to docker-compose
        }
    }

    if (Get-Command 'docker-compose' -ErrorAction SilentlyContinue) {
        try {
            docker-compose @Args
            return $true
        } catch {
            return $false
        }
    }

    Write-Error "Neither 'docker compose' nor 'docker-compose' were found in PATH. Please install Docker Desktop (with Compose) and try again."
    return $false
}

Write-Host "Starting Docker services (Orthanc, MySQL, Redis, PHP backend) defined in $composeFile..."
if ($Detach) {
    if (-not (Invoke-Compose -Args @('-f', $composeFile, 'up', '-d', '--remove-orphans'))) { exit 1 }
} else {
    if (-not (Invoke-Compose -Args @('-f', $composeFile, 'up', '--remove-orphans'))) { exit 1 }
}

# Wait for Orthanc to be healthy
$orthancUrl = $env:ORTHANC_URL -or 'http://localhost:8042'
$maxWait = 180
$waited = 0
Write-Host "Waiting for Orthanc to respond at $orthancUrl/system"
while ($waited -lt $maxWait) {
    try {
        $resp = Invoke-RestMethod -Uri "$orthancUrl/system" -Method Get -TimeoutSec 5
        if ($resp) {
            Write-Host "`n✅ Orthanc responded. Version: $($resp.Version)"
            break
        }
    } catch {
        Write-Host -NoNewline "."
    }
    Start-Sleep -Seconds 3
    $waited += 3
}

if ($waited -ge $maxWait) {
    Write-Warning "Orthanc did not respond within $maxWait seconds. Check docker logs: docker logs sa_ris_orthanc"
} else {
    Write-Host "All services started (or at least Orthanc is reachable). You can now start the backend:"
    Write-Host "  cd sa-ris-backend; npm install; npm start"
}
