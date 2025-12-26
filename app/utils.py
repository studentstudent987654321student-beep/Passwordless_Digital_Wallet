"""
Utility functions for the Passwordless Digital Wallet
Handles challenge storage, validation, and helper functions
Works with in-memory storage (no Redis required)
"""

import os
import secrets
import hashlib
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, request, current_app
import json

# In-memory challenge storage (imported from main when available)
_challenges = {}

def get_challenges():
    """Get the challenges dictionary from main module or use local"""
    global _challenges
    try:
        from app.main import challenges
        return challenges
    except ImportError:
        return _challenges

# ============================================
# Challenge Management (In-Memory)
# ============================================

def store_challenge(user_id: str, challenge: bytes, challenge_type: str = 'registration', ttl: int = 300) -> bool:
    """
    Store a WebAuthn challenge in memory
    
    Args:
        user_id: User identifier
        challenge: The challenge bytes
        challenge_type: 'registration' or 'authentication'
        ttl: Time to live in seconds (default 5 minutes)
    
    Returns:
        bool: Success status
    """
    try:
        challenges = get_challenges()
        key = f"webauthn_challenge:{challenge_type}:{user_id}"
        challenges[key] = {
            'challenge': challenge.hex() if isinstance(challenge, bytes) else challenge,
            'expires': time.time() + ttl
        }
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to store challenge: {e}")
        return False


def get_challenge(user_id: str, challenge_type: str = 'registration') -> bytes:
    """
    Retrieve and delete a WebAuthn challenge from memory
    
    Args:
        user_id: User identifier
        challenge_type: 'registration' or 'authentication'
    
    Returns:
        bytes: The challenge or None if not found/expired
    """
    try:
        challenges = get_challenges()
        key = f"webauthn_challenge:{challenge_type}:{user_id}"
        
        if key not in challenges:
            return None
            
        data = challenges[key]
        
        # Check expiration
        if time.time() > data.get('expires', 0):
            del challenges[key]
            return None
        
        # Delete after retrieval (one-time use)
        del challenges[key]
        
        challenge_hex = data.get('challenge')
        if challenge_hex:
            return bytes.fromhex(challenge_hex)
        return None
    except Exception as e:
        current_app.logger.error(f"Failed to get challenge: {e}")
        return None


def delete_challenge(user_id: str, challenge_type: str = 'registration') -> bool:
    """
    Delete a WebAuthn challenge from memory
    
    Args:
        user_id: User identifier
        challenge_type: 'registration' or 'authentication'
    
    Returns:
        bool: Success status
    """
    try:
        challenges = get_challenges()
        key = f"webauthn_challenge:{challenge_type}:{user_id}"
        if key in challenges:
            del challenges[key]
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to delete challenge: {e}")
        return False


def cleanup_expired_challenges():
    """Remove expired challenges from memory"""
    try:
        challenges = get_challenges()
        current_time = time.time()
        expired_keys = [
            key for key, data in challenges.items()
            if data.get('expires', 0) < current_time
        ]
        for key in expired_keys:
            del challenges[key]
        return len(expired_keys)
    except Exception as e:
        current_app.logger.error(f"Failed to cleanup challenges: {e}")
        return 0


# ============================================
# Session Management
# ============================================

def create_session(user_id: int, credential_id: str = None) -> dict:
    """
    Create a new user session after successful authentication
    
    Args:
        user_id: The authenticated user's ID
        credential_id: The credential used for authentication
    
    Returns:
        dict: Session data
    """
    session_data = {
        'user_id': user_id,
        'credential_id': credential_id,
        'authenticated_at': datetime.utcnow().isoformat(),
        'last_activity': datetime.utcnow().isoformat(),
        'step_up_verified': False,
        'step_up_expires': None
    }
    
    # Store in Flask session
    session['user'] = session_data
    session['authenticated'] = True
    session.permanent = True
    
    return session_data


def require_authentication(f):
    """
    Decorator to require WebAuthn authentication for a route
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated') or not session.get('user'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('main.login'))
        
        # Update last activity
        if 'user' in session:
            session['user']['last_activity'] = datetime.utcnow().isoformat()
        
        return f(*args, **kwargs)
    return decorated_function


def require_step_up_auth(f):
    """
    Decorator to require step-up authentication for sensitive operations
    Step-up auth is valid for 5 minutes after verification
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('main.login'))
        
        user_data = session.get('user', {})
        step_up_expires = user_data.get('step_up_expires')
        
        if step_up_expires:
            try:
                expires = datetime.fromisoformat(step_up_expires)
                if datetime.utcnow() < expires:
                    return f(*args, **kwargs)
            except (ValueError, TypeError):
                pass
        
        # Need step-up authentication
        session['step_up_required'] = True
        session['step_up_redirect'] = request.url
        flash('This action requires additional verification.', 'info')
        return redirect(url_for('wallet.step_up_auth'))
    
    return decorated_function


def complete_step_up_auth(duration_minutes: int = 5):
    """
    Mark step-up authentication as complete
    
    Args:
        duration_minutes: How long the step-up auth remains valid
    """
    if 'user' in session:
        session['user']['step_up_verified'] = True
        session['user']['step_up_expires'] = (
            datetime.utcnow() + timedelta(minutes=duration_minutes)
        ).isoformat()
        session.modified = True


