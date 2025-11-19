# Fix DNS using Cloudflare API

$ZONE_ID = "a204168154193f342d11d9418b0e68f6"
$HOSTNAME = "ubuntu-care.virons.uk"

Write-Host "Checking for existing DNS records..." -ForegroundColor Cyan

# You need your Cloudflare API token
$API_TOKEN = Read-Host "Enter your Cloudflare API Token (or press Enter to skip)"

if ($API_TOKEN) {
    $headers = @{
        "Authorization" = "Bearer $API_TOKEN"
        "Content-Type" = "application/json"
    }
    
    # List DNS records
    $response = Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=$HOSTNAME" -Headers $headers -Method Get
    
    if ($response.result.Count -gt 0) {
        Write-Host "Found existing record. Deleting..." -ForegroundColor Yellow
        $recordId = $response.result[0].id
        Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$recordId" -Headers $headers -Method Delete
        Write-Host "Deleted old record" -ForegroundColor Green
    }
    
    Write-Host "Creating new DNS route via cloudflared..." -ForegroundColor Cyan
    cloudflared tunnel route dns ubuntu-patient-care ubuntu-care.virons.uk
    
} else {
    Write-Host "`nNo API token provided. Please:" -ForegroundColor Yellow
    Write-Host "1. Click 'DNS Records' in the DNS section" -ForegroundColor White
    Write-Host "2. Search for 'ubuntu-care'" -ForegroundColor White
    Write-Host "3. Delete the record" -ForegroundColor White
    Write-Host "4. Run: cloudflared tunnel route dns ubuntu-patient-care ubuntu-care.virons.uk" -ForegroundColor Green
}
