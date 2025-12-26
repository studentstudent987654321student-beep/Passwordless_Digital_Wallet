/**
 * Login page JavaScript
 * Handles WebAuthn authentication flow
 * Passwordless Digital Wallet - FIDO2/WebAuthn
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('login-form');
    const loginBtn = document.getElementById('login-btn');
    const { 
        showError, 
        showSuccess, 
        hexToBuffer, 
        bufferToHex, 
        checkWebAuthnSupport,
        setButtonLoading 
    } = window.walletUtils;
    
    if (!checkWebAuthnSupport()) {
        loginBtn.disabled = true;
        return;
    }
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email').value.trim();
        
        if (!email) {
            showError('Please enter your email address.');
            return;
        }
        
        setButtonLoading(loginBtn, true);
        
        try {
            // Step 1: Begin authentication
            const beginResponse = await fetch('/auth/login/begin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email })
            });
            
            if (!beginResponse.ok) {
                const error = await beginResponse.json();
                throw new Error(error.error || 'Authentication failed');
            }
            
            const options = await beginResponse.json();
            
            // Step 2: Get credential with WebAuthn
            const publicKey = {
                challenge: hexToBuffer(options.publicKey.challenge),
                timeout: options.publicKey.timeout || 60000,
                rpId: options.publicKey.rpId,
                allowCredentials: options.publicKey.allowCredentials.map(cred => ({
                    type: cred.type,
                    id: hexToBuffer(cred.id),
                    transports: cred.transports || ['internal', 'hybrid']
                })),
                userVerification: options.publicKey.userVerification || 'required'
            };
            
            const assertion = await navigator.credentials.get({ publicKey });
            
            if (!assertion) {
                throw new Error('Authentication failed');
            }
            
            // Step 3: Send assertion to server
            const assertionData = {
                id: assertion.id,
                rawId: bufferToHex(assertion.rawId),
                type: assertion.type,
                response: {
                    clientDataJSON: bufferToHex(assertion.response.clientDataJSON),
                    authenticatorData: bufferToHex(assertion.response.authenticatorData),
                    signature: bufferToHex(assertion.response.signature)
                }
            };
            
            // Add userHandle if available
            if (assertion.response.userHandle) {
                assertionData.response.userHandle = bufferToHex(assertion.response.userHandle);
            }
            
            const completeResponse = await fetch('/auth/login/complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(assertionData)
            });
            
            if (!completeResponse.ok) {
                const error = await completeResponse.json();
                throw new Error(error.error || 'Authentication verification failed');
            }
            
            const result = await completeResponse.json();
            
            showSuccess('🎉 Login successful! Redirecting...');
            
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
            
        } catch (error) {
            console.error('Login error:', error);
            
            let errorMessage = error.message;
            
            // Handle specific WebAuthn errors
            if (error.name === 'NotAllowedError') {
                errorMessage = 'Authentication was cancelled or timed out. Please try again.';
            } else if (error.name === 'NotSupportedError') {
                errorMessage = 'Your device does not support the required authentication method.';
            } else if (error.name === 'InvalidStateError') {
                errorMessage = 'No credentials found. Please register first.';
            } else if (error.name === 'SecurityError') {
                errorMessage = 'Security error. Please ensure you are using HTTPS.';
            } else if (error.name === 'AbortError') {
                errorMessage = 'Authentication was cancelled.';
            }
            
            showError(errorMessage);
            setButtonLoading(loginBtn, false);
        }
    });
});
