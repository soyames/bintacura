// Patient Documents Management
document.addEventListener('DOMContentLoaded', function() {
    const uploadModal = document.getElementById('uploadModal');
    const viewModal = document.getElementById('viewModal');
    const shareModal = document.getElementById('shareModal');
    const uploadForm = document.getElementById('uploadForm');
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    
    // Open upload modal
    document.querySelectorAll('#uploadDocBtn, #uploadFirstDoc').forEach(btn => {
        btn.addEventListener('click', () => openModal(uploadModal));
    });
    
    // Close modals
    document.querySelectorAll('.close-modal, .cancel-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').classList.remove('active');
        });
    });
    
    // Upload zone interactions
    uploadZone.addEventListener('click', () => fileInput.click());
    
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    // Handle file selection
    function handleFileSelect(file) {
        const maxSize = 10 * 1024 * 1024; // 10 MB
        if (file.size > maxSize) {
            alert('Le fichier est trop volumineux. Taille maximale : 10 Mo');
            fileInput.value = '';
            return;
        }
        
        // Auto-fill document name
        if (!document.getElementById('docName').value) {
            document.getElementById('docName').value = file.name.replace(/\.[^/.]+$/, '');
        }
        
        uploadZone.querySelector('p').textContent = `Fichier sélectionné : ${file.name}`;
    }
    
    // Form submission
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const submitBtn = this.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Import en cours...';
        
        try {
            const response = await fetch('/api/patient/documents/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            });
            
            if (response.ok) {
                showNotification('Document importé avec succès', 'success');
                uploadModal.classList.remove('active');
                uploadForm.reset();
                location.reload();
            } else {
                throw new Error('Erreur lors de l\'import');
            }
        } catch (error) {
            showNotification('Erreur lors de l\'import du document', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-upload"></i> Importer';
        }
    });
    
    // View toggle
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const view = this.dataset.view;
            const grid = document.getElementById('documentsGrid');
            
            if (view === 'grid') {
                grid.classList.remove('view-list');
                grid.classList.add('view-grid');
            } else {
                grid.classList.remove('view-grid');
                grid.classList.add('view-list');
            }
        });
    });
    
    // Filters
    document.getElementById('docTypeFilter').addEventListener('change', applyFilters);
    document.getElementById('periodFilter').addEventListener('change', applyFilters);
    document.getElementById('searchDocs').addEventListener('input', applyFilters);
    
    function applyFilters() {
        const typeFilter = document.getElementById('docTypeFilter').value;
        const periodFilter = document.getElementById('periodFilter').value;
        const searchTerm = document.getElementById('searchDocs').value.toLowerCase();
        
        const cards = document.querySelectorAll('.document-card');
        const now = new Date();
        
        cards.forEach(card => {
            let show = true;
            
            // Type filter
            if (typeFilter !== 'all' && card.dataset.type !== typeFilter) {
                show = false;
            }
            
            // Period filter
            if (periodFilter !== 'all' && show) {
                const docDate = new Date(card.dataset.date);
                const diffTime = Math.abs(now - docDate);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                
                if (periodFilter === 'week' && diffDays > 7) show = false;
                if (periodFilter === 'month' && diffDays > 30) show = false;
                if (periodFilter === 'year' && diffDays > 365) show = false;
            }
            
            // Search filter
            if (searchTerm && show) {
                const text = card.dataset.name;
                if (!text.includes(searchTerm)) {
                    show = false;
                }
            }
            
            card.style.display = show ? 'block' : 'none';
        });
    }
    
    // Sort documents
    document.getElementById('sortBy').addEventListener('change', function() {
        const sortBy = this.value;
        const grid = document.getElementById('documentsGrid');
        const cards = Array.from(grid.querySelectorAll('.document-card'));
        
        cards.sort((a, b) => {
            switch(sortBy) {
                case 'date_desc':
                    return new Date(b.dataset.date) - new Date(a.dataset.date);
                case 'date_asc':
                    return new Date(a.dataset.date) - new Date(b.dataset.date);
                case 'name_asc':
                    return a.dataset.name.localeCompare(b.dataset.name);
                case 'name_desc':
                    return b.dataset.name.localeCompare(a.dataset.name);
                case 'type':
                    return a.dataset.type.localeCompare(b.dataset.type);
                default:
                    return 0;
            }
        });
        
        cards.forEach(card => grid.appendChild(card));
    });
    
    // Document actions
    document.addEventListener('click', async function(e) {
        const actionBtn = e.target.closest('[data-action]');
        if (!actionBtn) return;
        
        const action = actionBtn.dataset.action;
        const docId = actionBtn.dataset.docId;
        
        switch(action) {
            case 'view':
                await viewDocument(docId);
                break;
            case 'download':
                await downloadDocument(docId);
                break;
            case 'share':
                openShareModal(docId);
                break;
            case 'delete':
                await deleteDocument(docId);
                break;
        }
    });
    
    async function viewDocument(docId) {
        try {
            const response = await fetch(`/api/patient/documents/${docId}/`);
            const doc = await response.json();
            
            document.getElementById('viewDocTitle').textContent = doc.name;
            const viewer = document.getElementById('docViewer');
            
            if (doc.file_type === 'pdf') {
                viewer.innerHTML = `<embed src="${doc.file_url}" type="application/pdf" width="100%" height="600px">`;
            } else {
                viewer.innerHTML = `<img src="${doc.file_url}" alt="${doc.name}" style="max-width: 100%;">`;
            }
            
            openModal(viewModal);
        } catch (error) {
            showNotification('Erreur lors du chargement du document', 'error');
        }
    }
    
    async function downloadDocument(docId) {
        try {
            const response = await fetch(`/api/patient/documents/${docId}/download/`);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showNotification('Document téléchargé', 'success');
        } catch (error) {
            showNotification('Erreur lors du téléchargement', 'error');
        }
    }
    
    function openShareModal(docId) {
        shareModal.dataset.docId = docId;
        openModal(shareModal);
    }
    
    document.querySelector('.share-btn').addEventListener('click', async function() {
        const docId = shareModal.dataset.docId;
        const doctorId = document.getElementById('shareWithDoctor').value;
        const message = document.getElementById('shareMessage').value;
        const expires = document.getElementById('shareExpires').checked;
        
        if (!doctorId) {
            alert('Veuillez sélectionner un praticien');
            return;
        }
        
        try {
            const response = await fetch(`/api/patient/documents/${docId}/share/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    doctor_id: doctorId,
                    message: message,
                    expires_in_days: expires ? 7 : null
                })
            });
            
            if (response.ok) {
                showNotification('Document partagé avec succès', 'success');
                shareModal.classList.remove('active');
            } else {
                throw new Error('Erreur lors du partage');
            }
        } catch (error) {
            showNotification('Erreur lors du partage du document', 'error');
        }
    });
    
    async function deleteDocument(docId) {
        if (!confirm('Êtes-vous sûr de vouloir supprimer ce document ?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/patient/documents/${docId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            if (response.ok) {
                showNotification('Document supprimé avec succès', 'success');
                document.querySelector(`[data-doc-id="${docId}"]`).closest('.document-card').remove();
                
                if (document.querySelectorAll('.document-card').length === 0) {
                    location.reload();
                }
            } else {
                throw new Error('Erreur lors de la suppression');
            }
        } catch (error) {
            showNotification('Erreur lors de la suppression du document', 'error');
        }
    }
    
    function openModal(modal) {
        modal.classList.add('active');
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
    
    function showNotification(message, type) {
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            alert(message);
        }
    }
});
