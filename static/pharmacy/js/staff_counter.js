// Pharmacy Staff Counter Dashboard JavaScript

class PharmacyCounterApp {
    constructor() {
        this.currentOrder = null;
        this.scanner = null;
        this.initializeApp();
    }

    initializeApp() {
        this.loadPendingOrders();
        this.initializeQRScanner();
        this.setupEventListeners();
        this.startAutoRefresh();
    }

    setupEventListeners() {
        document.getElementById('scanQRBtn')?.addEventListener('click', () => this.openQRScanner());
        document.getElementById('refreshOrdersBtn')?.addEventListener('click', () => this.loadPendingOrders());
        document.getElementById('processPaymentBtn')?.addEventListener('click', () => this.processPayment());
    }

    async loadPendingOrders() {
        try {
            const response = await fetch('/pharmacy/api/staff/pending-orders/', {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to load orders');

            const data = await response.json();
            this.renderOrderQueue(data.results);
        } catch (error) {
            console.error('Error loading orders:', error);
            this.showNotification('Failed to load orders', 'error');
        }
    }

    renderOrderQueue(orders) {
        const container = document.getElementById('orderQueue');
        if (!container) return;

        if (orders.length === 0) {
            container.innerHTML = '<div class="no-orders">No pending orders</div>';
            return;
        }

        container.innerHTML = orders.map(order => `
            <div class="order-card" data-order-id="${order.id}">
                <div class="order-header">
                    <span class="order-number">#${order.order_number}</span>
                    <span class="order-type ${order.order_type}">${order.order_type}</span>
                </div>
                <div class="order-details">
                    <p><strong>Patient:</strong> ${order.patient_name}</p>
                    <p><strong>Items:</strong> ${order.items_count}</p>
                    <p><strong>Total:</strong> ${order.total_amount_display}</p>
                    <p><strong>Time:</strong> ${this.formatTime(order.created_at)}</p>
                </div>
                <div class="order-actions">
                    <button class="btn-view" onclick="counterApp.viewOrderDetails('${order.id}')">
                        View Details
                    </button>
                    <button class="btn-process" onclick="counterApp.processOrder('${order.id}')">
                        Process Order
                    </button>
                </div>
            </div>
        `).join('');
    }

    async viewOrderDetails(orderId) {
        try {
            const response = await fetch(`/pharmacy/api/staff/orders/${orderId}/`, {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to load order details');

            const order = await response.json();
            this.showOrderDetailsModal(order);
        } catch (error) {
            console.error('Error loading order details:', error);
            this.showNotification('Failed to load order details', 'error');
        }
    }

    showOrderDetailsModal(order) {
        const modal = document.getElementById('orderDetailsModal');
        if (!modal) return;

        const itemsHtml = order.items.map(item => `
            <tr>
                <td>${item.medicine_name}</td>
                <td>${item.quantity}</td>
                <td>${item.unit_price_display}</td>
                <td>${item.total_price_display}</td>
            </tr>
        `).join('');

        document.getElementById('modalOrderNumber').textContent = order.order_number;
        document.getElementById('modalPatientName').textContent = order.patient_name;
        document.getElementById('modalOrderType').textContent = order.order_type;
        document.getElementById('modalItemsTable').innerHTML = itemsHtml;
        document.getElementById('modalTotalAmount').textContent = order.total_amount_display;

        modal.style.display = 'block';
        this.currentOrder = order;
    }

    async processOrder(orderId) {
        if (!confirm('Start processing this order?')) return;

        try {
            const response = await fetch(`/pharmacy/api/staff/orders/${orderId}/process/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to process order');

            const data = await response.json();
            this.showNotification('Order processing started', 'success');
            this.showOrderDetailsModal(data);
        } catch (error) {
            console.error('Error processing order:', error);
            this.showNotification('Failed to process order', 'error');
        }
    }

    initializeQRScanner() {
        const videoElement = document.getElementById('qrVideo');
        if (!videoElement) return;

        this.scanner = new Html5Qrcode("qrVideo");
    }

    async openQRScanner() {
        const modal = document.getElementById('qrScannerModal');
        if (!modal) return;

        modal.style.display = 'block';

        try {
            await this.scanner.start(
                { facingMode: "environment" },
                {
                    fps: 10,
                    qrbox: { width: 250, height: 250 }
                },
                (decodedText) => this.handleQRCodeScanned(decodedText),
                (error) => console.log(error)
            );
        } catch (error) {
            console.error('Failed to start QR scanner:', error);
            this.showNotification('Failed to start camera', 'error');
        }
    }

    async handleQRCodeScanned(qrCode) {
        await this.scanner.stop();
        document.getElementById('qrScannerModal').style.display = 'none';

        try {
            const response = await fetch(`/pharmacy/api/staff/scan-qr/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ qr_code: qrCode })
            });

            if (!response.ok) throw new Error('Invalid QR code');

            const order = await response.json();
            this.showOrderDetailsModal(order);
        } catch (error) {
            console.error('Error scanning QR code:', error);
            this.showNotification('Invalid QR code', 'error');
        }
    }

    async processPayment() {
        if (!this.currentOrder) {
            this.showNotification('No order selected', 'error');
            return;
        }

        const paymentMethod = document.getElementById('paymentMethod')?.value;
        if (!paymentMethod) {
            this.showNotification('Please select payment method', 'error');
            return;
        }

        try {
            const response = await fetch(`/pharmacy/api/staff/orders/${this.currentOrder.id}/payment/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    payment_method: paymentMethod,
                    amount: this.currentOrder.total_amount
                })
            });

            if (!response.ok) throw new Error('Payment failed');

            const data = await response.json();
            this.showNotification('Payment processed successfully', 'success');
            this.closeAllModals();
            this.loadPendingOrders();
        } catch (error) {
            console.error('Error processing payment:', error);
            this.showNotification('Payment failed', 'error');
        }
    }

    closeAllModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
        this.currentOrder = null;
    }

    startAutoRefresh() {
        setInterval(() => {
            this.loadPendingOrders();
        }, 30000);
    }

    formatTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000 / 60);

        if (diff < 1) return 'Just now';
        if (diff < 60) return `${diff}m ago`;
        if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
        return date.toLocaleDateString();
    }

    getToken() {
        return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notificationContainer');
        if (!container) {
            alert(message);
            return;
        }

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        container.appendChild(notification);

        setTimeout(() => notification.remove(), 5000);
    }
}

let counterApp;
document.addEventListener('DOMContentLoaded', () => {
    counterApp = new PharmacyCounterApp();
});

document.querySelectorAll('.modal .close').forEach(closeBtn => {
    closeBtn.addEventListener('click', function() {
        this.closest('.modal').style.display = 'none';
    });
});

window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
});
