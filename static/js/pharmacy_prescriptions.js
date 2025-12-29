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

function viewPrescriptionDetails(prescriptionId) {
    window.location.href = `/pharmacy/prescription/${prescriptionId}/`;
}

function processPrescription(prescriptionId) {
    if (!confirm('Voulez-vous commencer le traitement de cette prescription?')) {
        return;
    }

    const csrftoken = getCookie('csrftoken');

    fetch(`/pharmacy/prescription/${prescriptionId}/process/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('La prescription est maintenant en cours de traitement');
            location.reload();
        } else {
            alert('Erreur: ' + (data.error || 'Une erreur est survenue'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Une erreur est survenue lors du traitement de la prescription');
    });
}

function markReady(prescriptionId) {
    if (!confirm('Confirmer que cette prescription est prête pour la livraison?')) {
        return;
    }

    const csrftoken = getCookie('csrftoken');

    fetch(`/pharmacy/prescription/${prescriptionId}/mark-ready/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('La prescription est maintenant marquée comme prête');
            location.reload();
        } else {
            alert('Erreur: ' + (data.error || 'Une erreur est survenue'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Une erreur est survenue');
    });
}

function deliverPrescription(prescriptionId) {
    if (!confirm('Confirmer la livraison de cette prescription?')) {
        return;
    }

    const csrftoken = getCookie('csrftoken');

    fetch(`/pharmacy/prescription/${prescriptionId}/deliver/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('La prescription a été livrée avec succès');
            location.reload();
        } else {
            alert('Erreur: ' + (data.error || 'Une erreur est survenue'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Une erreur est survenue lors de la livraison');
    });
}

function filterPrescriptions() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const cards = document.querySelectorAll('.prescription-card');

    cards.forEach(card => {
        const patient = card.dataset.patient || '';
        const doctor = card.dataset.doctor || '';
        const status = card.dataset.status || '';

        const matchesSearch = !searchTerm ||
            patient.includes(searchTerm) ||
            doctor.includes(searchTerm);

        const matchesStatus = !statusFilter || status === statusFilter;

        if (matchesSearch && matchesStatus) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterPrescriptions);
    }

    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', filterPrescriptions);
    }
});
