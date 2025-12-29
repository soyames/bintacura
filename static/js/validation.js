let allSubscriptions = [];
let currentFilter = 'all';

async function loadSubscriptions() {
    try {
        const response = await fetchApi('insurance/subscriptions/');
        const data = await response.json();
        allSubscriptions = data.results || data;
        updateStats();
        renderSubscriptions();
    } catch (error) {
        console.error('Error loading subscriptions:', error);
        document.getElementById('subscriptionsList').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <p>Erreur de chargement des demandes</p>
            </div>
        `;
    }
}

function updateStats() {
    const stats = {
        pending: allSubscriptions.filter(s => s.status === 'pending_approval' && !s.assigned_to).length,
        assigned: allSubscriptions.filter(s => s.status === 'pending_approval' && s.assigned_to).length,
        approved: allSubscriptions.filter(s => s.status === 'active').length,
        rejected: allSubscriptions.filter(s => s.status === 'cancelled').length
    };

    document.getElementById('pendingCount').textContent = stats.pending;
    document.getElementById('assignedCount').textContent = stats.assigned;
    document.getElementById('approvedCount').textContent = stats.approved;
    document.getElementById('rejectedCount').textContent = stats.rejected;
}

function filterSubscriptions(status) {
    currentFilter = status;

    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    let filtered = allSubscriptions;
    if (status === 'pending_approval') {
        filtered = allSubscriptions.filter(s => s.status === 'pending_approval' && !s.assigned_to);
    } else if (status === 'assigned') {
        filtered = allSubscriptions.filter(s => s.status === 'pending_approval' && s.assigned_to);
    } else if (status !== 'all') {
        filtered = allSubscriptions.filter(s => s.status === status);
    }

    renderSubscriptions(filtered);
}

function renderSubscriptions(subscriptions = allSubscriptions) {
    const list = document.getElementById('subscriptionsList');

    if (!subscriptions || subscriptions.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>Aucune demande trouvée</h3>
                <p>Il n'y a aucune demande d'abonnement ${currentFilter !== 'all' ? 'dans cette catégorie' : 'pour le moment'}</p>
            </div>
        `;
        return;
    }

    list.innerHTML = subscriptions.map(subscription => {
        const statusLabels = {
            pending_approval: 'En Attente d\'Approbation',
            active: 'Approuvée',
            suspended: 'Suspendue',
            cancelled: 'Rejetée',
            expired: 'Expirée'
        };

        const statusClass = subscription.status === 'pending_approval' ? 'pending' :
                          subscription.status === 'active' ? 'approved' :
                          subscription.status === 'cancelled' ? 'rejected' : 'review';

        const submittedDate = new Date(subscription.created_at).toLocaleDateString('fr-FR');

        return `
            <div class="claim-card" onclick="viewSubscriptionDetails('${subscription.id}')">
                <div class="claim-header">
                    <div>
                        <div class="claim-number">Demande #${subscription.id.substring(0, 8).toUpperCase()}</div>
                        <div class="claim-patient-info">
                            ${subscription.patient_name || 'Patient'} • ${subscription.insurance_package_name || 'Package'}
                        </div>
                    </div>
                    <div class="claim-status-badge ${statusClass}">
                        ${statusLabels[subscription.status] || subscription.status}
                    </div>
                </div>

                <div class="claim-details-grid">
                    <div>
                        <div class="claim-detail-label">Compagnie</div>
                        <div class="claim-detail-value">${subscription.company_name || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Prime</div>
                        <div class="claim-detail-value">${(subscription.premium_amount || 0).toLocaleString()} FCFA</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Fréquence</div>
                        <div class="claim-detail-value">${subscription.payment_frequency_display || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Date de soumission</div>
                        <div class="claim-detail-value">${submittedDate}</div>
                    </div>
                </div>

                ${subscription.assigned_to ? `
                    <div class="claim-diagnosis-box">
                        <div class="claim-detail-label">Assigné à</div>
                        <div class="claim-detail-value">${subscription.assigned_to_name || 'Staff'}</div>
                    </div>
                ` : ''}

                ${subscription.cancellation_reason ? `
                    <div class="claim-rejection-box">
                        <div class="claim-detail-label">Raison du rejet</div>
                        <div class="claim-detail-value">${subscription.cancellation_reason}</div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

async function viewSubscriptionDetails(subscriptionId) {
    const subscription = allSubscriptions.find(s => s.id === subscriptionId);
    if (!subscription) return;

    const modal = document.getElementById('subscriptionDetailModal');
    const modalTitle = document.getElementById('modalSubscriptionTitle');
    const modalBody = document.getElementById('subscriptionDetailBody');
    const modalActions = document.getElementById('subscriptionModalActions');

    modalTitle.textContent = `Demande #${subscription.id.substring(0, 8).toUpperCase()}`;

    const statusLabels = {
        pending_approval: 'En Attente d\'Approbation',
        active: 'Approuvée',
        suspended: 'Suspendue',
        cancelled: 'Rejetée',
        expired: 'Expirée'
    };

    const submittedDate = new Date(subscription.created_at).toLocaleDateString('fr-FR');
    const startDate = new Date(subscription.start_date).toLocaleDateString('fr-FR');

    modalBody.innerHTML = `
        <div class="detail-section">
            <h4>👤 Informations du Patient</h4>
            <div class="detail-row">
                <span class="label">Nom du patient:</span>
                <span class="value">${subscription.patient_name || 'N/A'}</span>
            </div>
        </div>

        <div class="detail-section">
            <h4>📦 Informations du Package</h4>
            <div class="detail-row">
                <span class="label">Compagnie:</span>
                <span class="value">${subscription.company_name || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Package:</span>
                <span class="value">${subscription.insurance_package_name || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Prime:</span>
                <span class="value">${(subscription.premium_amount || 0).toLocaleString()} FCFA</span>
            </div>
            <div class="detail-row">
                <span class="label">Fréquence de paiement:</span>
                <span class="value">${subscription.payment_frequency_display || 'N/A'}</span>
            </div>
        </div>

        <div class="detail-section">
            <h4>📅 Dates</h4>
            <div class="detail-row">
                <span class="label">Date de soumission:</span>
                <span class="value">${submittedDate}</span>
            </div>
            <div class="detail-row">
                <span class="label">Date de début:</span>
                <span class="value">${startDate}</span>
            </div>
            ${subscription.next_payment_date ? `
            <div class="detail-row">
                <span class="label">Prochain paiement:</span>
                <span class="value">${new Date(subscription.next_payment_date).toLocaleDateString('fr-FR')}</span>
            </div>
            ` : ''}
        </div>

        <div class="detail-section">
            <h4>💰 Paiement</h4>
            <div class="detail-row">
                <span class="label">Méthode de paiement:</span>
                <span class="value">${subscription.payment_method || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Total payé:</span>
                <span class="value">${(subscription.total_paid || 0).toLocaleString()} FCFA</span>
            </div>
            <div class="detail-row">
                <span class="label">Nombre de paiements:</span>
                <span class="value">${subscription.payment_count || 0}</span>
            </div>
        </div>

        ${subscription.insurance_card ? `
        <div class="detail-section">
            <h4>💳 Carte d'Assurance</h4>
            <div class="detail-row">
                <span class="label">Numéro de carte:</span>
                <span class="value">${subscription.insurance_card.card_number || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Numéro de police:</span>
                <span class="value">${subscription.insurance_card.policy_number || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Statut de la carte:</span>
                <span class="value">${subscription.insurance_card.status || 'N/A'}</span>
            </div>
        </div>
        ` : ''}

        <div class="detail-section">
            <h4>📋 Statut</h4>
            <div class="detail-row">
                <span class="label">Statut actuel:</span>
                <span class="value claim-status-badge ${subscription.status === 'pending_approval' ? 'pending' : subscription.status === 'active' ? 'approved' : 'rejected'}">${statusLabels[subscription.status]}</span>
            </div>
            ${subscription.assigned_to_name ? `
            <div class="detail-row">
                <span class="label">Assigné à:</span>
                <span class="value">${subscription.assigned_to_name}</span>
            </div>
            ` : ''}
            ${subscription.approved_by_name ? `
            <div class="detail-row">
                <span class="label">Approuvé par:</span>
                <span class="value">${subscription.approved_by_name}</span>
            </div>
            ` : ''}
            ${subscription.approved_at ? `
            <div class="detail-row">
                <span class="label">Date d'approbation:</span>
                <span class="value">${new Date(subscription.approved_at).toLocaleDateString('fr-FR')}</span>
            </div>
            ` : ''}
            ${subscription.approval_notes ? `
            <div class="detail-row">
                <span class="label">Notes d'approbation:</span>
                <span class="value">${subscription.approval_notes}</span>
            </div>
            ` : ''}
        </div>

        ${subscription.cancellation_reason ? `
        <div class="detail-section">
            <h4>❌ Raison du rejet</h4>
            <div class="claim-rejection-box">
                <p>${subscription.cancellation_reason}</p>
            </div>
        </div>
        ` : ''}
    `;

    let actions = '';
    if (subscription.status === 'pending_approval') {
        actions = `
            <button class="btn-action btn-review" onclick="assignSubscription('${subscription.id}')">Assigner à un Staff</button>
            <button class="btn-action btn-approve" onclick="approveSubscription('${subscription.id}')">Approuver</button>
            <button class="btn-action btn-reject" onclick="rejectSubscription('${subscription.id}')">Rejeter</button>
        `;
    }

    modalActions.innerHTML = actions;
    modal.classList.add('active');
}

function closeSubscriptionModal() {
    document.getElementById('subscriptionDetailModal').classList.remove('active');
}

async function approveSubscription(subscriptionId) {
    const notes = prompt('Notes d\'approbation (optionnel):');

    try {
        const response = await fetchApi(`insurance/subscriptions/${subscriptionId}/approve/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                approval_notes: notes || ''
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande approuvée avec succès!\n\nLe patient peut maintenant bénéficier de son assurance.');
            closeSubscriptionModal();
            await loadSubscriptions();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function assignSubscription(subscriptionId) {
    const staffId = prompt('ID du staff member:');
    if (!staffId) {
        alert('L\'ID du staff est requis');
        return;
    }

    try {
        const response = await fetchApi(`insurance/subscriptions/${subscriptionId}/assign/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                staff_id: staffId
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande assignée avec succès!');
            closeSubscriptionModal();
            await loadSubscriptions();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function rejectSubscription(subscriptionId) {
    const reason = prompt('Raison du rejet (requis):');
    if (!reason) {
        alert('La raison du rejet est requise');
        return;
    }

    try {
        const response = await fetchApi(`insurance/subscriptions/${subscriptionId}/reject/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                rejection_reason: reason
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande rejetée avec succès');
            closeSubscriptionModal();
            await loadSubscriptions();
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
    const modal = document.getElementById('subscriptionDetailModal');
    if (event.target === modal) {
        closeSubscriptionModal();
    }
}

loadSubscriptions();
