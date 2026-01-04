// Transport Payment Handler - Uses appointment booking payment modal (DEFAULT)
let currentTransportRequestId = null;
let transportAmount = 0;

async function payTransport(requestId, amount) {
    currentTransportRequestId = requestId;
    transportAmount = amount;
    
    // Calculate total with platform fee (from backend)
    const platformFee = (amount * (window.PLATFORM_FEE_RATE || 0.01)).toFixed(0);
    const total = (parseFloat(amount) + parseFloat(platformFee)).toFixed(0);
    
    try {
        // Use the SAME payment modal as appointment booking
        const paymentMethod = await showPaymentMethodModal();
        
        if (paymentMethod === 'online') {
            await initiateTransportOnlinePayment(requestId);
        } else if (paymentMethod === 'cash') {
            await requestTransportCashPayment(requestId);
        }
    } catch (error) {
        console.error('Payment cancelled or error:', error);
    } finally {
        currentTransportRequestId = null;
    }
}

// Reusable payment method modal (same as appointment booking)
function showPaymentMethodModal() {
    return new Promise((resolve, reject) => {
        const modal = document.createElement('div');
        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 20px;';
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
                reject('Cancelled');
            }
        };
        
        modal.innerHTML = `
            <div onclick="event.stopPropagation()" style="background: white; padding: 30px; border-radius: 16px; max-width: 550px; width: 100%; box-shadow: 0 10px 40px rgba(0,0,0,0.2);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #2d3748;">Choisir le mode de paiement</h3>
                    <button onclick="this.closest('div').parentElement.parentElement.remove();" style="background: none; border: none; font-size: 28px; cursor: pointer; color: #6b7280; padding: 0; line-height: 1;">&times;</button>
                </div>
                
                <!-- Fee Information Notice -->
                <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 13px; color: #856404;">
                    <strong>ℹ️ Informations sur les frais :</strong>
                    <ul style="margin: 8px 0 0 0; padding-left: 20px;">
                        <li>Frais de plateforme: <strong>1% du montant</strong></li>
                        <li>Paiement en ligne: <strong>Des frais de passerelle supplémentaires peuvent s'appliquer</strong></li>
                        <li>Paiement sur place: <strong>Aucun frais supplémentaire</strong></li>
                    </ul>
                </div>
                
                <div style="display: flex; flex-direction: column; gap: 15px;">
                    <button onclick="this.closest('div').parentElement.parentElement.remove(); window.transportPaymentChoice('online');" 
                            style="padding: 15px; border: 2px solid #4CAF50; background: #4CAF50; color: white; border-radius: 8px; cursor: pointer; font-size: 16px; transition: all 0.2s;"
                            onmouseover="this.style.background='#45a049'" 
                            onmouseout="this.style.background='#4CAF50'">
                        💳 Payer En ligne (avec FedaPay)
                    </button>
                    <button onclick="this.closest('div').parentElement.parentElement.remove(); window.transportPaymentChoice('cash');" 
                            style="padding: 15px; border: 2px solid #2196F3; background: #2196F3; color: white; border-radius: 8px; cursor: pointer; font-size: 16px; transition: all 0.2s;"
                            onmouseover="this.style.background='#0b7dda'" 
                            onmouseout="this.style.background='#2196F3'">
                        💵 Payer sur place (Cash)
                    </button>
                </div>
            </div>
        `;
        
        window.transportPaymentChoice = (choice) => {
            resolve(choice);
        };
        
        document.body.appendChild(modal);
    });
}

async function initiateTransportOnlinePayment(requestId) {
    // Show loading
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'transport-payment-loading';
    loadingDiv.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10001; display: flex; align-items: center; justify-content: center;';
    loadingDiv.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 12px; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 15px;">⏳</div>
            <div style="font-size: 18px; color: #2d3748;">Initialisation du paiement...</div>
        </div>
    `;
    document.body.appendChild(loadingDiv);
    
    try {
        const response = await fetch(`/api/v1/transport/requests/${requestId}/pay/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                payment_method: 'online'
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.payment_url) {
            window.location.href = data.payment_url;
        } else {
            loadingDiv.remove();
            showTransportAlert('error', data.message || 'Erreur lors de l\'initialisation du paiement');
        }
    } catch (error) {
        loadingDiv.remove();
        console.error('Payment error:', error);
        showTransportAlert('error', 'Une erreur est survenue lors du paiement');
    }
}

async function requestTransportCashPayment(requestId) {
    // Show loading
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'transport-payment-loading';
    loadingDiv.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10001; display: flex; align-items: center; justify-content: center;';
    loadingDiv.innerHTML = `
        <div style="background: white; padding: 30px; border-radius: 12px; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 15px;">⏳</div>
            <div style="font-size: 18px; color: #2d3748;">Envoi de la demande...</div>
        </div>
    `;
    document.body.appendChild(loadingDiv);
    
    try {
        const response = await fetch(`/api/v1/transport/requests/${requestId}/pay/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                payment_method: 'cash'
            })
        });
        
        const data = await response.json();
        loadingDiv.remove();
        
        if (data.success) {
            showTransportAlert('success', 'Demande de paiement envoyée! Le transporteur a été notifié et validera votre paiement en espèces à l\'arrivée.');
            setTimeout(() => location.reload(), 3000);
        } else {
            showTransportAlert('error', data.message || 'Erreur lors de l\'envoi de la demande');
        }
    } catch (error) {
        loadingDiv.remove();
        console.error('Payment request error:', error);
        showTransportAlert('error', 'Une erreur est survenue lors de l\'envoi de la demande');
    }
}

function showTransportAlert(type, message) {
    const alert = document.createElement('div');
    alert.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 10002; display: flex; align-items: center; justify-content: center; padding: 20px;';
    alert.onclick = () => alert.remove();
    
    const icon = type === 'success' ? '✅' : '❌';
    const bgColor = type === 'success' ? '#d4edda' : '#f8d7da';
    const borderColor = type === 'success' ? '#c3e6cb' : '#f5c6cb';
    const textColor = type === 'success' ? '#155724' : '#721c24';
    
    alert.innerHTML = `
        <div onclick="event.stopPropagation()" style="background: white; padding: 30px; border-radius: 16px; max-width: 450px; width: 100%; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.2);">
            <div style="font-size: 64px; margin-bottom: 15px;">${icon}</div>
            <div style="background: ${bgColor}; border: 1px solid ${borderColor}; color: ${textColor}; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                ${message}
            </div>
            <button onclick="this.closest('div').parentElement.remove();" style="padding: 12px 24px; background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; font-weight: 600;">
                OK
            </button>
        </div>
    `;
    
    document.body.appendChild(alert);
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
