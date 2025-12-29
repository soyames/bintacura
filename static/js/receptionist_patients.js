function filterPatients() {
    console.log('Filter patients');
}

function sortPatients() {
    console.log('Sort patients');
}

function openNewPatientModal() {
    document.getElementById('newPatientModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function viewPatient(patientId) {
    console.log('View patient:', patientId);
    document.getElementById('viewPatientModal').style.display = 'block';
}

function createAppointmentForPatient(patientId) {
    console.log('Create appointment for patient:', patientId);
}

function submitNewPatient(event) {
    event.preventDefault();
    console.log('Submit new patient');
    closeModal('newPatientModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
