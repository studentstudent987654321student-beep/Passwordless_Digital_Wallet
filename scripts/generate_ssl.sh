#!/bin/bash
# Generate self-signed SSL certificates for development
# For production, use Let's Encrypt with certbot

set -e

# Certificate configuration
CERT_DIR="./nginx/certs"
CERT_DAYS=365
CERT_COUNTRY="GB"
CERT_STATE="England"
CERT_CITY="London"
CERT_ORG="UK Fintech Research"
CERT_OU="Passwordless Wallet Project"
CERT_CN="localhost"

# Create certificate directory if it doesn't exist
mkdir -p "$CERT_DIR"

echo "=========================================="
echo "  SSL Certificate Generator"
echo "  For Development Use Only"
echo "=========================================="
echo ""

# Check if certificates already exist
if [ -f "$CERT_DIR/server.crt" ] && [ -f "$CERT_DIR/server.key" ]; then
    echo "⚠️  Certificates already exist in $CERT_DIR"
    read -p "Do you want to regenerate them? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Keeping existing certificates."
        exit 0
    fi
fi

echo "📝 Generating SSL certificates..."
echo "   Location: $CERT_DIR"
echo "   Valid for: $CERT_DAYS days"
echo ""

# Generate private key
openssl genrsa -out "$CERT_DIR/server.key" 2048

# Generate certificate signing request
openssl req -new \
    -key "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.csr" \
    -subj "/C=$CERT_COUNTRY/ST=$CERT_STATE/L=$CERT_CITY/O=$CERT_ORG/OU=$CERT_OU/CN=$CERT_CN"

# Generate self-signed certificate
openssl x509 -req \
    -days $CERT_DAYS \
    -in "$CERT_DIR/server.csr" \
    -signkey "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt"

# Create a SAN (Subject Alternative Name) certificate for modern browsers
cat > "$CERT_DIR/san.cnf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $CERT_COUNTRY
ST = $CERT_STATE
L = $CERT_CITY
O = $CERT_ORG
OU = $CERT_OU
CN = $CERT_CN

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

# Generate certificate with SAN
openssl req -new -x509 \
    -days $CERT_DAYS \
    -key "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -config "$CERT_DIR/san.cnf" \
    -extensions v3_req

# Clean up CSR file
rm -f "$CERT_DIR/server.csr"

# Set appropriate permissions
chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

echo ""
echo "✅ SSL certificates generated successfully!"
echo ""
echo "📁 Files created:"
echo "   - $CERT_DIR/server.crt (certificate)"
echo "   - $CERT_DIR/server.key (private key)"
echo "   - $CERT_DIR/san.cnf (config)"
echo ""
echo "🔒 Important Notes:"
echo "   1. These are SELF-SIGNED certificates for DEVELOPMENT ONLY"
echo "   2. For production, use Let's Encrypt:"
echo "      sudo certbot certonly --webroot -w /var/www/html -d yourdomain.com"
echo "   3. Add the certificate to your browser's trusted certificates"
echo "      to avoid security warnings during testing"
echo ""
echo "🌐 WebAuthn Requirements:"
echo "   WebAuthn only works on:"
echo "   - https://localhost"
echo "   - https://*.localhost"
echo "   - https:// with valid TLS certificate"
echo ""
