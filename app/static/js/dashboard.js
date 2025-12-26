/**
 * Dashboard JavaScript
 * Handles wallet operations and step-up authentication
 * Passwordless Digital Wallet - FIDO2/WebAuthn
 */

document.addEventListener('DOMContentLoaded', () => {
    const { showError, showSuccess, hexToBuffer, bufferToHex } = window.walletUtils;
    
    // Load initial data
    loadBalance();
    loadTransactions();
    
    // Form handlers
    const depositForm = document.getElementById('deposit-form');
    const transferForm = document.getElementById('transfer-form');
    const refreshBtn = document.getElementById('refresh-btn');
    
    if (depositForm) {
        depositForm.addEventListener('submit', handleDeposit);
    }
    
    if (transferForm) {
        transferForm.addEventListener('submit', handleTransfer);
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', (e) => {
            e.preventDefault();
            loadBalance();
            loadTransactions();
            showSuccess('Dashboard refreshed!');
        });
    }
});

// Load wallet balance
async function loadBalance() {
    const balanceEl = document.getElementById('balance-amount');
    
    try {
        const response = await fetch('/wallet/balance');
        
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }
            throw new Error('Failed to load balance');
        }
        
        const data = await response.json();
        balanceEl.innerHTML = `£${data.balance.toFixed(2)}<span class="balance-currency">${data.currency}</span>`;
        
    } catch (error) {
        console.error('Balance error:', error);
        balanceEl.textContent = '£0.00';
    }
}

// Load transaction history
async function loadTransactions() {
    const listEl = document.getElementById('transactions-list');
    
    try {
        const response = await fetch('/wallet/transactions?page=1&per_page=10');
        
        if (!response.ok) {
            throw new Error('Failed to load transactions');
        }
        
        const data = await response.json();
        displayTransactions(data.transactions);
        
    } catch (error) {
        console.error('Transactions error:', error);
        listEl.innerHTML = '<div class="no-transactions"><p>Failed to load transactions</p></div>';
    }
}

// Display transactions
function displayTransactions(transactions) {
    const listEl = document.getElementById('transactions-list');
    
    if (!transactions || transactions.length === 0) {
        listEl.innerHTML = `
            <div class="no-transactions">
                <span style="font-size: 3rem; margin-bottom: 1rem; display: block;">📋</span>
                <p>No transactions yet</p>
                <p style="font-size: 0.85rem; color: var(--text-muted);">Make your first deposit to get started!</p>
            </div>
        `;
        return;
    }
    
    listEl.innerHTML = transactions.map(tx => {
        const isPositive = tx.type === 'DEPOSIT' || tx.type === 'TRANSFER_IN';
        const amountClass = isPositive ? 'positive' : 'negative';
        const amountPrefix = isPositive ? '+' : '-';
        
        // Determine icon class
        let iconClass = 'deposit';
        if (tx.type === 'WITHDRAWAL') iconClass = 'withdrawal';
        if (tx.type.includes('TRANSFER')) iconClass = 'transfer';
        
        // Determine icon
        let icon = '💵';
        if (tx.type === 'WITHDRAWAL') icon = '💸';
        if (tx.type === 'TRANSFER_IN') icon = '📥';
        if (tx.type === 'TRANSFER_OUT') icon = '📤';
        
        return `
            <div class="transaction-item">
                <div class="transaction-info">
                    <div class="transaction-icon ${iconClass}">
                        ${icon}
                    </div>
                    <div class="transaction-details">
                        <h4>${formatTransactionType(tx.type)}</h4>
                        <p>${tx.description || 'No description'} • ${formatDate(tx.created_at)}</p>
                    </div>
                </div>
                <div class="transaction-amount ${amountClass}">
                    ${amountPrefix}£${tx.amount.toFixed(2)}
                </div>
            </div>
        `;
    }).join('');
}

