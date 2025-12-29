// Staff Management JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('addStaffModal');
    const addBtn = document.getElementById('addStaffBtn');
    const closeBtn = document.querySelector('.close');
    const cancelBtn = document.getElementById('cancelBtn');
    const addStaffForm = document.getElementById('addStaffForm');
    const autoGenerateCheckbox = document.getElementById('autoGeneratePassword');
    const manualPasswordSection = document.getElementById('manualPasswordSection');
    const passwordInput = document.getElementById('password');

    // Toggle manual password section
    autoGenerateCheckbox.addEventListener('change', function() {
        if (this.checked) {
            manualPasswordSection.style.display = 'none';
            passwordInput.removeAttribute('required');
        } else {
            manualPasswordSection.style.display = 'block';
            passwordInput.setAttribute('required', 'required');
        }
    });

    // Open modal
    addBtn.addEventListener('click', function() {
        modal.style.display = 'block';
    });

    // Close modal
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    cancelBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });

    // Handle add staff form submission
    addStaffForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(addStaffForm);
        const autoGenerate = autoGenerateCheckbox.checked;
        
        // Password validation if manual
        if (!autoGenerate) {
            const password = formData.get('password');
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            if (password !== confirmPassword) {
                showNotification('Les mots de passe ne correspondent pas', 'error');
                return;
            }
            
            if (password.length < 8) {
                showNotification('Le mot de passe doit contenir au moins 8 caractères', 'error');
                return;
            }
        }
        
        const data = {
            full_name: formData.get('full_name'),
            phone_number: formData.get('phone_number'),
            email: formData.get('email'),
            role: formData.get('role'),
            assigned_counter: formData.get('assigned_counter') || null,
            auto_generate_password: autoGenerate,
            password: autoGenerate ? '' : formData.get('password')
        };

        try {
            const response = await fetch('/api/v1/pharmacy/staff/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                const result = await response.json();
                showNotification('Personnel ajouté avec succès! Les accès ont été envoyés par email et SMS.', 'success');
                modal.style.display = 'none';
                addStaffForm.reset();
                
                // Reload page to show new staff
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                const error = await response.json();
                showNotification(error.message || 'Failed to add staff member', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('An error occurred. Please try again.', 'error');
        }
    });

    // Handle toggle staff (activate/deactivate) - Event delegation
    document.addEventListener('click', async function(e) {
        if (e.target.closest('.toggle-staff')) {
            const btn = e.target.closest('.toggle-staff');
            const staffId = btn.getAttribute('data-staff-id');
            const action = btn.getAttribute('data-action');
            
            const confirmMsg = action === 'deactivate' 
                ? 'Êtes-vous sûr de vouloir désactiver cet employé?' 
                : 'Êtes-vous sûr de vouloir activer cet employé?';
            
            if (!confirm(confirmMsg)) return;
            
            try {
                const response = await fetch(`/api/v1/pharmacy/staff/${staffId}/`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        is_active: action === 'activate'
                    })
                });
                
                if (response.ok) {
                    showNotification(
                        action === 'activate' ? 'Employé activé' : 'Employé désactivé', 
                        'success'
                    );
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    showNotification('Une erreur est survenue', 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('Erreur lors de la mise à jour', 'error');
            }
        }
    });

    // Handle edit staff
    document.querySelectorAll('.edit-staff').forEach(btn => {
        btn.addEventListener('click', function() {
            const staffId = this.dataset.staffId;
            // TODO: Implement edit functionality
            console.log('Edit staff:', staffId);
            showNotification('Fonctionnalité d\'édition bientôt disponible', 'info');
        });
    });

    // Handle delete staff
    document.querySelectorAll('.delete-staff').forEach(btn => {
        btn.addEventListener('click', async function() {
            const staffId = this.dataset.staffId;
            
            if (confirm('Êtes-vous sûr de vouloir supprimer cet employé? Cette action est irréversible.')) {
                try {
                    const response = await fetch(`/api/v1/pharmacy/staff/${staffId}/`, {
                        method: 'DELETE',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    });

                    if (response.ok) {
                        showNotification('Employé supprimé avec succès', 'success');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else {
                        showNotification('Erreur lors de la suppression', 'error');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showNotification('Une erreur est survenue', 'error');
                }
            }
        });
    });
});

// Helper function to get CSRF token
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

// Notification helper
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
        color: white;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
