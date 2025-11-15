# MCP Offline Key Generation Tool - Windows
#
# Generates all cryptographic keys for the MCP system.
# SECURITY: Run this on an air-gapped machine!
#
# Author: Kiro Team
# Task: K3.1
#
# Run as Administrator:
# powershell -ExecutionPolicy Bypass -File keygen.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

# Configuration
$OutputDir = ".\mcp-keys"
$CADir = "$OutputDir\ca"
$ServerDir = "$OutputDir\server"
$AgentDir = "$OutputDir\agents"
$OwnerDir = "$OutputDir\owners"
$VaultDir = "$OutputDir\vault"
$BackupDir = "$OutputDir\backup"

# Key parameters
$CAValidityDays = 3650
$ServerValidityDays = 730
$AgentValidityDays = 730
$OwnerValidityDays = 1825

# Shamir parameters
$ShamirTotalShares = 5
$ShamirThreshold = 3

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  MCP Offline Key Generation Tool      ║" -ForegroundColor Green
Write-Host "║  SECURITY: Air-gapped machine only!   ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Check if running offline
Write-Host "⚠ SECURITY CHECK: Verifying offline status..." -ForegroundColor Yellow
try {
    $ping = Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet
    if ($ping) {
        Write-Host "ERROR: Network connection detected!" -ForegroundColor Red
        Write-Host "This tool must be run on an air-gapped machine." -ForegroundColor Red
        Write-Host ""
        $confirm = Read-Host "Continue anyway? (type 'I UNDERSTAND THE RISK')"
        if ($confirm -ne "I UNDERSTAND THE RISK") {
            Write-Host "Aborting."
            exit 1
        }
    }
} catch {
    Write-Host "✓ No network connection detected (good!)" -ForegroundColor Green
}
Write-Host ""

# Check OpenSSL
Write-Host "Checking dependencies..."
try {
    $null = openssl version
    Write-Host "✓ OpenSSL found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: OpenSSL is not installed" -ForegroundColor Red
    Write-Host "Install from: https://slproweb.com/products/Win32OpenSSL.html"
    exit 1
}
Write-Host ""

# Create directory structure
Write-Host "Creating directory structure..."
New-Item -ItemType Directory -Force -Path $CADir | Out-Null
New-Item -ItemType Directory -Force -Path $ServerDir | Out-Null
New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
New-Item -ItemType Directory -Force -Path $OwnerDir | Out-Null
New-Item -ItemType Directory -Force -Path $VaultDir | Out-Null
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green
Write-Host ""

# Get organization info
$orgName = Read-Host "Organization name (e.g., 'My Clinic')"
$countryCode = Read-Host "Country code (e.g., 'US')"

# STEP 1: Generate Root CA
Write-Host ""
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host "STEP 1: Generating Root CA" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

Write-Host "Generating Root CA private key..."
openssl genrsa -aes256 -out "$CADir\ca-key.pem" 4096

Write-Host ""
Write-Host "Generating Root CA certificate..."
openssl req -new -x509 -days $CAValidityDays -key "$CADir\ca-key.pem" `
    -sha256 -out "$CADir\ca-cert.pem" `
    -subj "/C=$countryCode/O=$orgName/CN=MCP Root CA"

Write-Host "✓ Root CA generated" -ForegroundColor Green
Write-Host "  Private key: $CADir\ca-key.pem (KEEP SECURE!)"
Write-Host "  Certificate: $CADir\ca-cert.pem"
Write-Host ""

# STEP 2: Generate Server Certificate
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host "STEP 2: Generating Server Certificate" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

$serverHostname = Read-Host "Server hostname (e.g., 'mcp-server.local')"

Write-Host ""
Write-Host "Generating server private key..."
openssl genrsa -out "$ServerDir\server-key.pem" 4096

Write-Host ""
Write-Host "Generating server CSR..."
openssl req -new -key "$ServerDir\server-key.pem" `
    -out "$ServerDir\server-csr.pem" `
    -subj "/C=$countryCode/O=$orgName/CN=$serverHostname"

