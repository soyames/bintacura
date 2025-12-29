let allStaff = [];
let currentFilter = 'all';
let currentStaffId = null;

async function loadStaff() {
    try {
        const response = await fetchApi('insurance/staff/');
        const data = await response.json();
        allStaff = data.results || data;
        updateStats();
        renderStaff();
        loadSupervisorOptions();
    } catch (error) {
        console.error('Error loading staff:', error);
        document.getElementById('staffList').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <p>Erreur de chargement du personnel</p>
            </div>
        `;
    }
}

function updateStats() {
    const stats = {
        active: allStaff.filter(s => s.is_active).length,
        claimsProcessors: allStaff.filter(s => s.staff_role === 'claims_processor' && s.is_active).length,
        underwriters: allStaff.filter(s => s.staff_role === 'underwriter' && s.is_active).length,
        inactive: allStaff.filter(s => !s.is_active).length
    };

    document.getElementById('activeStaffCount').textContent = stats.active;
    document.getElementById('claimsProcessorCount').textContent = stats.claimsProcessors;
    document.getElementById('underwriterCount').textContent = stats.underwriters;
    document.getElementById('inactiveStaffCount').textContent = stats.inactive;
}

function filterStaff(role) {
    currentFilter = role;

    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    let filtered = allStaff;
    if (role === 'inactive') {
        filtered = allStaff.filter(s => !s.is_active);
    } else if (role !== 'all') {
        filtered = allStaff.filter(s => s.staff_role === role && s.is_active);
    }

    renderStaff(filtered);
}

function renderStaff(staff = allStaff) {
    const list = document.getElementById('staffList');

    if (!staff || staff.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>Aucun membre du personnel trouvé</h3>
                <p>Il n'y a aucun membre du personnel ${currentFilter !== 'all' ? 'dans cette catégorie' : 'pour le moment'}</p>
            </div>
        `;
        return;
    }

    const roleLabels = {
        claims_processor: 'Gestionnaire de Réclamations',
        underwriter: 'Souscripteur',
        customer_service: 'Service Client',
        manager: 'Manager',
        administrator: 'Administrateur'
    };

    list.innerHTML = staff.map(member => {
        const statusClass = member.is_active ? 'approved' : 'rejected';
        const statusLabel = member.is_active ? 'Actif' : 'Inactif';
        const hireDate = new Date(member.hire_date).toLocaleDateString('fr-FR');

        return `
            <div class="claim-card" onclick="viewStaffDetails('${member.id}')">
                <div class="claim-header">
                    <div>
                        <div class="claim-number">${member.staff_name || 'N/A'}</div>
                        <div class="claim-patient-info">
                            ${member.staff_email || 'N/A'} ${member.employee_id ? '• ' + member.employee_id : ''}
                        </div>
                    </div>
                    <div class="claim-status-badge ${statusClass}">
                        ${statusLabel}
                    </div>
                </div>

                <div class="claim-details-grid">
                    <div>
                        <div class="claim-detail-label">Rôle</div>
                        <div class="claim-detail-value">${roleLabels[member.staff_role] || member.staff_role}</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Département</div>
                        <div class="claim-detail-value">${member.department || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Superviseur</div>
                        <div class="claim-detail-value">${member.supervisor_name || 'Aucun'}</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Date d'embauche</div>
                        <div class="claim-detail-value">${hireDate}</div>
                    </div>
                </div>

                ${member.permissions && member.permissions.length > 0 ? `
                    <div class="claim-diagnosis-box">
                        <div class="claim-detail-label">Permissions</div>
                        <div class="claim-detail-value">${member.permissions.length} permission(s)</div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

async function viewStaffDetails(staffId) {
    const member = allStaff.find(s => s.id === staffId);
    if (!member) return;

    currentStaffId = staffId;

    const modal = document.getElementById('staffDetailModal');
    const modalTitle = document.getElementById('modalStaffTitle');
    const modalBody = document.getElementById('staffDetailBody');
    const modalActions = document.getElementById('staffModalActions');

    modalTitle.textContent = member.staff_name || 'Membre du Personnel';

    const roleLabels = {
        claims_processor: 'Gestionnaire de Réclamations',
        underwriter: 'Souscripteur',
        customer_service: 'Service Client',
        manager: 'Manager',
        administrator: 'Administrateur'
    };

    const hireDate = new Date(member.hire_date).toLocaleDateString('fr-FR');
    const terminationDate = member.termination_date ? new Date(member.termination_date).toLocaleDateString('fr-FR') : 'N/A';

    const permissionLabels = {
        approve_claims: 'Approuver les réclamations',
        reject_claims: 'Rejeter les réclamations',
        approve_subscriptions: 'Approuver les abonnements',
        manage_policies: 'Gérer les polices',
        view_reports: 'Voir les rapports',
        manage_staff: 'Gérer le personnel'
    };

    modalBody.innerHTML = `
        <div class="detail-section">
            <h4>👤 Informations Personnelles</h4>
            <div class="detail-row">
                <span class="label">Nom complet:</span>
                <span class="value">${member.staff_name || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Email:</span>
                <span class="value">${member.staff_email || 'N/A'}</span>
            </div>
        </div>

        <div class="detail-section">
            <h4>💼 Informations Professionnelles</h4>
            <div class="detail-row">
                <span class="label">Rôle:</span>
                <span class="value">${roleLabels[member.staff_role] || member.staff_role}</span>
            </div>
            <div class="detail-row">
                <span class="label">Département:</span>
                <span class="value">${member.department || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">ID Employé:</span>
                <span class="value">${member.employee_id || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Superviseur:</span>
                <span class="value">${member.supervisor_name || 'Aucun'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Date d'embauche:</span>
                <span class="value">${hireDate}</span>
            </div>
            ${!member.is_active && member.termination_date ? `
            <div class="detail-row">
                <span class="label">Date de fin:</span>
                <span class="value">${terminationDate}</span>
            </div>
            ` : ''}
        </div>

        <div class="detail-section">
            <h4>🔐 Permissions</h4>
            ${member.permissions && member.permissions.length > 0 ? `
                <div class="detail-row">
                    <ul style="margin: 0; padding-left: 20px;">
                        ${member.permissions.map(p => `<li>${permissionLabels[p] || p}</li>`).join('')}
                    </ul>
                </div>
            ` : `
                <div class="detail-row">
                    <span class="value">Aucune permission définie</span>
                </div>
            `}
        </div>

        <div class="detail-section">
            <h4>📋 Statut</h4>
            <div class="detail-row">
                <span class="label">Statut actuel:</span>
                <span class="value claim-status-badge ${member.is_active ? 'approved' : 'rejected'}">${member.is_active ? 'Actif' : 'Inactif'}</span>
            </div>
        </div>

        ${member.notes ? `
        <div class="detail-section">
            <h4>📝 Notes</h4>
            <div class="claim-diagnosis-box">
                <p>${member.notes}</p>
            </div>
        </div>
        ` : ''}
    `;

    let actions = '';
    if (member.is_active) {
        actions = `
            <button class="btn-action btn-review" onclick="openEditPermissionsModal('${member.id}')">Modifier les Permissions</button>
            <button class="btn-action btn-reject" onclick="deactivateStaff('${member.id}')">Désactiver</button>
        `;
    } else {
        actions = `
            <button class="btn-action btn-approve" onclick="reactivateStaff('${member.id}')">Réactiver</button>
        `;
    }

    modalActions.innerHTML = actions;
    modal.classList.add('active');
}

function closeStaffDetailModal() {
    document.getElementById('staffDetailModal').classList.remove('active');
    currentStaffId = null;
}

function openAddStaffModal() {
    document.getElementById('addStaffModal').classList.add('active');
    // Set today's date as default hire date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('hireDate').value = today;
}

function closeAddStaffModal() {
    document.getElementById('addStaffModal').classList.remove('active');
    document.getElementById('addStaffForm').reset();
}

function loadSupervisorOptions() {
    const supervisorSelect = document.getElementById('supervisor');
    if (!supervisorSelect) return;

    const activeManagers = allStaff.filter(s =>
        s.is_active && (s.staff_role === 'manager' || s.staff_role === 'administrator')
    );

    supervisorSelect.innerHTML = '<option value="">Aucun superviseur</option>';
    activeManagers.forEach(manager => {
        const option = document.createElement('option');
        option.value = manager.id;
        option.textContent = manager.staff_name || manager.staff_email;
        supervisorSelect.appendChild(option);
    });
}

async function submitAddStaff() {
    const fullName = document.getElementById('fullName').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value;
    const staffRole = document.getElementById('staffRole').value;
    const department = document.getElementById('department').value.trim();
    const employeeId = document.getElementById('employeeId').value.trim();
    const supervisor = document.getElementById('supervisor').value;
    const hireDate = document.getElementById('hireDate').value;
    const notes = document.getElementById('notes').value.trim();

    if (!fullName || !email || !password || !staffRole) {
        alert('Veuillez remplir tous les champs obligatoires (*, Email, Mot de passe, Rôle)');
        return;
    }

    // Get selected permissions
    const permissions = [];
    document.querySelectorAll('.permission-checkbox:checked').forEach(checkbox => {
        permissions.push(checkbox.value);
    });

    const staffData = {
        full_name: fullName,
        email: email,
        phone: phone || '',
        password: password,
        staff_role: staffRole,
        department: department || '',
        employee_id: employeeId || '',
        supervisor_id: supervisor || null,
        hire_date: hireDate || new Date().toISOString().split('T')[0],
        permissions: permissions,
        notes: notes || ''
    };

    try {
        const response = await fetchApi('insurance/staff/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(staffData)
        });

        const data = await response.json();

        if (response.ok) {
            alert('Membre du personnel ajouté avec succès!');
            closeAddStaffModal();
            await loadStaff();
        } else {
            alert('Erreur: ' + (data.detail || data.error || JSON.stringify(data) || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function deactivateStaff(staffId) {
    if (!confirm('Êtes-vous sûr de vouloir désactiver ce membre du personnel?')) {
        return;
    }

    try {
        const response = await fetchApi(`insurance/staff/${staffId}/deactivate/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        const data = await response.json();

        if (response.ok) {
            alert('Membre du personnel désactivé avec succès');
            closeStaffDetailModal();
            await loadStaff();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function reactivateStaff(staffId) {
    if (!confirm('Êtes-vous sûr de vouloir réactiver ce membre du personnel?')) {
        return;
    }

    try {
        const response = await fetchApi(`insurance/staff/${staffId}/reactivate/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        const data = await response.json();

        if (response.ok) {
            alert('Membre du personnel réactivé avec succès');
            closeStaffDetailModal();
            await loadStaff();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

function openEditPermissionsModal(staffId) {
    currentStaffId = staffId;
    const member = allStaff.find(s => s.id === staffId);
    if (!member) return;

    // Set current permissions
    document.querySelectorAll('.edit-permission-checkbox').forEach(checkbox => {
        checkbox.checked = member.permissions && member.permissions.includes(checkbox.value);
    });

    closeStaffDetailModal();
    document.getElementById('editPermissionsModal').classList.add('active');
}

function closeEditPermissionsModal() {
    document.getElementById('editPermissionsModal').classList.remove('active');
    currentStaffId = null;
}

async function submitEditPermissions() {
    if (!currentStaffId) return;

    // Get selected permissions
    const permissions = [];
    document.querySelectorAll('.edit-permission-checkbox:checked').forEach(checkbox => {
        permissions.push(checkbox.value);
    });

    try {
        const response = await fetchApi(`insurance/staff/${currentStaffId}/update_permissions/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ permissions: permissions })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Permissions mises à jour avec succès');
            closeEditPermissionsModal();
            await loadStaff();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
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

window.onclick = function(event) {
    const staffDetailModal = document.getElementById('staffDetailModal');
    const addStaffModal = document.getElementById('addStaffModal');
    const editPermissionsModal = document.getElementById('editPermissionsModal');

    if (event.target === staffDetailModal) {
        closeStaffDetailModal();
    }
    if (event.target === addStaffModal) {
        closeAddStaffModal();
    }
    if (event.target === editPermissionsModal) {
        closeEditPermissionsModal();
    }
}

loadStaff();
