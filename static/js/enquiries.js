let allEnquiries = [];
let currentFilter = 'all';

async function loadEnquiries() {
    try {
        const response = await fetchApi('insurance/enquiries/');
        const data = await response.json();
        allEnquiries = data.results || data;
        updateStats();
        renderEnquiries();
    } catch (error) {
        console.error('Error loading enquiries:', error);
        document.getElementById('enquiriesList').innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <p>Erreur de chargement des demandes</p>
            </div>
        `;
    }
}

function updateStats() {
    const stats = {
        pending: allEnquiries.filter(e => e.status === 'pending').length,
        under_review: allEnquiries.filter(e => e.status === 'under_review').length,
        approved: allEnquiries.filter(e => e.status === 'approved').length,
        rejected: allEnquiries.filter(e => e.status === 'rejected').length
    };

    document.getElementById('pendingCount').textContent = stats.pending;
    document.getElementById('reviewCount').textContent = stats.under_review;
    document.getElementById('approvedCount').textContent = stats.approved;
    document.getElementById('rejectedCount').textContent = stats.rejected;
}

function filterEnquiries(status) {
    currentFilter = status;

    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    const filtered = status === 'all' ? allEnquiries : allEnquiries.filter(e => e.status === status);
    renderEnquiries(filtered);
}

function renderEnquiries(enquiries = allEnquiries) {
    const list = document.getElementById('enquiriesList');

    if (!enquiries || enquiries.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>Aucune demande trouvée</h3>
                <p>Il n'y a aucune demande de pré-approbation ${currentFilter !== 'all' ? 'dans cette catégorie' : 'pour le moment'}</p>
            </div>
        `;
        return;
    }

    list.innerHTML = enquiries.map(enquiry => {
        const statusLabels = {
            pending: 'En Attente',
            under_review: 'En Révision',
            approved: 'Approuvée',
            rejected: 'Rejetée',
            expired: 'Expirée'
        };

        return `
            <div class="claim-card" onclick="viewEnquiryDetails('${enquiry.id}')">
                <div class="claim-header">
                    <div>
                        <div class="claim-number">${enquiry.enquiry_number || 'N/A'}</div>
                        <div class="claim-patient-info">
                            ${enquiry.patient_name || 'Patient'} • ${enquiry.service_type_display || 'Service'}
                        </div>
                    </div>
                    <div class="claim-status-badge ${enquiry.status}">
                        ${statusLabels[enquiry.status] || enquiry.status}
                    </div>
                </div>

                <div class="enquiry-service-info">
                    <strong>${enquiry.service_name}</strong>
                    <p>${enquiry.service_description}</p>
                </div>

                <div class="claim-details-grid">
                    <div>
                        <div class="claim-detail-label">Coût estimé</div>
                        <div class="claim-detail-value">${(enquiry.estimated_cost || 0).toLocaleString()} FCFA</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Prestataire</div>
                        <div class="claim-detail-value">${enquiry.partner_name || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Date prévue</div>
                        <div class="claim-detail-value">${enquiry.planned_date ? new Date(enquiry.planned_date).toLocaleDateString('fr-FR') : '-'}</div>
                    </div>
                    <div>
                        <div class="claim-detail-label">Soumis le</div>
                        <div class="claim-detail-value">${new Date(enquiry.created_at).toLocaleDateString('fr-FR')}</div>
                    </div>
                </div>

                ${enquiry.status === 'approved' && enquiry.insurance_coverage_percentage ? `
                    <div class="approval-info">
                        <strong>Couverture approuvée: ${enquiry.insurance_coverage_percentage}%</strong>
                        <div>Assurance: ${(enquiry.insurance_covers_amount || 0).toLocaleString()} FCFA | Patient: ${(enquiry.patient_pays_amount || 0).toLocaleString()} FCFA</div>
                    </div>
                ` : ''}

                ${enquiry.rejection_reason ? `
                    <div class="claim-rejection-box">
                        <div class="claim-detail-label">Raison du rejet</div>
                        <div class="claim-detail-value">${enquiry.rejection_reason}</div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

async function viewEnquiryDetails(enquiryId) {
    const enquiry = allEnquiries.find(e => e.id === enquiryId);
    if (!enquiry) return;

    const modal = document.getElementById('enquiryDetailModal');
    const modalTitle = document.getElementById('modalEnquiryNumber');
    const modalBody = document.getElementById('enquiryDetailBody');
    const modalActions = document.getElementById('enquiryModalActions');

    modalTitle.textContent = `Demande: ${enquiry.enquiry_number}`;

    const statusLabels = {
        pending: 'En Attente',
        under_review: 'En Révision',
        approved: 'Approuvée',
        rejected: 'Rejetée',
        expired: 'Expirée'
    };

    modalBody.innerHTML = `
        <div class="detail-section">
            <h4>📋 Informations Générales</h4>
            <div class="detail-row">
                <span class="label">Numéro de demande:</span>
                <span class="value">${enquiry.enquiry_number}</span>
            </div>
            <div class="detail-row">
                <span class="label">Patient:</span>
                <span class="value">${enquiry.patient_name || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Statut:</span>
                <span class="value claim-status-badge ${enquiry.status}">${statusLabels[enquiry.status]}</span>
            </div>
        </div>

        <div class="detail-section">
            <h4>🏥 Détails du Service</h4>
            <div class="detail-row">
                <span class="label">Type de service:</span>
                <span class="value">${enquiry.service_type_display || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Nom du service:</span>
                <span class="value">${enquiry.service_name}</span>
            </div>
            <div class="detail-row">
                <span class="label">Description:</span>
                <span class="value">${enquiry.service_description}</span>
            </div>
            <div class="detail-row">
                <span class="label">Coût estimé:</span>
                <span class="value">${(enquiry.estimated_cost || 0).toLocaleString()} FCFA</span>
            </div>
        </div>

        <div class="detail-section">
            <h4>🏢 Prestataire</h4>
            <div class="detail-row">
                <span class="label">Nom:</span>
                <span class="value">${enquiry.partner_name || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Type:</span>
                <span class="value">${enquiry.partner_type || 'N/A'}</span>
            </div>
            <div class="detail-row">
                <span class="label">Date prévue:</span>
                <span class="value">${enquiry.planned_date ? new Date(enquiry.planned_date).toLocaleDateString('fr-FR') : 'N/A'}</span>
            </div>
        </div>

        <div class="detail-section">
            <h4>📝 Justification Médicale</h4>
            <div class="detail-row">
                <span class="label">Nécessité médicale:</span>
                <span class="value">${enquiry.medical_necessity}</span>
            </div>
            ${enquiry.doctor_recommendation ? `
            <div class="detail-row">
                <span class="label">Recommandation du médecin:</span>
                <span class="value">${enquiry.doctor_recommendation}</span>
            </div>
            ` : ''}
        </div>

        ${enquiry.status === 'approved' ? `
        <div class="detail-section">
            <h4>✅ Détails de l'Approbation</h4>
            <div class="detail-row">
                <span class="label">Couverture assurance:</span>
                <span class="value">${enquiry.insurance_coverage_percentage}%</span>
            </div>
            <div class="detail-row">
                <span class="label">Montant couvert:</span>
                <span class="value">${(enquiry.insurance_covers_amount || 0).toLocaleString()} FCFA</span>
            </div>
            <div class="detail-row">
                <span class="label">À payer par patient:</span>
                <span class="value">${(enquiry.patient_pays_amount || 0).toLocaleString()} FCFA</span>
            </div>
            ${enquiry.approval_notes ? `
            <div class="detail-row">
                <span class="label">Notes d'approbation:</span>
                <span class="value">${enquiry.approval_notes}</span>
            </div>
            ` : ''}
            ${enquiry.conditions ? `
            <div class="detail-row">
                <span class="label">Conditions:</span>
                <span class="value">${enquiry.conditions}</span>
            </div>
            ` : ''}
            ${enquiry.expires_at ? `
            <div class="detail-row">
                <span class="label">Valide jusqu'au:</span>
                <span class="value">${new Date(enquiry.expires_at).toLocaleDateString('fr-FR')}</span>
            </div>
            ` : ''}
        </div>
        ` : ''}

        ${enquiry.rejection_reason ? `
        <div class="detail-section">
            <h4>❌ Raison du rejet</h4>
            <div class="claim-rejection-box">
                <p>${enquiry.rejection_reason}</p>
            </div>
        </div>
        ` : ''}
    `;

    let actions = '';
    if (enquiry.status === 'pending') {
        actions = `
            <button class="btn-action btn-review" onclick="reviewEnquiry('${enquiry.id}')">Mettre en révision</button>
            <button class="btn-action btn-approve" onclick="approveEnquiry('${enquiry.id}')">Approuver</button>
            <button class="btn-action btn-reject" onclick="rejectEnquiry('${enquiry.id}')">Rejeter</button>
        `;
    } else if (enquiry.status === 'under_review') {
        actions = `
            <button class="btn-action btn-approve" onclick="approveEnquiry('${enquiry.id}')">Approuver</button>
            <button class="btn-action btn-reject" onclick="rejectEnquiry('${enquiry.id}')">Rejeter</button>
        `;
    }

    modalActions.innerHTML = actions;
    modal.classList.add('active');
}

function closeEnquiryModal() {
    document.getElementById('enquiryDetailModal').classList.remove('active');
}

async function reviewEnquiry(enquiryId) {
    try {
        const response = await fetchApi(`insurance/enquiries/${enquiryId}/review/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande mise en révision avec succès');
            closeEnquiryModal();
            await loadEnquiries();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function approveEnquiry(enquiryId) {
    const enquiry = allEnquiries.find(e => e.id === enquiryId);
    const coveragePercentage = prompt('Pourcentage de couverture (0-100):', '70');
    if (!coveragePercentage) return;

    const approvalNotes = prompt('Notes d\'approbation (optionnel):');
    const conditions = prompt('Conditions particulières (optionnel):');
    const validityDays = prompt('Validité en jours:', '30');

    try {
        const response = await fetchApi(`insurance/enquiries/${enquiryId}/approve/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                coverage_percentage: parseFloat(coveragePercentage),
                approval_notes: approvalNotes || '',
                conditions: conditions || '',
                validity_days: parseInt(validityDays)
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande approuvée avec succès');
            closeEnquiryModal();
            await loadEnquiries();
        } else {
            alert('Erreur: ' + (data.detail || data.error || 'Une erreur est survenue'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Erreur de connexion');
    }
}

async function rejectEnquiry(enquiryId) {
    const reason = prompt('Raison du rejet (requis):');
    if (!reason) {
        alert('La raison du rejet est requise');
        return;
    }

    try {
        const response = await fetchApi(`insurance/enquiries/${enquiryId}/reject/`, {
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
            closeEnquiryModal();
            await loadEnquiries();
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
    const modal = document.getElementById('enquiryDetailModal');
    if (event.target === modal) {
        closeEnquiryModal();
    }
}

loadEnquiries();
