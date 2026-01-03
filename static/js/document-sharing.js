// Document Sharing JavaScript
document.addEventListener('DOMContentLoaded', function() {
    
    // Share document form
    const shareForm = document.getElementById('shareDocumentForm');
    if (shareForm) {
        shareForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(shareForm);
            const documentId = formData.get('document_id');
            
            fetch(`/api/health-records/documents/${documentId}/share/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    recipient_email: formData.get('recipient_email'),
                    recipient_type: formData.get('recipient_type'),
                    expiry_days: formData.get('expiry_days'),
                    can_download: formData.get('can_download') === 'on'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Document partagé avec succès', 'success');
                    shareForm.reset();
                    loadSharedDocuments();
                } else {
                    showNotification(data.error || 'Erreur lors du partage', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Erreur lors du partage du document', 'error');
            });
        });
    }
    
    // Load shared documents
    function loadSharedDocuments() {
        fetch('/api/health-records/shared-documents/', {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            displaySharedDocuments(data.documents);
        })
        .catch(error => console.error('Error loading shared documents:', error));
    }
    
    // Display shared documents
    function displaySharedDocuments(documents) {
        const container = document.getElementById('sharedDocumentsList');
        if (!container) return;
        
        if (documents.length === 0) {
            container.innerHTML = '<p class="text-muted">Aucun document partagé</p>';
            return;
        }
        
        container.innerHTML = documents.map(doc => `
            <div class="document-share-item">
                <div class="document-info">
                    <h5>${doc.document_name}</h5>
                    <p>Partagé avec: ${doc.recipient_email}</p>
                    <p>Expire: ${formatDate(doc.expires_at)}</p>
                </div>
                <div class="document-actions">
                    <button class="btn btn-sm btn-danger" onclick="revokeShare(${doc.id})">
                        Révoquer
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    // Revoke share
    window.revokeShare = function(shareId) {
        if (!confirm('Voulez-vous vraiment révoquer ce partage?')) return;
        
        fetch(`/api/health-records/shared-documents/${shareId}/revoke/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Partage révoqué', 'success');
                loadSharedDocuments();
            }
        })
        .catch(error => console.error('Error:', error));
    };
    
    // Initialize
    loadSharedDocuments();
});
