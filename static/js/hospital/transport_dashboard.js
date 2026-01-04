// Transport Dashboard JavaScript

async function showAssignmentModal(requestId, patientName) {
    document.getElementById('assignment_request_id').value = requestId;
    document.getElementById('assignment_patient_name').textContent = patientName;
    
    // Load drivers and vehicles
    await loadDrivers();
    await loadVehicles();
    
    document.getElementById('assignmentModal').style.display = 'flex';
}

function closeAssignmentModal() {
    document.getElementById('assignmentModal').style.display = 'none';
}

async function loadDrivers() {
    try {
        console.log('Loading drivers...');
        const response = await fetch('/api/v1/hospital/staff/by_role/?role=driver');
        console.log('Drivers response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Drivers data:', data);
        const select = document.getElementById('driver_id');
        select.innerHTML = '<option value="">Sélectionner un chauffeur</option>';
        
        if (data && data.length > 0) {
            data.forEach(driver => {
                const option = document.createElement('option');
                option.value = driver.staff_participant?.uid || driver.id;
                option.textContent = `${driver.full_name || driver.staff_participant?.full_name} - ${driver.phone_number || driver.staff_participant?.phone_number || ''}`;
                select.appendChild(option);
            });
        } else {
            select.innerHTML += '<option value="" disabled>Aucun chauffeur disponible - Ajoutez un staff avec le rôle "driver"</option>';
        }
    } catch (error) {
        console.error('Error loading drivers:', error);
        document.getElementById('driver_id').innerHTML = '<option value="" disabled>Erreur de chargement</option>';
    }
}

async function loadVehicles() {
    try {
        console.log('Loading vehicles from context...');
        const select = document.getElementById('vehicle_id');
        select.innerHTML = '<option value="">Sélectionner un véhicule</option>';
        
        // Use vehicles from Django context (passed via data attribute or inline script)
        if (typeof window.hospitalVehicles !== 'undefined' && window.hospitalVehicles.length > 0) {
            window.hospitalVehicles.forEach(vehicle => {
                const option = document.createElement('option');
                option.value = vehicle.plate;
                option.textContent = `${vehicle.name} (${vehicle.plate})`;
                select.appendChild(option);
            });
        } else {
            select.innerHTML += '<option value="" disabled>Aucun véhicule disponible</option>';
        }
    } catch (error) {
        console.error('Error loading vehicles:', error);
        document.getElementById('vehicle_id').innerHTML = '<option value="" disabled>Erreur de chargement</option>';
    }
}

// Accept transport request (Step 1: Lock it)
async function acceptRequest(requestId) {
    console.log('🔵 Accepting request:', requestId);
    
    if (!confirm('Voulez-vous accepter cette demande de transport? Elle sera réservée pour votre hôpital.')) {
        return;
    }
    
    try {
        const url = `/api/v1/hospital/transport/requests/${requestId}/accept/`;
        console.log('🔵 POST to:', url);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({})
        });
        
        let result;
        const responseText = await response.text();
        
        try {
            result = JSON.parse(responseText);
        } catch (e) {
            console.error('❌ Failed to parse JSON response:', e);
            result = { error: responseText };
        }
        
        if (response.ok) {
            // Get patient name from the button's data attribute
            const button = document.querySelector(`button[data-request-id="${requestId}"]`);
            const patientName = button ? button.getAttribute('data-patient-name') : '';
            
            // Immediately update the UI without page reload
            const actionsCell = document.querySelector(`td[data-request-id="${requestId}"]`);
            if (actionsCell) {
                actionsCell.innerHTML = `
                    <span class="status-accepted-by-me">✓ Acceptée</span>
                    <button class="btn-action btn-assign" 
                            onclick="showAssignmentModal('${requestId}', '${patientName}')"
                            data-request-id="${requestId}">
                        👤 Assigner
                    </button>
                `;
            }
            
            alert('✅ Transport accepté! Veuillez maintenant assigner le personnel.');
        } else {
            const errorMsg = result.error || result.message || result.detail || response.statusText || 'Une erreur est survenue';
            alert(`❌ Erreur (${response.status}): ${errorMsg}\n\nURL: ${url}`);
            console.error('Error response:', response.status, result);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        alert('❌ Erreur lors de l\'acceptation: ' + error.message);
    }
}

