let currentStaffId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadStaffList();
    setupEventListeners();
    
    // Password toggle functionality
    const autoGenerateCheckbox = document.getElementById('autoGeneratePassword');
    const manualPasswordSection = document.getElementById('manualPasswordSection');
    
    if (autoGenerateCheckbox && manualPasswordSection) {
        autoGenerateCheckbox.addEventListener('change', function() {
            if (this.checked) {
                manualPasswordSection.style.display = 'none';
                const passwordInput = document.getElementById('password');
                if (passwordInput) {
                    passwordInput.removeAttribute('required');
                }
            } else {
                manualPasswordSection.style.display = 'block';
                const passwordInput = document.getElementById('password');
                if (passwordInput) {
                    passwordInput.setAttribute('required', 'required');
                }
            }
        });
    }
});

function setupEventListeners() {
    const addStaffBtn = document.getElementById('addStaffBtn');
    if (addStaffBtn) {
        addStaffBtn.addEventListener('click', () => openStaffModal());
    }

    const staffForm = document.getElementById('addStaffForm');
    if (staffForm) {
        staffForm.addEventListener('submit', handleStaffSubmit);
    }

    const modalClose = document.querySelectorAll('.modal-close-modern');
    const modalOverlay = document.querySelector('.modal-overlay-modern');
    modalClose.forEach(btn => btn.addEventListener('click', closeStaffModal));
    if (modalOverlay) modalOverlay.addEventListener('click', closeStaffModal);
}

function loadStaffList() {
    fetch('/api/v1/pharmacy/staff/')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Staff data received:', data);
            console.log('Data type:', typeof data);
            console.log('Is array:', Array.isArray(data));
            renderStaffTable(data);
        })
        .catch(error => {
            console.error('Error loading staff:', error);
            showNotification('Erreur lors du chargement du personnel', 'error');
            const tbody = document.getElementById('staffTableBody');
            if (tbody) {
                tbody.innerHTML = `
                    <tr class="empty-state">
                        <td colspan="8">
                            <div class="empty-state-content">
                                <i class="fas fa-exclamation-triangle"></i>
                                <p>Erreur lors du chargement: ${error.message}</p>
                            </div>
                        </td>
                    </tr>
                `;
            }
        });
}

