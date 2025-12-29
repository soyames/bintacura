function openReorderModal() {
    document.getElementById('reorderModal').style.display = 'block';
}

function reorderItem(itemId) {
    console.log('Reorder item:', itemId);
    openReorderModal();
}

function editItem(itemId) {
    console.log('Edit item:', itemId);
}

function moveToDisposal(itemId) {
    console.log('Move to disposal:', itemId);
}

function viewItem(itemId) {
    console.log('View item:', itemId);
}

function addOrderItem() {
    console.log('Add order item');
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function submitReorder(event) {
    event.preventDefault();
    console.log('Submit reorder');
    closeModal('reorderModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
