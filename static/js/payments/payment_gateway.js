class PaymentGatewayHandler {
    constructor() {
        this.modal = null;
        this.currentTransaction = null;
        this.pollingInterval = null;
        this.webhookReceived = false;
    }

    initialize() {
        this.modal = $('#paymentGatewayModal');
        this.setupEventListeners();
        this.setupWebhookListener();
    }

    setupEventListeners() {
        const self = this;
        
        $('#retry-payment-btn').on('click', function() {
            if (self.currentTransaction) {
                self.openPaymentPanel(self.currentTransaction);
            }
        });

        this.modal.on('hidden.bs.modal', function() {
            self.cleanup();
        });

        window.addEventListener('message', function(event) {
            self.handlePaymentMessage(event);
        });
    }

    setupWebhookListener() {
        const self = this;
        
        if (window.WebSocket) {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/payments/`;
            
            try {
                this.websocket = new WebSocket(wsUrl);
                
                this.websocket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    self.handleWebhookNotification(data);
                };
            } catch (error) {
                console.log('WebSocket not available, will use polling');
            }
        }
    }

    async initiatePayment(paymentData) {
        try {
            this.showLoading();
            this.modal.modal('show');

            const response = await fetch('/api/v1/payments/service/pay/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(paymentData)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Payment initiation failed');
            }

            this.currentTransaction = result;
            this.displayPaymentDetails(result);
            
            if (paymentData.payment_method === 'onsite_cash') {
                this.handleOnsitePayment(result);
            } else {
                await this.openPaymentPanel(result);
            }

            return result;

        } catch (error) {
            this.showError(error.message);
            throw error;
        }
    }

    displayPaymentDetails(transaction) {
        $('#payment-service-description').text(transaction.service_description || 'Service de santé');
        $('#payment-amount').text(`${transaction.amount} ${transaction.currency}`);
        
        if (transaction.fee_details) {
            $('#payment-gross-amount').text(`${transaction.fee_details.gross_amount} ${transaction.currency}`);
            $('#payment-platform-fee').text(`${transaction.fee_details.platform_fee} ${transaction.currency}`);
            $('#payment-tax').text(`${transaction.fee_details.tax} ${transaction.currency}`);
        }
    }

    async openPaymentPanel(transaction) {
        try {
            this.hideLoading();
            this.hideError();

            if (!transaction.payment_url) {
                throw new Error('Payment URL not available');
            }

            const iframe = document.getElementById('payment-iframe');
            const container = document.getElementById('payment-iframe-container');

            iframe.src = transaction.payment_url;
            container.style.display = 'block';

            this.startStatusPolling(transaction.service_transaction_id || transaction.transaction_ref);

        } catch (error) {
            this.showError('Failed to open payment panel: ' + error.message);
        }
    }

    handleOnsitePayment(result) {
        this.hideLoading();
        
        const receiptUrl = `/payments/receipts/${result.receipt.id}/`;
        
        $('#payment-success-message').html(`
            Paiement en espèces enregistré avec succès!<br>
            <a href="${receiptUrl}" target="_blank">Voir le reçu</a>
        `);
        $('#payment-success').show();
        
        setTimeout(() => {
            window.location.href = receiptUrl;
        }, 2000);
    }

    startStatusPolling(transactionId) {
        const self = this;
        let pollCount = 0;
        const maxPolls = 60;

        this.pollingInterval = setInterval(async function() {
            pollCount++;

            if (pollCount > maxPolls || self.webhookReceived) {
                clearInterval(self.pollingInterval);
                if (!self.webhookReceived) {
                    self.showError('Payment timeout. Please check your transaction status.');
                }
                return;
            }

            try {
                const response = await fetch(`/api/v1/payments/service-transactions/${transactionId}/status/`, {
                    headers: {
                        'X-CSRFToken': self.getCsrfToken()
                    }
                });

                const status = await response.json();

                if (status.status === 'completed') {
                    clearInterval(self.pollingInterval);
                    self.handlePaymentSuccess(transactionId);
                } else if (status.status === 'failed') {
                    clearInterval(self.pollingInterval);
                    self.handlePaymentFailure(status.message);
                }

            } catch (error) {
                console.error('Status polling error:', error);
            }
        }, 5000);
    }

    handlePaymentMessage(event) {
        if (event.data && typeof event.data === 'object') {
            if (event.data.type === 'payment_success') {
                this.handlePaymentSuccess(event.data.transaction_id);
            } else if (event.data.type === 'payment_failed') {
                this.handlePaymentFailure(event.data.message);
            }
        }
    }

    handleWebhookNotification(data) {
        if (data.event_type === 'transaction.approved') {
            this.webhookReceived = true;
            this.handlePaymentSuccess(data.transaction_id);
        } else if (data.event_type === 'transaction.declined' || data.event_type === 'transaction.canceled') {
            this.webhookReceived = true;
            this.handlePaymentFailure(data.message || 'Payment declined');
        }
    }

    async handlePaymentSuccess(transactionId) {
        clearInterval(this.pollingInterval);
        
        $('#payment-iframe-container').hide();
        $('#payment-success').show();

        try {
            const response = await fetch(`/api/v1/payments/service-transactions/${transactionId}/receipt/`, {
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });

            const receiptData = await response.json();
            
            setTimeout(() => {
                window.location.href = receiptData.receipt_url || '/payments/receipts/';
            }, 2000);

        } catch (error) {
            console.error('Failed to fetch receipt:', error);
            setTimeout(() => {
                this.modal.modal('hide');
                window.location.reload();
            }, 2000);
        }
    }

    handlePaymentFailure(message) {
        clearInterval(this.pollingInterval);
        
        $('#payment-iframe-container').hide();
        this.showError(message || 'Payment failed. Please try again.');
        $('#retry-payment-btn').show();
    }

    showLoading() {
        $('#payment-loading').show();
        $('#payment-iframe-container').hide();
        $('#payment-error').hide();
        $('#payment-success').hide();
        $('#retry-payment-btn').hide();
    }

    hideLoading() {
        $('#payment-loading').hide();
    }

    showError(message) {
        $('#payment-error-message').text(message);
        $('#payment-error').show();
        $('#retry-payment-btn').show();
    }

    hideError() {
        $('#payment-error').hide();
    }

    cleanup() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        
        $('#payment-iframe').attr('src', 'about:blank');
        $('#payment-iframe-container').hide();
        $('#payment-loading').hide();
        $('#payment-error').hide();
        $('#payment-success').hide();
        $('#retry-payment-btn').hide();
        
        this.currentTransaction = null;
        this.webhookReceived = false;
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
               '';
    }
}

const paymentGateway = new PaymentGatewayHandler();

document.addEventListener('DOMContentLoaded', function() {
    paymentGateway.initialize();
});

window.initiatePayment = function(paymentData) {
    return paymentGateway.initiatePayment(paymentData);
};
