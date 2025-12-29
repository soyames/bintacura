function viewOrder(orderId) {
    console.log('View order:', orderId);
    document.getElementById('orderModal').style.display = 'block';
}

function prepareOrder(orderId) {
    console.log('Prepare order:', orderId);
}

function deliverOrder(orderId) {
    console.log('Deliver order:', orderId);
}

function orderStock(itemId) {
    console.log('Order stock for item:', itemId);
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
