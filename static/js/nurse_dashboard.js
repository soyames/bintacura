function recordVitals(admissionId) {
    document.getElementById('admissionId').value = admissionId;
    document.getElementById('vitalsModal').style.display = 'block';
}

function administMedication(admissionId) {
    document.getElementById('medicationAdmissionId').value = admissionId;
    document.getElementById('medicationModal').style.display = 'block';
}

function addNurseNotes(admissionId) {
    console.log('Add nurse notes for admission:', admissionId);
}

function startTask(taskId) {
    console.log('Start task:', taskId);
}

function completeTask(taskId) {
    console.log('Complete task:', taskId);
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function submitVitals(event) {
    event.preventDefault();
    console.log('Submit vitals');
    closeModal('vitalsModal');
}

function submitMedication(event) {
    event.preventDefault();
    console.log('Submit medication');
    closeModal('medicationModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
