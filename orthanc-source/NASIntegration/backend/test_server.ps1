# PowerShell script to test the server endpoints
Write-Host "Testing Orthanc NAS Integration Server..." -ForegroundColor Green

# Test 1: Auth status
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/status" -Method GET -ErrorAction Stop
    Write-Host "✓ Auth status endpoint: SUCCESS" -ForegroundColor Green
    Write-Host "  Response: $($response | ConvertTo-Json)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Auth status endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Login
try {
    $loginData = @{
        username = "admin"
        password = "admin123"
    } | ConvertTo-Json
    
    $headers = @{
        'Content-Type' = 'application/json'
    }
    
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $response = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" -Method POST -Body $loginData -Headers $headers -WebSession $session -ErrorAction Stop
    
    Write-Host "✓ Login endpoint: SUCCESS" -ForegroundColor Green
    Write-Host "  Response: $($response | ConvertTo-Json)" -ForegroundColor Gray
    
    # Test 3: Admin users endpoint using the same session
    try {
        $adminResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/admin/users" -Method GET -WebSession $session -ErrorAction Stop
        Write-Host "✓ Admin users endpoint: SUCCESS" -ForegroundColor Green
        Write-Host "  Users count: $($adminResponse.users.Count)" -ForegroundColor Gray
    } catch {
        Write-Host "✗ Admin users endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Status code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
    
} catch {
    Write-Host "✗ Login failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Test completed." -ForegroundColor Green
