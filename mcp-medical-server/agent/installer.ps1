# MCP Agent Installer - Windows
#
# Installs the per-subnet agent as a Windows service.
#
# Author: Kiro Team
# Task: K2.6
#
# Run as Administrator:
# powershell -ExecutionPolicy Bypass -File installer.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

# Configuration
$AgentName = "MCPAgent"
$InstallDir = "C:\Program Files\MCP-Agent"
$ConfigDir = "C:\ProgramData\MCP-Agent"
$DataDir = "$ConfigDir\data"
$LogDir = "$ConfigDir\logs"

Write-Host "MCP Agent Installer - Windows" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python is not installed" -ForegroundColor Red
    Write-Host "Please install Python 3.8 or higher from python.org"
    exit 1
}

# Create directories
Write-Host ""
Write-Host "Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path "$DataDir\certs" | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green

# Copy files
Write-Host ""
Write-Host "Installing agent files..." -ForegroundColor Yellow
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item -Path "$ScriptDir\*" -Destination $InstallDir -Recurse -Force
Write-Host "✓ Files copied" -ForegroundColor Green

# Create virtual environment
Write-Host ""
Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
python -m venv "$InstallDir\venv"
Write-Host "✓ Virtual environment created" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "Installing Python packages..." -ForegroundColor Yellow
& "$InstallDir\venv\Scripts\pip.exe" install --upgrade pip
& "$InstallDir\venv\Scripts\pip.exe" install flask cryptography paramiko pysmb requests pyyaml
Write-Host "✓ Packages installed" -ForegroundColor Green

# Copy config
Write-Host ""
Write-Host "Installing configuration..." -ForegroundColor Yellow
if (Test-Path "$ConfigDir\config.json") {
    Write-Host "Config already exists, skipping" -ForegroundColor Yellow
} else {
    Copy-Item -Path "$InstallDir\config.json" -Destination "$ConfigDir\config.json"
    
    # Generate agent ID
    $agentId = "agent-" + [System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(8)).Replace("-", "").ToLower()
    (Get-Content "$ConfigDir\config.json") -replace 'agent-subnet-1', $agentId | Set-Content "$ConfigDir\config.json"
    
    Write-Host "✓ Config installed (Agent ID: $agentId)" -ForegroundColor Green
}

# Set permissions
Write-Host ""
Write-Host "Setting permissions..." -ForegroundColor Yellow
$acl = Get-Acl $ConfigDir
$acl.SetAccessRuleProtection($true, $false)
$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.AddAccessRule($adminRule)
$acl.AddAccessRule($systemRule)
Set-Acl $ConfigDir $acl
Write-Host "✓ Permissions set" -ForegroundColor Green

# Install as Windows service using NSSM (if available) or create scheduled task
Write-Host ""
Write-Host "Installing service..." -ForegroundColor Yellow

# Check if NSSM is available
$nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
if ($nssmPath) {
    # Use NSSM to create service
    Write-Host "Using NSSM to create service..." -ForegroundColor Yellow
    
    # Remove existing service if present
    $existingService = Get-Service -Name $AgentName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Host "Removing existing service..." -ForegroundColor Yellow
        nssm stop $AgentName
        nssm remove $AgentName confirm
    }
    
    # Install service
    nssm install $AgentName "$InstallDir\venv\Scripts\python.exe" "$InstallDir\service.py --config $ConfigDir\config.json"
    nssm set $AgentName AppDirectory $InstallDir
    nssm set $AgentName DisplayName "MCP Agent Service"
    nssm set $AgentName Description "Per-subnet credential retrieval agent"
    nssm set $AgentName Start SERVICE_AUTO_START
    nssm set $AgentName AppStdout "$LogDir\agent.log"
    nssm set $AgentName AppStderr "$LogDir\agent-error.log"
    
    # Start service
    nssm start $AgentName
    Write-Host "✓ Service installed and started" -ForegroundColor Green
} else {
    # Fallback: Create scheduled task
    Write-Host "NSSM not found, creating scheduled task..." -ForegroundColor Yellow
    Write-Host "(For production, install NSSM: choco install nssm)" -ForegroundColor Yellow
    
    $action = New-ScheduledTaskAction -Execute "$InstallDir\venv\Scripts\python.exe" -Argument "$InstallDir\service.py --config $ConfigDir\config.json" -WorkingDirectory $InstallDir
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    
    Register-ScheduledTask -TaskName $AgentName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
    Start-ScheduledTask -TaskName $AgentName
    
    Write-Host "✓ Scheduled task created and started" -ForegroundColor Green
}

# Wait for service to start
Write-Host ""
Write-Host "Waiting for service to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Health check
Write-Host ""
Write-Host "Running health check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8444/agent/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Health check passed" -ForegroundColor Green
    } else {
        Write-Host "⚠ Health check returned status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Health check failed (service may still be starting)" -ForegroundColor Yellow
}

# Print summary
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Install directory: $InstallDir"
Write-Host "Config directory: $ConfigDir"
Write-Host "Data directory: $DataDir"
Write-Host "Log directory: $LogDir"
Write-Host ""
if ($nssmPath) {
    Write-Host "Service commands:"
    Write-Host "  Start:   nssm start $AgentName"
    Write-Host "  Stop:    nssm stop $AgentName"
    Write-Host "  Status:  nssm status $AgentName"
    Write-Host "  Logs:    Get-Content $LogDir\agent.log -Tail 50 -Wait"
} else {
    Write-Host "Scheduled task commands:"
    Write-Host "  Start:   Start-ScheduledTask -TaskName $AgentName"
    Write-Host "  Stop:    Stop-ScheduledTask -TaskName $AgentName"
    Write-Host "  Status:  Get-ScheduledTask -TaskName $AgentName"
    Write-Host "  Logs:    Get-Content $LogDir\agent.log -Tail 50 -Wait"
}
Write-Host ""
Write-Host "Health check: Invoke-WebRequest http://localhost:8444/agent/health"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit config: $ConfigDir\config.json"
Write-Host "2. Configure adapters for your environment"
Write-Host "3. Restart service"
Write-Host ""
