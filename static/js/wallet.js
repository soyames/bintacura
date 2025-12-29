// Wallet and Payment Integration with FedaPay
// BINTACURA Platform

class WalletManager {
    constructor() {
        this.currentCurrency = 'XAF';
        this.currencySymbols = {
            'EUR': '€',
            'USD': '$',
            'GBP': '£',
            'XAF': 'CFA',
            'XOF': 'CFA',
            'NGN': '₦',
            'GHS': '₵'
        };
        this.fedaPayPublicKey = null;
    }

    async init() {
        await this.loadUserCurrency();
        await this.loadFedaPayConfig();
        this.loadWalletBalance();
        this.loadTransactionHistory();
    }

    async loadUserCurrency() {
        try {
            const response = await fetch('/api/v1/core/system/consultation-fee/');
            const data = await response.json();
            if (data.currency) {
                this.currentCurrency = data.currency;
            }
        } catch (error) {
            console.error('Error loading user currency:', error);
        }
    }

    async loadFedaPayConfig() {
        try {
            // Load FedaPay configuration from backend
            const response = await fetch('/api/v1/payments/fedapay-config/');
            const data = await response.json();
            if (data.public_key) {
                this.fedaPayPublicKey = data.public_key;
            }
        } catch (error) {
            console.error('Error loading FedaPay config:', error);
        }
    }

    async loadWalletBalance() {
        try {
            const response = await fetch('/api/v1/payments/wallet/balance/');
            const data = await response.json();
            
            const balanceElement = document.getElementById('balance');
            const currencyElement = document.getElementById('currencySymbol');
            
            if (balanceElement && data.balance !== undefined) {
                balanceElement.textContent = this.formatAmount(data.balance);
            }
            
            if (currencyElement && data.currency) {
                this.currentCurrency = data.currency;
                currencyElement.textContent = this.currencySymbols[data.currency] || data.currency;
            }
            
            return data;
        } catch (error) {
            console.error('Error loading wallet balance:', error);
            return null;
        }
    }

