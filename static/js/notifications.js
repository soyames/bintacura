// BINTACURA Notifications and Messages Handler
// Handles notification badge updates, dropdowns, and click events

(function() {
    'use strict';

    // Configuration
    const config = {
        checkInterval: 30000,
        notificationsApiUrl: '/api/v1/communication/notifications/unread_count/',
        notificationsListUrl: '/api/v1/communication/notifications/',
        markReadUrl: '/api/v1/communication/notifications/{id}/mark_read/',
        messagesApiUrl: '/api/v1/communication/messages/unread_count/'
    };

    // DOM Elements
    let notificationsIcon, notificationsBadge, notificationsPanel, notificationsContent;
    let messagesIcon, messagesBadge, messagesPanel, messagesContent;
    let markAllReadBtn;

    // State
    let notificationsPanelOpen = false;
    let messagesPanelOpen = false;

    // Initialize
    function init() {
        notificationsIcon = document.getElementById('notificationsIcon');
        notificationsBadge = document.getElementById('notificationsBadge');
        notificationsPanel = document.getElementById('notificationsPanel');
        notificationsContent = document.getElementById('notificationsContent');
        
        messagesIcon = document.getElementById('messagesIcon');
        messagesBadge = document.getElementById('messagesBadge');
        messagesPanel = document.getElementById('messagesPanel');
        messagesContent = document.getElementById('messagesContent');
        
        markAllReadBtn = document.getElementById('markAllReadBtn');

        if (!notificationsIcon || !messagesIcon) {
            console.warn('Notification/Message icons not found in DOM');
            return;
        }

        // Click handlers
        notificationsIcon.addEventListener('click', toggleNotificationsPanel);
        messagesIcon.addEventListener('click', toggleMessagesPanel);
        
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', markAllAsRead);
        }

        // Close dropdowns when clicking outside
        document.addEventListener('click', handleOutsideClick);

        // Initial load
        updateNotificationCount();
        updateMessageCount();

        // Periodic checking
        setInterval(updateNotificationCount, config.checkInterval);
        setInterval(updateMessageCount, config.checkInterval);
    }

    // Toggle notifications panel
    function toggleNotificationsPanel(e) {
        e.stopPropagation();
        
        if (messagesPanelOpen) {
            closeMessagesPanel();
        }
        
        notificationsPanelOpen = !notificationsPanelOpen;
        notificationsPanel.style.display = notificationsPanelOpen ? 'block' : 'none';
        
        if (notificationsPanelOpen) {
            loadNotifications();
        }
    }

    // Toggle messages panel
    function toggleMessagesPanel(e) {
        e.stopPropagation();
        
        if (notificationsPanelOpen) {
            closeNotificationsPanel();
        }
        
        messagesPanelOpen = !messagesPanelOpen;
        messagesPanel.style.display = messagesPanelOpen ? 'block' : 'none';
    }

    // Close panels
    function closeNotificationsPanel() {
        notificationsPanelOpen = false;
        notificationsPanel.style.display = 'none';
    }

    function closeMessagesPanel() {
        messagesPanelOpen = false;
        messagesPanel.style.display = 'none';
    }

    // Handle clicks outside dropdowns
    function handleOutsideClick(e) {
        if (notificationsPanelOpen && !notificationsIcon.contains(e.target) && !notificationsPanel.contains(e.target)) {
            closeNotificationsPanel();
        }
        if (messagesPanelOpen && !messagesIcon.contains(e.target) && !messagesPanel.contains(e.target)) {
            closeMessagesPanel();
        }
    }

    // Update notification count
    async function updateNotificationCount() {
        try {
            const response = await fetch(config.notificationsApiUrl, {
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                const count = data.count || data.unread_count || 0;
                
                if (count > 0) {
                    notificationsBadge.textContent = count > 99 ? '99+' : count;
                    notificationsBadge.style.display = 'flex';
                } else {
                    notificationsBadge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error fetching notification count:', error);
        }
    }

    // Update message count
    async function updateMessageCount() {
        try {
            const response = await fetch(config.messagesApiUrl, {
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                const count = data.count || data.unread_count || 0;
                
                if (count > 0) {
                    messagesBadge.textContent = count > 99 ? '99+' : count;
                    messagesBadge.style.display = 'flex';
                } else {
                    messagesBadge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error fetching message count:', error);
        }
    }

    // Load notifications list
    async function loadNotifications() {
        try {
            notificationsContent.innerHTML = '<div class="loading-message">Chargement...</div>';
            
            const response = await fetch(config.notificationsListUrl + '?is_read=false&page_size=10', {
                credentials: 'same-origin'
            });

            if (response.ok) {
                const data = await response.json();
                const notifications = data.results || data;
                
                if (notifications.length === 0) {
                    notificationsContent.innerHTML = '<div class="empty-message">Aucune notification</div>';
                    return;
                }
                
                notificationsContent.innerHTML = notifications.map(notif => `
                    <div class="notification-item ${notif.is_read ? 'read' : 'unread'}" data-id="${notif.id}" data-url="${notif.action_url || ''}">
                        <div class="notification-icon ${notif.notification_type}">
                            ${getNotificationIcon(notif.notification_type)}
                        </div>
                        <div class="notification-content">
                            <div class="notification-title">${notif.title}</div>
                            <div class="notification-message">${notif.message}</div>
                            <div class="notification-time">${formatTime(notif.created_at)}</div>
                        </div>
                    </div>
                `).join('');
                
                // Add click handlers to notification items
                document.querySelectorAll('.notification-item').forEach(item => {
                    item.addEventListener('click', () => handleNotificationClick(item));
                });
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
            notificationsContent.innerHTML = '<div class="error-message">Erreur de chargement</div>';
        }
    }

    // Handle notification click
    async function handleNotificationClick(item) {
        const id = item.dataset.id;
        const url = item.dataset.url;
        
        // Mark as read
        try {
            await fetch(config.markReadUrl.replace('{id}', id), {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            // Update UI
            item.classList.remove('unread');
            item.classList.add('read');
            updateNotificationCount();
            
            // Navigate if URL exists
            if (url) {
                window.location.href = url;
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }

    // Mark all as read
    async function markAllAsRead() {
        try {
            const unreadItems = document.querySelectorAll('.notification-item.unread');
            
            for (const item of unreadItems) {
                const id = item.dataset.id;
                await fetch(config.markReadUrl.replace('{id}', id), {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });
            }
            
            // Reload notifications
            await loadNotifications();
            await updateNotificationCount();
        } catch (error) {
            console.error('Error marking all as read:', error);
        }
    }

    // Get notification icon
    function getNotificationIcon(type) {
        const icons = {
            'payment': '💰',
            'appointment': '📅',
            'prescription': '💊',
            'message': '💬',
            'alert': '⚠️',
            'system': 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }

    // Format time
    function formatTime(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (minutes < 1) return 'À l\'instant';
        if (minutes < 60) return `Il y a ${minutes} min`;
        if (hours < 24) return `Il y a ${hours}h`;
        if (days < 7) return `Il y a ${days}j`;
        return date.toLocaleDateString('fr-FR');
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

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose API
    window.BINTACURA_Notifications = {
        refresh: function() {
            updateNotificationCount();
            updateMessageCount();
        },
        updateNotifications: updateNotificationCount,
        updateMessages: updateMessageCount
    };

})();
