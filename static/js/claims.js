let allClaims = [];
let currentFilter = 'all';

async function loadClaims() {
    try {
        const response = await fetchApi('insurance/claims/');
        const data = await response.json();
        allClaims = data.results || data;
        updateStats();
        renderClaims();
    } catch (error) {
        console.error('Error loading claims:', error);
        document.getElementById('claimsList').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <p>Erreur de chargement des réclamations</p>
            </div>
        `;
    }
}

function updateStats() {
    const stats = {
        submitted: allClaims.filter(c => c.status === 'submitted').length,
        underReview: allClaims.filter(c => c.status === 'underReview').length,
        approved: allClaims.filter(c => c.status === 'approved').length,
        paid: allClaims.filter(c => c.status === 'paid').length
    };

    document.getElementById('submittedCount').textContent = stats.submitted;
    document.getElementById('reviewCount').textContent = stats.underReview;
    document.getElementById('approvedCount').textContent = stats.approved;
    document.getElementById('paidCount').textContent = stats.paid;
}

function filterClaims(status) {
    currentFilter = status;

    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    const filtered = status === 'all' ? allClaims : allClaims.filter(c => c.status === status);
    renderClaims(filtered);
}

function renderClaims(claims = allClaims) {
    const list = document.getElementById('claimsList');

    if (!claims || claims.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>Aucune demande trouvée</h3>
                <p>Il n'y a aucune réclamation ${currentFilter !== 'all' ? 'dans cette catégorie' : 'pour le moment'}</p>
            </div>
        `;
        return;
    }

    list.innerHTML = claims.map(claim => {
        const statusLabels = {
            submitted: 'Soumise',
            underReview: 'En Révision',
            approved: 'Approuvée',
            rejected: 'Rejetée',
            paid: 'Payée'
        };

        return `
            <div class="claim-card" onclick="viewClaimDetails('${claim.id}')">
                <div class="claim-header">
                    <div>
                        <div class="claim-number">${claim.claim_number || 'N/A'}</div>
                        <div class="claim-patient-info">
                            ${claim.patient_name || 'Patient'} • ${claim.service_type || 'Service'}
                        </div>
                    </div>
                    <div class="claim-status-badge ${claim.status}">
                        ${statusLabels[claim.status] || claim.status}
                    </div>
                </div>

                <div class="claim-details-grid">
                    <div>
                        <div class="claim-detail-label">Montant réclamé</div>
                        <div class="claim-detail-value">${(claim.claimed_amount || 0).toLocaleString()} FCFA</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Montant approuvé</div>
                        <div class="claim-detail-value">${(claim.approved_amount || 0).toLocaleString()} FCFA</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Date service</div>
                        <div class="claim-detail-value">${claim.service_date ? new Date(claim.service_date).toLocaleDateString('fr-FR') : '-'}</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Date soumission</div>
                        <div class="claim-detail-value">${new Date(claim.submission_date || claim.created_at).toLocaleDateString('fr-FR')}</div>
                    </div>
                </div>

                ${claim.diagnosis ? `
                    <div class="claim-diagnosis-box">
                        <div class="claim-detail-label">Diagnostic</div>
                        <div class="claim-detail-value">${claim.diagnosis}</div>
                    </div>
                ` : ''}

                ${claim.rejection_reason ? `
                    <div class="claim-rejection-box">
                        <div class="claim-detail-label">Raison du rejet</div>
                        <div class="claim-detail-value">${claim.rejection_reason}</div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

async function viewClaimDetails(claimId) {
    const claim = allClaims.find(c => c.id === claimId);
    if (!claim) return;

    const modal = document.getElementById('claimDetailModal');
    const modalTitle = document.getElementById('modalClaimNumber');
    const modalBody = document.getElementById('claimDetailBody');
    const modalActions = document.getElementById('claimModalActions');

    modalTitle.textContent = `Réclamation: ${claim.claim_number}`;

    const statusLabels = {
        submitted: 'Soumise',
        underReview: 'En Révision',
        approved: 'Approuvée',
        rejected: 'Rejetée',
        paid: 'Payée'
    };

    modalBody.innerHTML = `
        <div class="detail-section">
            <h4>📋 Informations Générales</h4>
            <div class="detail-row">
                <span class="label">Numéro de réclamation:</span>
                <span class="value">${claim.claim_number}</span>
            </div>
            <div class="detail-row">
                <span class="label">Patient:</span>
                <span class="value">${claim.patient_name || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Statut:</span>
                <span class="value claim-status-badge ${claim.status}">${statusLabels[claim.status]}</span>
            </div>
            <div class="detail-row">
                <span class="label">Type de service:</span>
                <span class="value">${claim.service_type || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Nom du prestataire:</span>
                <span class="value">${claim.partner_name || 'N/A'}</span>
            </div>
        </div>

        <div class="detail-section">
            <h4>💰 Informations Financières</h4>
            <div class="detail-row">
                <span class="label">Montant réclamé:</span>
                <span class="value">${(claim.claimed_amount || 0).toLocaleString()} FCFA</span>
            </div>
            ${claim.approved_amount ? `
            <div class="detail-row">
                <span class="label">Montant approuvé:</span>
                <span class="value">${claim.approved_amount.toLocaleString()} FCFA</span>
            </div>
            ` : ''}
            ${claim.paid_amount ? `
            <div class="detail-row">
                <span class="label">Montant payé:</span>
                <span class="value">${claim.paid_amount.toLocaleString()} FCFA</span>
            </div>
            ` : ''}
        </div>

        <div class="detail-section">
            <h4>📅 Dates</h4>
            <div class="detail-row">
                <span class="label">Date du service:</span>
                <span class="value">${claim.service_date ? new Date(claim.service_date).toLocaleDateString('fr-FR') : 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Date de soumission:</span>
                <span class="value">${new Date(claim.submission_date || claim.created_at).toLocaleDateString('fr-FR')}</span>
            </div>
            ${claim.review_date ? `
            <div class="detail-row">
                <span class="label">Date de révision:</span>
                <span class="value">${new Date(claim.review_date).toLocaleDateString('fr-FR')}</span>
            </div>
            ` : ''}
            ${claim.approval_date ? `
            <div class="detail-row">
                <span class="label">Date d'approbation:</span>
                <span class="value">${new Date(claim.approval_date).toLocaleDateString('fr-FR')}</span>
            </div>
            ` : ''}
            ${claim.payment_date ? `
            <div class="detail-row">
                <span class="label">Date de paiement:</span>
                <span class="value">${new Date(claim.payment_date).toLocaleDateString('fr-FR')}</span>
            </div>
            ` : ''}
        </div>

        ${claim.diagnosis || claim.treatment_details ? `
        <div class="detail-section">
            <h4>🏥 Détails Médicaux</h4>
            ${claim.diagnosis ? `
            <div class="detail-row">
                <span class="label">Diagnostic:</span>
                <span class="value">${claim.diagnosis}</span>
            </div>
            ` : ''}
            ${claim.treatment_details ? `
            <div class="detail-row">
                <span class="label">Détails du traitement:</span>
                <span class="value">${claim.treatment_details}</span>
            </div>
            ` : ''}
        </div>
        ` : ''}

        ${claim.reviewer_notes ? `
        <div class="detail-section">
            <h4>📝 Notes du réviseur</h4>
            <p>${claim.reviewer_notes}</p>
        </div>
        ` : ''}

        ${claim.rejection_reason ? `
        <div class="detail-section">
            <h4>❌ Raison du rejet</h4>
            <div class="claim-rejection-box">
                <p>${claim.rejection_reason}</p>
            </div>
        </div>
        ` : ''}
    `;

    let actions = '';
    if (claim.status === 'submitted') {
        actions = `
            <button class="btn-action btn-review" onclick="reviewClaim('${claim.id}')">Mettre en révision</button>
            <button class="btn-action btn-approve" onclick="approveClaim('${claim.id}')">Approuver</button>
            <button class="btn-action btn-reject" onclick="rejectClaim('${claim.id}')">Rejeter</button>
        `;
    } else if (claim.status === 'underReview') {
        actions = `
            <button class="btn-action btn-approve" onclick="approveClaim('${claim.id}')">Approuver</button>
            <button class="btn-action btn-reject" onclick="rejectClaim('${claim.id}')">Rejeter</button>
        `;
    } else if (claim.status === 'approved') {
        actions = `
            <button class="btn-action btn-mark-paid" onclick="markPaid('${claim.id}')">Marquer comme payé</button>
        `;
    }

    modalActions.innerHTML = actions;
    modal.classList.add('active');
}

function closeClaimModal() {
    document.getElementById('claimDetailModal').classList.remove('active');
}

async function reviewClaim(claimId) {
    const notes = prompt('Notes de révision (optionnel):');

    try {
        const response = await fetchApi(`insurance/claims/${claimId}/review/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ reviewer_notes: notes || '' })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande mise en révision avec succès');
            closeClaimModal();
            await loadClaims();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function approveClaim(claimId) {
    const claim = allClaims.find(c => c.id === claimId);
    const amount = prompt('Montant approuvé (FCFA):', claim?.claimed_amount || '');
    if (!amount) return;

    const notes = prompt('Notes (optionnel):');

    try {
        const response = await fetchApi(`insurance/claims/${claimId}/approve/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                approved_amount: parseInt(amount),
                reviewer_notes: notes || ''
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande approuvée avec succès');
            closeClaimModal();
            await loadClaims();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function rejectClaim(claimId) {
    const reason = prompt('Raison du rejet (requis):');
    if (!reason) {
        alert('La raison du rejet est requise');
        return;
    }

    const notes = prompt('Notes additionnelles (optionnel):');

    try {
        const response = await fetchApi(`insurance/claims/${claimId}/reject/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                rejection_reason: reason,
                reviewer_notes: notes || ''
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande rejetée avec succès');
            closeClaimModal();
            await loadClaims();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function markPaid(claimId) {
    const claim = allClaims.find(c => c.id === claimId);
    const amount = prompt('Montant payé (FCFA):', claim?.approved_amount || '');
    if (!amount) return;

    try {
        const response = await fetchApi(`insurance/claims/${claimId}/mark_paid/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ paid_amount: parseInt(amount) })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande marquée comme payée avec succès');
            closeClaimModal();
            await loadClaims();
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
    const claimModal = document.getElementById('claimDetailModal');
    const enquiryModal = document.getElementById('enquiryDetailModal');
    if (event.target === claimModal) {
        closeClaimModal();
    }
    if (event.target === enquiryModal) {
        closeEnquiryModal();
    }
}

function switchTab(tabName) {
    const tabs = document.querySelectorAll('.tab-content');
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabs.forEach(tab => tab.classList.remove('active'));
    tabBtns.forEach(btn => btn.classList.remove('active'));

    if (tabName === 'claims') {
        document.getElementById('claimsTab').classList.add('active');
        tabBtns[0].classList.add('active');
    } else if (tabName === 'enquiries') {
        document.getElementById('enquiriesTab').classList.add('active');
        tabBtns[1].classList.add('active');
        if (typeof loadEnquiries === 'function') {
            loadEnquiries();
        }
    }
}

loadClaims();
