"""
Configuration management for the Flask application.
Loads from environment variables for security.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_database_uri():
    """Get database URI, defaulting to SQLite for easy local development."""
    db_url = os.getenv('DATABASE_URL', '')
    if db_url:
        return db_url
    # Default to SQLite for local development
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return f'sqlite:///{os.path.join(basedir, "wallet.db")}'


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    
    # Database - SQLite by default for easy setup
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }
    
    # Redis (optional)
    REDIS_URL = os.getenv('REDIS_URL', '')
    
    # Session Configuration
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.getenv('PERMANENT_SESSION_LIFETIME', '3600')))
    
    # WebAuthn Configuration
    RP_ID = os.getenv('WEBAUTHN_RP_ID', os.getenv('RP_ID', 'localhost'))
    RP_NAME = os.getenv('WEBAUTHN_RP_NAME', os.getenv('RP_NAME', 'Passwordless Digital Wallet'))
    RP_ORIGIN = os.getenv('WEBAUTHN_ORIGIN', os.getenv('RP_ORIGIN', 'https://localhost:5000'))
    
    # Rate Limiting (uses memory by default)
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    # GDPR Compliance
    DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', '90'))
    ENABLE_AUDIT_LOG = os.getenv('ENABLE_AUDIT_LOG', 'True') == 'True'
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
    }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