// Format transaction type
function formatTransactionType(type) {
    const types = {
        'DEPOSIT': 'Deposit',
        'WITHDRAWAL': 'Withdrawal',
        'TRANSFER_IN': 'Transfer Received',
        'TRANSFER_OUT': 'Transfer Sent'
    };
    return types[type] || type;
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Handle deposit
async function handleDeposit(e) {
    e.preventDefault();
    
    const { showError, showSuccess, hexToBuffer, bufferToHex } = window.walletUtils;
    const amount = document.getElementById('deposit-amount').value;
    const description = document.getElementById('deposit-description').value || 'Deposit';
    const btn = document.getElementById('deposit-btn');
    
    if (!amount || parseFloat(amount) <= 0) {
        showError('Please enter a valid amount');
        return;
    }
    
    btn.disabled = true;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading-spinner" style="width: 20px; height: 20px; display: inline-block;"></span> Processing...';
    
    try {
        // Step 1: Begin deposit
        const beginResponse = await fetch('/wallet/deposit/begin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                amount: parseFloat(amount), 
                description 
            })
        });
        
        if (!beginResponse.ok) {
            const error = await beginResponse.json();
            throw new Error(error.error || 'Deposit failed');
        }
        
        const options = await beginResponse.json();
        
        // Step 2: Perform step-up authentication
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
        
        btn.innerHTML = '👆 Authenticate...';
        
        const assertion = await navigator.credentials.get({ publicKey });
        
        if (!assertion) {
            throw new Error('Authentication failed');
        }
        
        btn.innerHTML = '✅ Completing...';
        
        // Step 3: Complete deposit
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
        
        const completeResponse = await fetch('/wallet/deposit/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(assertionData)
        });
        
        if (!completeResponse.ok) {
            const error = await completeResponse.json();
            throw new Error(error.error || 'Deposit verification failed');
        }
        
        const result = await completeResponse.json();
        
        showSuccess(`🎉 Deposit successful! New balance: £${result.transaction.new_balance.toFixed(2)}`);
        
        // Reload data
        loadBalance();
        loadTransactions();
        
        // Reset form
        e.target.reset();
        
    } catch (error) {
        console.error('Deposit error:', error);
        
        let errorMessage = error.message;
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Authentication was cancelled or timed out.';
        }
        
        showError(errorMessage);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Handle transfer
async function handleTransfer(e) {
    e.preventDefault();
    
    const { showError, showSuccess, hexToBuffer, bufferToHex } = window.walletUtils;
    const recipient_email = document.getElementById('transfer-recipient').value;
    const amount = document.getElementById('transfer-amount').value;
    const description = document.getElementById('transfer-description').value || 'Transfer';
    const btn = document.getElementById('transfer-btn');
    
    if (!recipient_email) {
        showError('Please enter recipient email');
        return;
    }
    
    if (!amount || parseFloat(amount) <= 0) {
        showError('Please enter a valid amount');
        return;
    }
    
    btn.disabled = true;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading-spinner" style="width: 20px; height: 20px; display: inline-block;"></span> Processing...';
    
    try {
        // Step 1: Begin transfer
        const beginResponse = await fetch('/wallet/transfer/begin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                recipient_email, 
                amount: parseFloat(amount), 
                description 
            })
        });
        
        if (!beginResponse.ok) {
            const error = await beginResponse.json();
            throw new Error(error.error || 'Transfer failed');
        }
        
        const options = await beginResponse.json();
        
        // Step 2: Perform step-up authentication
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
        
        btn.innerHTML = '👆 Authenticate...';
        
        const assertion = await navigator.credentials.get({ publicKey });
        
        if (!assertion) {
            throw new Error('Authentication failed');
        }
        
        btn.innerHTML = '✅ Completing...';
        
        // Step 3: Complete transfer
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
        
        const completeResponse = await fetch('/wallet/transfer/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(assertionData)
        });
        
        if (!completeResponse.ok) {
            const error = await completeResponse.json();
            throw new Error(error.error || 'Transfer verification failed');
        }
        
        const result = await completeResponse.json();
        
        showSuccess(`🎉 Transfer successful! New balance: £${result.transaction.new_balance.toFixed(2)}`);
        
        // Reload data
        loadBalance();
        loadTransactions();
        
        // Reset form
        e.target.reset();
        
    } catch (error) {
        console.error('Transfer error:', error);
        
        let errorMessage = error.message;
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Authentication was cancelled or timed out.';
        }
        
        showError(errorMessage);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}
