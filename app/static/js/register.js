/**
 * Registration page JavaScript
 * Handles WebAuthn registration flow
 * Passwordless Digital Wallet - FIDO2/WebAuthn
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('register-form');
    const registerBtn = document.getElementById('register-btn');
    const { 
        showError, 
        showSuccess, 
        hexToBuffer, 
        bufferToHex, 
        checkWebAuthnSupport,
        setButtonLoading 
    } = window.walletUtils;
    
    if (!checkWebAuthnSupport()) {
        registerBtn.disabled = true;
        return;
    }
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email').value.trim();
        const displayName = document.getElementById('display-name').value.trim();
        const gdprConsent = document.getElementById('gdpr-consent').checked;
        
        if (!gdprConsent) {
            showError('You must consent to data processing to continue.');
            return;
        }
        
        if (!email || !displayName) {
            showError('Please fill in all required fields.');
            return;
        }
        
        setButtonLoading(registerBtn, true);
        
        try {
            // Step 1: Begin registration
            const beginResponse = await fetch('/auth/register/begin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    display_name: displayName
                })
            });
            
            if (!beginResponse.ok) {
                const error = await beginResponse.json();
                throw new Error(error.error || 'Registration failed');
            }
            
            const options = await beginResponse.json();
            
            // Step 2: Create credential with WebAuthn
            const publicKey = {
                challenge: hexToBuffer(options.publicKey.challenge),
                rp: options.publicKey.rp,
                user: {
                    id: new TextEncoder().encode(options.publicKey.user.id),
                    name: options.publicKey.user.name,
                    displayName: options.publicKey.user.displayName
                },
                pubKeyCredParams: options.publicKey.pubKeyCredParams,
                timeout: options.publicKey.timeout || 60000,
                attestation: options.publicKey.attestation || 'none',
                authenticatorSelection: options.publicKey.authenticatorSelection || {
                    authenticatorAttachment: 'platform',
                    userVerification: 'required',
                    residentKey: 'preferred'
                }
            };
            
            // Add excludeCredentials if present
            if (options.publicKey.excludeCredentials) {
                publicKey.excludeCredentials = options.publicKey.excludeCredentials.map(cred => ({
                    ...cred,
                    id: hexToBuffer(cred.id)
                }));
            }
            
            const credential = await navigator.credentials.create({ publicKey });
            
            if (!credential) {
                throw new Error('Credential creation failed');
            }
            
            // Step 3: Send credential to server
            const credentialData = {
                id: credential.id,
                rawId: bufferToHex(credential.rawId),
                type: credential.type,
                response: {
                    clientDataJSON: bufferToHex(credential.response.clientDataJSON),
                    attestationObject: bufferToHex(credential.response.attestationObject)
                }
            };
            
            const completeResponse = await fetch('/auth/register/complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(credentialData)
            });
            
            if (!completeResponse.ok) {
                const error = await completeResponse.json();
                throw new Error(error.error || 'Registration verification failed');
            }
            
            const result = await completeResponse.json();
            
            showSuccess('🎉 Registration successful! Redirecting to login...');
            
            // Redirect to login page
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
            
        } catch (error) {
            console.error('Registration error:', error);
            
            let errorMessage = error.message;
            
            // Handle specific WebAuthn errors
            if (error.name === 'NotAllowedError') {
                errorMessage = 'Registration was cancelled or timed out. Please try again.';
            } else if (error.name === 'NotSupportedError') {
                errorMessage = 'Your device does not support the required authentication method.';
            } else if (error.name === 'InvalidStateError') {
                errorMessage = 'This authenticator is already registered. Try logging in instead.';
            } else if (error.name === 'SecurityError') {
                errorMessage = 'Security error. Please ensure you are using HTTPS.';
            } else if (error.name === 'AbortError') {
                errorMessage = 'Registration was cancelled.';
            }
            
            showError(errorMessage);
            setButtonLoading(registerBtn, false);
        }
    });
});
