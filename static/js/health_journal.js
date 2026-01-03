// Health Journal JavaScript

// Get CSRF token
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

const csrftoken = getCookie('csrftoken');
let currentNoteId = null;

// Show Add Note Modal
function showAddNoteModal() {
    document.getElementById('noteModal').style.display = 'block';
    document.getElementById('modalTitle').textContent = 'Ajouter une note';
    document.getElementById('noteForm').reset();
    document.getElementById('noteId').value = '';
    document.getElementById('noteDate').valueAsDate = new Date();
    currentNoteId = null;
}

// Close Note Modal
function closeNoteModal() {
    document.getElementById('noteModal').style.display = 'none';
    document.getElementById('noteForm').reset();
    currentNoteId = null;
}

// Show View Note Modal
function showViewNoteModal(note) {
    document.getElementById('viewNoteModal').style.display = 'block';
    document.getElementById('viewNoteTitle').textContent = note.title;
    document.getElementById('viewNoteDate').textContent = formatDate(note.note_date);
    document.getElementById('viewNoteCategory').textContent = note.category_display;
    document.getElementById('viewNoteContent').textContent = note.content;
    document.getElementById('viewNoteCreated').textContent = formatDateTime(note.created_at);
    document.getElementById('viewNoteUpdated').textContent = formatDateTime(note.updated_at);
    
    // Display tags
    const tagsContainer = document.getElementById('viewNoteTags');
    if (note.tags && note.tags.length > 0) {
        tagsContainer.innerHTML = '<div class="detail-tags">' + 
            note.tags.map(tag => `<span class="tag">${tag}</span>`).join('') + 
            '</div>';
    } else {
        tagsContainer.innerHTML = '';
    }
    
    currentNoteId = note.id;
}

// Close View Note Modal
function closeViewNoteModal() {
    document.getElementById('viewNoteModal').style.display = 'none';
    currentNoteId = null;
}

// Close modals when clicking outside
window.onclick = function(event) {
    const noteModal = document.getElementById('noteModal');
    const viewNoteModal = document.getElementById('viewNoteModal');
    if (event.target === noteModal) {
        closeNoteModal();
    } else if (event.target === viewNoteModal) {
        closeViewNoteModal();
    }
}

// Add/Edit Note Form Submission
document.getElementById('noteForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const tags = document.getElementById('noteTags').value
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0);
    
    const formData = {
        title: document.getElementById('noteTitle').value,
        note_date: document.getElementById('noteDate').value,
        category: document.getElementById('noteCategory').value,
        content: document.getElementById('noteContent').value,
        tags: tags
    };
    
    const noteId = document.getElementById('noteId').value;
    const url = noteId 
        ? `/api/v1/patient/health-notes/${noteId}/`
        : '/api/v1/patient/health-notes/';
    const method = noteId ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            closeNoteModal();
            location.reload();
        } else {
            const error = await response.json();
            alert('Erreur: ' + JSON.stringify(error));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Une erreur s\'est produite. Veuillez réessayer.');
    }
});

// View Note
async function viewNote(noteId) {
    try {
        const response = await fetch(`/api/v1/patient/health-notes/${noteId}/`);
        const note = await response.json();
        showViewNoteModal(note);
    } catch (error) {
        console.error('Error:', error);
        alert('Impossible de charger la note.');
    }
}

// Edit Note
async function editNote(noteId) {
    try {
        const response = await fetch(`/api/v1/patient/health-notes/${noteId}/`);
        const note = await response.json();
        
        // Populate form
        document.getElementById('noteId').value = note.id;
        document.getElementById('noteTitle').value = note.title;
        document.getElementById('noteDate').value = note.note_date;
        document.getElementById('noteCategory').value = note.category;
        document.getElementById('noteContent').value = note.content;
        document.getElementById('noteTags').value = note.tags ? note.tags.join(', ') : '';
        
        document.getElementById('modalTitle').textContent = 'Modifier la note';
        document.getElementById('noteModal').style.display = 'block';
    } catch (error) {
        console.error('Error:', error);
        alert('Impossible de charger la note.');
    }
}

// Edit Note from View Modal
function editNoteFromView() {
    closeViewNoteModal();
    if (currentNoteId) {
        editNote(currentNoteId);
    }
}

// Delete Note
async function deleteNote(noteId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette note?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/patient/health-notes/${noteId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrftoken
            }
        });
        
        if (response.ok) {
            location.reload();
        } else {
            alert('Erreur lors de la suppression de la note.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Une erreur s\'est produite. Veuillez réessayer.');
    }
}

// Filter by Category
function filterByCategory(category) {
    // Update button states
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Filter notes
    const notes = document.querySelectorAll('.note-card');
    notes.forEach(note => {
        if (category === 'all' || note.dataset.category === category) {
            note.style.display = 'flex';
        } else {
            note.style.display = 'none';
        }
    });
}

// Search Notes
function searchNotes() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const notes = document.querySelectorAll('.note-card');
    
    notes.forEach(note => {
        const title = note.querySelector('.note-title').textContent.toLowerCase();
        const content = note.querySelector('.note-content').textContent.toLowerCase();
        
        if (title.includes(searchTerm) || content.includes(searchTerm)) {
            note.style.display = 'flex';
        } else {
            note.style.display = 'none';
        }
    });
}

// Search on Enter key
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchNotes();
    }
});

// Utility Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function formatDateTime(dateTimeString) {
    const date = new Date(dateTimeString);
    return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
