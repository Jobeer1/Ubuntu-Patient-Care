# 🏥 Ubuntu Patient Care - Easy Start Script
# This script starts both the Medical Reporting Module and Image Storage System

Write-Host "🏥 Starting Ubuntu Patient Care System..." -ForegroundColor Green
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = py --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found! Please install Python from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "   During installation, check the box: 'Add Python to PATH'" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Starting Service 1: Medical Reporting Module" -ForegroundColor Cyan
Write-Host "  📝 Voice dictation and report generation" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Start Medical Reporting Module
$reportingPath = "C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\medical-reporting-module"

if (Test-Path $reportingPath) {
    $reportingJob = Start-Job -Name "MedicalReporting" -ScriptBlock {
        param($path)
        Set-Location $path
        py app.py 2>&1
    } -ArgumentList $reportingPath
    
    Write-Host "✅ Medical Reporting Module starting (Job ID: $($reportingJob.Id))..." -ForegroundColor Green
    Start-Sleep -Seconds 3
} else {
    Write-Host "❌ Medical Reporting Module folder not found at:" -ForegroundColor Red
    Write-Host "   $reportingPath" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Starting Service 2: Image Storage System" -ForegroundColor Cyan
Write-Host "  🖼️ Medical image management (X-rays, CT, MRI)" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Start NAS Integration Backend
$nasPath = "C:\Users\Admin\Desktop\ELC\Ubuntu-Patient-Care\Orthanc\orthanc-source\NASIntegration\backend"

if (Test-Path $nasPath) {
    $nasJob = Start-Job -Name "ImageStorage" -ScriptBlock {
        param($path)
        Set-Location $path
        py app.py 2>&1
    } -ArgumentList $nasPath
    
    Write-Host "✅ Image Storage System starting (Job ID: $($nasJob.Id))..." -ForegroundColor Green
    Start-Sleep -Seconds 5
} else {
    Write-Host "❌ Image Storage System folder not found at:" -ForegroundColor Red
    Write-Host "   $nasPath" -ForegroundColor Yellow
    Stop-Job -Name "MedicalReporting"
    Remove-Job -Name "MedicalReporting"
    pause
    exit 1
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  ✅ SYSTEM READY!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 You can now access:" -ForegroundColor White
Write-Host ""
Write-Host "   📝 Medical Reporting (Voice Dictation):" -ForegroundColor Yellow
Write-Host "      https://127.0.0.1:5443" -ForegroundColor Cyan
Write-Host ""
Write-Host "   🖼️ Image Storage (View Medical Images):" -ForegroundColor Yellow
Write-Host "      http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host ""
Write-Host "📊 Checking service status..." -ForegroundColor White
Start-Sleep -Seconds 3

# Check job status
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Yellow
Get-Job | Format-Table -Property Id, Name, State

Write-Host ""
Write-Host "💡 TIPS:" -ForegroundColor Yellow
Write-Host "   • Keep this window open while working" -ForegroundColor White
Write-Host "   • To see service logs: Receive-Job -Name MedicalReporting -Keep" -ForegroundColor White
Write-Host "   • To stop: Press Ctrl+C or close this window" -ForegroundColor White
Write-Host ""
Write-Host "   • For microphone to work on phone/tablet:" -ForegroundColor White
Write-Host "     Run: cloudflared tunnel --url 'https://127.0.0.1:5443' --no-tls-verify" -ForegroundColor Cyan
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor White
Write-Host ""
Write-Host "Streaming logs from both services (press Ctrl+C to stop watching logs)..." -ForegroundColor Gray
Write-Host ""

# Stream logs from both jobs
try {
    while ($true) {
        # Get logs from both jobs
        $reportingLogs = Receive-Job -Name "MedicalReporting" -Keep
        $nasLogs = Receive-Job -Name "ImageStorage" -Keep
        
        if ($reportingLogs) {
            Write-Host "📝 [Medical Reporting] $reportingLogs" -ForegroundColor Cyan
        }
        
        if ($nasLogs) {
            Write-Host "🖼️ [Image Storage] $nasLogs" -ForegroundColor Magenta
        }
        
        Start-Sleep -Seconds 2
        
        # Check if jobs are still running
        $jobs = Get-Job -Name "MedicalReporting","ImageStorage"
        $failedJobs = $jobs | Where-Object { $_.State -eq "Failed" }
        
        if ($failedJobs) {
            Write-Host ""
            Write-Host "❌ One or more services have failed!" -ForegroundColor Red
            Write-Host "Failed services:" -ForegroundColor Yellow
            $failedJobs | Format-Table -Property Name, State
            break
        }
    }
} finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Stop-Job -Name "MedicalReporting","ImageStorage" -ErrorAction SilentlyContinue
    Remove-Job -Name "MedicalReporting","ImageStorage" -ErrorAction SilentlyContinue
    Write-Host "✅ All services stopped." -ForegroundColor Green
}
