/**
 * Settings Management with Database Storage
 * All settings are stored in database and synced across devices
 */

const API_BASE_URL = '/api/v1/preferences/';
let currentPreferences = null;

// Debounce function to avoid too many API calls
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Get CSRF token from cookie
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

// Fetch preferences from database
async function loadPreferences() {
    try {
        const response = await fetch(API_BASE_URL, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            credentials: 'same-origin',
        });
        
        if (response.ok) {
            currentPreferences = await response.json();
            applyPreferences(currentPreferences);
            return currentPreferences;
        } else {
            console.error('Failed to load preferences:', response.statusText);
            return null;
        }
    } catch (error) {
        console.error('Error loading preferences:', error);
        return null;
    }
}

// Update preferences in database
async function updatePreferences(updates) {
    try {
        const response = await fetch(API_BASE_URL, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            credentials: 'same-origin',
            body: JSON.stringify(updates),
        });
        
        if (response.ok) {
            currentPreferences = await response.json();
            applyPreferences(currentPreferences);
            showNotification('Paramètres sauvegardés avec succès', 'success');
            return true;
        } else {
            const error = await response.json();
            console.error('Failed to update preferences:', error);
            showNotification('Erreur lors de la sauvegarde', 'error');
            return false;
        }
    } catch (error) {
        console.error('Error updating preferences:', error);
        showNotification('Erreur de connexion', 'error');
        return false;
    }
}

// Debounced update function
const debouncedUpdate = debounce(updatePreferences, 500);

// Apply preferences to UI
function applyPreferences(prefs) {
    if (!prefs) return;
    
    // Apply theme
    document.documentElement.setAttribute('data-theme', prefs.theme || 'light');
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        if (prefs.theme === 'dark') {
            darkModeToggle.classList.add('active');
        } else {
            darkModeToggle.classList.remove('active');
        }
    }
    
    // Apply font size
    const sizes = { 'small': '14px', 'medium': '16px', 'large': '18px' };
    if (prefs.font_size) {
        document.documentElement.style.fontSize = sizes[prefs.font_size];
        const fontSizeSelect = document.getElementById('fontSizeSelect');
        if (fontSizeSelect) {
            fontSizeSelect.value = prefs.font_size;
        }
    }
    
    // Apply notification toggles
    setToggleState('notificationsToggle', prefs.enable_push_notifications);
    setToggleState('emailNotificationsToggle', prefs.enable_email_notifications);
    setToggleState('smsNotificationsToggle', prefs.enable_sms_notifications);
    setToggleState('twoFactorToggle', prefs.enable_two_factor_auth);
    setToggleState('profileVisibleToggle', prefs.profile_visible_to_providers);
    setToggleState('dataSharingToggle', prefs.allow_anonymous_data_sharing);
    setToggleState('autoBackupToggle', prefs.enable_auto_backup);
    
    // Apply reminder time
    const reminderTimeSelect = document.getElementById('reminderTimeSelect');
    if (reminderTimeSelect && prefs.appointment_reminder_time !== undefined) {
        reminderTimeSelect.value = prefs.appointment_reminder_time;
    }
    
    // Apply blood type
    const bloodTypeSelect = document.getElementById('bloodTypeSelect');
    if (bloodTypeSelect && prefs.blood_type) {
        bloodTypeSelect.value = prefs.blood_type;
    }
}

// Helper to set toggle state
function setToggleState(toggleId, isActive) {
    const toggle = document.getElementById(toggleId);
    if (toggle) {
        if (isActive) {
            toggle.classList.add('active');
        } else {
            toggle.classList.remove('active');
        }
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#48bb78' : '#f56565'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Toggle functions
function toggleDarkMode() {
    const toggle = document.getElementById('darkModeToggle');
    const isDark = toggle.classList.contains('active');
    updatePreferences({ theme: isDark ? 'light' : 'dark' });
}

function changeFontSize(size) {
    updatePreferences({ font_size: size });
}

function toggleNotifications() {
    const toggle = document.getElementById('notificationsToggle');
    const isActive = !toggle.classList.contains('active');
    updatePreferences({ enable_push_notifications: isActive });
    
    if (isActive && 'Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function toggleEmailNotifications() {
    const toggle = document.getElementById('emailNotificationsToggle');
    const isActive = !toggle.classList.contains('active');
    updatePreferences({ enable_email_notifications: isActive });
}

function toggleSmsNotifications() {
    const toggle = document.getElementById('smsNotificationsToggle');
    const isActive = !toggle.classList.contains('active');
    updatePreferences({ enable_sms_notifications: isActive });
}

function toggleTwoFactor() {
    const toggle = document.getElementById('twoFactorToggle');
    const isActive = !toggle.classList.contains('active');
    
    if (isActive) {
        // Enabling 2FA - show setup dialog
        alert('Configuration de 2FA bientôt disponible');
    } else {
        // Disabling 2FA
        if (confirm('Désactiver l\'authentification à deux facteurs ?')) {
            updatePreferences({ enable_two_factor_auth: false });
        }
    }
}

function toggleProfileVisible() {
    const toggle = document.getElementById('profileVisibleToggle');
    const isActive = !toggle.classList.contains('active');
    updatePreferences({ profile_visible_to_providers: isActive });
}

function toggleDataSharing() {
    const toggle = document.getElementById('dataSharingToggle');
    const isActive = !toggle.classList.contains('active');
    updatePreferences({ allow_anonymous_data_sharing: isActive });
}

function toggleAutoBackup() {
    const toggle = document.getElementById('autoBackupToggle');
    const isActive = !toggle.classList.contains('active');
    updatePreferences({ enable_auto_backup: isActive });
}

function updateReminderTime() {
    const select = document.getElementById('reminderTimeSelect');
    if (select) {
        updatePreferences({ appointment_reminder_time: parseInt(select.value) });
    }
}

function updateBloodType() {
    const select = document.getElementById('bloodTypeSelect');
    if (select) {
        updatePreferences({ blood_type: select.value });
    }
}

async function resetSettings() {
    if (confirm('Réinitialiser tous les paramètres ? Cette action ne peut pas être annulée.')) {
        const defaultSettings = {
            theme: 'light',
            font_size: 'medium',
            enable_push_notifications: true,
            enable_email_notifications: true,
            enable_sms_notifications: false,
            enable_two_factor_auth: false,
            profile_visible_to_providers: true,
            allow_anonymous_data_sharing: false,
            enable_auto_backup: true,
            appointment_reminder_time: 60,
        };
        
        const success = await updatePreferences(defaultSettings);
        if (success) {
            location.reload();
        }
    }
}

function deleteAccount() {
    const confirmation = prompt('Pour supprimer votre compte, tapez "SUPPRIMER" :');
    if (confirmation === 'SUPPRIMER') {
        alert('Suppression de compte bientôt disponible. Contactez le support.');
    }
}

// Initialize settings on page load
document.addEventListener('DOMContentLoaded', async function() {
    // Load preferences from database
    await loadPreferences();
    
    // Add event listeners for select elements
    const reminderTimeSelect = document.getElementById('reminderTimeSelect');
    if (reminderTimeSelect) {
        reminderTimeSelect.addEventListener('change', updateReminderTime);
    }
    
    const bloodTypeSelect = document.getElementById('bloodTypeSelect');
    if (bloodTypeSelect) {
        bloodTypeSelect.addEventListener('change', updateBloodType);
    }
    
    const fontSizeSelect = document.getElementById('fontSizeSelect');
    if (fontSizeSelect) {
        fontSizeSelect.addEventListener('change', (e) => changeFontSize(e.target.value));
    }
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