function renderStaffTable(responseData) {
    const tbody = document.getElementById('staffTableBody');
    if (!tbody) return;

    console.log('renderStaffTable called with:', responseData);

    // Handle different response formats
    let staffList = responseData;
    
    // DRF paginated response
    if (responseData && typeof responseData === 'object' && responseData.results) {
        staffList = responseData.results;
        console.log('Using results from paginated response');
    }
    // Wrapped in data object
    else if (responseData && typeof responseData === 'object' && responseData.data) {
        staffList = responseData.data;
        console.log('Using data property');
    }
    // Direct array
    else if (Array.isArray(responseData)) {
        staffList = responseData;
        console.log('Using direct array');
    }

    console.log('Final staffList:', staffList);
    console.log('Is array:', Array.isArray(staffList));
    console.log('Length:', staffList ? staffList.length : 'N/A');

    if (!staffList || !Array.isArray(staffList)) {
        console.error('staffList is not an array:', staffList);
        tbody.innerHTML = `
            <tr class="empty-state">
                <td colspan="8">
                    <div class="empty-state-content">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Format de données invalide</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    if (staffList.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-state">
                <td colspan="8">
                    <div class="empty-state-content">
                        <i class="fas fa-users"></i>
                        <p>Aucun membre du personnel</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = staffList.map(staff => {
        const initials = staff.full_name.split(' ').map(n => n[0]).join('').toUpperCase();
        const roleLabels = {
            'pharmacist': 'Pharmacien',
            'cashier': 'Caissier',
            'manager': 'Gérant',
            'inventory_clerk': 'Magasinier',
            'delivery_person': 'Livreur'
        };
        
        return `
            <tr data-staff-id="${staff.id}">
                <td>
                    <div class="staff-name-cell">
                        <div class="staff-avatar">${initials}</div>
                        <span class="staff-name">${staff.full_name}</span>
                    </div>
                </td>
                <td><span class="badge badge-role">${roleLabels[staff.role] || staff.role}</span></td>
                <td>${staff.phone_number || '-'}</td>
                <td>${staff.email}</td>
                <td>
                    ${staff.assigned_counter ? 
                        `<span class="badge badge-info">Comptoir ${staff.assigned_counter.counter_number}</span>` : 
                        '<span class="text-muted">Non assigné</span>'}
                </td>
                <td>
                    <span class="badge ${staff.is_active ? 'badge-success' : 'badge-secondary'}">
                        <i class="fas fa-${staff.is_active ? 'check-circle' : 'ban'}"></i>
                        ${staff.is_active ? 'Actif' : 'Inactif'}
                    </span>
                </td>
                <td>${staff.created_at || staff.hire_date ? new Date(staff.created_at || staff.hire_date).toLocaleDateString('fr-FR') : '-'}</td>
                <td>
                    <div class="action-buttons-modern">
                        <button class="btn-icon-modern btn-edit" onclick="editStaff('${staff.id}')" title="Modifier les informations">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-icon-modern ${staff.is_active ? 'btn-warning' : 'btn-success'}" 
                                onclick="toggleStaffStatus('${staff.id}')" 
                                title="${staff.is_active ? 'Désactiver l\'accès' : 'Réactiver l\'accès'}">
                            <i class="fas fa-${staff.is_active ? 'user-lock' : 'user-check'}"></i>
                        </button>
                        <button class="btn-icon-modern btn-danger" onclick="deleteStaff('${staff.id}')" title="Supprimer définitivement">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function openStaffModal(staffId = null) {
    currentStaffId = staffId;
    const modal = document.getElementById('addStaffModal');
    const form = document.getElementById('addStaffForm');
    const title = modal.querySelector('h2');
    
    if (staffId) {
        title.innerHTML = '<i class="fas fa-user-edit"></i> Modifier le Personnel';
        fetch(`/api/v1/pharmacy/staff/${staffId}/`)
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch staff');
                return response.json();
            })
            .then(staff => {
                document.getElementById('fullName').value = staff.full_name;
                document.getElementById('email').value = staff.email;
                document.getElementById('phoneNumber').value = staff.phone_number || '';
                document.getElementById('role').value = staff.role;
                if (document.getElementById('counter')) {
                    document.getElementById('counter').value = staff.assigned_counter?.id || '';
                }
                const passwordSection = document.getElementById('manualPasswordSection');
                if (passwordSection) {
                    passwordSection.style.display = 'none';
                }
                const autoGenSection = document.getElementById('autoGeneratePassword');
                if (autoGenSection && autoGenSection.closest('.form-group-modern')) {
                    autoGenSection.closest('.form-group-modern').style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error loading staff:', error);
                showNotification('Erreur lors du chargement des données', 'error');
            });
    } else {
        title.innerHTML = '<i class="fas fa-user-plus"></i> Ajouter un Membre du Personnel';
        form.reset();
        const passwordSection = document.getElementById('manualPasswordSection');
        if (passwordSection) {
            passwordSection.style.display = 'none';
        }
        const autoGenSection = document.getElementById('autoGeneratePassword');
        if (autoGenSection && autoGenSection.closest('.form-group-modern')) {
            autoGenSection.closest('.form-group-modern').style.display = 'block';
        }
    }
    
    modal.style.display = 'flex';
}

function closeStaffModal() {
    const modal = document.getElementById('addStaffModal');
    modal.style.display = 'none';
    currentStaffId = null;
    document.getElementById('addStaffForm').reset();
}

function handleStaffSubmit(e) {
    e.preventDefault();
    
    const formData = {
        full_name: document.getElementById('fullName').value,
        email: document.getElementById('email').value,
        phone_number: document.getElementById('phoneNumber').value,
        role: document.getElementById('role').value,
    };
    
    // Add counter if selected
    const counterSelect = document.getElementById('counter');
    if (counterSelect && counterSelect.value) {
        formData.assigned_counter = counterSelect.value;
    }
    
    // Only add password fields when creating new staff
    if (!currentStaffId) {
        formData.auto_generate_password = document.getElementById('autoGeneratePassword').checked;
        
        if (!formData.auto_generate_password) {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            if (password !== confirmPassword) {
                showNotification('Les mots de passe ne correspondent pas', 'error');
                return;
            }
            
            if (password.length < 8) {
                showNotification('Le mot de passe doit contenir au moins 8 caractères', 'error');
                return;
            }
            
            formData.password = password;
        }
    }
    
    const url = currentStaffId 
        ? `/api/v1/pharmacy/staff/${currentStaffId}/`
        : '/api/v1/pharmacy/staff/';
    
    const method = currentStaffId ? 'PUT' : 'POST';
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.json();
    })
    .then(data => {
        showNotification(
            currentStaffId ? 'Personnel mis à jour avec succès' : 'Personnel ajouté avec succès',
            'success'
        );
        closeStaffModal();
        loadStaffList();
    })
    .catch(error => {
        console.error('Error saving staff:', error);
        const errorMsg = error.email ? error.email[0] : 
                        error.detail || 
                        error.non_field_errors?.[0] ||
                        'Une erreur est survenue lors de l\'enregistrement';
        showNotification(errorMsg, 'error');
    });
}

function editStaff(staffId) {
    openStaffModal(staffId);
}

function toggleStaffStatus(staffId) {
    const row = document.querySelector(`tr[data-staff-id="${staffId}"]`);
    const isActive = row.querySelector('.badge-success') !== null;
    const action = isActive ? 'désactiver' : 'activer';
    const message = isActive ? 
        'Désactiver cet employé ? Il ne pourra plus se connecter mais ses données seront conservées.' : 
        'Activer cet employé ? Il pourra à nouveau se connecter.';
    
    if (!confirm(message)) {
        return;
    }
    
    fetch(`/api/v1/pharmacy/staff/${staffId}/toggle_status/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification(data.message, 'success');
            loadStaffList();
        } else {
            throw new Error(data.message || 'Erreur lors du changement de statut');
        }
    })
    .catch(error => {
        console.error('Error toggling status:', error);
        showNotification(error.message || 'Erreur lors du changement de statut', 'error');
    });
}

function deleteStaff(staffId) {
    if (!confirm('⚠️ ATTENTION: Supprimer définitivement cet employé ?\n\nCette action est irréversible et effacera toutes ses données.\n\nPour simplement désactiver l\'accès, utilisez le bouton Désactiver.')) {
        return;
    }
    
    fetch(`/api/v1/pharmacy/staff/${staffId}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => {
        if (response.ok || response.status === 204) {
            showNotification('Personnel supprimé avec succès', 'success');
            loadStaffList();
        } else {
            return response.json().then(data => {
                throw new Error(data.message || 'Erreur lors de la suppression');
            });
        }
    })
    .catch(error => {
        console.error('Error deleting staff:', error);
        showNotification(error.message || 'Erreur lors de la suppression', 'error');
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10001;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
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