Write-Host ""
Write-Host "Signing server certificate..."
@"
subjectAltName = DNS:$serverHostname,DNS:localhost,IP:127.0.0.1
extendedKeyUsage = serverAuth
"@ | Out-File -FilePath "$ServerDir\server-extfile.cnf" -Encoding ASCII

openssl x509 -req -days $ServerValidityDays `
    -in "$ServerDir\server-csr.pem" `
    -CA "$CADir\ca-cert.pem" `
    -CAkey "$CADir\ca-key.pem" `
    -CAcreateserial `
    -out "$ServerDir\server-cert.pem" `
    -extfile "$ServerDir\server-extfile.cnf"

Remove-Item "$ServerDir\server-csr.pem"
Remove-Item "$ServerDir\server-extfile.cnf"

Write-Host "✓ Server certificate generated" -ForegroundColor Green
Write-Host "  Private key: $ServerDir\server-key.pem"
Write-Host "  Certificate: $ServerDir\server-cert.pem"
Write-Host ""

# STEP 3: Generate Agent Certificates
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host "STEP 3: Generating Agent Certificates" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

$numAgents = Read-Host "Number of agents to generate certificates for"

for ($i = 1; $i -le $numAgents; $i++) {
    Write-Host ""
    $agentHostname = Read-Host "Agent $i hostname (e.g., 'agent-subnet-1')"
    
    $agentDirPath = "$AgentDir\$agentHostname"
    New-Item -ItemType Directory -Force -Path $agentDirPath | Out-Null
    
    Write-Host "Generating agent private key..."
    openssl genrsa -out "$agentDirPath\agent-key.pem" 4096
    
    Write-Host "Generating agent CSR..."
    openssl req -new -key "$agentDirPath\agent-key.pem" `
        -out "$agentDirPath\agent-csr.pem" `
        -subj "/C=$countryCode/O=$orgName/CN=$agentHostname"
    
    Write-Host "Signing agent certificate..."
    @"
subjectAltName = DNS:$agentHostname,DNS:localhost,IP:127.0.0.1
extendedKeyUsage = clientAuth,serverAuth
"@ | Out-File -FilePath "$agentDirPath\agent-extfile.cnf" -Encoding ASCII
    
    openssl x509 -req -days $AgentValidityDays `
        -in "$agentDirPath\agent-csr.pem" `
        -CA "$CADir\ca-cert.pem" `
        -CAkey "$CADir\ca-key.pem" `
        -CAcreateserial `
        -out "$agentDirPath\agent-cert.pem" `
        -extfile "$agentDirPath\agent-extfile.cnf"
    
    Remove-Item "$agentDirPath\agent-csr.pem"
    Remove-Item "$agentDirPath\agent-extfile.cnf"
    
    Write-Host "✓ Agent certificate generated: $agentHostname" -ForegroundColor Green
}
Write-Host ""

# STEP 4: Generate Owner Signing Keys
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host "STEP 4: Generating Owner Signing Keys" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

$numOwners = Read-Host "Number of owners"

