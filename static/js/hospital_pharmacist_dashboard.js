function viewPrescription(prescriptionId) {
    console.log('View prescription:', prescriptionId);
    document.getElementById('prescriptionModal').style.display = 'block';
}

function preparePrescription(prescriptionId) {
    document.getElementById('prescriptionId').value = prescriptionId;
    document.getElementById('preparePrescriptionModal').style.display = 'block';
}

function deliverPrescription(prescriptionId) {
    console.log('Deliver prescription:', prescriptionId);
}

function orderStock(itemId) {
    console.log('Order stock for item:', itemId);
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function submitPrescriptionPreparation(event) {
    event.preventDefault();
    console.log('Submit prescription preparation');
    closeModal('preparePrescriptionModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
