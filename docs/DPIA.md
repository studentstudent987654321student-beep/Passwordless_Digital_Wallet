# Data Protection Impact Assessment (DPIA)
## Passwordless Digital Wallet Using WebAuthn (FIDO2)

**Document Version:** 1.0  
**Date:** January 2025  
**Classification:** Internal/Academic  

---

## 1. Project Overview

### 1.1 Description
This DPIA assesses the data protection implications of a passwordless digital wallet application that uses WebAuthn (FIDO2) biometric authentication for UK fintech users.

### 1.2 Purpose
The system enables users to:
- Create digital wallet accounts without passwords
- Authenticate using biometric authenticators (fingerprint, face recognition)
- Perform financial transactions with step-up authentication

### 1.3 Scope
- User registration and authentication
- Wallet balance management
- Peer-to-peer transfers
- Transaction history
- Audit logging

---

## 2. Data Processing Activities

### 2.1 Personal Data Categories

| Data Category | Data Elements | Legal Basis | Retention |
|---------------|---------------|-------------|-----------|
| Identity | Email address, Display name | Consent | Account lifetime + 6 years |
| Authentication | Public keys, Credential IDs | Legitimate interest | Account lifetime |
| Transactional | Amounts, Timestamps, Descriptions | Contract | 6 years (legal requirement) |
| Technical | IP addresses, User agents | Legitimate interest | 90 days |

### 2.2 Special Category Data

**Biometric Data Assessment:**

This system does **NOT** process special category biometric data:
- Biometric templates are generated and stored on the user's device
- Only cryptographic public keys are transmitted to the server
- The server cannot reconstruct biometric information from public keys
- This architecture is specifically designed to avoid special category data processing

### 2.3 Data Flows

```
[User Device]
    ├── Biometric Sensor → [Secure Enclave]
    │                           │
    │                      Private Key (never leaves device)
    │                           │
    │                      Signs Challenge
    │                           │
    └── Public Key + Signature → [Server]
                                     │
                                [PostgreSQL] ← Public keys, Credentials
                                     │
                                [Redis] ← Sessions, Challenges (temporary)
                                     │
                                [Audit Logs] ← Security events
```

---

## 3. Risk Assessment

### 3.1 Risk Matrix

| Risk | Likelihood | Impact | Mitigation | Residual Risk |
|------|------------|--------|------------|---------------|
| Credential breach | Very Low | Low | No passwords stored; public keys not sensitive | Very Low |
| Biometric theft | None | N/A | Biometrics never leave device | None |
| Replay attack | Very Low | Medium | Single-use challenges, Redis expiry | Very Low |
| Session hijacking | Low | High | HttpOnly cookies, secure session management | Low |
| SQL injection | Low | High | SQLAlchemy ORM, parameterized queries | Very Low |
| XSS attack | Low | Medium | CSP headers, template escaping | Very Low |
| MITM attack | Low | High | HTTPS everywhere, HSTS | Very Low |
| Unauthorized access | Low | High | Step-up auth for transactions | Low |

### 3.2 Risk Calculations

**Overall Risk Score:** LOW

The passwordless architecture significantly reduces risk compared to traditional password-based systems:
- No credential database to breach
- Phishing attacks ineffective
- No password reuse vulnerabilities

---

## 4. Data Protection Principles Compliance

### 4.1 Lawfulness, Fairness, and Transparency (Article 5(1)(a))

| Requirement | Implementation |
|-------------|----------------|
| Legal basis | Consent (registration), Contract (transactions), Legitimate interest (security) |
| Fair processing | Clear privacy notice, no hidden data collection |
| Transparency | Privacy policy, clear authentication flow explanation |

### 4.2 Purpose Limitation (Article 5(1)(b))

| Purpose | Data Used |
|---------|-----------|
| Account authentication | Email, public keys, credential IDs |
| Transaction processing | User ID, amounts, timestamps |
| Security monitoring | IP addresses, user agents, audit events |
| Regulatory compliance | Transaction records |

### 4.3 Data Minimization (Article 5(1)(c))

**Minimal Data Collected:**
- Email address (required for account identification)
- Display name (user-friendly identification)
- Public cryptographic keys (authentication only)
- Transaction data (contractual necessity)

**Data NOT Collected:**
- Full name (unless provided in display name)
- Address, phone number
- Biometric templates
- Device identifiers beyond credential IDs

### 4.4 Accuracy (Article 5(1)(d))

