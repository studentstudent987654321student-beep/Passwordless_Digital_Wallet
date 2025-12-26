/**
 * Main JavaScript - Common functionality
 * Passwordless Digital Wallet - WebAuthn (FIDO2)
 */

// Logout functionality
document.addEventListener('DOMContentLoaded', () => {
    const logoutBtn = document.getElementById('logout-btn');
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    window.location.href = '/';
                } else {
                    console.error('Logout failed');
                }
            } catch (error) {
                console.error('Logout error:', error);
            }
        });
    }
    
    // Add smooth scrolling and nav effects
    initNavEffects();
});

// Initialize navigation effects
function initNavEffects() {
    const navbar = document.querySelector('.navbar');
    
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.style.background = 'rgba(2, 6, 23, 0.95)';
                navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.3)';
            } else {
                navbar.style.background = 'rgba(2, 6, 23, 0.8)';
                navbar.style.boxShadow = 'none';
            }
        });
    }
}

// Utility functions
function showError(message, elementId = 'error-message') {
    const errorEl = document.getElementById(elementId);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
        errorEl.style.display = 'flex';
        setTimeout(() => {
            errorEl.classList.add('hidden');
            errorEl.style.display = 'none';
        }, 5000);
    }
}

function showSuccess(message, elementId = 'success-message') {
    const successEl = document.getElementById(elementId);
    if (successEl) {
        successEl.textContent = message;
        successEl.classList.remove('hidden');
        successEl.style.display = 'flex';
        setTimeout(() => {
            successEl.classList.add('hidden');
            successEl.style.display = 'none';
        }, 5000);
    }
}

function hideMessage(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.classList.add('hidden');
        el.style.display = 'none';
    }
}

// WebAuthn helper functions
function bufferToBase64(buffer) {
    return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}

function base64ToBuffer(base64) {
    const binary = atob(base64);
    const buffer = new ArrayBuffer(binary.length);
    const view = new Uint8Array(buffer);
    for (let i = 0; i < binary.length; i++) {
        view[i] = binary.charCodeAt(i);
    }
    return buffer;
}

function hexToBuffer(hex) {
    const bytes = new Uint8Array(hex.length / 2);
    for (let i = 0; i < hex.length; i += 2) {
        bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
    }
    return bytes.buffer;
}

function bufferToHex(buffer) {
    return Array.from(new Uint8Array(buffer))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
}

// Base64URL encoding/decoding
function base64UrlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const padding = base64.length % 4;
    const padded = padding ? base64 + '='.repeat(4 - padding) : base64;
    return base64ToBuffer(padded);
}

function bufferToBase64Url(buffer) {
    const base64 = bufferToBase64(buffer);
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// Check browser support for WebAuthn
function checkWebAuthnSupport() {
    if (!window.PublicKeyCredential) {
        showError('Your browser does not support WebAuthn. Please use a modern browser like Chrome, Edge, or Safari.');
        return false;
    }
    return true;
}

// Check if platform authenticator is available
async function isPlatformAuthenticatorAvailable() {
    try {
        return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    } catch (e) {
        return false;
    }
}

// Set loading state on button
function setButtonLoading(button, loading) {
    if (loading) {
        button.classList.add('loading');
        button.disabled = true;
    } else {
        button.classList.remove('loading');
        button.disabled = false;
    }
}

// Export for use in other scripts
window.walletUtils = {
    showError,
    showSuccess,
    hideMessage,
    bufferToBase64,
    base64ToBuffer,
    hexToBuffer,
    bufferToHex,
    base64UrlToBuffer,
    bufferToBase64Url,
    checkWebAuthnSupport,
    isPlatformAuthenticatorAvailable,
    setButtonLoading
};
