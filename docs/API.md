# API Documentation
## Passwordless Digital Wallet

---

## Base URL

**Development:** `https://localhost`  
**Production:** `https://your-domain.com`

---

## Authentication

This API uses WebAuthn (FIDO2) for authentication. Sessions are managed via secure, HttpOnly cookies.

### Headers

All requests should include:
```
Content-Type: application/json
```

---

## Endpoints

### Authentication

#### Start Registration

Begin the registration process by requesting WebAuthn options.

```http
POST /auth/register/options
```

**Request Body:**
```json
{
    "email": "user@example.com",
    "display_name": "John Doe"
}
```

**Response (200):**
```json
{
    "challenge": "base64-encoded-challenge",
    "rp": {
        "name": "Passwordless Wallet",
        "id": "localhost"
    },
    "user": {
        "id": "base64-encoded-user-handle",
        "name": "user@example.com",
        "displayName": "John Doe"
    },
    "pubKeyCredParams": [
        {"type": "public-key", "alg": -7},
        {"type": "public-key", "alg": -257}
    ],
    "authenticatorSelection": {
        "authenticatorAttachment": "platform",
        "userVerification": "required"
    },
    "timeout": 60000,
    "attestation": "none"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid email or missing fields
- `409 Conflict` - Email already registered
- `429 Too Many Requests` - Rate limited

---

#### Complete Registration

Submit the credential created by the authenticator.

```http
POST /auth/register/verify
```

**Request Body:**
```json
{
    "email": "user@example.com",
    "response": {
        "id": "credential-id",
        "rawId": "base64-raw-id",
        "type": "public-key",
        "response": {
            "clientDataJSON": "base64-client-data",
            "attestationObject": "base64-attestation"
        }
    }
}
```

**Response (201):**
```json
{
    "success": true,
    "message": "Registration successful",
    "user_id": 1
}
```

**Error Responses:**
- `400 Bad Request` - Invalid credential or challenge
- `410 Gone` - Challenge expired

---

#### Start Login

Begin the login process by requesting WebAuthn assertion options.

```http
POST /auth/login/options
```

**Request Body:**
```json
{
    "email": "user@example.com"
}
```

**Response (200):**
```json
{
    "challenge": "base64-encoded-challenge",
    "timeout": 60000,
    "rpId": "localhost",
    "allowCredentials": [
        {
            "type": "public-key",
            "id": "base64-credential-id"
        }
    ],
    "userVerification": "required"
}
```

**Error Responses:**
- `400 Bad Request` - Missing email
- `404 Not Found` - User not found or no credentials

---

#### Complete Login

Submit the signed assertion from the authenticator.

```http
POST /auth/login/verify
```

**Request Body:**
```json
{
    "email": "user@example.com",
    "response": {
        "id": "credential-id",
        "rawId": "base64-raw-id",
        "type": "public-key",
        "response": {
            "clientDataJSON": "base64-client-data",
            "authenticatorData": "base64-auth-data",
            "signature": "base64-signature"
        }
    }
}
```

**Response (200):**
```json
{
    "success": true,
    "message": "Login successful",
    "redirect": "/dashboard"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid assertion
- `401 Unauthorized` - Verification failed
- `410 Gone` - Challenge expired

---

#### Logout

End the current session.

```http
POST /auth/logout
```

**Response (200):**
```json
{
    "success": true,
    "message": "Logged out successfully"
}
```

---

### Wallet Operations

All wallet endpoints require an authenticated session.

#### Get Balance

Retrieve current wallet balance.

```http
GET /wallet/balance
```

**Response (200):**
```json
{
    "balance": 1234.56,
    "currency": "GBP",
    "last_updated": "2025-01-15T10:30:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Not authenticated

---

#### Get Transactions

Retrieve transaction history with pagination.

```http
GET /wallet/transactions?limit=20&offset=0
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 20 | Number of transactions |
| offset | integer | 0 | Pagination offset |

**Response (200):**
```json
{
    "transactions": [
        {
            "id": 123,
            "type": "deposit",
            "amount": 100.00,
            "description": "Initial deposit",
            "created_at": "2025-01-15T10:30:00Z",
            "related_user": null
        },
        {
            "id": 124,
            "type": "transfer_out",
            "amount": -50.00,
            "description": "Payment to friend",
            "created_at": "2025-01-15T11:00:00Z",
            "related_user": "friend@example.com"
        }
    ],
    "total": 45,
    "limit": 20,
    "offset": 0
}
```

---

#### Deposit (Step 1: Request Challenge)

Initiate a deposit with step-up authentication.

```http
POST /wallet/deposit
```

**Request Body:**
```json
{
    "amount": 100.00,
    "description": "Salary"
}
```

**Response (200) - Requires Step-Up:**
```json
{
    "require_verification": true,
    "challenge": "base64-encoded-challenge",
    "allowCredentials": [...],
    "operation_id": "uuid-for-operation"
}
```

---

#### Deposit (Step 2: Verify and Execute)

Complete the deposit with biometric verification.

```http
POST /wallet/deposit/verify
```

**Request Body:**
```json
{
    "operation_id": "uuid-for-operation",
    "response": {
        "id": "credential-id",
        "rawId": "base64-raw-id",
        "type": "public-key",
        "response": {
            "clientDataJSON": "base64-client-data",
            "authenticatorData": "base64-auth-data",
            "signature": "base64-signature"
        }
    }
}
```

**Response (200):**
```json
{
    "success": true,
    "message": "Deposit successful",
    "new_balance": 1334.56,
    "transaction_id": 125
}
```

**Error Responses:**
- `400 Bad Request` - Invalid amount or verification
- `401 Unauthorized` - Not authenticated or verification failed

---

#### Transfer (Step 1: Request Challenge)

Initiate a transfer with step-up authentication.

```http
POST /wallet/transfer
```

**Request Body:**
```json
{
    "recipient_email": "recipient@example.com",
    "amount": 50.00,
    "description": "Dinner split"
}
```

**Response (200) - Requires Step-Up:**
```json
{
    "require_verification": true,
    "challenge": "base64-encoded-challenge",
    "allowCredentials": [...],
    "operation_id": "uuid-for-operation",
    "recipient_display_name": "Jane Doe"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid amount or self-transfer
- `402 Payment Required` - Insufficient balance
- `404 Not Found` - Recipient not found

---

#### Transfer (Step 2: Verify and Execute)

Complete the transfer with biometric verification.

```http
POST /wallet/transfer/verify
```

**Request Body:**
```json
{
    "operation_id": "uuid-for-operation",
    "response": {
        "id": "credential-id",
        "rawId": "base64-raw-id",
        "type": "public-key",
        "response": {
            "clientDataJSON": "base64-client-data",
            "authenticatorData": "base64-auth-data",
            "signature": "base64-signature"
        }
    }
}
```

**Response (200):**
```json
{
    "success": true,
    "message": "Transfer successful",
    "new_balance": 1284.56,
    "transaction_id": 126
}
```

---

### Health & Status

#### Health Check

Check API health status.

```http
GET /health
```

**Response (200):**
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Error Format

All errors follow this format:

```json
{
    "error": "error_code",
    "message": "Human-readable error message",
    "details": {} // Optional additional details
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_request` | 400 | Missing or invalid request parameters |
| `unauthorized` | 401 | Not authenticated or invalid session |
| `forbidden` | 403 | Authenticated but not authorized |
| `not_found` | 404 | Resource not found |
| `conflict` | 409 | Resource already exists |
| `gone` | 410 | Resource expired (e.g., challenge) |
| `insufficient_funds` | 402 | Not enough balance for operation |
| `rate_limited` | 429 | Too many requests |
| `server_error` | 500 | Internal server error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/auth/register/*` | 5 per minute |
| `/auth/login/*` | 10 per minute |
| `/wallet/*` | 30 per minute |
| General | 100 per minute |

When rate limited, the response includes:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705322400
Retry-After: 45
```

---

## WebAuthn Flow Diagrams

### Registration Flow

```
┌────────┐          ┌────────┐          ┌───────────┐
│ Client │          │ Server │          │Authenticator│
└───┬────┘          └───┬────┘          └─────┬─────┘
    │                   │                     │
    │  POST /register/options                 │
    │  {email, display_name}                  │
    │─────────────────>│                      │
    │                   │                     │
    │  {challenge, rp, user, pubKeyCredParams}│
    │<─────────────────│                      │
    │                   │                     │
    │  navigator.credentials.create()         │
    │────────────────────────────────────────>│
    │                   │                     │
    │                   │    User verification│
    │                   │    (biometric)      │
    │                   │<────────────────────│
    │                   │                     │
    │  {credential}     │                     │
    │<────────────────────────────────────────│
    │                   │                     │
    │  POST /register/verify                  │
    │  {email, credential}                    │
    │─────────────────>│                      │
    │                   │                     │
    │  {success, user_id}                     │
    │<─────────────────│                      │
```

### Login Flow

```
┌────────┐          ┌────────┐          ┌───────────┐
│ Client │          │ Server │          │Authenticator│
└───┬────┘          └───┬────┘          └─────┬─────┘
    │                   │                     │
    │  POST /login/options                    │
    │  {email}          │                     │
    │─────────────────>│                      │
    │                   │                     │
    │  {challenge, allowCredentials}          │
    │<─────────────────│                      │
    │                   │                     │
    │  navigator.credentials.get()            │
    │────────────────────────────────────────>│
    │                   │                     │
    │                   │    User verification│
    │                   │    (biometric)      │
    │                   │<────────────────────│
    │                   │                     │
    │  {assertion}      │                     │
    │<────────────────────────────────────────│
    │                   │                     │
    │  POST /login/verify                     │
    │  {email, assertion}                     │
    │─────────────────>│                      │
    │                   │                     │
    │  {success, session cookie}              │
    │<─────────────────│                      │
```

---

## Security Considerations

1. **HTTPS Required**: All endpoints require HTTPS
2. **Challenge Expiry**: Challenges expire after 5 minutes
3. **Sign Count**: Server validates authenticator sign counts
4. **Rate Limiting**: Protects against brute force attacks
5. **CORS**: Restricted to same-origin or allowed domains
6. **Session Security**: HttpOnly, Secure, SameSite=Strict cookies

---

## SDK Examples

### JavaScript (Browser)

```javascript
// Registration
async function register(email, displayName) {
    // Get options
    const optionsResponse = await fetch('/auth/register/options', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, display_name: displayName})
    });
    const options = await optionsResponse.json();
    
    // Create credential
    const credential = await navigator.credentials.create({
        publicKey: {
            ...options,
            challenge: base64ToBuffer(options.challenge),
            user: {
                ...options.user,
                id: base64ToBuffer(options.user.id)
            }
        }
    });
    
    // Verify
    const verifyResponse = await fetch('/auth/register/verify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            email,
            response: {
                id: credential.id,
                rawId: bufferToBase64(credential.rawId),
                type: credential.type,
                response: {
                    clientDataJSON: bufferToBase64(credential.response.clientDataJSON),
                    attestationObject: bufferToBase64(credential.response.attestationObject)
                }
            }
        })
    });
    
    return verifyResponse.json();
}
```

### Python (Testing)

```python
import requests

session = requests.Session()

# Login flow would require actual WebAuthn device
# Use for testing unauthenticated endpoints
response = session.get('https://localhost/health', verify=False)
print(response.json())
```

---

## Changelog

### v1.0.0 (2025-01-15)
- Initial release
- WebAuthn registration and login
- Wallet operations with step-up authentication
- Comprehensive audit logging