| Mechanism | Description |
|-----------|-------------|
| User profile | Users can update display name |
| Email verification | Email validated at registration |
| Transaction records | Immutable for accuracy |

### 4.5 Storage Limitation (Article 5(1)(e))

| Data Type | Retention Period | Justification |
|-----------|------------------|---------------|
| Account data | Account lifetime + 6 years | Regulatory requirement |
| Transaction records | 6 years | Legal/tax requirements |
| Audit logs | 2 years | Security best practice |
| Session data | 24 hours max | Operational necessity |
| Challenges | 5 minutes | Technical requirement |

### 4.6 Integrity and Confidentiality (Article 5(1)(f))

| Control | Implementation |
|---------|----------------|
| Encryption in transit | TLS 1.3 via Nginx |
| Encryption at rest | PostgreSQL encryption |
| Access control | Session-based authentication |
| Input validation | Server and client-side |
| Audit logging | Immutable event records |

### 4.7 Accountability (Article 5(2))

| Measure | Description |
|---------|-------------|
| This DPIA | Documented risk assessment |
| Privacy notice | Published to users |
| Training | Security awareness for operators |
| Auditing | Comprehensive event logging |
| DPO contact | Designated point of contact |

---

## 5. Data Subject Rights

### 5.1 Rights Implementation

| Right | Implementation | Process |
|-------|----------------|---------|
| Information (Art. 13/14) | Privacy notice at registration | Automatic |
| Access (Art. 15) | Profile page, transaction history | Self-service |
| Rectification (Art. 16) | Profile editing | Self-service |
| Erasure (Art. 17) | Account deletion feature | Self-service/request |
| Portability (Art. 20) | JSON export of personal data | Request |
| Object (Art. 21) | Stop processing option | Request |

### 5.2 Request Handling

- Response time: Within 1 month
- Verification: Email confirmation required
- Documentation: All requests logged
- Escalation: DPO involvement if complex

---

## 6. Security Measures

### 6.1 Technical Measures

| Measure | Implementation |
|---------|----------------|
| Authentication | WebAuthn (FIDO2) with biometrics |
| Session security | HttpOnly, Secure, SameSite cookies |
| Transport security | TLS 1.3, HSTS |
| Rate limiting | Per-IP and per-user limits |
| Input validation | Whitelist approach |
| Output encoding | Template auto-escaping |
| Security headers | CSP, X-Frame-Options, etc. |

### 6.2 Organizational Measures

| Measure | Implementation |
|---------|----------------|
| Access control | Role-based, principle of least privilege |
| Monitoring | Audit log review, anomaly detection |
| Incident response | Documented procedure |
| Backup | Daily encrypted backups |
| Testing | Regular security testing |

---

## 7. Third-Party Processing

### 7.1 Sub-Processors

| Processor | Purpose | Data Shared | Safeguards |
|-----------|---------|-------------|------------|
| None | N/A | N/A | Self-hosted |

*Note: This research prototype is self-hosted. Production deployment may require assessment of cloud providers.*

### 7.2 International Transfers

No international data transfers. All processing within UK.

---

## 8. DPIA Decision

### 8.1 Summary

| Criterion | Assessment |
|-----------|------------|
| Legal basis | ✅ Appropriate bases identified |
| Necessity | ✅ Data processing necessary for stated purposes |
| Proportionality | ✅ Minimal data collection |
| Risk level | ✅ LOW - significantly lower than password systems |
| Mitigation | ✅ Appropriate technical and organizational measures |

### 8.2 Conclusion

**RECOMMENDATION: PROCEED**

The passwordless authentication architecture presents significantly lower privacy risks than traditional password-based systems. The WebAuthn standard ensures biometric data never leaves the user's device, eliminating the primary privacy concern with biometric authentication.

### 8.3 Conditions

1. Maintain security updates and patches
2. Review DPIA annually or upon significant changes
3. Monitor for new vulnerabilities in WebAuthn implementations
4. Conduct penetration testing before production use
5. Implement user notification for security events

---

## 9. Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Lead | | | |
| Data Protection Officer | | | |
| Security Reviewer | | | |

---

## 10. Review Schedule

| Review Type | Frequency | Next Review |
|-------------|-----------|-------------|
| DPIA Review | Annual | January 2026 |
| Security Review | Quarterly | April 2025 |
| Risk Assessment | Annual | January 2026 |

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 2025 | Research Team | Initial DPIA |