    async loadTransactionHistory(limit = 50) {
        try {
            const response = await fetch(`/api/v1/payments/transactions/?limit=${limit}`);
            const data = await response.json();
            
            const transactionList = document.getElementById('transactionList');
            if (!transactionList) return;

            if (!data.results || data.results.length === 0) {
                transactionList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">💳</div>
                        <p>Aucune transaction</p>
                    </div>
                `;
                return;
            }

            transactionList.innerHTML = data.results.map(transaction => 
                this.createTransactionCard(transaction)
            ).join('');
            
        } catch (error) {
            console.error('Error loading transaction history:', error);
        }
    }

    createTransactionCard(transaction) {
        const icon = this.getTransactionIcon(transaction.transaction_type);
        const isPositive = ['deposit', 'refund', 'credit'].includes(transaction.transaction_type);
        const amountClass = isPositive ? 'amount-positive' : 'amount-negative';
        const amountSign = isPositive ? '+' : '-';
        
        const date = new Date(transaction.created_at);
        const formattedDate = date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
        const formattedTime = date.toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });

        const statusBadge = this.getStatusBadge(transaction.status, transaction.payment_method);
        const amount = Math.abs(transaction.amount);
        const currency = this.currencySymbols[transaction.currency] || transaction.currency;

        const downloadButton = transaction.receipt_url ? 
            `<button class="download-receipt-btn" onclick="walletManager.downloadReceipt('${transaction.id}')">
                📄 Télécharger
            </button>` : '';

        return `
            <div class="transaction-card">
                <div class="transaction-icon">${icon}</div>
                <div class="transaction-info">
                    <div class="transaction-name">${transaction.description || 'Transaction'}</div>
                    <div class="transaction-date">${formattedDate} • ${formattedTime}</div>
                    <div class="transaction-meta">
                        ${statusBadge}
                        ${transaction.reference ? `<span class="transaction-ref">Réf: ${transaction.reference}</span>` : ''}
                    </div>
                </div>
                <div class="transaction-right">
                    <div class="transaction-amount ${amountClass}">
                        ${currency}${amountSign}${this.formatAmount(amount)}
                    </div>
                    ${downloadButton}
                </div>
            </div>
        `;
    }

    getTransactionIcon(type) {
        const icons = {
            'deposit': '🏦',
            'withdrawal': '💸',
            'payment': '🏥',
            'refund': '↩️',
            'transfer': '💱',
            'commission': '💼',
            'fee': '📋',
            'credit': '✅',
            'debit': '💳'
        };
        return icons[type] || '💳';
    }

    getStatusBadge(status, paymentMethod) {
        const statusConfig = {
            'pending': { text: 'En attente', class: 'status-pending' },
            'processing': { text: 'En cours', class: 'status-processing' },
            'completed': { text: 'Terminé', class: 'status-completed' },
            'failed': { text: 'Échoué', class: 'status-failed' },
            'cancelled': { text: 'Annulé', class: 'status-cancelled' },
            'reversed': { text: 'Inversé', class: 'status-reversed' }
        };

        const config = statusConfig[status] || { text: status, class: 'status-default' };
        let badge = `<span class="transaction-status ${config.class}">${config.text}</span>`;

        if (paymentMethod === 'cash') {
            badge += ' <span class="payment-method-badge">💵 Espèces</span>';
        } else if (paymentMethod === 'wallet') {
            badge += ' <span class="payment-method-badge">💳 Wallet</span>';
        }

        return badge;
    }

    formatAmount(amount) {
        return amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    }

    async topUpWallet() {
        const amount = prompt('Montant à recharger (en ' + this.currentCurrency + '):');
        if (!amount || isNaN(amount) || parseFloat(amount) <= 0) {
            return;
        }

        try {
            // Create a wallet topup transaction
            const response = await fetch('/api/v1/payments/wallet/topup/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    amount: parseFloat(amount),
                    currency: this.currentCurrency
                })
            });

            const data = await response.json();

            if (response.ok && data.payment_url) {
                // Redirect to FedaPay payment page
                window.location.href = data.payment_url;
            } else {
                alert('Erreur: ' + (data.error || 'Impossible de créer la transaction'));
            }
        } catch (error) {
            console.error('Error initiating wallet topup:', error);
            alert('Erreur de connexion. Veuillez réessayer.');
        }
    }

    async payForService(serviceType, serviceId, amount, description) {
        try {
            const paymentMethod = await this.selectPaymentMethod(amount);
            
            if (!paymentMethod) {
                return null; // User cancelled
            }

            const response = await fetch('/api/v1/payments/service/pay/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    service_type: serviceType,
                    service_id: serviceId,
                    amount: amount,
                    payment_method: paymentMethod,
                    description: description
                })
            });

            const data = await response.json();

            if (response.ok) {
                if (paymentMethod === 'wallet') {
                    // Payment completed with wallet
                    this.showPaymentSuccess(data);
                    this.loadWalletBalance();
                    this.loadTransactionHistory();
                    return data;
                } else if (paymentMethod === 'fedapay' && data.payment_url) {
                    // Redirect to FedaPay
                    window.location.href = data.payment_url;
                    return null;
                } else if (paymentMethod === 'cash') {
                    // Cash payment recorded
                    this.showCashPaymentConfirmation(data);
                    return data;
                }
            } else {
                if (data.error && data.error.includes('Insufficient')) {
                    this.showInsufficientBalanceDialog(amount);
                } else {
                    alert('Erreur de paiement: ' + (data.error || 'Une erreur est survenue'));
                }
                return null;
            }
        } catch (error) {
            console.error('Error processing payment:', error);
            alert('Erreur de connexion lors du paiement');
            return null;
        }
    }

    async selectPaymentMethod(amount) {
        const balance = await this.loadWalletBalance();
        const hasEnoughBalance = balance && balance.balance >= amount;

        const options = [];
        
        if (hasEnoughBalance) {
            options.push({
                value: 'wallet',
                text: `💳 Payer avec le Wallet (Solde: ${this.currencySymbols[this.currentCurrency]}${this.formatAmount(balance.balance)})`
            });
        }
        
        options.push({
            value: 'fedapay',
            text: '🏦 Payer par Mobile Money/Carte Bancaire'
        });
        
        options.push({
            value: 'cash',
            text: '💵 Payer sur place (Espèces)'
        });

        // Create a custom modal for payment method selection
        return new Promise((resolve) => {
            const modal = this.createPaymentMethodModal(options, amount, (method) => {
                resolve(method);
            });
            document.body.appendChild(modal);
        });
    }

    createPaymentMethodModal(options, amount, callback) {
        const modal = document.createElement('div');
        modal.className = 'payment-modal';
        modal.innerHTML = `
            <div class="payment-modal-content">
                <h3>Choisir le mode de paiement</h3>
                <p class="payment-amount">Montant: ${this.currencySymbols[this.currentCurrency]}${this.formatAmount(amount)}</p>
                <div class="payment-options">
                    ${options.map(opt => `
                        <button class="payment-option-btn" data-method="${opt.value}">
                            ${opt.text}
                        </button>
                    `).join('')}
                </div>
                <button class="payment-cancel-btn">Annuler</button>
            </div>
        `;

        modal.querySelectorAll('.payment-option-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const method = btn.getAttribute('data-method');
                modal.remove();
                callback(method);
            });
        });

        modal.querySelector('.payment-cancel-btn').addEventListener('click', () => {
            modal.remove();
            callback(null);
        });

        return modal;
    }

    showPaymentSuccess(data) {
        alert(`✅ Paiement effectué avec succès!\n\nRéférence: ${data.reference || 'N/A'}\n\nVous pouvez télécharger votre reçu dans l'historique des transactions.`);
    }

    showCashPaymentConfirmation(data) {
        alert(`✅ Paiement en espèces enregistré!\n\nVous devrez payer ${this.currencySymbols[this.currentCurrency]}${this.formatAmount(data.amount)} sur place.\n\nRéférence: ${data.reference || 'N/A'}`);
    }

    showInsufficientBalanceDialog(requiredAmount) {
        if (confirm(`❌ Solde insuffisant!\n\nMontant requis: ${this.currencySymbols[this.currentCurrency]}${this.formatAmount(requiredAmount)}\n\nVoulez-vous recharger votre wallet?`)) {
            this.topUpWallet();
        }
    }

    async downloadReceipt(transactionId) {
        try {
            window.open(`/api/v1/payments/transactions/${transactionId}/download-receipt/`, '_blank');
        } catch (error) {
            console.error('Error downloading receipt:', error);
            alert('Erreur lors du téléchargement du reçu');
        }
    }

    getCookie(name) {
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
}

// Initialize wallet manager
const walletManager = new WalletManager();

// Auto-init on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => walletManager.init());
} else {
    walletManager.init();
}

