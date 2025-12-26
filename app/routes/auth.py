"""
WebAuthn authentication routes.
Implements FIDO2 registration and authentication flows.
"""
from flask import Blueprint, request, jsonify, session, current_app, render_template
from fido2.server import Fido2Server
from fido2.webauthn import (
    PublicKeyCredentialRpEntity, 
    UserVerificationRequirement,
    AuthenticatorAttestationResponse,
    AuthenticatorAssertionResponse,
    CollectedClientData,
    AttestationObject,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType
)
from fido2 import cbor
import secrets
import base64

from app.main import db, limiter
from app.models import User, WebAuthnCredential
from app.utils import (
    log_audit_event, 
    store_challenge, 
    get_challenge,
    validate_email,
    sanitize_user_input
)

auth_bp = Blueprint('auth', __name__)


def get_fido2_server():
    """Create and return a configured FIDO2 server instance."""
    rp = PublicKeyCredentialRpEntity(
        id=current_app.config['RP_ID'],
        name=current_app.config['RP_NAME']
    )
    return Fido2Server(rp)


@auth_bp.route('/register/begin', methods=['POST'])
@limiter.limit("5 per minute")
def register_begin():
    """
    Begin WebAuthn registration process.
    Generates a challenge and registration options.
    """
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        display_name = sanitize_user_input(data.get('display_name', ''))
        
        if not email or not display_name:
            return jsonify({'error': 'Email and display name are required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User already exists'}), 409
        
        # Create temporary user ID for this registration session
        temp_user_id = f"temp_{secrets.token_urlsafe(16)}"
        
        # Generate registration options
        server = get_fido2_server()
        options, state = server.register_begin(
            user={
                'id': temp_user_id.encode('utf-8'),
                'name': email,
                'displayName': display_name
            },
            user_verification=UserVerificationRequirement.PREFERRED,
            authenticator_attachment='platform'  # Prefer platform authenticators (Touch ID, Windows Hello)
        )
        
        # In fido2 1.1.x, options is CredentialCreationOptions with public_key attribute
        public_key_options = options.public_key
        challenge = public_key_options.challenge
        
        # Store challenge in memory
        store_challenge(temp_user_id, challenge)
        
        # Store registration state in session
        session['registration_state'] = {
            'temp_user_id': temp_user_id,
            'email': email,
            'display_name': display_name,
            'state': cbor.encode(state).hex()
        }
        session.modified = True
        
        current_app.logger.info(f"Registration begun for {email}")
        
        # Build pubKeyCredParams list
        pub_key_cred_params = []
        for param in public_key_options.pub_key_cred_params:
            pub_key_cred_params.append({
                'type': param.type,
                'alg': param.alg
            })
        
        # Return registration options to client
        return jsonify({
            'publicKey': {
                'challenge': challenge.hex(),
                'rp': {
                    'name': public_key_options.rp.name,
                    'id': public_key_options.rp.id
                },
                'user': {
                    'id': temp_user_id,
                    'name': email,
                    'displayName': display_name
                },
                'pubKeyCredParams': pub_key_cred_params,
                'timeout': 60000,
                'attestation': 'none',
                'authenticatorSelection': {
                    'authenticatorAttachment': 'platform',
                    'requireResidentKey': False,
                    'userVerification': 'preferred'
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Registration begin error: {e}")
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/register/complete', methods=['POST'])
@limiter.limit("5 per minute")
def register_complete():
    """
    Complete WebAuthn registration.
    Verifies the attestation and creates the user account.
    """
    try:
        data = request.get_json()
        reg_state = session.get('registration_state')
        
        if not reg_state:
            return jsonify({'error': 'No registration in progress'}), 400
        
        temp_user_id = reg_state['temp_user_id']
        email = reg_state['email']
        display_name = reg_state['display_name']
        
        # Retrieve challenge
        challenge = get_challenge(temp_user_id)
        if not challenge:
            return jsonify({'error': 'Challenge expired or invalid'}), 400
        
        # Decode state
        state = cbor.decode(bytes.fromhex(reg_state['state']))
        
        # Parse client response using fido2 1.1.x classes
        client_data = CollectedClientData(bytes.fromhex(data['response']['clientDataJSON']))
        attestation_object = AttestationObject(bytes.fromhex(data['response']['attestationObject']))
        
        # Verify attestation
        server = get_fido2_server()
        auth_data = server.register_complete(state, client_data, attestation_object)
        
        # Create user account
        user = User(
            email=email,
            display_name=display_name,
            gdpr_consent=True
        )
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Store credential - auth_data is AuthenticatorData
        # credential_data is AttestedCredentialData with: aaguid, credential_id, public_key
        # counter (sign_count) is on auth_data itself
        # public_key is a CoseKey object, need to serialize to bytes
        cred_data = auth_data.credential_data
        credential = WebAuthnCredential(
            user_id=user.id,
            credential_id=bytes(cred_data.credential_id),
            public_key=cbor.encode(dict(cred_data.public_key)),
            sign_count=auth_data.counter,
            aaguid=str(cred_data.aaguid) if cred_data.aaguid else None,
            device_name=f"Device registered on {user.created_at.strftime('%Y-%m-%d')}"
        )
        db.session.add(credential)
        
        # Create wallet for user
        from app.models import Wallet
        wallet = Wallet(user_id=user.id)
        db.session.add(wallet)
        
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            user_id=user.id,
            event_type='REGISTRATION',
            event_data={'description': f'User registered with email {email}'}
        )
        
        # Clear registration state
        session.pop('registration_state', None)
        session.modified = True
        
        current_app.logger.info(f"Registration completed for {email}")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'email': user.email,
                'display_name': user.display_name
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration complete error: {e}")
        return jsonify({'error': 'Registration verification failed'}), 500


@auth_bp.route('/login/begin', methods=['POST'])
@limiter.limit("10 per minute")
def login_begin():
    """
    Begin WebAuthn authentication.
    Generates a challenge for login.
    """
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Find user
        user = User.query.filter_by(email=email, is_active=True).first()
        if not user:
            # Don't reveal if user exists - return generic error
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Get user's credentials
        credentials = WebAuthnCredential.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        if not credentials:
            return jsonify({'error': 'No credentials found'}), 401
        
        # Generate authentication options
        # Build proper credential descriptors for fido2 1.1.x
        credential_descriptors = [
            PublicKeyCredentialDescriptor(
                type=PublicKeyCredentialType.PUBLIC_KEY,
                id=cred.credential_id
            ) for cred in credentials
        ]
        
        server = get_fido2_server()
        options, state = server.authenticate_begin(
            credentials=credential_descriptors,
            user_verification=UserVerificationRequirement.PREFERRED
        )
        
        # In fido2 1.1.x, options is CredentialRequestOptions with public_key attribute
        public_key_options = options.public_key
        challenge = public_key_options.challenge
        
        # Store challenge
        store_challenge(user.user_id, challenge)
        
        # Store authentication state
        session['auth_state'] = {
            'user_id': user.user_id,
            'email': email,
            'state': cbor.encode(state).hex()
        }
        session.modified = True
        
        current_app.logger.info(f"Login begun for {email}")
        
        return jsonify({
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
                'userVerification': 'preferred'
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login begin error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500


@auth_bp.route('/login/complete', methods=['POST'])
@limiter.limit("10 per minute")
def login_complete():
    """
    Complete WebAuthn authentication.
    Verifies the assertion and creates a session.
    """
    try:
        data = request.get_json()
        auth_state = session.get('auth_state')
        
        if not auth_state:
            return jsonify({'error': 'No authentication in progress'}), 400
        
        user_id = auth_state['user_id']
        email = auth_state['email']
        
        # Retrieve challenge
        challenge = get_challenge(user_id)
        if not challenge:
            return jsonify({'error': 'Challenge expired or invalid'}), 400
        
        # Decode state
        state = cbor.decode(bytes.fromhex(auth_state['state']))
        
        # Find user and credential
        user = User.query.filter_by(user_id=user_id, is_active=True).first()
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        credential_id = bytes.fromhex(data['rawId'])
        credential = WebAuthnCredential.query.filter_by(
            credential_id=credential_id,
            user_id=user.id,
            is_active=True
        ).first()
        
        if not credential:
            return jsonify({'error': 'Credential not found'}), 401
        
        # Parse client response using fido2 1.1.x classes
        from fido2.webauthn import AuthenticatorData, AttestedCredentialData, Aaguid
        from fido2.cose import CoseKey
        
        client_data = CollectedClientData(bytes.fromhex(data['response']['clientDataJSON']))
        auth_data = AuthenticatorData(bytes.fromhex(data['response']['authenticatorData']))
        signature = bytes.fromhex(data['response']['signature'])
        
        # Decode stored public key and build AttestedCredentialData
        stored_public_key = CoseKey.parse(cbor.decode(credential.public_key))
        
        # Build AttestedCredentialData for verification
        # aaguid can be zeros if not stored
        aaguid_bytes = bytes.fromhex(credential.aaguid.replace('-', '')) if credential.aaguid else bytes(16)
        attested_cred_data = AttestedCredentialData.create(
            aaguid_bytes,
            credential.credential_id,
            stored_public_key
        )
        
        # Verify assertion
        server = get_fido2_server()
        server.authenticate_complete(
            state,
            [attested_cred_data],
            credential_id,
            client_data,
            auth_data,
            signature
        )
        
        # Update credential
        credential.sign_count += 1
        credential.last_used = db.func.now()
        db.session.commit()
        
        # Create session
        session.clear()
        session['user_id'] = user.user_id
        session['email'] = user.email
        session['authenticated'] = True
        session.permanent = True
        session.modified = True
        
        # Log audit event
        log_audit_event(
            user_id=user.id,
            event_type='LOGIN',
            event_data={'description': f'User {email} logged in successfully'}
        )
        
        current_app.logger.info(f"Login completed for {email}")
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'email': user.email,
                'display_name': user.display_name
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Login complete error: {e}")
        
        # Log failed attempt
        if 'auth_state' in session:
            user = User.query.filter_by(email=session['auth_state']['email']).first()
            if user:
                log_audit_event(
                    user_id=user.id,
                    event_type='LOGIN_FAILED',
                    event_data={'description': 'Authentication verification failed', 'error': str(e)}
                )
        
        return jsonify({'error': 'Authentication verification failed'}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user and clear session."""
    try:
        user_id = session.get('user_id')
        email = session.get('email')
        
        if user_id:
            user = User.query.filter_by(user_id=user_id).first()
            if user:
                log_audit_event(
                    user_id=user.id,
                    event_type='LOGOUT',
                    event_data={'description': f'User {email} logged out'}
                )
        
        session.clear()
        current_app.logger.info(f"User {email} logged out")
        
        return jsonify({'success': True, 'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """Check authentication status."""
    if session.get('authenticated'):
        return jsonify({
            'authenticated': True,
            'email': session.get('email')
        }), 200
    return jsonify({'authenticated': False}), 200
