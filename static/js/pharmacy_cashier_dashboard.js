function openNewSaleModal() {
    document.getElementById('newSaleModal').style.display = 'block';
}

function togglePatientSearch(customerType) {
    const patientSearchGroup = document.getElementById('patientSearchGroup');
    if (customerType === 'patient') {
        patientSearchGroup.style.display = 'block';
    } else {
        patientSearchGroup.style.display = 'none';
    }
}

function addSaleItem() {
    console.log('Add sale item');
}

function viewSale(saleId) {
    console.log('View sale:', saleId);
}

function printReceipt(saleId) {
    console.log('Print receipt for sale:', saleId);
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function submitNewSale(event) {
    event.preventDefault();
    console.log('Submit new sale');
    closeModal('newSaleModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
