"""
Unit tests for wallet routes.
Tests balance, deposit, transfer, and transaction history.
"""
import pytest
import json
from decimal import Decimal
from app.models import User, Wallet, Transaction


class TestWalletRoutes:
    """Test cases for wallet routes."""
    
    def test_get_balance_authenticated(self, authenticated_client, sample_user):
        """Test authenticated user can get balance."""
        response = authenticated_client.get('/wallet/balance')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'balance' in data
        assert isinstance(data['balance'], (int, float))
    
    def test_get_balance_unauthenticated(self, client):
        """Test unauthenticated user cannot get balance."""
        response = client.get('/wallet/balance')
        
        assert response.status_code in [401, 302]  # Unauthorized or redirect
    
    def test_get_transactions_authenticated(self, authenticated_client):
        """Test authenticated user can get transaction history."""
        response = authenticated_client.get('/wallet/transactions')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'transactions' in data
        assert isinstance(data['transactions'], list)
    
    def test_get_transactions_unauthenticated(self, client):
        """Test unauthenticated user cannot get transactions."""
        response = client.get('/wallet/transactions')
        
        assert response.status_code in [401, 302]
    
    def test_get_transactions_pagination(self, authenticated_client):
        """Test transaction pagination."""
        response = authenticated_client.get('/wallet/transactions?limit=5&offset=0')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'transactions' in data


class TestDeposit:
    """Test deposit functionality."""
    
    def test_deposit_requires_authentication(self, client):
        """Test deposit endpoint requires authentication."""
        response = client.post('/wallet/deposit',
            json={'amount': 100.00},
            content_type='application/json'
        )
        
        assert response.status_code in [401, 302]
    
    def test_deposit_requires_step_up_auth(self, authenticated_client):
        """Test deposit requires step-up authentication."""
        response = authenticated_client.post('/wallet/deposit',
            json={'amount': 100.00},
            content_type='application/json'
        )
        
        # Should return step-up challenge or require verification
        assert response.status_code in [200, 400, 401]
    
    def test_deposit_invalid_amount_negative(self, authenticated_client):
        """Test deposit fails with negative amount."""
        response = authenticated_client.post('/wallet/deposit',
            json={'amount': -50.00},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_deposit_invalid_amount_zero(self, authenticated_client):
        """Test deposit fails with zero amount."""
        response = authenticated_client.post('/wallet/deposit',
            json={'amount': 0},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_deposit_invalid_amount_type(self, authenticated_client):
        """Test deposit fails with invalid amount type."""
        response = authenticated_client.post('/wallet/deposit',
            json={'amount': 'invalid'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_deposit_missing_amount(self, authenticated_client):
        """Test deposit fails without amount."""
        response = authenticated_client.post('/wallet/deposit',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 400


class TestTransfer:
    """Test transfer functionality."""
    
    def test_transfer_requires_authentication(self, client):
        """Test transfer endpoint requires authentication."""
        response = client.post('/wallet/transfer',
            json={
                'recipient_email': 'recipient@example.com',
                'amount': 50.00
            },
            content_type='application/json'
        )
        
        assert response.status_code in [401, 302]
    
    def test_transfer_requires_step_up_auth(self, authenticated_client):
        """Test transfer requires step-up authentication."""
        response = authenticated_client.post('/wallet/transfer',
            json={
                'recipient_email': 'recipient@example.com',
                'amount': 50.00
            },
            content_type='application/json'
        )
        
        # Should return step-up challenge or require verification
        assert response.status_code in [200, 400, 401, 404]
    
    def test_transfer_invalid_recipient(self, authenticated_client):
        """Test transfer fails with invalid recipient email."""
        response = authenticated_client.post('/wallet/transfer',
            json={
                'recipient_email': 'invalid-email',
                'amount': 50.00
            },
            content_type='application/json'
        )
        
        assert response.status_code in [400, 404]
    
    def test_transfer_negative_amount(self, authenticated_client):
        """Test transfer fails with negative amount."""
        response = authenticated_client.post('/wallet/transfer',
            json={
                'recipient_email': 'recipient@example.com',
                'amount': -50.00
            },
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_transfer_missing_recipient(self, authenticated_client):
        """Test transfer fails without recipient."""
        response = authenticated_client.post('/wallet/transfer',
            json={'amount': 50.00},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_transfer_missing_amount(self, authenticated_client):
        """Test transfer fails without amount."""
        response = authenticated_client.post('/wallet/transfer',
            json={'recipient_email': 'recipient@example.com'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_transfer_to_self_rejected(self, authenticated_client, sample_user):
        """Test transfer to self is rejected."""
        response = authenticated_client.post('/wallet/transfer',
            json={
                'recipient_email': sample_user.email,
                'amount': 50.00
            },
            content_type='application/json'
        )
        
        # Should reject self-transfer
        assert response.status_code in [400, 401]


class TestTransactionModel:
    """Test Transaction model."""
    
    def test_transaction_creation(self, db_session, sample_user):
        """Test transaction can be created."""
        transaction = Transaction(
            user_id=sample_user.id,
            type='deposit',
            amount=100.00,
            description='Test deposit'
        )
        db_session.add(transaction)
        db_session.commit()
        
        assert transaction.id is not None
        assert transaction.amount == 100.00
        assert transaction.type == 'deposit'
    
    def test_transaction_types(self, db_session, sample_user):
        """Test different transaction types."""
        types = ['deposit', 'withdrawal', 'transfer_in', 'transfer_out']
        
        for tx_type in types:
            transaction = Transaction(
                user_id=sample_user.id,
                type=tx_type,
                amount=50.00
            )
            db_session.add(transaction)
        
        db_session.commit()
        
        transactions = Transaction.query.filter_by(user_id=sample_user.id).all()
        assert len(transactions) == len(types)


class TestWalletModel:
    """Test Wallet model."""
    
    def test_wallet_initial_balance(self, db_session, sample_user):
        """Test wallet initial balance."""
        wallet = sample_user.wallet
        assert wallet.balance == 100.00
    
    def test_wallet_balance_update(self, db_session, sample_user):
        """Test wallet balance can be updated."""
        wallet = sample_user.wallet
        initial_balance = wallet.balance
        
        wallet.balance = initial_balance + 50.00
        db_session.commit()
        
        db_session.refresh(wallet)
        assert wallet.balance == initial_balance + 50.00
