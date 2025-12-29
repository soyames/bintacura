document.addEventListener('DOMContentLoaded', function() {
    setupInvoiceActions();
});

function setupInvoiceActions() {
    const perPageSelect = document.getElementById('per-page-select');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            console.log('Per page changed to:', this.value);
        });
    }
}

function printReceipt() {
    window.print();
}
