// Notifications JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeFilters();
});

function initializeFilters() {
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all buttons
            filterBtns.forEach(b => b.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            
            const filter = this.dataset.filter;
            filterNotifications(filter);
        });
    });
}

function filterNotifications(filter) {
    const notifications = document.querySelectorAll('.notification-item');
    
    notifications.forEach(notification => {
        const isUnread = notification.classList.contains('unread');
        
        if (filter === 'all') {
            notification.style.display = 'flex';
        } else if (filter === 'unread') {
            notification.style.display = isUnread ? 'flex' : 'none';
        } else if (filter === 'read') {
            notification.style.display = !isUnread ? 'flex' : 'none';
        }
    });
}

async function markAsRead(notificationId) {
    try {
        const response = await fetch(`/api/v1/notifications/${notificationId}/mark-read/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (response.ok) {
            const notificationItem = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (notificationItem) {
                notificationItem.classList.remove('unread');
                const markReadBtn = notificationItem.querySelector('.btn-mark-read');
                if (markReadBtn) {
                    markReadBtn.remove();
                }
            }
            updateNotificationCount();
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

async function markAllAsRead() {
    try {
        const response = await fetch('/api/v1/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (response.ok) {
            const notifications = document.querySelectorAll('.notification-item.unread');
            notifications.forEach(notification => {
                notification.classList.remove('unread');
                const markReadBtn = notification.querySelector('.btn-mark-read');
                if (markReadBtn) {
                    markReadBtn.remove();
                }
            });
            updateNotificationCount();
        }
    } catch (error) {
        console.error('Error marking all notifications as read:', error);
    }
}

async function deleteNotification(notificationId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette notification ?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/notifications/${notificationId}/delete/`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (response.ok) {
            const notificationItem = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (notificationItem) {
                notificationItem.remove();
            }
            updateNotificationCount();
        }
    } catch (error) {
        console.error('Error deleting notification:', error);
    }
}

function updateNotificationCount() {
    // Update the notification badge count in the top nav
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        const unreadCount = document.querySelectorAll('.notification-item.unread').length;
        badge.textContent = unreadCount;
        if (unreadCount === 0) {
            badge.style.display = 'none';
        }
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
