function openAddDepartmentModal() {
    document.getElementById('addDepartmentModal').style.display = 'block';
}

function editDepartment(departmentId) {
    console.log('Edit department:', departmentId);
}

function viewDepartment(departmentId) {
    console.log('View department:', departmentId);
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function submitNewDepartment(event) {
    event.preventDefault();
    console.log('Submit new department');
    closeModal('addDepartmentModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