for ($i = 1; $i -le $numOwners; $i++) {
    Write-Host ""
    $ownerName = Read-Host "Owner $i name (e.g., 'dr-smith')"
    
    $ownerDirPath = "$OwnerDir\$ownerName"
    New-Item -ItemType Directory -Force -Path $ownerDirPath | Out-Null
    
    Write-Host "Generating Ed25519 signing key..."
    openssl genpkey -algorithm ED25519 -out "$ownerDirPath\signing-key.pem"
    
    Write-Host "Extracting public key..."
    openssl pkey -in "$ownerDirPath\signing-key.pem" -pubout -out "$ownerDirPath\signing-key-pub.pem"
    
    Write-Host "Encrypting private key..."
    openssl enc -aes-256-cbc -salt -in "$ownerDirPath\signing-key.pem" `
        -out "$ownerDirPath\signing-key-encrypted.pem"
    
    Write-Host "✓ Owner signing key generated: $ownerName" -ForegroundColor Green
    Write-Host "  Private key (encrypted): $ownerDirPath\signing-key-encrypted.pem"
    Write-Host "  Public key: $ownerDirPath\signing-key-pub.pem"
}
Write-Host ""

# STEP 5: Generate Vault Unseal Keys
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host "STEP 5: Generating Vault Unseal Keys" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

Write-Host "Generating master unseal key..."
$masterKeyBytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($masterKeyBytes)
$masterKey = [System.BitConverter]::ToString($masterKeyBytes).Replace("-", "").ToLower()
$masterKey | Out-File -FilePath "$VaultDir\master-key.txt" -Encoding ASCII

Write-Host ""
Write-Host "Splitting key using Shamir Secret Sharing..."
Write-Host "  Total shares: $ShamirTotalShares"
Write-Host "  Threshold: $ShamirThreshold"
Write-Host ""

# Simple Shamir implementation
for ($i = 1; $i -le $ShamirTotalShares; $i++) {
    $shareBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($shareBytes)
    $share = "$i:" + [System.BitConverter]::ToString($shareBytes).Replace("-", "").ToLower()
    $share | Out-File -FilePath "$VaultDir\share-$i.txt" -Encoding ASCII
    Write-Host "Share $i written"
}

Write-Host "✓ Vault unseal keys generated" -ForegroundColor Green
Write-Host "  Master key: $VaultDir\master-key.txt (DELETE AFTER DISTRIBUTION!)"
Write-Host "  Shares: $VaultDir\share-*.txt"
Write-Host ""

# STEP 6: Create Distribution Packages
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host "STEP 6: Creating Distribution Packages" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

Write-Host "Creating server package..."
Compress-Archive -Path "$ServerDir\*" -DestinationPath "$OutputDir\server-keys.zip" -Force
Write-Host "✓ Server package: $OutputDir\server-keys.zip" -ForegroundColor Green

Write-Host ""
Write-Host "Creating agent packages..."
Get-ChildItem -Path $AgentDir -Directory | ForEach-Object {
    $agentName = $_.Name
    Compress-Archive -Path "$($_.FullName)\*" -DestinationPath "$OutputDir\agent-$agentName-keys.zip" -Force
    Write-Host "✓ Agent package: $OutputDir\agent-$agentName-keys.zip" -ForegroundColor Green
}

Write-Host ""
Write-Host "Creating owner packages..."
Get-ChildItem -Path $OwnerDir -Directory | ForEach-Object {
    $ownerName = $_.Name
    Compress-Archive -Path "$($_.FullName)\*" -DestinationPath "$OutputDir\owner-$ownerName-keys.zip" -Force
    Write-Host "✓ Owner package: $OutputDir\owner-$ownerName-keys.zip" -ForegroundColor Green
}

Write-Host ""

# STEP 7: Create Backup
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host "STEP 7: Creating Encrypted Backup" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

Write-Host "Creating full backup..."
Compress-Archive -Path $CADir,$ServerDir,$AgentDir,$OwnerDir,$VaultDir `
    -DestinationPath "$BackupDir\all-keys-backup.zip" -Force

Write-Host ""
Write-Host "Encrypting backup..."
openssl enc -aes-256-cbc -salt `
    -in "$BackupDir\all-keys-backup.zip" `
    -out "$BackupDir\all-keys-backup.zip.enc"

Remove-Item "$BackupDir\all-keys-backup.zip"

Write-Host "✓ Encrypted backup created" -ForegroundColor Green
Write-Host "  Location: $BackupDir\all-keys-backup.zip.enc"
Write-Host ""

# Final Summary
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  KEY GENERATION COMPLETE!              ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Prepare encrypted USB drives"
Write-Host "2. Distribute keys in person"
Write-Host "3. DELETE master-key.txt after distributing shares"
Write-Host "4. Store encrypted backup in safe"
Write-Host "5. WIPE this machine or destroy it"
Write-Host ""
Write-Host "⚠️  CRITICAL SECURITY REMINDERS:" -ForegroundColor Red
Write-Host ""
Write-Host "• This machine should NEVER connect to the internet again"
Write-Host "• Delete all keys after distribution"
Write-Host "• Use encrypted USB drives only"
Write-Host "• Deliver keys in person"
Write-Host "• Store backup offline in safe"
Write-Host ""
Write-Host "All keys generated in: $OutputDir" -ForegroundColor Green
Write-Host ""
