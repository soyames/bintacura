// Preventive Care Reminders JavaScript

// Get CSRF token
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

const csrftoken = getCookie('csrftoken');

// Show Add Reminder Modal
function showAddReminderModal() {
    document.getElementById('addReminderModal').style.display = 'block';
    // Set today as default date
    document.getElementById('dueDate').valueAsDate = new Date();
}

// Close Add Reminder Modal
function closeAddReminderModal() {
    document.getElementById('addReminderModal').style.display = 'none';
    document.getElementById('addReminderForm').reset();
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('addReminderModal');
    if (event.target === modal) {
        closeAddReminderModal();
    }
}

// Add Reminder Form Submission
document.getElementById('addReminderForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        reminder_type: document.getElementById('reminderType').value,
        due_date: document.getElementById('dueDate').value,
        description: document.getElementById('description').value
    };
    
    try {
        const response = await fetch('/api/v1/patient/preventive-reminders/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            closeAddReminderModal();
            location.reload(); // Reload to show new reminder
        } else {
            const error = await response.json();
            alert('Erreur: ' + JSON.stringify(error));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Une erreur s\'est produite. Veuillez réessayer.');
    }
});

// Complete Reminder
async function completeReminder(reminderId) {
    if (!confirm('Marquer ce rappel comme complété?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/patient/preventive-reminders/${reminderId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({
                is_completed: true,
                completed_date: new Date().toISOString().split('T')[0]
            })
        });
        
        if (response.ok) {
            location.reload();
        } else {
            alert('Erreur lors de la mise à jour du rappel.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Une erreur s\'est produite. Veuillez réessayer.');
    }
}

// Edit Reminder
async function editReminder(reminderId) {
    try {
        const response = await fetch(`/api/v1/patient/preventive-reminders/${reminderId}/`);
        const reminder = await response.json();
        
        // Populate form with reminder data
        document.getElementById('reminderType').value = reminder.reminder_type;
        document.getElementById('dueDate').value = reminder.due_date;
        document.getElementById('description').value = reminder.description;
        
        // Show modal
        showAddReminderModal();
        
        // Change form submission to update
        const form = document.getElementById('addReminderForm');
        form.onsubmit = async function(e) {
            e.preventDefault();
            
            const formData = {
                reminder_type: document.getElementById('reminderType').value,
                due_date: document.getElementById('dueDate').value,
                description: document.getElementById('description').value
            };
            
            try {
                const updateResponse = await fetch(`/api/v1/patient/preventive-reminders/${reminderId}/`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify(formData)
                });
                
                if (updateResponse.ok) {
                    closeAddReminderModal();
                    location.reload();
                } else {
                    alert('Erreur lors de la mise à jour du rappel.');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Une erreur s\'est produite. Veuillez réessayer.');
            }
        };
    } catch (error) {
        console.error('Error:', error);
        alert('Impossible de charger le rappel.');
    }
}

// Delete Reminder
async function deleteReminder(reminderId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce rappel?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/patient/preventive-reminders/${reminderId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrftoken
            }
        });
        
        if (response.ok) {
            location.reload();
        } else {
            alert('Erreur lors de la suppression du rappel.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Une erreur s\'est produite. Veuillez réessayer.');
    }
}
