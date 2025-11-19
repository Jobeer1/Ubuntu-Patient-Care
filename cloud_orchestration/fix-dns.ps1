# Fix DNS Route for Ubuntu Care Demo

Write-Host "Fixing DNS Route..." -ForegroundColor Yellow

# You need to manually delete the DNS record from Cloudflare Dashboard:
# 1. Go to https://dash.cloudflare.com
# 2. Select your domain: virons.uk
# 3. Go to DNS > Records
# 4. Find and DELETE the CNAME record for: ubuntu-care.virons.uk
# 5. Then run this command:

Write-Host "`nOption 1: Manual Fix (Recommended)" -ForegroundColor Cyan
Write-Host "1. Go to: https://dash.cloudflare.com" -ForegroundColor White
Write-Host "2. Select domain: virons.uk" -ForegroundColor White
Write-Host "3. DNS > Records" -ForegroundColor White
Write-Host "4. Delete CNAME: ubuntu-care.virons.uk" -ForegroundColor White
Write-Host "5. Run: cloudflared tunnel route dns ubuntu-patient-care ubuntu-care.virons.uk" -ForegroundColor Green

Write-Host "`nOption 2: Try force delete (may not work)" -ForegroundColor Cyan
$response = Read-Host "Try to delete via CLI? (y/n)"

if ($response -eq 'y') {
    Write-Host "Attempting to remove old route..." -ForegroundColor Yellow
    cloudflared tunnel route dns delete ubuntu-care.virons.uk
    
    Start-Sleep -Seconds 2
    
    Write-Host "Creating new route..." -ForegroundColor Yellow
    cloudflared tunnel route dns ubuntu-patient-care ubuntu-care.virons.uk
}
