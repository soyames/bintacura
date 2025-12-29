function filterAppointments() {
    console.log('Filter appointments');
}

function openNewAppointmentModal() {
    document.getElementById('newAppointmentModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function searchPatients(query) {
    console.log('Search patients:', query);
}

function submitNewAppointment(event) {
    event.preventDefault();
    console.log('Submit new appointment');
    closeModal('newAppointmentModal');
}

function submitEditAppointment(event) {
    event.preventDefault();
    console.log('Submit edit appointment');
    closeModal('editAppointmentModal');
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}
