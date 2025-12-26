"""
pytest configuration and fixtures for Passwordless Digital Wallet tests.
"""
import os
import pytest
from flask import Flask
from app.main import create_app
from app.models import db, User, Wallet, WebAuthnCredential, Transaction, AuditLog

# Test configuration
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope='session')
def app():
    """Create and configure a test application instance."""
    # Set test environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
    os.environ['DATABASE_URL'] = TEST_DATABASE_URL
    os.environ['WEBAUTHN_RP_ID'] = 'localhost'
    os.environ['WEBAUTHN_RP_NAME'] = 'Test Wallet'
    os.environ['WEBAUTHN_ORIGIN'] = 'https://localhost'
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': TEST_DATABASE_URL,
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost',
    })
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    yield app
    
    # Cleanup
    with app.app_context():
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the application."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create a test CLI runner for the application."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """Create a database session for testing."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        email='test@example.com',
        display_name='Test User',
        user_handle=os.urandom(32)
    )
    db_session.add(user)
    db_session.commit()
    
    # Create wallet for user
    wallet = Wallet(user_id=user.id, balance=100.00)
    db_session.add(wallet)
    db_session.commit()
    
    return user


@pytest.fixture
def sample_credential(db_session, sample_user):
    """Create a sample WebAuthn credential for testing."""
    credential = WebAuthnCredential(
        user_id=sample_user.id,
        credential_id=os.urandom(32),
        public_key=os.urandom(64),
        sign_count=0,
        device_name='Test Authenticator',
        aaguid=os.urandom(16)
    )
    db_session.add(credential)
    db_session.commit()
    return credential


@pytest.fixture
def authenticated_client(client, sample_user, app):
    """Create an authenticated test client."""
    with client.session_transaction() as session:
        session['authenticated'] = True
        session['user_id'] = sample_user.id
        session['user_email'] = sample_user.email
    return client


class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self._store = {}
        self._expires = {}
    
    def set(self, key, value, ex=None):
        self._store[key] = value
        if ex:
            self._expires[key] = ex
        return True
    
    def get(self, key):
        return self._store.get(key)
    
    def delete(self, *keys):
        for key in keys:
            self._store.pop(key, None)
            self._expires.pop(key, None)
        return len(keys)
    
    def exists(self, key):
        return key in self._store
    
    def expire(self, key, seconds):
        self._expires[key] = seconds
        return True


@pytest.fixture
def mock_redis(monkeypatch):
    """Provide a mock Redis client."""
    mock = MockRedis()
    return mock
