// Messages JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize message functionality
});

async function loadConversation(conversationId) {
    try {
        const response = await fetch(`/api/v1/messages/conversation/${conversationId}/`);
        const data = await response.json();
        
        // Display conversation in the view panel
        displayConversation(data);
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

function displayConversation(data) {
    const conversationView = document.getElementById('conversationView');
    // Implementation for displaying conversation messages
    // This will be expanded based on requirements
}

function openCompose() {
    // Open compose message modal
    // Implementation will be added
    alert('Compose message functionality coming soon');
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
