// Appointment Reminders JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    // Load reminder preferences
    function loadReminderPreferences() {
        fetch('/api/appointments/reminder-preferences/', {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            populateReminderForm(data);
        })
        .catch(error => console.error('Error loading preferences:', error));
    }
    
    // Populate reminder form
    function populateReminderForm(preferences) {
        if (preferences.email_enabled) {
            document.getElementById('emailReminders').checked = true;
        }
        if (preferences.sms_enabled) {
            document.getElementById('smsReminders').checked = true;
        }
        if (preferences.push_enabled) {
            document.getElementById('pushReminders').checked = true;
        }
        
        if (preferences.reminder_times) {
            preferences.reminder_times.forEach(time => {
                addReminderTimeField(time);
            });
        }
    }
    
    // Save reminder preferences
    const reminderForm = document.getElementById('reminderPreferencesForm');
    if (reminderForm) {
        reminderForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(reminderForm);
            const reminderTimes = Array.from(document.querySelectorAll('.reminder-time-input'))
                .map(input => parseInt(input.value));
            
            fetch('/api/appointments/reminder-preferences/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email_enabled: formData.get('email_enabled') === 'on',
                    sms_enabled: formData.get('sms_enabled') === 'on',
                    push_enabled: formData.get('push_enabled') === 'on',
                    reminder_times: reminderTimes
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Préférences de rappel enregistrées', 'success');
                } else {
                    showNotification('Erreur lors de l\'enregistrement', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Erreur de connexion', 'error');
            });
        });
    }
    
    // Add reminder time field
    window.addReminderTimeField = function(value = 24) {
        const container = document.getElementById('reminderTimesContainer');
        const div = document.createElement('div');
        div.className = 'reminder-time-field';
        div.innerHTML = `
            <select class="reminder-time-input form-control">
                <option value="1" ${value === 1 ? 'selected' : ''}>1 heure avant</option>
                <option value="2" ${value === 2 ? 'selected' : ''}>2 heures avant</option>
                <option value="24" ${value === 24 ? 'selected' : ''}>1 jour avant</option>
                <option value="48" ${value === 48 ? 'selected' : ''}>2 jours avant</option>
                <option value="72" ${value === 72 ? 'selected' : ''}>3 jours avant</option>
                <option value="168" ${value === 168 ? 'selected' : ''}>1 semaine avant</option>
            </select>
            <button type="button" class="btn btn-sm btn-danger" onclick="this.parentElement.remove()">
                Supprimer
            </button>
        `;
        container.appendChild(div);
    };
    
    // Initialize
    if (document.getElementById('reminderPreferencesForm')) {
        loadReminderPreferences();
    }
});
