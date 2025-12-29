/**
 * BINTACURA Geolocation Helper
 * Provides robust geolocation functionality with proper error handling and user feedback
 */

console.log('🗺️ BINTACURA Geolocation Helper Loading...');

class GeolocationHelper {
    constructor() {
        this.isAvailable = 'geolocation' in navigator;
        this.isSecureContext = window.isSecureContext;
    }

    /**
     * Check if geolocation is supported and available
     * @returns {Object} Status object with availability and error message if any
     */
    checkAvailability() {
        if (!this.isAvailable) {
            return {
                available: false,
                error: 'UNSUPPORTED',
                message: 'Votre navigateur ne supporte pas la géolocalisation.',
                messageEn: 'Your browser does not support geolocation.'
            };
        }

        if (!this.isSecureContext && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            return {
                available: false,
                error: 'INSECURE_CONTEXT',
                message: 'La géolocalisation nécessite une connexion HTTPS sécurisée.',
                messageEn: 'Geolocation requires a secure HTTPS connection.',
                hint: 'Contactez l\'administrateur du site pour activer HTTPS.'
            };
        }

        return {
            available: true,
            message: 'Géolocalisation disponible',
            messageEn: 'Geolocation available'
        };
    }

    /**
     * Check current permission status for geolocation
     * @returns {Promise<String>} Permission status: 'granted', 'denied', 'prompt', or 'unknown'
     */
    async checkPermission() {
        if (!navigator.permissions || !navigator.permissions.query) {
            // Permissions API not supported, return unknown
            return 'unknown';
        }

        try {
            const result = await navigator.permissions.query({ name: 'geolocation' });
            return result.state; // 'granted', 'denied', or 'prompt'
        } catch (error) {
            console.warn('Permission check failed:', error);
            return 'unknown';
        }
    }

    /**
     * Get user's current position with proper error handling
     * @param {Object} options - Geolocation options
     * @returns {Promise<Object>} Position object or error
     */
    async getCurrentPosition(options = {}) {
        const defaultOptions = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
            ...options
        };

        // Check availability first
        const availability = this.checkAvailability();
        if (!availability.available) {
            throw new Error(availability.message);
        }

        // Check permission status
        const permission = await this.checkPermission();
        if (permission === 'denied') {
            throw new Error(
                'Permission de géolocalisation refusée. Veuillez autoriser l\'accès à votre position dans les paramètres de votre navigateur.'
            );
        }

        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    console.log('📍 Position obtained:', position.coords);
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: position.timestamp
                    });
                },
                (error) => {
                    console.error('❌ Geolocation error:', error);
                    const errorMessage = this.getErrorMessage(error);
                    reject(new Error(errorMessage));
                },
                defaultOptions
            );
        });
    }

    /**
     * Get human-readable error message from GeolocationPositionError
     * @param {GeolocationPositionError} error
     * @returns {String} User-friendly error message
     */
    getErrorMessage(error) {
        switch (error.code) {
            case error.PERMISSION_DENIED:
                return 'Permission de géolocalisation refusée. Veuillez autoriser l\'accès à votre position dans les paramètres de votre navigateur.';

            case error.POSITION_UNAVAILABLE:
                return 'Position indisponible. Vérifiez que les services de localisation sont activés sur votre appareil.';

            case error.TIMEOUT:
                return 'Délai de localisation dépassé. Veuillez réessayer.';

            default:
                return `Erreur de géolocalisation: ${error.message || 'Erreur inconnue'}`;
        }
    }

    /**
     * Get position with user-friendly UI feedback
     * @param {Object} options - Configuration object
     * @param {Function} options.onSuccess - Success callback with position
     * @param {Function} options.onError - Error callback with error message
     * @param {Function} options.onStart - Optional callback when starting
     * @param {HTMLElement} options.button - Optional button element to show loading state
     * @returns {Promise}
     */
    async getPositionWithFeedback(options = {}) {
        const { onSuccess, onError, onStart, button } = options;

        let originalButtonContent = null;

        try {
            // Call onStart callback
            if (onStart) onStart();

            // Update button state if provided
            if (button) {
                originalButtonContent = button.innerHTML;
                button.disabled = true;
                button.innerHTML = '<span class="spinner"></span> Localisation en cours...';
            }

            // Get position
            const position = await this.getCurrentPosition();

            // Call success callback
            if (onSuccess) {
                onSuccess(position);
            }

            return position;

        } catch (error) {
            // Call error callback
            if (onError) {
                onError(error.message);
            } else {
                // Default error handling - show alert
                alert(error.message);
            }

            throw error;

        } finally {
            // Restore button state
            if (button && originalButtonContent) {
                button.disabled = false;
                button.innerHTML = originalButtonContent;
            }
        }
    }

    /**
     * Watch position continuously
     * @param {Function} onSuccess - Success callback with position
     * @param {Function} onError - Error callback with error message
     * @param {Object} options - Geolocation options
     * @returns {Number} Watch ID for clearing the watch
     */
    watchPosition(onSuccess, onError, options = {}) {
        const defaultOptions = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 30000,
            ...options
        };

        if (!this.isAvailable) {
            const error = this.checkAvailability();
            if (onError) onError(error.message);
            return null;
        }

        return navigator.geolocation.watchPosition(
            (position) => {
                onSuccess({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: position.timestamp
                });
            },
            (error) => {
                const errorMessage = this.getErrorMessage(error);
                if (onError) onError(errorMessage);
            },
            defaultOptions
        );
    }

    /**
     * Clear a position watch
     * @param {Number} watchId - Watch ID returned from watchPosition
     */
    clearWatch(watchId) {
        if (watchId && this.isAvailable) {
            navigator.geolocation.clearWatch(watchId);
        }
    }

    /**
     * Format coordinates for display
     * @param {Number} latitude
     * @param {Number} longitude
     * @param {Number} decimals - Number of decimal places (default: 6)
     * @returns {String} Formatted coordinates
     */
    formatCoordinates(latitude, longitude, decimals = 6) {
        const lat = latitude.toFixed(decimals);
        const lon = longitude.toFixed(decimals);
        const latDir = latitude >= 0 ? 'N' : 'S';
        const lonDir = longitude >= 0 ? 'E' : 'O';
        return `${Math.abs(lat)}°${latDir}, ${Math.abs(lon)}°${lonDir}`;
    }
}

// Create global instance
window.BINTACURAGeolocation = new GeolocationHelper();
console.log('✅ BINTACURA Geolocation Helper Initialized');
console.log('   - Available:', window.BINTACURAGeolocation.isAvailable);
console.log('   - Secure Context:', window.BINTACURAGeolocation.isSecureContext);

