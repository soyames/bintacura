// Hospital Transport Dashboard JavaScript

let map;
let markers = {};
let currentRequestId = null;
let refreshInterval;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    loadRequests();
    setupEventListeners();
    startAutoRefresh();
});

// Initialize Leaflet map
function initializeMap() {
    map = L.map('transportMap').setView([6.1319, 1.2223], 13); // Lomé, Togo default
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

// Load transport requests
async function loadRequests() {
    try {
        const statusFilter = document.getElementById('statusFilter').value;
        const urgencyFilter = document.getElementById('urgencyFilter').value;
        
        let url = '/api/v1/transport/hospital/requests/';
        const params = new URLSearchParams();
        
        if (statusFilter !== 'all') params.append('status', statusFilter);
        if (urgencyFilter !== 'all') params.append('urgency', urgencyFilter);
        
        if (params.toString()) url += '?' + params.toString();
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Failed to load requests');
        
        const data = await response.json();
        displayRequests(data.results || data);
        updateStats(data.results || data);
        updateMap(data.results || data);
        
    } catch (error) {
        console.error('Error loading requests:', error);
        showError('Erreur lors du chargement des demandes');
    }
}

// Display requests in list
function displayRequests(requests) {
    const requestsList = document.getElementById('requestsList');
    
    if (requests.length === 0) {
        requestsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>Aucune demande de transport pour le moment</p>
            </div>
        `;
        return;
    }
    
    requestsList.innerHTML = requests.map(request => `
        <div class="request-card ${request.urgency}" data-id="${request.id}" onclick="showRequestDetails('${request.id}')">
            <div class="request-header">
                <span class="request-number">#${request.request_number}</span>
                <span class="urgency-badge ${request.urgency}">
                    ${getUrgencyIcon(request.urgency)} ${getUrgencyLabel(request.urgency)}
                </span>
            </div>
            <div class="request-info">
                <p><strong>Patient:</strong> ${request.patient_name || 'N/A'}</p>
                <p><strong>De:</strong> ${truncateAddress(request.pickup_address)}</p>
                <p><strong>Vers:</strong> ${truncateAddress(request.dropoff_address)}</p>
                <p><strong>Heure:</strong> ${formatDateTime(request.scheduled_pickup_time)}</p>
                ${request.driver_name ? `<p><strong>Chauffeur:</strong> ${request.driver_name}</p>` : ''}
            </div>
            <span class="status-badge ${request.status}">${getStatusLabel(request.status)}</span>
        </div>
    `).join('');
}

// Update statistics cards
function updateStats(requests) {
    const pending = requests.filter(r => r.status === 'pending').length;
    const active = requests.filter(r => ['driver_assigned', 'en_route', 'arrived', 'in_transit'].includes(r.status)).length;
    const completed = requests.filter(r => {
        const today = new Date().toDateString();
        const completedDate = new Date(r.updated_at).toDateString();
        return r.status === 'completed' && completedDate === today;
    }).length;
    
    document.getElementById('pendingCount').textContent = pending;
    document.getElementById('activeCount').textContent = active;
    document.getElementById('completedCount').textContent = completed;
}

// Update map markers
function updateMap(requests) {
    // Clear existing markers
    Object.values(markers).forEach(marker => map.removeLayer(marker));
    markers = {};
    
    requests.forEach(request => {
        if (request.pickup_latitude && request.pickup_longitude) {
            const icon = L.divIcon({
                className: 'custom-marker',
                html: getMarkerIcon(request.urgency, request.status),
                iconSize: [30, 30]
            });
            
            const marker = L.marker([request.pickup_latitude, request.pickup_longitude], { icon })
                .addTo(map)
                .bindPopup(getPopupContent(request));
            
            marker.on('click', () => showRequestDetails(request.id));
            markers[request.id] = marker;
        }
    });
    
    // Fit map to show all markers
    if (Object.keys(markers).length > 0) {
        const group = L.featureGroup(Object.values(markers));
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

// Show request details modal
async function showRequestDetails(requestId) {
    currentRequestId = requestId;
    
    try {
        const response = await fetch(`/api/v1/transport/hospital/requests/${requestId}/`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Failed to load request details');
        
        const request = await response.json();
        
        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <div class="modal-body-content">
                <div class="detail-row">
                    <span class="detail-label">Numéro de Demande:</span>
                    <span class="detail-value">${request.request_number}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Patient:</span>
                    <span class="detail-value">${request.patient_name || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Téléphone:</span>
                    <span class="detail-value">${request.contact_phone || 'N/A'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Type de Transport:</span>
                    <span class="detail-value">${getTransportTypeLabel(request.transport_type)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Urgence:</span>
                    <span class="detail-value">${getUrgencyLabel(request.urgency)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Statut:</span>
                    <span class="detail-value">${getStatusLabel(request.status)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Adresse de Départ:</span>
                    <span class="detail-value">${request.pickup_address}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Adresse d'Arrivée:</span>
                    <span class="detail-value">${request.dropoff_address}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Heure Prévue:</span>
                    <span class="detail-value">${formatDateTime(request.scheduled_pickup_time)}</span>
                </div>
                ${request.driver_name ? `
                <div class="detail-row">
                    <span class="detail-label">Chauffeur:</span>
                    <span class="detail-value">${request.driver_name} (${request.driver_phone})</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Véhicule:</span>
                    <span class="detail-value">${request.vehicle_number}</span>
                </div>
                ` : ''}
                ${request.patient_notes ? `
                <div class="detail-row">
                    <span class="detail-label">Notes Patient:</span>
                    <span class="detail-value">${request.patient_notes}</span>
                </div>
                ` : ''}
                ${request.special_requirements ? `
                <div class="detail-row">
                    <span class="detail-label">Exigences Spéciales:</span>
                    <span class="detail-value">${request.special_requirements}</span>
                </div>
                ` : ''}
            </div>
        `;
        
        // Show/hide buttons based on status
        document.getElementById('acceptBtn').style.display = 
            request.status === 'pending' && !request.assigned_hospital ? 'inline-block' : 'none';
        document.getElementById('assignDriverBtn').style.display = 
            request.status === 'pending' || request.status === 'driver_assigned' ? 'inline-block' : 'none';
        document.getElementById('updateStatusBtn').style.display = 
            request.status !== 'completed' && request.status !== 'cancelled' ? 'inline-block' : 'none';
        
        document.getElementById('requestModal').style.display = 'flex';
        
    } catch (error) {
        console.error('Error loading request details:', error);
        showError('Erreur lors du chargement des détails');
    }
}

// Accept transport request
async function acceptRequest() {
    if (!currentRequestId) return;
    
    if (!confirm('Voulez-vous accepter cette demande de transport?')) return;
    
    try {
        const response = await fetch(`/api/v1/transport/hospital/requests/${currentRequestId}/accept/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Failed to accept request');
        
        showSuccess('Demande acceptée avec succès');
        document.getElementById('requestModal').style.display = 'none';
        loadRequests();
        
    } catch (error) {
        console.error('Error accepting request:', error);
        showError('Erreur lors de l\'acceptation de la demande');
    }
}

// Show driver assignment modal
function showDriverAssignment() {
    document.getElementById('assignRequestId').value = currentRequestId;
    document.getElementById('requestModal').style.display = 'none';
    document.getElementById('driverModal').style.display = 'flex';
}

// Assign driver to request
async function assignDriver(event) {
    event.preventDefault();
    
    const requestId = document.getElementById('assignRequestId').value;
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await fetch(`/api/v1/transport/hospital/requests/${requestId}/assign_driver/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) throw new Error('Failed to assign driver');
        
        showSuccess('Chauffeur assigné avec succès');
        document.getElementById('driverModal').style.display = 'none';
        document.getElementById('driverAssignmentForm').reset();
        loadRequests();
        
    } catch (error) {
        console.error('Error assigning driver:', error);
        showError('Erreur lors de l\'assignation du chauffeur');
    }
}

// Show status update modal
function showStatusUpdate() {
    document.getElementById('statusRequestId').value = currentRequestId;
    document.getElementById('requestModal').style.display = 'none';
    document.getElementById('statusModal').style.display = 'flex';
}

// Update request status
async function updateStatus(event) {
    event.preventDefault();
    
    const requestId = document.getElementById('statusRequestId').value;
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await fetch(`/api/v1/transport/hospital/requests/${requestId}/update_status/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) throw new Error('Failed to update status');
        
        showSuccess('Statut mis à jour avec succès');
        document.getElementById('statusModal').style.display = 'none';
        document.getElementById('statusUpdateForm').reset();
        loadRequests();
        
    } catch (error) {
        console.error('Error updating status:', error);
        showError('Erreur lors de la mise à jour du statut');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', loadRequests);
    
    // Filters
    document.getElementById('statusFilter').addEventListener('change', loadRequests);
    document.getElementById('urgencyFilter').addEventListener('change', loadRequests);
    
    // Accept button
    document.getElementById('acceptBtn').addEventListener('click', acceptRequest);
    
    // Assign driver button
    document.getElementById('assignDriverBtn').addEventListener('click', showDriverAssignment);
    
    // Update status button
    document.getElementById('updateStatusBtn').addEventListener('click', showStatusUpdate);
    
    // Driver assignment form
    document.getElementById('driverAssignmentForm').addEventListener('submit', assignDriver);
    
    // Status update form
    document.getElementById('statusUpdateForm').addEventListener('submit', updateStatus);
    
    // Close modals
    document.querySelectorAll('.close, .close-modal').forEach(element => {
        element.addEventListener('click', function() {
            document.querySelectorAll('.modal').forEach(modal => {
                modal.style.display = 'none';
            });
        });
    });
    
    // Close modal on outside click
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    });
}

// Start auto-refresh
function startAutoRefresh() {
    refreshInterval = setInterval(loadRequests, 30000); // Refresh every 30 seconds
}

// Helper functions
function getAuthToken() {
    return localStorage.getItem('auth_token') || '';
}

function getUrgencyIcon(urgency) {
    const icons = {
        'emergency': '🔴',
        'urgent': '🟠',
        'scheduled': '🟢',
        'routine': '⚪'
    };
    return icons[urgency] || '⚪';
}

function getUrgencyLabel(urgency) {
    const labels = {
        'emergency': 'Urgence',
        'urgent': 'Urgent',
        'scheduled': 'Planifié',
        'routine': 'Routine'
    };
    return labels[urgency] || urgency;
}

function getStatusLabel(status) {
    const labels = {
        'pending': 'En Attente',
        'driver_assigned': 'Chauffeur Assigné',
        'en_route': 'En Route',
        'arrived': 'Arrivé',
        'in_transit': 'En Transit',
        'completed': 'Complété',
        'cancelled': 'Annulé'
    };
    return labels[status] || status;
}

function getTransportTypeLabel(type) {
    const labels = {
        'ambulance': 'Ambulance',
        'medical_taxi': 'Taxi Médical',
        'wheelchair_transport': 'Transport Fauteuil Roulant',
        'stretcher_transport': 'Transport Brancard',
        'regular_taxi': 'Taxi Régulier'
    };
    return labels[type] || type;
}

function getMarkerIcon(urgency, status) {
    const colors = {
        'emergency': '#e74c3c',
        'urgent': '#f39c12',
        'scheduled': '#27ae60',
        'routine': '#95a5a6'
    };
    const color = colors[urgency] || '#95a5a6';
    
    return `<div style="background:${color};width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:18px;border:3px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);">🚑</div>`;
}

function getPopupContent(request) {
    return `
        <div class="popup-content">
            <h3>#${request.request_number}</h3>
            <p><strong>Patient:</strong> ${request.patient_name || 'N/A'}</p>
            <p><strong>Urgence:</strong> ${getUrgencyLabel(request.urgency)}</p>
            <p><strong>Statut:</strong> ${getStatusLabel(request.status)}</p>
        </div>
    `;
}

function truncateAddress(address, maxLength = 50) {
    if (!address) return 'N/A';
    return address.length > maxLength ? address.substring(0, maxLength) + '...' : address;
}

function formatDateTime(datetime) {
    if (!datetime) return 'N/A';
    const date = new Date(datetime);
    return date.toLocaleString('fr-FR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showSuccess(message) {
    alert(message); // Replace with better notification system
}

function showError(message) {
    alert(message); // Replace with better notification system
}
