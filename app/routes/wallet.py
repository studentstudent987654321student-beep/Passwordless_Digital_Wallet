"""
Digital wallet routes.
Handles wallet operations and transactions with step-up authentication.
"""
from flask import Blueprint, request, jsonify, session, current_app
from decimal import Decimal, InvalidOperation
from fido2.server import Fido2Server
from fido2.webauthn import (
    PublicKeyCredentialRpEntity, 
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    CollectedClientData,
    AuthenticatorData,
    AttestedCredentialData
)
from fido2.cose import CoseKey
from fido2 import cbor

from app.main import db, limiter
from app.models import User, Wallet, Transaction, WebAuthnCredential
from app.utils import (
    log_audit_event,
    store_challenge,
    get_challenge,
    sanitize_user_input
)

wallet_bp = Blueprint('wallet', __name__)


def login_required(f):
    """Decorator to require authentication."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get the currently authenticated user."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.filter_by(user_id=user_id, is_active=True).first()


def verify_step_up_auth(user, data, state, credential):
    """
    Verify step-up authentication for transactions.
    Returns True if verification succeeds, raises exception otherwise.
    """
    # Parse client response using fido2 1.1.x classes
    client_data = CollectedClientData(bytes.fromhex(data['response']['clientDataJSON']))
    auth_data = AuthenticatorData(bytes.fromhex(data['response']['authenticatorData']))
    signature = bytes.fromhex(data['response']['signature'])
    
    # Decode stored public key and build AttestedCredentialData
    stored_public_key = CoseKey.parse(cbor.decode(credential.public_key))
    
    # Build AttestedCredentialData for verification
    aaguid_bytes = bytes.fromhex(credential.aaguid.replace('-', '')) if credential.aaguid else bytes(16)
    attested_cred_data = AttestedCredentialData.create(
        aaguid_bytes,
        credential.credential_id,
        stored_public_key
    )
    
    # Verify assertion
    rp = PublicKeyCredentialRpEntity(
        id=current_app.config['RP_ID'],
        name=current_app.config['RP_NAME']
    )
    server = Fido2Server(rp)
    server.authenticate_complete(
        state,
        [attested_cred_data],
        bytes.fromhex(data['rawId']),
        client_data,
        auth_data,
        signature
    )
    return True


@wallet_bp.route('/balance', methods=['GET'])
@login_required
@limiter.limit("30 per minute")
def get_balance():
    """Get current wallet balance."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        wallet = Wallet.query.filter_by(user_id=user.id, is_active=True).first()
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        return jsonify({
            'balance': float(wallet.balance),
            'currency': wallet.currency,
            'wallet_id': wallet.wallet_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get balance error: {e}")
        return jsonify({'error': 'Failed to retrieve balance'}), 500


@wallet_bp.route('/transactions', methods=['GET'])
@login_required
@limiter.limit("30 per minute")
def get_transactions():
    """Get transaction history."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        wallet = Wallet.query.filter_by(user_id=user.id, is_active=True).first()
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)  # Max 100 per page
        
        # Query transactions
        transactions_query = Transaction.query.filter_by(wallet_id=wallet.id)\
            .order_by(Transaction.created_at.desc())
        
        paginated = transactions_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        transactions = [{
            'transaction_id': t.transaction_id,
            'type': t.transaction_type,
            'amount': float(t.amount),
            'currency': t.currency,
            'description': t.description,
            'recipient_email': t.recipient_email,
            'status': t.status,
            'created_at': t.created_at.isoformat(),
            'completed_at': t.completed_at.isoformat() if t.completed_at else None,
            'webauthn_verified': t.webauthn_verified
        } for t in paginated.items]
        
        return jsonify({
            'transactions': transactions,
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get transactions error: {e}")
        return jsonify({'error': 'Failed to retrieve transactions'}), 500


@wallet_bp.route('/deposit/begin', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def deposit_begin():
    """
    Begin deposit process - requires step-up authentication.
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        amount_str = data.get('amount')
        description = sanitize_user_input(data.get('description', 'Deposit'))
        
        # Validate amount with clear messages
        if amount_str is None or amount_str == '':
            return jsonify({'error': 'Please enter an amount'}), 400
            
        try:
            amount = Decimal(str(amount_str))
            if amount <= 0:
                return jsonify({'error': 'Amount must be greater than zero'}), 400
            if amount > 10000:
                return jsonify({'error': 'Maximum deposit amount is £10,000'}), 400
            if amount < 1:
                return jsonify({'error': 'Minimum deposit amount is £1'}), 400
        except (InvalidOperation, TypeError, ValueError):
            return jsonify({'error': 'Please enter a valid number'}), 400
        
        # Get user's credentials for step-up auth
        credentials = WebAuthnCredential.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        if not credentials:
            return jsonify({'error': 'No credentials found. Please register a device first.'}), 401
        
        # Generate authentication challenge for step-up using fido2 1.1.x API
        rp = PublicKeyCredentialRpEntity(
            id=current_app.config['RP_ID'],
            name=current_app.config['RP_NAME']
        )
        server = Fido2Server(rp)
        
        # Build proper credential descriptors
        credential_descriptors = [
            PublicKeyCredentialDescriptor(
                type=PublicKeyCredentialType.PUBLIC_KEY,
                id=cred.credential_id
            ) for cred in credentials
        ]
        
        options, state = server.authenticate_begin(
            credentials=credential_descriptors,
            user_verification=UserVerificationRequirement.REQUIRED
        )
        
        # In fido2 1.1.x, options is CredentialRequestOptions with public_key attribute
        public_key_options = options.public_key
        challenge = public_key_options.challenge
        
        transaction_id = f"dep_{user.user_id}_{challenge.hex()[:16]}"
        store_challenge(transaction_id, challenge)
        
        # Store transaction intent in session
        session['pending_deposit'] = {
            'transaction_id': transaction_id,
            'amount': str(amount),
            'description': description,
            'state': cbor.encode(state).hex()
        }
        session.modified = True
        
        current_app.logger.info(f"Deposit begun for user {user.email}: {amount}")
        
        return jsonify({
            'transaction_id': transaction_id,
            'publicKey': {
                'challenge': challenge.hex(),
                'timeout': 60000,
                'rpId': current_app.config['RP_ID'],
                'allowCredentials': [
                    {
                        'type': 'public-key',
                        'id': cred.credential_id.hex()
                    } for cred in credentials
                ],
                'userVerification': 'required'
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Deposit begin error: {e}")
        return jsonify({'error': 'Failed to initiate deposit. Please try again.'}), 500


@wallet_bp.route('/deposit/complete', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def deposit_complete():
    """
    Complete deposit after step-up authentication.
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        pending = session.get('pending_deposit')
        
        if not pending:
            return jsonify({'error': 'No pending deposit. Please start again.'}), 400
        
        transaction_id = pending['transaction_id']
        
        # Retrieve challenge
        challenge = get_challenge(transaction_id)
        if not challenge:
            return jsonify({'error': 'Session expired. Please try again.'}), 400
        
        # Decode state
        state = cbor.decode(bytes.fromhex(pending['state']))
        
        # Find credential
        credential_id = bytes.fromhex(data['rawId'])
        credential = WebAuthnCredential.query.filter_by(
            credential_id=credential_id,
            user_id=user.id,
            is_active=True
        ).first()
        
        if not credential:
            return jsonify({'error': 'Credential not found'}), 401
        
        # Verify step-up authentication
        verify_step_up_auth(user, data, state, credential)
        
        # Authentication successful - process deposit
        wallet = Wallet.query.filter_by(user_id=user.id, is_active=True).first()
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        amount = Decimal(pending['amount'])
        
        # Create transaction record
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type='DEPOSIT',
            amount=amount,
            currency=wallet.currency,
            description=pending['description'],
            status='COMPLETED',
            completed_at=db.func.now(),
            webauthn_verified=True
        )
        db.session.add(transaction)
        
        # Update wallet balance
        wallet.balance += amount
        
        # Update credential usage
        credential.sign_count += 1
        credential.last_used = db.func.now()
        
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            user_id=user.id,
            event_type='DEPOSIT',
            event_data={'description': f'Deposit of {amount} {wallet.currency} completed', 'amount': str(amount)}
        )
        
        # Clear pending transaction
        session.pop('pending_deposit', None)
        session.modified = True
        
        current_app.logger.info(f"Deposit completed for user {user.email}: {amount}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully deposited £{amount}',
            'transaction': {
                'transaction_id': transaction.transaction_id,
                'amount': float(transaction.amount),
                'currency': transaction.currency,
                'new_balance': float(wallet.balance)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Deposit complete error: {e}")
        return jsonify({'error': 'Deposit verification failed. Please try again.'}), 500


@wallet_bp.route('/transfer/begin', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def transfer_begin():
    """
    Begin transfer to another user - requires step-up authentication.
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        recipient_email = data.get('recipient_email', '').lower().strip()
        amount_str = data.get('amount')
        description = sanitize_user_input(data.get('description', 'Transfer'))
        
        # Validate recipient with clear messages
        if not recipient_email:
            return jsonify({'error': 'Please enter recipient email address'}), 400
        if recipient_email == user.email:
            return jsonify({'error': 'You cannot transfer to yourself'}), 400
        
        recipient = User.query.filter_by(email=recipient_email, is_active=True).first()
        if not recipient:
            return jsonify({'error': 'Recipient not found. Please check the email address.'}), 404
        
        # Validate amount with clear messages
        if amount_str is None or amount_str == '':
            return jsonify({'error': 'Please enter an amount'}), 400
            
        try:
            amount = Decimal(str(amount_str))
            if amount <= 0:
                return jsonify({'error': 'Amount must be greater than zero'}), 400
            if amount < 1:
                return jsonify({'error': 'Minimum transfer amount is £1'}), 400
        except (InvalidOperation, TypeError, ValueError):
            return jsonify({'error': 'Please enter a valid number'}), 400
        
        # Check balance
        wallet = Wallet.query.filter_by(user_id=user.id, is_active=True).first()
        if not wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        if wallet.balance < amount:
            return jsonify({'error': f'Insufficient balance. Your balance is £{wallet.balance}'}), 400
        
        # Get credentials for step-up auth
        credentials = WebAuthnCredential.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        if not credentials:
            return jsonify({'error': 'No credentials found. Please register a device first.'}), 401
        
        # Generate challenge using fido2 1.1.x API
        rp = PublicKeyCredentialRpEntity(
            id=current_app.config['RP_ID'],
            name=current_app.config['RP_NAME']
        )
        server = Fido2Server(rp)
        
        # Build proper credential descriptors
        credential_descriptors = [
            PublicKeyCredentialDescriptor(
                type=PublicKeyCredentialType.PUBLIC_KEY,
                id=cred.credential_id
            ) for cred in credentials
        ]
        
        options, state = server.authenticate_begin(
            credentials=credential_descriptors,
            user_verification=UserVerificationRequirement.REQUIRED
        )
        
        public_key_options = options.public_key
        challenge = public_key_options.challenge
        
        transaction_id = f"txf_{user.user_id}_{challenge.hex()[:16]}"
        store_challenge(transaction_id, challenge)
        
        # Store transfer intent
        session['pending_transfer'] = {
            'transaction_id': transaction_id,
            'recipient_email': recipient_email,
            'recipient_id': recipient.id,
            'amount': str(amount),
            'description': description,
            'state': cbor.encode(state).hex()
        }
        session.modified = True
        
        current_app.logger.info(f"Transfer begun from {user.email} to {recipient_email}: {amount}")
        
        return jsonify({
            'transaction_id': transaction_id,
            'recipient': {
                'email': recipient.email,
                'display_name': recipient.display_name
            },
            'publicKey': {
                'challenge': challenge.hex(),
                'timeout': 60000,
                'rpId': current_app.config['RP_ID'],
                'allowCredentials': [
                    {
                        'type': 'public-key',
                        'id': cred.credential_id.hex()
                    } for cred in credentials
                ],
                'userVerification': 'required'
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Transfer begin error: {e}")
        return jsonify({'error': 'Failed to initiate transfer. Please try again.'}), 500


@wallet_bp.route('/transfer/complete', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def transfer_complete():
    """
    Complete transfer after step-up authentication.
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        pending = session.get('pending_transfer')
        
        if not pending:
            return jsonify({'error': 'No pending transfer. Please start again.'}), 400
        
        transaction_id = pending['transaction_id']
        
        # Retrieve and verify challenge
        challenge = get_challenge(transaction_id)
        if not challenge:
            return jsonify({'error': 'Session expired. Please try again.'}), 400
        
        state = cbor.decode(bytes.fromhex(pending['state']))
        
        # Verify credential
        credential_id = bytes.fromhex(data['rawId'])
        credential = WebAuthnCredential.query.filter_by(
            credential_id=credential_id,
            user_id=user.id,
            is_active=True
        ).first()
        
        if not credential:
            return jsonify({'error': 'Credential not found'}), 401
        
        # Verify step-up authentication
        verify_step_up_auth(user, data, state, credential)
        
        # Process transfer
        sender_wallet = Wallet.query.filter_by(user_id=user.id, is_active=True).first()
        recipient = User.query.get(pending['recipient_id'])
        recipient_wallet = Wallet.query.filter_by(user_id=recipient.id, is_active=True).first()
        
        if not sender_wallet or not recipient_wallet:
            return jsonify({'error': 'Wallet not found'}), 404
        
        amount = Decimal(pending['amount'])
        
        # Double-check balance
        if sender_wallet.balance < amount:
            return jsonify({'error': f'Insufficient balance. Your balance is £{sender_wallet.balance}'}), 400
        
        # Create outgoing transaction
        outgoing = Transaction(
            wallet_id=sender_wallet.id,
            transaction_type='TRANSFER_OUT',
            amount=amount,
            currency=sender_wallet.currency,
            description=pending['description'],
            recipient_email=pending['recipient_email'],
            status='COMPLETED',
            completed_at=db.func.now(),
            webauthn_verified=True
        )
        db.session.add(outgoing)
        
        # Create incoming transaction
        incoming = Transaction(
            wallet_id=recipient_wallet.id,
            transaction_type='TRANSFER_IN',
            amount=amount,
            currency=recipient_wallet.currency,
            description=f"Transfer from {user.email}",
            recipient_email=user.email,
            status='COMPLETED',
            completed_at=db.func.now(),
            webauthn_verified=True
        )
        db.session.add(incoming)
        
        # Update balances
        sender_wallet.balance -= amount
        recipient_wallet.balance += amount
        
        # Update credential
        credential.sign_count += 1
        credential.last_used = db.func.now()
        
        db.session.commit()
        
        # Log audit events
        log_audit_event(
            user_id=user.id,
            event_type='TRANSFER_OUT',
            event_data={'description': f'Transfer of {amount} to {pending["recipient_email"]}', 'amount': str(amount), 'recipient': pending['recipient_email']}
        )
        log_audit_event(
            user_id=recipient.id,
            event_type='TRANSFER_IN',
            event_data={'description': f'Received {amount} from {user.email}', 'amount': str(amount), 'sender': user.email}
        )
        
        # Clear pending transfer
        session.pop('pending_transfer', None)
        session.modified = True
        
        current_app.logger.info(f"Transfer completed: {user.email} -> {recipient.email}: {amount}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully transferred £{amount} to {pending["recipient_email"]}',
            'transaction': {
                'transaction_id': outgoing.transaction_id,
                'amount': float(amount),
                'recipient': pending['recipient_email'],
                'new_balance': float(sender_wallet.balance)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Transfer complete error: {e}")
        return jsonify({'error': 'Transfer verification failed. Please try again.'}), 500
