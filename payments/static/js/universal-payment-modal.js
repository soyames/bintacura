// Universal Payment Modal - Reusable across entire BINTACURA platform
// Version: 1.0
console.log('💳 Loading universal-payment-modal.js v1.0');

class UniversalPaymentModal {
    constructor() {
        this.modalId = 'universalPaymentModal';
        this.currentReceiptId = null;
        this.currentAmount = 0;
        this.currentCurrency = 'XOF';
        this.onPaymentComplete = null;
        this.platformFeePercentage = 0.01;
    }

    async loadPlatformFee() {
        try {
            const response = await fetch('/api/v1/core/settings/platform-fee/');
            const data = await response.json();
            if (data.fee_percentage) {
                this.platformFeePercentage = parseFloat(data.fee_percentage) / 100;
            }
        } catch (error) {
            console.error('Error loading platform fee:', error);
        }
    }

    async show(receiptId, amount, currency = 'XOF', onComplete = null) {
        this.currentReceiptId = receiptId;
        this.currentAmount = amount;
        this.currentCurrency = currency;
        this.onPaymentComplete = onComplete;

        await this.loadPlatformFee();

        return new Promise((resolve) => {
            const modal = this.createModal();
            document.body.appendChild(modal);

            window._universalPaymentResolve = resolve;

            setTimeout(() => {
                modal.style.display = 'flex';
                modal.classList.add('show');
            }, 10);
        });
    }

    createModal() {
        const platformFeeAmount = this.currentAmount * this.platformFeePercentage;
        const platformFeePercent = (this.platformFeePercentage * 100).toFixed(1);

        const modal = document.createElement('div');
        modal.id = this.modalId;
        modal.innerHTML = `
            <div class="universal-payment-overlay" onclick="window.universalPaymentModal.close()"></div>
            <div class="universal-payment-content">
                <button class="universal-payment-close" onclick="window.universalPaymentModal.close()" title="Fermer">×</button>
                <h3 class="universal-payment-title">Choisir le mode de paiement</h3>
                
                <div class="universal-payment-info">
                    <strong>ℹ️ Informations sur les frais :</strong>
                    <ul>
                        <li>Frais de plateforme: <strong>${platformFeePercent}% du montant</strong></li>
                        <li>Paiement en ligne: <strong>Des frais de passerelle supplémentaires peuvent s'appliquer</strong></li>
                        <li>Paiement sur place: <strong>Aucun frais supplémentaire</strong></li>
                    </ul>
                </div>
                
                <div class="universal-payment-options">
                    <button class="universal-payment-btn universal-payment-online" onclick="window.universalPaymentModal.selectPayment('online')">
                        💳 Payer En ligne (avec FedaPay)
                    </button>
                    <button class="universal-payment-btn universal-payment-cash" onclick="window.universalPaymentModal.selectPayment('cash')">
                        💵 Payer sur place (Cash)
                    </button>
                </div>
            </div>
        `;

        return modal;
    }

    selectPayment(method) {
        const modal = document.getElementById(this.modalId);
        if (modal) {
            modal.remove();
        }

        if (window._universalPaymentResolve) {
            window._universalPaymentResolve(method);
            delete window._universalPaymentResolve;
        }

        if (this.onPaymentComplete) {
            this.onPaymentComplete(method);
        }
    }

    close() {
        const modal = document.getElementById(this.modalId);
        if (modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        }

        if (window._universalPaymentResolve) {
            window._universalPaymentResolve(null);
            delete window._universalPaymentResolve;
        }
    }
}

window.universalPaymentModal = new UniversalPaymentModal();
