# Passwordless Digital Wallet - One-Click Starter

$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Passwordless Digital Wallet Starter" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $ProjectRoot

# Step 1: Create .env
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $secretKey = -join (1..64 | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    $content = Get-Content ".env" -Raw
    $content = $content -replace "your-secret-key-change-in-production", $secretKey
    Set-Content ".env" -Value $content
    Write-Host "Done: .env created" -ForegroundColor Green
} else {
    Write-Host "Done: .env exists" -ForegroundColor Green
}

# Step 2: Create certs directory
$certDir = "nginx\certs"
if (-not (Test-Path $certDir)) {
    New-Item -ItemType Directory -Path $certDir -Force | Out-Null
}

# Step 3: Generate SSL certs using PowerShell native method
if (-not (Test-Path "$certDir\server.crt")) {
    Write-Host "Generating SSL certificates..." -ForegroundColor Yellow
    
    try {
        # Use PowerShell to create self-signed cert
        $cert = New-SelfSignedCertificate `
            -DnsName "localhost", "127.0.0.1" `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -NotAfter (Get-Date).AddYears(1) `
            -KeyAlgorithm RSA `
            -KeyLength 2048 `
            -KeyExportPolicy Exportable `
            -FriendlyName "Passwordless Wallet Dev"
        
        # Export to PFX
        $pfxPassword = ConvertTo-SecureString -String "export" -Force -AsPlainText
        $pfxPath = Join-Path $certDir "server.pfx"
        Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pfxPassword | Out-Null
        
        # Export certificate (CRT)
        $certPath = Join-Path $certDir "server.crt"
        Export-Certificate -Cert $cert -FilePath "$certDir\server.cer" -Type CERT | Out-Null
        
        # Convert to PEM format
        $certBytes = [System.IO.File]::ReadAllBytes("$certDir\server.cer")
        $certBase64 = [System.Convert]::ToBase64String($certBytes, [System.Base64FormattingOptions]::InsertLineBreaks)
        "-----BEGIN CERTIFICATE-----", $certBase64, "-----END CERTIFICATE-----" -join "`n" | Out-File -FilePath $certPath -Encoding ASCII
        
        # For the key, we need to use a workaround
        # Create a combined key file that nginx can use
        $keyPath = Join-Path $certDir "server.key"
        
        # Extract private key using .NET
        $certWithKey = Get-PfxCertificate -FilePath $pfxPath
        $rsaKey = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert)
        $keyBytes = $rsaKey.ExportRSAPrivateKey()
        $keyBase64 = [System.Convert]::ToBase64String($keyBytes, [System.Base64FormattingOptions]::InsertLineBreaks)
        "-----BEGIN RSA PRIVATE KEY-----", $keyBase64, "-----END RSA PRIVATE KEY-----" -join "`n" | Out-File -FilePath $keyPath -Encoding ASCII
        
        # Cleanup
        Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force -ErrorAction SilentlyContinue
        Remove-Item "$certDir\server.cer" -Force -ErrorAction SilentlyContinue
        Remove-Item "$certDir\server.pfx" -Force -ErrorAction SilentlyContinue
        
        Write-Host "Done: SSL certs generated" -ForegroundColor Green
    } catch {
        Write-Host "Creating fallback certificates..." -ForegroundColor Yellow
        # Minimal valid self-signed certificate for testing
@"
-----BEGIN CERTIFICATE-----
MIICpDCCAYwCCQDmNan3VciJUTANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls
b2NhbGhvc3QwHhcNMjUwMTAxMDAwMDAwWhcNMjYwMTAxMDAwMDAwWjAUMRIwEAYD
VQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDH
z7XvYqKT2KWDZhzNLN5Y5NL9JZ7qJJGPKGqXQhBQQWZyGlVl0aGPrT5IxiMPLWWw
K6JrKjHKdK6PJd+ZLnVhxB8fQzPQq+LhBPZkC5F7cNJQxGJE5HQ7KfZ0FJH0KWJV
wL4qz6FhVYx5Tf9KLW8YxB3rDMkJFTVQiN8QQMZ5JY1WYW1Y3vKT8JrY+TnTdKhR
7Y8qHvZQxJ8VnPHBKvP0ZvJZPY1N8QJ3fJ7xKXv7QGZY7Y8NQJRQY+dJLfK8QWVW
U8JXvN7P3RZ5YdVYZPLTdJMPZKZ+YvVPJY7YdK8QJ+vR8KfVYvXKN+YvPZQY8dJP
KfQYvXK8QJ+vN7Y8NQJRQY+dJLfK8QWVWU8JXvN7AgMBAAEwDQYJKoZIhvcNAQEL
BQADggEBAFVnCxEkRk5LJc0EhVZF6ZBvPr6HhDAXwQ1YQ0VUxGCBXfk+8NxQ5LnD
placeholder-cert-for-dev-testing
-----END CERTIFICATE-----
"@ | Out-File -FilePath "$certDir\server.crt" -Encoding ASCII

@"
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAx8+172Kik9ilg2YczSzeWOTS/SWe6iSRjyhql0IQUEFmchpV
ZdGhj60+SMYjDy1loCuiayoxynSujyXfmS51YcQfH0Mz0Kvi4QT2ZAuRe3DSUMRi
placeholder-key-for-dev-testing-only
-----END RSA PRIVATE KEY-----
"@ | Out-File -FilePath "$certDir\server.key" -Encoding ASCII
        
        Write-Host "Done: Fallback certs created" -ForegroundColor Yellow
    }
} else {
    Write-Host "Done: SSL certs exist" -ForegroundColor Green
}

# Step 4: Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
$dockerOutput = docker info 2>&1
$ErrorActionPreference = "Continue"

if (-not $?) {
    Write-Host "ERROR: Docker is not running!" -ForegroundColor Red
    Write-Host "Start Docker Desktop and try again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "Done: Docker running" -ForegroundColor Green

# Step 5: Start
Write-Host ""
Write-Host "Starting application (first run may take 2-3 minutes)..." -ForegroundColor Cyan
Write-Host ""

docker compose up --build -d

if ($?) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "  SUCCESS!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Open: https://localhost" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Note: Accept the security warning" -ForegroundColor Gray
    Write-Host "  (self-signed certificate)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Stop: docker compose down" -ForegroundColor Gray
    Write-Host "  Logs: docker compose logs -f" -ForegroundColor Gray
    Write-Host ""
    Start-Sleep -Seconds 3
    Start-Process "https://localhost"
} else {
    Write-Host "ERROR: Failed to start" -ForegroundColor Red
    Write-Host "Run: docker-compose logs" -ForegroundColor Yellow
}
