// Pharmacy Counter Dashboard JavaScript

let html5QrCode = null;
let currentOrderId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeFilterButtons();
    loadPendingOrders();
    startAutoRefresh();
});

// Filter buttons functionality
function initializeFilterButtons() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            filterButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            filterOrders(this.dataset.filter);
        });
    });
}

function filterOrders(filterType) {
    const orders = document.querySelectorAll('.order-card');
    orders.forEach(order => {
        if (filterType === 'all') {
            order.style.display = 'block';
        } else {
            const orderType = order.dataset.orderType;
            order.style.display = orderType === filterType ? 'block' : 'none';
        }
    });
}

// QR Scanner
function openQRScanner() {
    const modal = document.getElementById('qrScannerModal');
    modal.style.display = 'block';
    initializeQRScanner();
}

function closeQRScanner() {
    const modal = document.getElementById('qrScannerModal');
    modal.style.display = 'none';
    if (html5QrCode) {
        html5QrCode.stop().then(() => {
            html5QrCode = null;
        }).catch(err => console.error(err));
    }
}

function initializeQRScanner() {
    const qrReaderDiv = document.getElementById('qr-reader');
    html5QrCode = new Html5Qrcode("qr-reader");
    
    const config = { 
        fps: 10, 
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0
    };
    
    html5QrCode.start(
        { facingMode: "environment" },
        config,
        onScanSuccess,
        onScanFailure
    ).catch(err => {
        console.error('Unable to start QR scanner:', err);
        alert('Erreur: Impossible de démarrer la caméra. Veuillez vérifier les permissions.');
    });
}

function onScanSuccess(decodedText, decodedResult) {
    console.log(`QR Code scanned: ${decodedText}`);
    closeQRScanner();
    searchByQRCode(decodedText);
}

function onScanFailure(error) {
    // Silent - scanning in progress
}

function searchByCode() {
    const code = document.getElementById('manualCode').value.trim();
    if (!code) {
        alert('Veuillez entrer un code');
        return;
    }
    closeQRScanner();
    searchByQRCode(code);
}

function searchByQRCode(code) {
    showLoading('Recherche de la prescription...');
    
    fetch(`/pharmacy/api/prescription/search/?code=${encodeURIComponent(code)}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displayPrescriptionDetails(data.prescription);
        } else {
            alert('Prescription non trouvée: ' + (data.message || 'Code invalide'));
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        alert('Erreur lors de la recherche de la prescription');
    });
}

function displayPrescriptionDetails(prescription) {
    const processingSection = document.getElementById('processingSection');
    const processingContent = document.getElementById('processingContent');
    
    let html = `
        <div class="prescription-details">
            <div class="details-header">
                <h3>Prescription #${prescription.prescription_number}</h3>
                <span class="status-badge">${prescription.status}</span>
            </div>
            <div class="patient-info">
                <h4>Information Patient</h4>
                <p><strong>Nom:</strong> ${prescription.patient_name}</p>
                <p><strong>Téléphone:</strong> ${prescription.patient_phone || 'N/A'}</p>
            </div>
            <div class="medications-list">
                <h4>Médicaments Prescrits</h4>
                <table class="medications-table">
                    <thead>
                        <tr>
                            <th>Médicament</th>
                            <th>Quantité</th>
                            <th>Disponible</th>
                            <th>Prix Unitaire</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
    `;
    
    let totalAmount = 0;
    prescription.medications.forEach(med => {
        const medTotal = med.quantity * med.unit_price;
        totalAmount += medTotal;
        html += `
            <tr>
                <td>${med.medicine_name}</td>
                <td>${med.quantity}</td>
                <td>${med.available ? '<span class="badge-success">Oui</span>' : '<span class="badge-danger">Non</span>'}</td>
                <td>${med.unit_price} ${med.currency}</td>
                <td>${medTotal.toFixed(2)} ${med.currency}</td>
            </tr>
        `;
    });
    
    html += `
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="4" class="text-right"><strong>Total:</strong></td>
                            <td><strong>${totalAmount.toFixed(2)} ${prescription.currency}</strong></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            <div class="action-buttons">
                <button class="btn-primary" onclick="prepareMedications('${prescription.id}')">
                    Préparer les Médicaments
                </button>
                <button class="btn-secondary" onclick="cancelProcessing()">
                    Annuler
                </button>
            </div>
        </div>
    `;
    
    processingContent.innerHTML = html;
    processingSection.style.display = 'block';
    processingSection.scrollIntoView({ behavior: 'smooth' });
}

function processOrder(orderId) {
    currentOrderId = orderId;
    showLoading('Chargement de la commande...');
    
    fetch(`/pharmacy/api/orders/${orderId}/`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displayPrescriptionDetails(data.prescription);
        } else {
            alert('Erreur lors du chargement de la commande');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        alert('Erreur lors du chargement de la commande');
    });
}

function prepareMedications(prescriptionId) {
    if (!confirm('Confirmer que tous les médicaments sont prêts?')) {
        return;
    }
    
    showLoading('Préparation en cours...');
    
    fetch(`/pharmacy/api/prescriptions/${prescriptionId}/prepare/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            counter_id: getCounterId()
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            alert('Médicaments préparés avec succès!');
            proceedToPayment(prescriptionId, data.order_id);
        } else {
            alert('Erreur: ' + (data.message || 'Échec de la préparation'));
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        alert('Erreur lors de la préparation des médicaments');
    });
}

function proceedToPayment(prescriptionId, orderId) {
    window.location.href = `/pharmacy/payment/${orderId}/`;
}

function viewOrderDetails(orderId) {
    processOrder(orderId);
}

function cancelProcessing() {
    if (confirm('Annuler le traitement en cours?')) {
        document.getElementById('processingSection').style.display = 'none';
        currentOrderId = null;
    }
}

function loadPendingOrders() {
    // Auto-refresh pending orders list
    fetch('/pharmacy/api/orders/pending/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateOrdersList(data.orders);
        }
    })
    .catch(error => console.error('Error loading orders:', error));
}

function updateOrdersList(orders) {
    // Update pending count
    const pendingCount = document.querySelector('.counter-stats .stat-value');
    if (pendingCount) {
        pendingCount.textContent = orders.length;
    }
}

function startAutoRefresh() {
    // Refresh orders every 30 seconds
    setInterval(loadPendingOrders, 30000);
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

function getCounterId() {
    // Extract counter number from page
    const counterHeader = document.querySelector('.counter-info h2');
    if (counterHeader) {
        const match = counterHeader.textContent.match(/Comptoir (\d+)/);
        return match ? match[1] : '1';
    }
    return '1';
}

function showLoading(message) {
    // Create loading overlay
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
            <p style="margin-top: 16px; color: #333;">${message}</p>
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
