// Top Navigation Bar Functionality
(function() {
    'use strict';

    // Update notification count badge
    function updateNotificationBadge(count) {
        const badge = document.getElementById('notificationsBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    // Update message count badge
    function updateMessageBadge(count) {
        const badge = document.getElementById('messagesBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    // Fetch notification count
    async function fetchNotificationCount() {
        try {
            const response = await fetch('/api/v1/communication/notifications/unread_count/', {
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            if (response.ok) {
                const data = await response.json();
                updateNotificationBadge(data.count);
            }
        } catch (error) {
            console.error('Error fetching notification count:', error);
        }
    }

    // Fetch unread notifications
    async function fetchUnreadNotifications() {
        try {
            const response = await fetch('/api/v1/communication/notifications/unread/', {
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            if (response.ok) {
                const notifications = await response.json();
                displayNotifications(notifications);
            }
        } catch (error) {
            console.error('Error fetching notifications:', error);
        }
    }

    // Display notifications in dropdown
    function displayNotifications(notifications) {
        const content = document.getElementById('notificationsContent');
        if (!content) return;

        if (notifications.length === 0) {
            content.innerHTML = '<div class="no-notifications">Aucune notification</div>';
            return;
        }

        content.innerHTML = notifications.map(notification => `
            <div class="notification-item ${notification.is_read ? 'read' : 'unread'}" data-id="${notification.id}">
                <div class="notification-icon">
                    ${getNotificationIcon(notification.notification_type)}
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${formatTime(notification.created_at)}</div>
                </div>
            </div>
        `).join('');

        // Add click handlers
        content.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', async () => {
                const id = item.dataset.id;
                await markNotificationRead(id);
                const notification = notifications.find(n => n.id === id);
                if (notification.action_url) {
                    window.location.href = notification.action_url;
                }
            });
        });
    }

    // Get icon for notification type
    function getNotificationIcon(type) {
        const icons = {
            'appointment': '📅',
            'prescription': '💊',
            'payment': '💰',
            'system': 'ℹ️',
            'message': '✉️'
        };
        return icons[type] || 'ℹ️';
    }

    // Format time ago
    function formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'À l\'instant';
        if (seconds < 3600) return `Il y a ${Math.floor(seconds / 60)} min`;
        if (seconds < 86400) return `Il y a ${Math.floor(seconds / 3600)} h`;
        return `Il y a ${Math.floor(seconds / 86400)} j`;
    }

    // Mark notification as read
    async function markNotificationRead(notificationId) {
        try {
            const response = await fetch(`/api/v1/communication/notifications/${notificationId}/mark_read/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            if (response.ok) {
                await fetchNotificationCount();
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    // Mark all notifications as read
    async function markAllNotificationsRead() {
        try {
            const response = await fetch('/api/v1/communication/notifications/mark_all_read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            if (response.ok) {
                await fetchNotificationCount();
                await fetchUnreadNotifications();
            }
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
        }
    }

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

    // Toggle notification panel
    function toggleNotificationPanel() {
        const panel = document.getElementById('notificationsPanel');
        const messagesPanel = document.getElementById('messagesPanel');
        
        if (panel) {
            const isVisible = panel.style.display !== 'none';
            panel.style.display = isVisible ? 'none' : 'block';
            
            // Hide messages panel
            if (messagesPanel) {
                messagesPanel.style.display = 'none';
            }
            
            if (!isVisible) {
                fetchUnreadNotifications();
            }
        }
    }

    // Toggle message panel
    function toggleMessagePanel() {
        const panel = document.getElementById('messagesPanel');
        const notificationsPanel = document.getElementById('notificationsPanel');
        
        if (panel) {
            const isVisible = panel.style.display !== 'none';
            panel.style.display = isVisible ? 'none' : 'block';
            
            // Hide notifications panel
            if (notificationsPanel) {
                notificationsPanel.style.display = 'none';
            }
            
            if (!isVisible) {
                // TODO: Load messages
                const content = document.getElementById('messagesContent');
                if (content) {
                    content.innerHTML = '<div class="no-notifications">Fonctionnalité de messagerie à venir</div>';
                }
            }
        }
    }

    // Initialize
    document.addEventListener('DOMContentLoaded', () => {
        // Fetch initial counts
        fetchNotificationCount();
        
        // Poll for updates every 30 seconds
        setInterval(fetchNotificationCount, 30000);

        // Set up click handlers
        const notificationsIcon = document.getElementById('notificationsIcon');
        if (notificationsIcon) {
            notificationsIcon.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleNotificationPanel();
            });
        }

        const messagesIcon = document.getElementById('messagesIcon');
        if (messagesIcon) {
            messagesIcon.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleMessagePanel();
            });
        }

        const markAllReadBtn = document.getElementById('markAllReadBtn');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                markAllNotificationsRead();
            });
        }

        // Close panels when clicking outside
        document.addEventListener('click', (e) => {
            const notificationsPanel = document.getElementById('notificationsPanel');
            const messagesPanel = document.getElementById('messagesPanel');
            
            if (notificationsPanel && !e.target.closest('#notificationsIcon') && !e.target.closest('#notificationsPanel')) {
                notificationsPanel.style.display = 'none';
            }
            
            if (messagesPanel && !e.target.closest('#messagesIcon') && !e.target.closest('#messagesPanel')) {
                messagesPanel.style.display = 'none';
            }
        });
    });
})();
