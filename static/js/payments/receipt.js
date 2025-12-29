document.addEventListener('DOMContentLoaded', function() {
    setupReceiptActions();
});

function setupReceiptActions() {
    const printButton = document.querySelector('.receipt-actions button[onclick*="print"]');
    if (printButton) {
        printButton.addEventListener('click', handlePrint);
    }
}

function handlePrint(event) {
    if (event) {
        event.preventDefault();
    }
    window.print();
}

function printReceipt() {
    window.print();
}
