// Multi-practitioner Appointments JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    let selectedPractitioners = [];
    
    // Search practitioners
    const practitionerSearch = document.getElementById('practitionerSearch');
    if (practitionerSearch) {
        let searchTimeout;
        practitionerSearch.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchPractitioners(e.target.value);
            }, 300);
        });
    }
    
    function searchPractitioners(query) {
        if (query.length < 2) return;
        
        fetch(`/api/appointments/search-practitioners/?q=${encodeURIComponent(query)}`, {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            displayPractitionerResults(data.practitioners);
        })
        .catch(error => console.error('Error:', error));
    }
    
    function displayPractitionerResults(practitioners) {
        const container = document.getElementById('practitionerResults');
        if (!container) return;
        
        container.innerHTML = practitioners.map(p => `
            <div class="practitioner-result" onclick="addPractitioner(${p.id}, '${p.name}', '${p.specialty}')">
                <div class="practitioner-info">
                    <strong>${p.name}</strong>
                    <span class="text-muted">${p.specialty}</span>
                </div>
                <button type="button" class="btn btn-sm btn-primary">Ajouter</button>
            </div>
        `).join('');
    }
    
    window.addPractitioner = function(id, name, specialty) {
        if (selectedPractitioners.find(p => p.id === id)) {
            showNotification('Praticien déjà ajouté', 'warning');
            return;
        }
        
        selectedPractitioners.push({ id, name, specialty });
        updateSelectedPractitioners();
    };
    
    window.removePractitioner = function(id) {
        selectedPractitioners = selectedPractitioners.filter(p => p.id !== id);
        updateSelectedPractitioners();
    };
    
    function updateSelectedPractitioners() {
        const container = document.getElementById('selectedPractitioners');
        if (!container) return;
        
        container.innerHTML = selectedPractitioners.map(p => `
            <div class="selected-practitioner">
                <div>
                    <strong>${p.name}</strong>
                    <span class="text-muted">${p.specialty}</span>
                </div>
                <button type="button" class="btn btn-sm btn-danger" onclick="removePractitioner(${p.id})">
                    Retirer
                </button>
            </div>
        `).join('');
        
        // Update hidden input
        document.getElementById('practitionerIds').value = selectedPractitioners.map(p => p.id).join(',');
    }
    
    // Book multi-practitioner appointment
    const multiPractitionerForm = document.getElementById('multiPractitionerAppointmentForm');
    if (multiPractitionerForm) {
        multiPractitionerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (selectedPractitioners.length === 0) {
                showNotification('Veuillez sélectionner au moins un praticien', 'warning');
                return;
            }
            
            const formData = new FormData(multiPractitionerForm);
            
            fetch('/api/appointments/multi-practitioner/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    practitioners: selectedPractitioners.map(p => p.id),
                    date: formData.get('date'),
                    time: formData.get('time'),
                    reason: formData.get('reason'),
                    notes: formData.get('notes')
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Rendez-vous créé avec succès', 'success');
                    window.location.href = '/appointments/';
                } else {
                    showNotification(data.error || 'Erreur lors de la création', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Erreur de connexion', 'error');
            });
        });
    }
});
