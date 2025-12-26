# 🔐 Passwordless Digital Wallet

> A secure digital wallet application implementing WebAuthn (FIDO2) passwordless authentication using Flask

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![WebAuthn](https://img.shields.io/badge/WebAuthn-FIDO2-orange.svg)](https://webauthn.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [Security Features](#-security-features)
- [Testing](#-testing)
- [Docker Deployment](#-docker-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## 🎯 Overview

This project is a **MSc Computing Final Project** demonstrating a passwordless digital wallet application that replaces traditional password-based authentication with modern WebAuthn (FIDO2) biometric authentication. Users can register and login using Windows Hello, Touch ID, Face ID, or hardware security keys.

### Why Passwordless?

| Traditional Passwords | WebAuthn (This Project) |
|----------------------|------------------------|
| ❌ Vulnerable to phishing | ✅ Phishing-resistant |
| ❌ Can be stolen/leaked | ✅ Private keys never leave device |
| ❌ Reused across sites | ✅ Unique per site |
| ❌ Brute-force attacks | ✅ Cryptographically secure |
| ❌ Social engineering | ✅ Requires biometric |

## ✨ Features

- **🔐 Passwordless Authentication** - Register and login using biometrics (fingerprint, face recognition)
- **💰 Digital Wallet** - Manage your digital wallet balance
- **💸 Secure Transactions** - Deposit and transfer funds with step-up authentication
- **📊 Transaction History** - View complete transaction records
- **🛡️ Security First** - Rate limiting, input sanitization, HTTPS encryption
- **📱 Multi-Device Support** - Register multiple authenticators per account
- **📝 Audit Logging** - Comprehensive security event logging

## 🛠️ Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| Backend Framework | Flask | 3.0.x |
| Database ORM | SQLAlchemy | 2.0.36 |
| Database | SQLite | 3.x |
| Authentication | python-fido2 | 1.1.3 |
| Session Management | Flask-Session | 0.8.0 |
| Rate Limiting | Flask-Limiter | 3.5.0 |
| Input Sanitization | Bleach | 6.1.0 |
| Frontend | HTML5, CSS3, JavaScript | ES6+ |
| Containerization | Docker | 24.x |

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **Modern Browser** - Chrome, Edge, Firefox, or Safari (with WebAuthn support)
- **Windows Hello / Touch ID / Security Key** - For biometric authentication

### Verify Prerequisites

```powershell
# Check Python version
python --version
# Expected: Python 3.11.x or higher

# Check pip
pip --version

# Check Git
git --version
```

## 🚀 Installation

### Step 1: Clone the Repository

```powershell
# Clone the repository
git clone https://github.com/studentstudent987654321student-beep/Passwordless_Digital_Wallet.git

# Navigate to project directory
cd Passwordless_Digital_Wallet
```

### Step 2: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate virtual environment (Windows CMD)
.\venv\Scripts\activate.bat

# Activate virtual environment (Linux/macOS)
source venv/bin/activate
```

### Step 3: Install Dependencies

```powershell
# Install all required packages
pip install -r requirements.txt
```

### Step 4: Generate SSL Certificates

WebAuthn requires HTTPS. Generate self-signed certificates for development:

```powershell
# Create certs directory
mkdir certs -ErrorAction SilentlyContinue

# Generate self-signed certificate (Windows with OpenSSL)
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=localhost"

# Alternative: Use the provided script
.\scripts\generate_ssl.ps1
```

### Step 5: Initialize Database

```powershell
# Initialize the SQLite database
python init_db.py
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Flask Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
FLASK_ENV=development
DEBUG=True

# WebAuthn Configuration
RP_ID=localhost
RP_NAME=Passwordless Digital Wallet
RP_ORIGIN=https://localhost:5000

# Database
DATABASE_URL=sqlite:///wallet.db

# Session Configuration
SESSION_TYPE=filesystem
```

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for session signing | Auto-generated |
| `RP_ID` | WebAuthn Relying Party ID (domain) | `localhost` |
| `RP_NAME` | Application display name | `Passwordless Digital Wallet` |
| `RP_ORIGIN` | Full origin URL | `https://localhost:5000` |
| `DEBUG` | Enable debug mode | `True` |

## ▶️ Running the Application

### Development Server

```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run the Flask development server
python server.py
```

### Expected Output

```
============================================================
  PASSWORDLESS DIGITAL WALLET SERVER
============================================================

  Open your browser to:

    https://localhost:5000

  Note: Accept the security warning (self-signed cert)

  Press Ctrl+C to stop the server
============================================================

 * Running on https://127.0.0.1:5000
 * Running on https://192.168.x.x:5000
```

### Access the Application

1. Open your browser and navigate to: **https://localhost:5000**
2. Accept the security warning (self-signed certificate)
3. Register a new account using your email
4. Complete biometric verification (Windows Hello, Touch ID, etc.)
5. Login and start using the wallet!

## 📚 API Documentation

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /auth/register/begin` | POST | Start registration ceremony |
| `POST /auth/register/complete` | POST | Complete registration |
| `POST /auth/login/begin` | POST | Start authentication |
| `POST /auth/login/complete` | POST | Complete authentication |
| `POST /auth/logout` | POST | Logout user |
| `GET /auth/status` | GET | Check auth status |

### Wallet Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `GET /wallet/balance` | GET | ✅ | Get wallet balance |
| `GET /wallet/transactions` | GET | ✅ | Get transaction history |
| `POST /wallet/deposit/begin` | POST | ✅ | Start deposit (step-up auth) |
| `POST /wallet/deposit/complete` | POST | ✅ | Complete deposit |
| `POST /wallet/transfer/begin` | POST | ✅ | Start transfer (step-up auth) |
| `POST /wallet/transfer/complete` | POST | ✅ | Complete transfer |

### Example API Usage

```javascript
// Register a new user
const response = await fetch('/auth/register/begin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        email: 'user@example.com',
        display_name: 'John Doe'
    })
});
const options = await response.json();

