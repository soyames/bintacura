function openNewAppointmentModal() {
    document.getElementById('newAppointmentModal').style.display = 'block';
}

function openNewAdmissionModal() {
    document.getElementById('newAdmissionModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function confirmAppointment(appointmentId) {
    console.log('Confirm appointment:', appointmentId);
}

function rescheduleAppointment(appointmentId) {
    console.log('Reschedule appointment:', appointmentId);
}

function assignDoctor(appointmentId, doctorId) {
    if (doctorId) {
        console.log('Assign doctor', doctorId, 'to appointment', appointmentId);
    }
}

function approveAppointment(appointmentId) {
    console.log('Approve appointment:', appointmentId);
}

function rejectAppointment(appointmentId) {
    console.log('Reject appointment:', appointmentId);
}

function assignBed(admissionId) {
    console.log('Assign bed to admission:', admissionId);
}

function viewAdmission(admissionId) {
    console.log('View admission:', admissionId);
}

function searchPatients(query) {
    console.log('Search patients:', query);
}

function submitNewAppointment(event) {
    event.preventDefault();
    console.log('Submit new appointment');
    closeModal('newAppointmentModal');
}

function submitNewAdmission(event) {
    event.preventDefault();
    console.log('Submit new admission');
    closeModal('newAdmissionModal');
}

function searchPatientsForAdmission(query) {
    console.log('Search patients for admission:', query);
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
