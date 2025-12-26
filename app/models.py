"""
Database models for the passwordless digital wallet.
GDPR-compliant, minimal data storage.
"""
from datetime import datetime, timezone
from app.main import db
import uuid


class User(db.Model):
    """
    User model - stores minimal identifying information.
    No passwords, no biometric data.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now(), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    gdpr_consent = db.Column(db.Boolean, default=False, nullable=False)
    gdpr_consent_date = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    credentials = db.relationship("WebAuthnCredential", back_populates="user", cascade="all, delete-orphan")
    wallet = db.relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class WebAuthnCredential(db.Model):
    """
    WebAuthn credential storage.
    Stores only public keys and credential metadata - private keys never leave the device.
    """
    __tablename__ = 'webauthn_credentials'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    credential_id = db.Column(db.LargeBinary, unique=True, nullable=False, index=True)
    public_key = db.Column(db.LargeBinary, nullable=False)
    sign_count = db.Column(db.Integer, default=0, nullable=False)
    transports = db.Column(db.String(255), nullable=True)  # JSON array as string
    aaguid = db.Column(db.String(255), nullable=True)
    attestation_format = db.Column(db.String(50), nullable=True)
    device_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    last_used = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="credentials")

    def __repr__(self):
        return f"<WebAuthnCredential user_id={self.user_id} device={self.device_name}>"


class Wallet(db.Model):
    """
    Digital wallet - stores balance and basic wallet information.
    """
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    wallet_id = db.Column(db.String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    balance = db.Column(db.Numeric(precision=18, scale=2), default=0.00, nullable=False)
    currency = db.Column(db.String(3), default='GBP', nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now(), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="wallet")
    transactions = db.relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Wallet {self.wallet_id} balance={self.balance} {self.currency}>"


class Transaction(db.Model):
    """
    Transaction records - immutable financial events.
    """
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(255), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    currency = db.Column(db.String(3), default='GBP', nullable=False)
    description = db.Column(db.Text, nullable=True)
    recipient_email = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='PENDING', nullable=False)  # PENDING, COMPLETED, FAILED
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    webauthn_verified = db.Column(db.Boolean, default=False, nullable=False)  # Step-up auth verification

    # Relationships
    wallet = db.relationship("Wallet", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.transaction_id} {self.transaction_type} {self.amount}>"


class AuditLog(db.Model):
    """
    Immutable audit log for GDPR compliance and security monitoring.
    Records all significant actions without storing sensitive data.
    """
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    event_type = db.Column(db.String(100), nullable=False, index=True)  # REGISTRATION, LOGIN, TRANSACTION, etc.
    event_description = db.Column(db.Text, nullable=True)
    event_data = db.Column(db.Text, nullable=True)  # JSON string for additional data
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.Text, nullable=True)
    success = db.Column(db.Boolean, default=True, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.event_type} success={self.success}>"