// Create credential using WebAuthn API
const credential = await navigator.credentials.create({
    publicKey: options.publicKey
});
```

## 📁 Project Structure

```
passwordless-wallet/
├── app/
│   ├── __init__.py          # Package initializer
│   ├── main.py              # Application factory
│   ├── models.py            # Database models
│   ├── config.py            # Configuration classes
│   ├── utils.py             # Utility functions
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── main.py          # Main routes
│   │   └── wallet.py        # Wallet operations
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Application styles
│   │   └── js/
│   │       ├── main.js      # Utility functions
│   │       ├── register.js  # Registration logic
│   │       ├── login.js     # Login logic
│   │       └── dashboard.js # Dashboard logic
│   └── templates/
│       ├── base.html        # Base template
│       ├── index.html       # Landing page
│       ├── register.html    # Registration page
│       ├── login.html       # Login page
│       ├── dashboard.html   # User dashboard
│       └── errors/          # Error pages
├── certs/                   # SSL certificates
├── docs/                    # Documentation
├── migrations/              # Database migrations
├── tests/                   # Test suite
├── .env                     # Environment variables
├── .gitignore              # Git ignore rules
├── docker-compose.yml      # Docker composition
├── Dockerfile              # Docker image
├── requirements.txt        # Python dependencies
├── server.py               # Entry point
└── README.md               # This file
```

## 🔒 Security Features

### Authentication Security
- ✅ **WebAuthn/FIDO2** - Phishing-resistant authentication
- ✅ **Biometric Verification** - Required for all authentications
- ✅ **Step-Up Authentication** - Re-verify for sensitive operations
- ✅ **Sign Counter Validation** - Detect credential cloning

### Application Security
- ✅ **HTTPS Only** - All traffic encrypted with TLS
- ✅ **Rate Limiting** - Prevent brute force attacks
- ✅ **Input Sanitization** - XSS and injection prevention
- ✅ **Server-Side Sessions** - Secure session management
- ✅ **CSRF Protection** - SameSite cookie attribute

### Data Security
- ✅ **No Password Storage** - Only public keys stored
- ✅ **CBOR Encoding** - Efficient credential storage
- ✅ **Audit Logging** - Complete activity trail

## 🧪 Testing

### Run All Tests

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run tests with pytest
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

### Test Categories

```powershell
# Unit tests
pytest tests/test_models.py -v

# Authentication tests
pytest tests/test_auth.py -v

# Wallet operation tests
pytest tests/test_wallet.py -v

# End-to-end tests (requires browser)
pytest tests/test_e2e.py -v
```

## 🐳 Docker Deployment

### Build and Run with Docker

```powershell
# Build the Docker image
docker build -t passwordless-wallet .

# Run the container
docker run -p 5000:5000 passwordless-wallet
```

### Using Docker Compose

```powershell
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./certs:/app/certs:ro
      - wallet_data:/app/instance
    restart: unless-stopped

volumes:
  wallet_data:
```

## ❓ Troubleshooting

### Common Issues

#### 1. "WebAuthn is not supported"
```
Solution: Ensure you're using HTTPS and a modern browser
- Use https://localhost:5000 (not http://)
- Update your browser to the latest version
```

#### 2. "SSL Certificate Error"
```
Solution: Accept the self-signed certificate warning
- Click "Advanced" → "Proceed to localhost"
- Or generate proper certificates for production
```

#### 3. "No authenticator available"
```
Solution: Enable Windows Hello or use a security key
- Windows: Settings → Accounts → Sign-in options → Windows Hello
- macOS: System Preferences → Touch ID
- Or use a hardware security key (YubiKey, etc.)
```

#### 4. "Module not found" errors
```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

#### 5. Database errors
```powershell
# Reset the database
Remove-Item wallet.db -ErrorAction SilentlyContinue
python init_db.py
```

### Debug Mode

Enable detailed logging:

```python
# In .env file
DEBUG=True
FLASK_ENV=development
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Student Developer**
- MSc Computing Final Project
- Module: CMP7200

## 🙏 Acknowledgments

- [FIDO Alliance](https://fidoalliance.org/) - WebAuthn specification
- [Yubico](https://www.yubico.com/) - python-fido2 library
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [W3C](https://www.w3.org/TR/webauthn/) - WebAuthn standard

---

<p align="center">
  Made with ❤️ for a more secure, passwordless future
</p>
