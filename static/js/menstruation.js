/**
 * Menstruation Tracker - JavaScript
 * BINTACURA Healthcare Platform
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initMiniCalendar();
    setupFormValidation();
});

/**
 * Initialize mini calendar on tracker page
 */
function initMiniCalendar() {
    const calendarEl = document.getElementById('miniCalendar');
    if (!calendarEl) return;

    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth();
    
    // Simple mini calendar (7 days view)
    const days = [];
    for (let i = -3; i <= 3; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);
        days.push(date);
    }
    
    let html = '<div class="mini-calendar-days">';
    days.forEach(date => {
        const isToday = date.toDateString() === today.toDateString();
        html += `
            <div class="mini-calendar-day ${isToday ? 'today' : ''}">
                <div class="mini-day-weekday">${date.toLocaleDateString('fr-FR', { weekday: 'short' })}</div>
                <div class="mini-day-number">${date.getDate()}</div>
            </div>
        `;
    });
    html += '</div>';
    
    calendarEl.innerHTML = html;
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Validate form fields
 */
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value || field.value.trim() === '') {
            showFieldError(field, 'Ce champ est requis');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    return isValid;
}

/**
 * Show field error
 */
function showFieldError(field, message) {
    clearFieldError(field);
    
    field.classList.add('field-error');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error-message';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
}

/**
 * Clear field error
 */
function clearFieldError(field) {
    field.classList.remove('field-error');
    
    const errorMessage = field.parentNode.querySelector('.field-error-message');
    if (errorMessage) {
        errorMessage.remove();
    }
}

/**
 * Calculate cycle statistics
 */
function calculateCycleStats(cycles) {
    if (!cycles || cycles.length === 0) {
        return {
            avgCycleLength: 28,
            avgPeriodLength: 5,
            totalCycles: 0
        };
    }
    
    const totalCycleLength = cycles.reduce((sum, cycle) => sum + cycle.cycle_length, 0);
    const totalPeriodLength = cycles.reduce((sum, cycle) => sum + cycle.period_length, 0);
    
    return {
        avgCycleLength: Math.round(totalCycleLength / cycles.length),
        avgPeriodLength: Math.round(totalPeriodLength / cycles.length),
        totalCycles: cycles.length
    };
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}

/**
 * Calculate days between dates
 */
function daysBetween(date1, date2) {
    const oneDay = 24 * 60 * 60 * 1000;
    const firstDate = new Date(date1);
    const secondDate = new Date(date2);
    
    return Math.round(Math.abs((firstDate - secondDate) / oneDay));
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${getNotificationIcon(type)}</span>
            <span class="notification-message">${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

/**
 * Get notification icon
 */
function getNotificationIcon(type) {
    const icons = {
        'success': '✓',
        'error': '✗',
        'warning': '⚠',
        'info': 'ℹ'
    };
    return icons[type] || icons.info;
}

/**
 * Export cycle data
 */
async function exportCycleData(format = 'csv') {
    try {
        const response = await fetch('/api/v1/menstruation/cycles/export/', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Export failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cycle_data_${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
        showNotification('Données exportées avec succès', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Erreur lors de l\'export', 'error');
    }
}

/**
 * Get auth token from cookie or localStorage
 */
function getAuthToken() {
    // Try localStorage first
    let token = localStorage.getItem('authToken');
    
    // Try cookie if not in localStorage
    if (!token) {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'authToken') {
                token = value;
                break;
            }
        }
    }
    
    return token;
}

/**
 * Toggle reminder
 */
async function toggleReminder(reminderId, isEnabled) {
    try {
        const response = await fetch(`/api/v1/menstruation/reminders/${reminderId}/`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ is_enabled: isEnabled })
        });
        
        if (!response.ok) throw new Error('Failed to toggle reminder');
        
        showNotification(
            isEnabled ? 'Rappel activé' : 'Rappel désactivé',
            'success'
        );
    } catch (error) {
        console.error('Toggle reminder error:', error);
        showNotification('Erreur lors de la modification du rappel', 'error');
    }
}

/**
 * Get CSRF token
 */
function getCsrfToken() {
    const name = 'csrftoken';
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

// CSS for mini calendar days
const style = document.createElement('style');
style.textContent = `
    .mini-calendar-days {
        display: flex;
        gap: 8px;
        justify-content: center;
        padding: 16px 0;
    }
    
    .mini-calendar-day {
        text-align: center;
        padding: 12px 8px;
        border-radius: 8px;
        transition: all 0.2s;
        cursor: pointer;
    }
    
    .mini-calendar-day:hover {
        background: var(--primary-pink-light);
    }
    
    .mini-calendar-day.today {
        background: var(--primary-pink);
        color: white;
    }
    
    .mini-day-weekday {
        font-size: 11px;
        text-transform: uppercase;
        margin-bottom: 4px;
        opacity: 0.7;
    }
    
    .mini-day-number {
        font-size: 16px;
        font-weight: 600;
    }
    
    .field-error {
        border-color: var(--period-red) !important;
    }
    
    .field-error-message {
        color: var(--period-red);
        font-size: 12px;
        margin-top: 4px;
    }
    
    .notification {
        position: fixed;
        top: 80px;
        right: 20px;
        background: white;
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
        max-width: 400px;
    }
    
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .notification-icon {
        font-size: 20px;
    }
    
    .notification-success {
        border-left: 4px solid var(--ovulation-green);
    }
    
    .notification-error {
        border-left: 4px solid var(--period-red);
    }
    
    .notification-warning {
        border-left: 4px solid var(--fertile-yellow);
    }
    
    .notification-info {
        border-left: 4px solid var(--primary-pink);
    }
    
    .notification-close {
        position: absolute;
        top: 8px;
        right: 8px;
        background: none;
        border: none;
        font-size: 20px;
        cursor: pointer;
        color: var(--text-muted);
    }
`;
document.head.appendChild(style);
