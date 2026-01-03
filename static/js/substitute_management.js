// Substitute Management JavaScript

let currentAppointmentId = null;

// Load appointments on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAppointments();
    loadAvailableDoctors();
    setupFormHandlers();
});

// Load appointments with filters
function loadAppointments() {
    const startDate = document.getElementById('filter-start-date').value;
    const endDate = document.getElementById('filter-end-date').value;
    const status = document.getElementById('filter-status').value;

    let url = '/api/appointments/my-appointments/?';
    const params = [];
    
    if (startDate) params.push(`start_date=${startDate}`);
    if (endDate) params.push(`end_date=${endDate}`);
    if (status) params.push(`status=${status}`);
    
    url += params.join('&');

    fetch(url, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        displayAppointments(data.results || data);
    })
    .catch(error => {
        console.error('Error loading appointments:', error);
        showError('Erreur lors du chargement des rendez-vous');
    });
}

// Display appointments
function displayAppointments(appointments) {
    const grid = document.getElementById('appointments-grid');
    
    if (!appointments || appointments.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-calendar-times"></i>
                <p>Aucun rendez-vous trouvé</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = appointments.map(apt => {
        const hasSubstitute = apt.substitute_doctor;
        const date = new Date(apt.appointment_date);
        
        return `
            <div class="appointment-card ${hasSubstitute ? 'has-substitute' : ''}">
                <div class="appointment-header">
                    <div>
                        <div class="appointment-date">${formatDate(date)}</div>
                        <div class="appointment-time">${formatTime(date)}</div>
                    </div>
                    <span class="status-badge status-${apt.status}">
                        ${getStatusLabel(apt.status)}
                    </span>
                </div>

                <div class="patient-info">
                    <div class="patient-name">
                        <i class="fas fa-user"></i> ${apt.patient_name}
                    </div>
                    <div class="appointment-type">
                        <i class="fas fa-stethoscope"></i> ${apt.appointment_type_display || apt.appointment_type}
                    </div>
                </div>

                ${hasSubstitute ? `
                    <div class="substitute-info">
                        <div class="label">MÉDECIN REMPLAÇANT</div>
                        <div class="doctor-name">
                            <i class="fas fa-user-md"></i> Dr. ${apt.substitute_doctor_name}
                        </div>
                        <div class="reason">
                            <i class="fas fa-info-circle"></i> ${getReasonLabel(apt.substitute_reason)}
                        </div>
                    </div>
                ` : ''}

                <div class="card-actions">
                    ${!hasSubstitute ? `
                        <button class="btn-assign" onclick="openSubstituteModal('${apt.uid}')">
                            <i class="fas fa-user-plus"></i> Assigner un remplaçant
                        </button>
                    ` : `
                        <button class="btn-cancel-substitute" onclick="openCancelModal('${apt.uid}')">
                            <i class="fas fa-times"></i> Annuler le remplacement
                        </button>
                    `}
                    <button class="btn-view" onclick="viewAppointmentDetails('${apt.uid}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Load available doctors for substitution
function loadAvailableDoctors() {
    fetch('/api/doctors/', {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        const select = document.getElementById('substitute-doctor');
        select.innerHTML = '<option value="">Sélectionnez un médecin</option>' +
            data.results.map(doc => 
                `<option value="${doc.uid}">Dr. ${doc.full_name} - ${doc.specialty || 'Médecine Générale'}</option>`
            ).join('');
    })
    .catch(error => console.error('Error loading doctors:', error));
}

// Open substitute modal
function openSubstituteModal(appointmentId) {
    // Fetch appointment details
    fetch(`/api/appointments/${appointmentId}/`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(apt => {
        document.getElementById('appointment-id').value = apt.uid;
        document.getElementById('patient-info').textContent = apt.patient_name;
        document.getElementById('appointment-date').textContent = 
            formatDate(new Date(apt.appointment_date)) + ' à ' + formatTime(new Date(apt.appointment_date));
        
        document.getElementById('substituteModal').style.display = 'block';
    })
    .catch(error => {
        console.error('Error loading appointment:', error);
        showError('Erreur lors du chargement du rendez-vous');
    });
}

// Close substitute modal
function closeSubstituteModal() {
    document.getElementById('substituteModal').style.display = 'none';
    document.getElementById('substituteForm').reset();
}

// Open cancel modal
function openCancelModal(appointmentId) {
    document.getElementById('cancel-appointment-id').value = appointmentId;
    document.getElementById('cancelSubstituteModal').style.display = 'block';
}

// Close cancel modal
function closeCancelModal() {
    document.getElementById('cancelSubstituteModal').style.display = 'none';
}

// Setup form handlers
function setupFormHandlers() {
    document.getElementById('substituteForm').addEventListener('submit', function(e) {
        e.preventDefault();
        assignSubstitute();
    });
}

// Assign substitute
function assignSubstitute() {
    const appointmentId = document.getElementById('appointment-id').value;
    const substituteDoctor = document.getElementById('substitute-doctor').value;
    const reason = document.getElementById('substitute-reason').value;

    if (!substituteDoctor || !reason) {
        showError('Veuillez remplir tous les champs obligatoires');
        return;
    }

    fetch(`/api/appointments/${appointmentId}/assign-substitute/`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            substitute_doctor: substituteDoctor,
            reason: reason
        })
    })
    .then(response => {
        if (!response.ok) throw new Error('Erreur lors de l\'assignation');
        return response.json();
    })
    .then(data => {
        showSuccess('Médecin remplaçant assigné avec succès');
        closeSubstituteModal();
        loadAppointments();
    })
    .catch(error => {
        console.error('Error assigning substitute:', error);
        showError('Erreur lors de l\'assignation du remplaçant');
    });
}

// Confirm cancel substitute
function confirmCancelSubstitute() {
    const appointmentId = document.getElementById('cancel-appointment-id').value;

    fetch(`/api/appointments/${appointmentId}/cancel-substitute/`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Erreur lors de l\'annulation');
        return response.json();
    })
    .then(data => {
        showSuccess('Remplacement annulé avec succès');
        closeCancelModal();
        loadAppointments();
    })
    .catch(error => {
        console.error('Error canceling substitute:', error);
        showError('Erreur lors de l\'annulation du remplacement');
    });
}

// View appointment details
function viewAppointmentDetails(appointmentId) {
    window.location.href = `/appointments/${appointmentId}/`;
}

// Utility functions
function formatDate(date) {
    return date.toLocaleDateString('fr-FR', { 
        weekday: 'long',
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
}

function formatTime(date) {
    return date.toLocaleTimeString('fr-FR', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function getStatusLabel(status) {
    const labels = {
        'pending': 'En attente',
        'confirmed': 'Confirmé',
        'cancelled': 'Annulé',
        'completed': 'Terminé',
        'no_show': 'Non présenté'
    };
    return labels[status] || status;
}

function getReasonLabel(reason) {
    const labels = {
        'vacation': 'Congé / Vacances',
        'sick_leave': 'Congé Maladie',
        'emergency': 'Urgence',
        'conference': 'Conférence / Formation',
        'other': 'Autre'
    };
    return labels[reason] || reason;
}

function showSuccess(message) {
    // You can integrate your existing notification system
    alert(message);
}

function showError(message) {
    // You can integrate your existing notification system
    alert(message);
}

// Close modals when clicking outside
window.onclick = function(event) {
    const substituteModal = document.getElementById('substituteModal');
    const cancelModal = document.getElementById('cancelSubstituteModal');
    
    if (event.target == substituteModal) {
        closeSubstituteModal();
    }
    if (event.target == cancelModal) {
        closeCancelModal();
    }
}
