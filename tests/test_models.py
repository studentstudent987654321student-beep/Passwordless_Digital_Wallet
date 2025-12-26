"""
Unit tests for database models.
Tests User, WebAuthnCredential, Wallet, Transaction, and AuditLog models.
"""
import pytest
import os
from datetime import datetime
from app.models import User, WebAuthnCredential, Wallet, Transaction, AuditLog


class TestUserModel:
    """Test cases for User model."""
    
    def test_user_creation(self, db_session):
        """Test user can be created successfully."""
        user = User(
            email='modeltest@example.com',
            display_name='Model Test User',
            user_handle=os.urandom(32)
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == 'modeltest@example.com'
        assert user.display_name == 'Model Test User'
        assert user.created_at is not None
    
    def test_user_email_uniqueness(self, db_session, sample_user):
        """Test user email must be unique."""
        duplicate_user = User(
            email=sample_user.email,  # Same email
            display_name='Duplicate',
            user_handle=os.urandom(32)
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
    
    def test_user_handle_uniqueness(self, db_session, sample_user):
        """Test user handle must be unique."""
        duplicate_user = User(
            email='different@example.com',
            display_name='Different User',
            user_handle=sample_user.user_handle  # Same handle
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):
            db_session.commit()
    
    def test_user_wallet_relationship(self, db_session, sample_user):
        """Test user has wallet relationship."""
        assert sample_user.wallet is not None
        assert sample_user.wallet.user_id == sample_user.id
    
    def test_user_credentials_relationship(self, db_session, sample_user, sample_credential):
        """Test user has credentials relationship."""
        assert len(sample_user.credentials) >= 1
        assert sample_credential in sample_user.credentials
    
    def test_user_is_active_default(self, db_session):
        """Test user is_active defaults to True."""
        user = User(
            email='activetest@example.com',
            display_name='Active Test',
            user_handle=os.urandom(32)
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.is_active is True
    
    def test_user_repr(self, sample_user):
        """Test user string representation."""
        repr_str = repr(sample_user)
        assert 'User' in repr_str
        assert sample_user.email in repr_str


class TestWebAuthnCredentialModel:
    """Test cases for WebAuthnCredential model."""
    
    def test_credential_creation(self, db_session, sample_user):
        """Test credential can be created successfully."""
        credential = WebAuthnCredential(
            user_id=sample_user.id,
            credential_id=os.urandom(32),
            public_key=os.urandom(64),
            sign_count=0,
            device_name='Test Device'
        )
        db_session.add(credential)
        db_session.commit()
        
        assert credential.id is not None
        assert credential.user_id == sample_user.id
        assert credential.sign_count == 0
    
    def test_credential_sign_count_increment(self, db_session, sample_credential):
        """Test credential sign count can be incremented."""
        initial_count = sample_credential.sign_count
        sample_credential.sign_count += 1
        db_session.commit()
        
        db_session.refresh(sample_credential)
        assert sample_credential.sign_count == initial_count + 1
    
    def test_credential_user_relationship(self, sample_credential, sample_user):
        """Test credential has user relationship."""
        assert sample_credential.user == sample_user
    
    def test_credential_last_used(self, db_session, sample_credential):
        """Test credential last_used timestamp can be updated."""
        sample_credential.last_used = datetime.utcnow()
        db_session.commit()
        
        assert sample_credential.last_used is not None
    
    def test_credential_id_uniqueness(self, db_session, sample_user, sample_credential):
        """Test credential ID must be unique."""
        duplicate = WebAuthnCredential(
            user_id=sample_user.id,
            credential_id=sample_credential.credential_id,  # Same credential ID
            public_key=os.urandom(64),
            sign_count=0
        )
        db_session.add(duplicate)
        
        with pytest.raises(Exception):
            db_session.commit()


class TestWalletModel:
    """Test cases for Wallet model."""
    
    def test_wallet_creation(self, db_session, sample_user):
        """Test wallet is created with user."""
        assert sample_user.wallet is not None
        assert sample_user.wallet.balance >= 0
    
    def test_wallet_balance_precision(self, db_session, sample_user):
        """Test wallet balance handles decimal precision."""
        wallet = sample_user.wallet
        wallet.balance = 123.45
        db_session.commit()
        
        db_session.refresh(wallet)
        assert wallet.balance == 123.45
    
    def test_wallet_user_uniqueness(self, db_session, sample_user):
        """Test one wallet per user constraint."""
        duplicate_wallet = Wallet(
            user_id=sample_user.id,
            balance=0.0
        )
        db_session.add(duplicate_wallet)
        
        with pytest.raises(Exception):
            db_session.commit()


class TestTransactionModel:
    """Test cases for Transaction model."""
    
    def test_transaction_creation(self, db_session, sample_user):
        """Test transaction can be created."""
        transaction = Transaction(
            user_id=sample_user.id,
            type='deposit',
            amount=100.00,
            description='Test transaction'
        )
        db_session.add(transaction)
        db_session.commit()
        
        assert transaction.id is not None
        assert transaction.created_at is not None
    
    def test_transaction_types(self, db_session, sample_user):
        """Test all transaction types are valid."""
        valid_types = ['deposit', 'withdrawal', 'transfer_in', 'transfer_out']
        
        for tx_type in valid_types:
            tx = Transaction(
                user_id=sample_user.id,
                type=tx_type,
                amount=10.00
            )
            db_session.add(tx)
        
        db_session.commit()
        
        for tx_type in valid_types:
            tx = Transaction.query.filter_by(
                user_id=sample_user.id,
                type=tx_type
            ).first()
            assert tx is not None
    
    def test_transaction_related_user(self, db_session, sample_user):
        """Test transaction with related user."""
        # Create another user as recipient
        recipient = User(
            email='recipient@example.com',
            display_name='Recipient',
            user_handle=os.urandom(32)
        )
        db_session.add(recipient)
        db_session.commit()
        
        # Create wallet for recipient
        recipient_wallet = Wallet(user_id=recipient.id, balance=0.0)
        db_session.add(recipient_wallet)
        db_session.commit()
        
        transaction = Transaction(
            user_id=sample_user.id,
            type='transfer_out',
            amount=50.00,
            related_user_id=recipient.id
        )
        db_session.add(transaction)
        db_session.commit()
        
        assert transaction.related_user_id == recipient.id


class TestAuditLogModel:
    """Test cases for AuditLog model."""
    
    def test_audit_log_creation(self, db_session, sample_user):
        """Test audit log can be created."""
        log = AuditLog(
            user_id=sample_user.id,
            action='login',
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )
        db_session.add(log)
        db_session.commit()
        
        assert log.id is not None
        assert log.timestamp is not None
    
    def test_audit_log_actions(self, db_session, sample_user):
        """Test various audit log actions."""
        actions = [
            'registration_started',
            'registration_completed',
            'login_started',
            'login_completed',
            'login_failed',
            'deposit',
            'transfer',
            'logout'
        ]
        
        for action in actions:
            log = AuditLog(
                user_id=sample_user.id,
                action=action,
                ip_address='127.0.0.1'
            )
            db_session.add(log)
        
        db_session.commit()
        
        logs = AuditLog.query.filter_by(user_id=sample_user.id).all()
        assert len(logs) >= len(actions)
    
    def test_audit_log_details(self, db_session, sample_user):
        """Test audit log can store JSON details."""
        log = AuditLog(
            user_id=sample_user.id,
            action='transfer',
            ip_address='127.0.0.1',
            details={'amount': 100.00, 'recipient': 'test@example.com'}
        )
        db_session.add(log)
        db_session.commit()
        
        db_session.refresh(log)
        assert log.details is not None
        assert log.details.get('amount') == 100.00
    
    def test_audit_log_without_user(self, db_session):
        """Test audit log can be created without user (for failed logins)."""
        log = AuditLog(
            action='login_failed',
            ip_address='192.168.1.1',
            details={'email': 'unknown@example.com', 'reason': 'user_not_found'}
        )
        db_session.add(log)
        db_session.commit()
        
        assert log.id is not None
        assert log.user_id is None
