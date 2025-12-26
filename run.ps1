# Passwordless Digital Wallet - Final Project Launcher
# Single command to run everything!

param(
    [switch]$Install,
    [switch]$Help
)

$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = $PSScriptRoot

# Colors
function Write-Success { param($msg) Write-Host $msg -ForegroundColor Green }
function Write-Info { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host $msg -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host $msg -ForegroundColor Red }

# Show banner
function Show-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "  ======================================================" -ForegroundColor Cyan
    Write-Host "  |                                                    |" -ForegroundColor Cyan
    Write-Host "  |   PASSWORDLESS DIGITAL WALLET                      |" -ForegroundColor Cyan
    Write-Host "  |   WebAuthn (FIDO2) + Flask                         |" -ForegroundColor Cyan
    Write-Host "  |   MSc Computing Final Project                      |" -ForegroundColor Cyan
    Write-Host "  |                                                    |" -ForegroundColor Cyan
    Write-Host "  ======================================================" -ForegroundColor Cyan
    Write-Host ""
}

# Help
if ($Help) {
    Show-Banner
    Write-Host "Usage: .\run.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Install    Force reinstall dependencies"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    exit 0
}

Show-Banner

# Check Python
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    $result = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($result) {
        $pythonCmd = $cmd
        break
    }
}

if (-not $pythonCmd) {
    Write-Err "Python not found! Please install Python 3.9+ from python.org"
    exit 1
}

Write-Info "Using Python: $pythonCmd"

# Set project directory
Set-Location $ProjectRoot
Write-Info "Project directory: $ProjectRoot"

# Create virtual environment
$venvPath = Join-Path $ProjectRoot "venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

if (-not (Test-Path $venvPath) -or $Install) {
    Write-Info "Creating virtual environment..."
    & $pythonCmd -m venv $venvPath
    Write-Success "Virtual environment created"
}

# Activate and install dependencies
Write-Info "Installing dependencies..."
& $venvPip install --upgrade pip -q
& $venvPip install -r requirements.txt -q
Write-Success "Dependencies installed"

# Create .env file if not exists
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Info "Creating .env file..."
    $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    
    $envContent = @"
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=$secretKey

# Database (SQLite for local development)
DATABASE_URL=sqlite:///wallet.db

# WebAuthn Configuration
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_NAME=Passwordless Digital Wallet
WEBAUTHN_ORIGIN=https://localhost:5000

# Session Configuration
SESSION_TYPE=filesystem
"@
    $envContent | Out-File -FilePath $envFile -Encoding UTF8
    Write-Success ".env file created"
}

# Create SSL certificates directory
$certDir = Join-Path $ProjectRoot "certs"
if (-not (Test-Path $certDir)) {
    New-Item -ItemType Directory -Path $certDir -Force | Out-Null
}

# Create init script
$initScript = Join-Path $ProjectRoot "init_db.py"
$initScriptContent = @"
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app
from app.models import db

app = create_app()
with app.app_context():
    db.create_all()
    print('Database initialized successfully!')
"@
$initScriptContent | Out-File -FilePath $initScript -Encoding UTF8

# Initialize database
Write-Info "Initializing database..."
& $venvPython $initScript
Write-Success "Database ready"

# Create run script
$runScript = Join-Path $ProjectRoot "server.py"
$runScriptContent = @"
import os
import sys
import ssl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app

if __name__ == '__main__':
    app = create_app()
    
    # Check for SSL certificates
    cert_dir = os.path.join(os.path.dirname(__file__), 'certs')
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')
    
    ssl_context = None
    if os.path.exists(cert_file) and os.path.exists(key_file):
        with open(cert_file, 'r') as f:
            if 'BEGIN CERTIFICATE' in f.read():
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(cert_file, key_file)
    
    if ssl_context is None:
        # Use Flask's adhoc SSL
        ssl_context = 'adhoc'
    
    print('')
    print('=' * 60)
    print('  PASSWORDLESS DIGITAL WALLET SERVER')
    print('=' * 60)
    print('')
    print('  Open your browser to:')
    print('')
    print('    https://localhost:5000')
    print('')
    print('  Note: Accept the security warning (self-signed cert)')
    print('')
    print('  Press Ctrl+C to stop the server')
    print('=' * 60)
    print('')
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        ssl_context=ssl_context
    )
"@
$runScriptContent | Out-File -FilePath $runScript -Encoding UTF8

# Ready message
Write-Host ""
Write-Host "  ======================================================" -ForegroundColor Green
Write-Host "  |                                                    |" -ForegroundColor Green
Write-Host "  |   READY TO LAUNCH!                                 |" -ForegroundColor Green
Write-Host "  |                                                    |" -ForegroundColor Green
Write-Host "  ======================================================" -ForegroundColor Green
Write-Host ""
Write-Info "Starting server..."
Write-Host ""

# Run the server
& $venvPython $runScript
