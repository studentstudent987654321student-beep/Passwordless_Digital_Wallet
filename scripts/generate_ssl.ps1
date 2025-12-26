# PowerShell script to generate self-signed SSL certificates for development
# For production, use Let's Encrypt with certbot

$ErrorActionPreference = "Stop"

# Certificate configuration
$CERT_DIR = ".\nginx\certs"
$CERT_DAYS = 365
$CERT_CN = "localhost"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  SSL Certificate Generator" -ForegroundColor Cyan
Write-Host "  For Development Use Only" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Create certificate directory if it doesn't exist
if (-not (Test-Path $CERT_DIR)) {
    New-Item -ItemType Directory -Path $CERT_DIR -Force | Out-Null
    Write-Host "📁 Created directory: $CERT_DIR" -ForegroundColor Green
}

# Check if certificates already exist
$certPath = Join-Path $CERT_DIR "server.crt"
$keyPath = Join-Path $CERT_DIR "server.key"

if ((Test-Path $certPath) -and (Test-Path $keyPath)) {
    Write-Host "⚠️  Certificates already exist in $CERT_DIR" -ForegroundColor Yellow
    $confirm = Read-Host "Do you want to regenerate them? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Keeping existing certificates."
        exit 0
    }
}

Write-Host "📝 Generating SSL certificates..." -ForegroundColor Cyan
Write-Host "   Location: $CERT_DIR"
Write-Host "   Valid for: $CERT_DAYS days"
Write-Host ""

try {
    # Generate self-signed certificate using PowerShell
    $cert = New-SelfSignedCertificate `
        -DnsName "localhost", "*.localhost", "127.0.0.1" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddDays($CERT_DAYS) `
        -KeyAlgorithm RSA `
        -KeyLength 2048 `
        -FriendlyName "Passwordless Wallet Dev Certificate"

    # Export the certificate
    $certPassword = ConvertTo-SecureString -String "password123" -Force -AsPlainText
    $pfxPath = Join-Path $CERT_DIR "server.pfx"
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $certPassword | Out-Null

    # Use OpenSSL to convert PFX to PEM format (if OpenSSL is available)
    $opensslAvailable = $null -ne (Get-Command openssl -ErrorAction SilentlyContinue)
    
    if ($opensslAvailable) {
        # Extract certificate and key using OpenSSL
        & openssl pkcs12 -in $pfxPath -clcerts -nokeys -out $certPath -passin pass:password123
        & openssl pkcs12 -in $pfxPath -nocerts -nodes -out $keyPath -passin pass:password123
        
        # Clean up PFX file
        Remove-Item $pfxPath -Force
    } else {
        Write-Host ""
        Write-Host "⚠️  OpenSSL not found. Using alternative method..." -ForegroundColor Yellow
        
        # Export certificate as Base64
        $certBytes = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
        $certBase64 = [System.Convert]::ToBase64String($certBytes, [System.Base64FormattingOptions]::InsertLineBreaks)
        $certPem = "-----BEGIN CERTIFICATE-----`n$certBase64`n-----END CERTIFICATE-----"
        Set-Content -Path $certPath -Value $certPem
        
        Write-Host ""
        Write-Host "⚠️  Note: Private key export requires OpenSSL." -ForegroundColor Yellow
        Write-Host "   Install OpenSSL or use the PFX file directly." -ForegroundColor Yellow
        Write-Host "   PFX file: $pfxPath (password: password123)" -ForegroundColor Yellow
    }

    # Remove from cert store (optional - keeps it clean)
    Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force

    Write-Host ""
    Write-Host "✅ SSL certificates generated successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📁 Files created:" -ForegroundColor Cyan
    Write-Host "   - $certPath (certificate)"
    if (Test-Path $keyPath) {
        Write-Host "   - $keyPath (private key)"
    }
    Write-Host ""
    Write-Host "🔒 Important Notes:" -ForegroundColor Yellow
    Write-Host "   1. These are SELF-SIGNED certificates for DEVELOPMENT ONLY"
    Write-Host "   2. For production, use Let's Encrypt"
    Write-Host "   3. Add the certificate to your browser's trusted certificates"
    Write-Host "      to avoid security warnings during testing"
    Write-Host ""
    Write-Host "🌐 WebAuthn Requirements:" -ForegroundColor Cyan
    Write-Host "   WebAuthn only works on:"
    Write-Host "   - https://localhost"
    Write-Host "   - https://*.localhost"
    Write-Host "   - https:// with valid TLS certificate"
    Write-Host ""

} catch {
    Write-Host "❌ Error generating certificates: $_" -ForegroundColor Red
    exit 1
}
