let selectedPaymentMethod = null;
let currentReceiptId = null;

function initiatePayment(receiptId) {
    currentReceiptId = receiptId;
    $('#paymentReceiptId').val(receiptId);
    
    // Get receipt details from page if available
    const amountElement = document.querySelector('.total-row .amount-cell strong');
    const invoiceElement = document.querySelector('.receipt-header h2');
    
    if (amountElement) {
        $('#paymentAmount').text(amountElement.textContent.trim());
    }
    
    if (invoiceElement) {
        const invoiceNumber = invoiceElement.textContent.replace('Facture #', '').trim();
        $('#paymentInvoiceNumber').text(invoiceNumber);
    }
    
    // Reset selection
    selectedPaymentMethod = null;
    $('.payment-option-card').removeClass('selected');
    $('#paymentMethodError').hide();
    
    // Show modal
    $('#paymentSelectionModal').modal('show');
}

function selectPaymentMethod(method) {
    selectedPaymentMethod = method;
    
    // Update UI
    $('.payment-option-card').removeClass('selected');
    event.currentTarget.classList.add('selected');
    $('#paymentMethodError').hide();
}

function proceedWithPayment() {
    if (!selectedPaymentMethod) {
        $('#paymentMethodError').show();
        return;
    }
    
    const receiptId = $('#paymentReceiptId').val();
    
    if (selectedPaymentMethod === 'online') {
        initiateOnlinePayment(receiptId);
    } else if (selectedPaymentMethod === 'cash') {
        requestCashPayment(receiptId);
    }
}

function initiateOnlinePayment(receiptId) {
    $('#paymentSelectionModal').modal('hide');
    
    // Show loading
    showLoadingModal('Initialisation du paiement en ligne...');
    
    // Call FedaPay integration
    fetch(`/api/v1/payments/initiate-online-payment/${receiptId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingModal();
        
        if (data.success && data.payment_url) {
            // Redirect to FedaPay
            window.location.href = data.payment_url;
        } else {
            showErrorAlert(data.message || 'Erreur lors de l\'initialisation du paiement');
        }
    })
    .catch(error => {
        hideLoadingModal();
        console.error('Payment error:', error);
        showErrorAlert('Une erreur est survenue lors du paiement');
    });
}

function requestCashPayment(receiptId) {
    $('#paymentSelectionModal').modal('hide');
    
    // Show loading
    showLoadingModal('Envoi de la demande de paiement...');
    
    // Send cash payment request
    fetch('/api/v1/payments/request-cash-payment/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            receipt_id: receiptId
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingModal();
        
        if (data.success) {
            showSuccessAlert(
                'Demande de paiement envoyée!',
                'Le prestataire de service a été notifié et validera votre paiement en espèces.'
            );
            
            // Reload page after 3 seconds
            setTimeout(() => {
                location.reload();
            }, 3000);
        } else {
            showErrorAlert(data.message || 'Erreur lors de l\'envoi de la demande');
        }
    })
    .catch(error => {
        hideLoadingModal();
        console.error('Payment request error:', error);
        showErrorAlert('Une erreur est survenue lors de l\'envoi de la demande');
    });
}

function showLoadingModal(message) {
    const modalHtml = `
        <div class="modal fade" id="loadingModal" tabindex="-1" role="dialog" data-backdrop="static" data-keyboard="false">
            <div class="modal-dialog modal-dialog-centered modal-sm" role="document">
                <div class="modal-content">
                    <div class="modal-body text-center py-4">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="sr-only">Chargement...</span>
                        </div>
                        <p class="mb-0">${message}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $('body').append(modalHtml);
    $('#loadingModal').modal('show');
}

function hideLoadingModal() {
    $('#loadingModal').modal('hide');
    setTimeout(() => {
        $('#loadingModal').remove();
    }, 500);
}

function showSuccessAlert(title, message) {
    const alertHtml = `
        <div class="modal fade" id="successModal" tabindex="-1" role="dialog">
            <div class="modal-dialog modal-dialog-centered" role="document">
                <div class="modal-content">
                    <div class="modal-body text-center py-4">
                        <i class="fas fa-check-circle fa-4x text-success mb-3"></i>
                        <h5 class="mb-3">${title}</h5>
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" data-dismiss="modal">OK</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $('body').append(alertHtml);
    $('#successModal').modal('show');
    
    $('#successModal').on('hidden.bs.modal', function() {
        $(this).remove();
    });
}

function showErrorAlert(message) {
    const alertHtml = `
        <div class="modal fade" id="errorModal" tabindex="-1" role="dialog">
            <div class="modal-dialog modal-dialog-centered" role="document">
                <div class="modal-content">
                    <div class="modal-body text-center py-4">
                        <i class="fas fa-exclamation-circle fa-4x text-danger mb-3"></i>
                        <h5 class="mb-3">Erreur</h5>
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Fermer</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $('body').append(alertHtml);
    $('#errorModal').modal('show');
    
    $('#errorModal').on('hidden.bs.modal', function() {
        $(this).remove();
    });
}

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