# ============================================
# Security Utilities
# ============================================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token
    
    Args:
        length: Length of the token in bytes
    
    Returns:
        str: Hex-encoded token
    """
    return secrets.token_hex(length)


def hash_credential_id(credential_id: bytes) -> str:
    """
    Create a hash of a credential ID for logging purposes
    (Don't log raw credential IDs)
    
    Args:
        credential_id: The raw credential ID bytes
    
    Returns:
        str: SHA-256 hash of the credential ID
    """
    if isinstance(credential_id, str):
        credential_id = credential_id.encode()
    return hashlib.sha256(credential_id).hexdigest()[:16]


def validate_transaction_amount(amount) -> tuple:
    """
    Validate a transaction amount
    
    Args:
        amount: The amount to validate
    
    Returns:
        tuple: (is_valid, cleaned_amount or error_message)
    """
    try:
        # Convert to float
        amount = float(amount)
        
        # Check for negative or zero
        if amount <= 0:
            return False, "Amount must be positive"
        
        # Check for reasonable maximum
        max_amount = current_app.config.get('MAX_TRANSACTION_AMOUNT', 10000)
        if amount > max_amount:
            return False, f"Amount exceeds maximum of {max_amount}"
        
        # Round to 2 decimal places
        amount = round(amount, 2)
        
        return True, amount
    except (ValueError, TypeError):
        return False, "Invalid amount format"


def validate_email(email: str) -> bool:
    """
    Basic email validation
    
    Args:
        email: Email address to validate
    
    Returns:
        bool: True if valid format
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> tuple:
    """
    Validate username format
    
    Args:
        username: Username to validate
    
    Returns:
        tuple: (is_valid, error_message or None)
    """
    if not username:
        return False, "Username is required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 50:
        return False, "Username must be less than 50 characters"
    
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    return True, None


def sanitize_user_input(input_str: str, max_length: int = 255) -> str:
    """
    Sanitize user input to prevent XSS and other injection attacks
    
    Args:
        input_str: The string to sanitize
        max_length: Maximum allowed length
    
    Returns:
        str: Sanitized string
    """
    if not input_str:
        return ""
    
    import html
    import re
    
    # Convert to string if needed
    input_str = str(input_str)
    
    # Truncate to max length
    input_str = input_str[:max_length]
    
    # Remove null bytes
    input_str = input_str.replace('\x00', '')
    
    # HTML escape special characters
    input_str = html.escape(input_str, quote=True)
    
    # Remove control characters except newlines and tabs
    input_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', input_str)
    
    return input_str.strip()


# ============================================
# Audit Logging
# ============================================

def log_audit_event(
    user_id: int,
    event_type: str,
    event_data: dict = None,
    ip_address: str = None,
    user_agent: str = None
):
    """
    Log an audit event to the database
    
    Args:
        user_id: The user ID (can be None for failed logins)
        event_type: Type of event (login, logout, transaction, etc.)
        event_data: Additional event data as dict
        ip_address: Client IP address
        user_agent: Client user agent string
    """
    try:
        from app.main import db
        from app.models import AuditLog
        
        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            event_data=json.dumps(event_data) if event_data else None,
            ip_address=ip_address or get_client_ip(),
            user_agent=user_agent or request.headers.get('User-Agent', '')[:500]
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"Failed to log audit event: {e}")


def get_client_ip() -> str:
    """
    Get the client's real IP address, considering proxies
    
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers (when behind proxy/load balancer)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or 'unknown'


# ============================================
# Rate Limiting Helpers
# ============================================

_rate_limit_data = {}

def check_rate_limit(key: str, max_attempts: int = 5, window_seconds: int = 300) -> tuple:
    """
    Check if a rate limit has been exceeded (in-memory implementation)
    
    Args:
        key: Unique key for the rate limit (e.g., 'login:username')
        max_attempts: Maximum attempts allowed
        window_seconds: Time window in seconds
    
    Returns:
        tuple: (is_allowed, attempts_remaining, seconds_until_reset)
    """
    global _rate_limit_data
    current_time = time.time()
    
    if key not in _rate_limit_data:
        _rate_limit_data[key] = {
            'attempts': 0,
            'window_start': current_time
        }
    
    data = _rate_limit_data[key]
    
    # Reset if window has passed
    if current_time - data['window_start'] > window_seconds:
        data['attempts'] = 0
        data['window_start'] = current_time
    
    # Check limit
    if data['attempts'] >= max_attempts:
        seconds_remaining = int(window_seconds - (current_time - data['window_start']))
        return False, 0, seconds_remaining
    
    # Increment and allow
    data['attempts'] += 1
    attempts_remaining = max_attempts - data['attempts']
    seconds_until_reset = int(window_seconds - (current_time - data['window_start']))
    
    return True, attempts_remaining, seconds_until_reset


def reset_rate_limit(key: str):
    """
    Reset a rate limit counter
    
    Args:
        key: The rate limit key to reset
    """
    global _rate_limit_data
    if key in _rate_limit_data:
        del _rate_limit_data[key]


# ============================================
# WebAuthn Helpers
# ============================================

def format_credential_for_storage(credential_data) -> dict:
    """
    Format credential data for database storage
    
    Args:
        credential_data: Raw credential data from WebAuthn
    
    Returns:
        dict: Formatted credential data
    """
    return {
        'credential_id': credential_data.credential_id.hex() if hasattr(credential_data.credential_id, 'hex') else credential_data.credential_id,
        'public_key': credential_data.public_key.hex() if hasattr(credential_data.public_key, 'hex') else credential_data.public_key,
        'sign_count': credential_data.sign_count,
        'created_at': datetime.utcnow().isoformat()
    }


def bytes_to_base64url(data: bytes) -> str:
    """
    Convert bytes to base64url encoding (used by WebAuthn)
    
    Args:
        data: Bytes to encode
    
    Returns:
        str: Base64url encoded string
    """
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def base64url_to_bytes(data: str) -> bytes:
    """
    Convert base64url string to bytes
    
    Args:
        data: Base64url encoded string
    
    Returns:
        bytes: Decoded bytes
    """
    import base64
    # Add padding if needed
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)
