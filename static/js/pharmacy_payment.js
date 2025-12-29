// Pharmacy Payment Processing JavaScript

let selectedPaymentMethod = null;

document.addEventListener('DOMContentLoaded', function() {
    initializePaymentForm();
});

function selectPaymentMethod(method) {
    selectedPaymentMethod = method;
    
    // Update UI
    document.querySelectorAll('.payment-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    document.querySelector(`[data-method="${method}"]`).classList.add('selected');
    
    // Show payment form
    const paymentForm = document.getElementById('paymentForm');
    paymentForm.style.display = 'block';
    
    // Hide all method forms
    document.querySelectorAll('.method-form').forEach(form => {
        form.style.display = 'none';
    });
    
    // Show selected method form
    const formMap = {
        'mobile_money': 'mobileMoneyForm',
        'cash': 'cashForm',
        'card': 'cardForm',
        'insurance': 'insuranceForm'
    };
    
    const formId = formMap[method];
    if (formId) {
        document.getElementById(formId).style.display = 'block';
    }
    
    // Enable process button
    validatePaymentForm();
}

function initializePaymentForm() {
    // Cash received input handler
    const cashReceived = document.getElementById('cashReceived');
    if (cashReceived) {
        cashReceived.addEventListener('input', function() {
            calculateChange();
            validatePaymentForm();
        });
    }
    
    // Mobile money form handlers
    const mobileOperator = document.getElementById('mobileOperator');
    const mobilePhone = document.getElementById('mobilePhone');
    
    if (mobileOperator) {
        mobileOperator.addEventListener('change', validatePaymentForm);
    }
    if (mobilePhone) {
        mobilePhone.addEventListener('input', validatePaymentForm);
    }
    
    // Insurance form handlers
    const policyNumber = document.getElementById('policyNumber');
    const authCode = document.getElementById('authCode');
    
    if (policyNumber) {
        policyNumber.addEventListener('input', validatePaymentForm);
    }
    if (authCode) {
        authCode.addEventListener('input', validatePaymentForm);
    }
}

function calculateChange() {
    const cashReceived = parseFloat(document.getElementById('cashReceived').value) || 0;
    const change = cashReceived - TOTAL_AMOUNT;
    
    const changeDisplay = document.getElementById('changeDisplay');
    const changeAmount = document.getElementById('changeAmount');
    
    if (change >= 0) {
        changeDisplay.style.display = 'block';
        changeAmount.textContent = `${change.toFixed(2)} ${CURRENCY}`;
    } else {
        changeDisplay.style.display = 'none';
    }
}

function validatePaymentForm() {
    const processBtn = document.getElementById('processPaymentBtn');
    let isValid = false;
    
    if (!selectedPaymentMethod) {
        processBtn.disabled = true;
        return;
    }
    
    switch (selectedPaymentMethod) {
        case 'mobile_money':
            const operator = document.getElementById('mobileOperator').value;
            const phone = document.getElementById('mobilePhone').value;
            isValid = operator && phone && phone.length >= 9;
            break;
            
        case 'cash':
            const cashReceived = parseFloat(document.getElementById('cashReceived').value) || 0;
            isValid = cashReceived >= TOTAL_AMOUNT;
            break;
            
        case 'card':
            isValid = true; // Card validation happens at terminal
            break;
            
        case 'insurance':
            const policy = document.getElementById('policyNumber').value;
            const auth = document.getElementById('authCode').value;
            isValid = policy && auth;
            break;
    }
    
    processBtn.disabled = !isValid;
}

function processPayment() {
    if (!selectedPaymentMethod) {
        alert('Veuillez sélectionner une méthode de paiement');
        return;
    }
    
    const paymentData = {
        order_id: ORDER_ID,
        payment_method: selectedPaymentMethod,
        amount: TOTAL_AMOUNT,
        currency: CURRENCY
    };
    
    // Add method-specific data
    switch (selectedPaymentMethod) {
        case 'mobile_money':
            paymentData.operator = document.getElementById('mobileOperator').value;
            paymentData.phone = document.getElementById('mobilePhone').value;
            break;
            
        case 'cash':
            paymentData.cash_received = parseFloat(document.getElementById('cashReceived').value);
            paymentData.change = paymentData.cash_received - TOTAL_AMOUNT;
            break;
            
        case 'insurance':
            paymentData.policy_number = document.getElementById('policyNumber').value;
            paymentData.auth_code = document.getElementById('authCode').value;
            break;
    }
    
    // Show loading
    showLoading('Traitement du paiement...');
    
    // Process payment
    fetch('/pharmacy/api/payments/process/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(paymentData)
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showSuccessMessage(data);
        } else {
            alert('Erreur: ' + (data.message || 'Échec du paiement'));
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        alert('Erreur lors du traitement du paiement');
    });
}

function showSuccessMessage(data) {
    // Create success modal
    const modal = document.createElement('div');
    modal.className = 'success-modal';
    modal.innerHTML = `
        <div class="success-content">
            <div class="success-icon">✓</div>
            <h2>Paiement Réussi!</h2>
            <p>Transaction #${data.transaction_id}</p>
            <div class="success-details">
                <p><strong>Montant:</strong> ${TOTAL_AMOUNT} ${CURRENCY}</p>
                <p><strong>Méthode:</strong> ${getPaymentMethodLabel(selectedPaymentMethod)}</p>
                ${selectedPaymentMethod === 'cash' && data.change > 0 ? 
                    `<p class="change-info"><strong>Monnaie:</strong> ${data.change.toFixed(2)} ${CURRENCY}</p>` : ''}
            </div>
            <div class="success-actions">
                <button class="btn-primary" onclick="printReceipt('${data.receipt_id}')">
                    Imprimer Reçu
                </button>
                <button class="btn-secondary" onclick="finishTransaction()">
                    Terminer
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function getPaymentMethodLabel(method) {
    const labels = {
        'mobile_money': 'Mobile Money',
        'cash': 'Espèces',
        'card': 'Carte Bancaire',
        'insurance': 'Assurance'
    };
    return labels[method] || method;
}

function printReceipt(receiptId) {
    window.open(`/pharmacy/receipts/${receiptId}/print/`, '_blank');
}

function finishTransaction() {
    window.location.href = '/pharmacy/staff/counter/';
}

function cancelPayment() {
    if (confirm('Annuler ce paiement?')) {
        window.history.back();
    }
}

// Utility functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showLoading(message) {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    overlay.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 12px; text-align: center;">
            <div class="spinner"></div>
            <p style="margin-top: 16px; color: #333; font-size: 1.1rem;">${message}</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

// Success modal styles (injected)
const style = document.createElement('style');
style.textContent = `
    .success-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    
    .success-content {
        background: white;
        padding: 40px;
        border-radius: 16px;
        text-align: center;
        max-width: 500px;
    }
    
    .success-icon {
        width: 80px;
        height: 80px;
        background: var(--pharmacy-primary);
        color: white;
        font-size: 3rem;
        line-height: 80px;
        border-radius: 50%;
        margin: 0 auto 20px;
    }
    
    .success-content h2 {
        color: var(--pharmacy-primary);
        margin: 0 0 12px 0;
    }
    
    .success-details {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        margin: 20px 0;
        text-align: left;
    }
    
    .success-details p {
        margin: 8px 0;
        color: #333;
    }
    
    .change-info {
        color: var(--pharmacy-primary);
        font-size: 1.1rem;
    }
    
    .success-actions {
        display: flex;
        gap: 16px;
    }
    
    .success-actions button {
        flex: 1;
        padding: 14px;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        cursor: pointer;
    }
    
    .spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid var(--pharmacy-primary);
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);
