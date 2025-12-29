function startDelivery(orderId) {
    console.log('Start delivery:', orderId);
    document.getElementById('deliveryOrderId').value = orderId;
    document.getElementById('deliveryConfirmModal').style.display = 'block';
}

function viewMap(orderId) {
    console.log('View map for order:', orderId);
}

function callCustomer(phone_number) {
    console.log('Call customer:', phone_number);
    window.location.href = 'tel:' + phone_number;
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function clearSignature() {
    const canvas = document.getElementById('signatureCanvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function confirmDelivery(event) {
    event.preventDefault();
    console.log('Confirm delivery');
    closeModal('deliveryConfirmModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