// Submit staff assignment (Step 2)
async function submitAssignment(event) {
    event.preventDefault();
    
    const requestId = document.getElementById('assignment_request_id').value;
    const driverId = document.getElementById('driver_id').value;
    const vehicleId = document.getElementById('vehicle_id').value;
    const notes = document.getElementById('assignment_notes').value;

    console.log('Submitting assignment:', { requestId, driverId, vehicleId, notes });

    try {
        const url = `/api/v1/hospital/transport/requests/${requestId}/assign/`;
        console.log('POST to:', url);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                driver_id: driverId,
                vehicle_id: vehicleId,
                notes: notes
            })
        });
        
        console.log('Response status:', response.status);
        const result = await response.json();
        console.log('Response data:', result);
        
        if (response.ok) {
            alert('✅ Personnel assigné avec succès!');
            closeAssignmentModal();
            location.reload();
        } else {
            alert('❌ Erreur: ' + (result.error || result.message || 'Une erreur est survenue'));
            console.error('Error response:', result);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        alert('❌ Erreur lors de l\'assignation: ' + error.message);
    }
}

async function transferTransport(uid) {
    document.getElementById('transfer_request_id').value = uid;
    await loadHospitals();
    document.getElementById('transferModal').style.display = 'flex';
}

function closeTransferModal() {
    document.getElementById('transferModal').style.display = 'none';
}

async function loadHospitals() {
    try {
        const response = await fetch('/api/v1/core/participants/?role=hospital&is_active=true');
        const data = await response.json();
        const select = document.getElementById('target_hospital_id');
        select.innerHTML = '<option value="">Sélectionner un hôpital</option>';
        
        if (data.results) {
            data.results.forEach(hospital => {
                const currentUserId = document.querySelector('[data-user-id]')?.getAttribute('data-user-id');
                if (hospital.uid !== currentUserId) {
                    const option = document.createElement('option');
                    option.value = hospital.uid;
                    option.textContent = hospital.full_name;
                    select.appendChild(option);
                }
            });
        }
    } catch (error) {
        console.error('Error loading hospitals:', error);
    }
}

async function submitTransfer(event) {
    event.preventDefault();
    
    const requestId = document.getElementById('transfer_request_id').value;
    const data = {
        target_hospital_id: document.getElementById('target_hospital_id').value,
        notes: document.getElementById('transfer_notes').value
    };

    try {
        const response = await fetch(`/api/v1/hospital/transport/requests/${requestId}/transfer/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (response.ok) {
            alert(result.message);
            closeTransferModal();
            location.reload();
        } else {
            alert('Erreur: ' + (result.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        alert('Erreur lors du transfert');
    }
}

function viewTransport(uid) {
    window.location.href = '/transport/track/' + uid + '/';
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Timer functionality for 30-minute auto-release
function updateTimers() {
    const timerBadges = document.querySelectorAll('.timer-badge');
    
    timerBadges.forEach(badge => {
        const acceptedTime = badge.getAttribute('data-accepted-time');
        if (!acceptedTime) return;
        
        const acceptedDate = new Date(acceptedTime);
        const now = new Date();
        const elapsed = Math.floor((now - acceptedDate) / 1000); // seconds
        const remaining = (30 * 60) - elapsed; // 30 minutes in seconds
        
        if (remaining <= 0) {
            badge.textContent = '⏰ Expiré';
            badge.style.background = '#fee';
            badge.style.color = '#c00';
            // Auto-reload to show updated status
            setTimeout(() => location.reload(), 2000);
        } else {
            const minutes = Math.floor(remaining / 60);
            const seconds = remaining % 60;
            badge.textContent = `⏱️ ${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            if (minutes < 5) {
                badge.style.background = '#fee';
                badge.style.color = '#c00';
            } else if (minutes < 10) {
                badge.style.background = '#fff3cd';
                badge.style.color = '#856404';
            } else {
                badge.style.background = '#d4edda';
                badge.style.color = '#155724';
            }
        }
    });
}

// Update timers every second
if (document.querySelectorAll('.timer-badge').length > 0) {
    updateTimers();
    setInterval(updateTimers, 1000);
}
