// BINTACURA Transport - Modern JavaScript (Uber/Gozem Style)

// Global Variables
let map = null;
let pickupMarker = null;
let dropoffMarker = null;
let routeLine = null;
let pickupCoords = null;
let dropoffCoords = null;
let currentLocationMarker = null;
let selectedType = null;
let selectedUrgency = null;
let autocompleteTimeout = null;

// Map Icons (defined as function to ensure L is loaded)
const createCustomIcon = (emoji, color) => {
    if (typeof L === 'undefined') {
        console.error('Cannot create icon: Leaflet not loaded');
        return null;
    }
    return L.divIcon({
        className: 'custom-marker',
        html: `<div style="background: ${color}; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 2px 12px rgba(0,0,0,0.3); font-size: 20px;">${emoji}</div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18]
    });
};

// Wait for Leaflet to load before initializing
function waitForLeafletAndInit() {
    console.log('Checking if Leaflet is loaded...');

    if (typeof L !== 'undefined') {
        console.log('✅ Leaflet is loaded! Version:', L.version);
        initMap();
        setupAutocomplete();
        setupGeolocation();
        setupFormSelections();
    } else {
        console.log('⏳ Leaflet not loaded yet, retrying in 100ms...');
        setTimeout(waitForLeafletAndInit, 100);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');
    waitForLeafletAndInit();
});

// Backup: also try after full window load
window.addEventListener('load', () => {
    console.log('Window fully loaded');
    if (!map && typeof L !== 'undefined') {
        console.log('Initializing map after window load...');
        waitForLeafletAndInit();
    }
});

// Initialize Map
function initMap() {
    if (map) {
        console.log('Map already initialized');
        return;
    }

    console.log('Starting map initialization...');

    // Check if Leaflet is loaded
    if (typeof L === 'undefined') {
        console.error('Leaflet (L) is not loaded!');
        alert('Erreur: Leaflet n\'est pas chargé. Rechargez la page.');
        return;
    }

    // Check if map container exists
    const mapContainer = document.getElementById('mainMap');
    if (!mapContainer) {
        console.error('Map container #mainMap not found!');
        return;
    }

    console.log('Map container found:', mapContainer);
    console.log('Map container dimensions:', mapContainer.offsetWidth, 'x', mapContainer.offsetHeight);

    try {
        // Initialize map centered on Togo/West Africa
        console.log('Creating Leaflet map...');
        map = L.map('mainMap', {
            center: [6.1319, 1.2228], // Lomé, Togo
            zoom: 13,
            zoomControl: true,
            scrollWheelZoom: true
        });

        console.log('Map object created:', map);

        // Add OpenStreetMap tiles
        console.log('Adding tile layer...');
        const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        });

        tileLayer.addTo(map);
        console.log('Tile layer added');

        // Force map to recalculate size after a short delay
        setTimeout(() => {
            if (map) {
                console.log('Calling invalidateSize...');
                map.invalidateSize();
                console.log('Map dimensions after invalidate:', mapContainer.offsetWidth, 'x', mapContainer.offsetHeight);
                // Get user's current location
                getUserLocation();
            }
        }, 500);

        // Also try again after a longer delay
        setTimeout(() => {
            if (map) {
                map.invalidateSize();
            }
        }, 1000);

        console.log('✅ Map initialized successfully');
    } catch (error) {
        console.error('❌ Map initialization error:', error);
        alert('Erreur lors de l\'initialisation de la carte: ' + error.message);
    }
}

// Get User's Current Location
async function getUserLocation() {
    if (!navigator.geolocation) {
        console.log('Geolocation not supported');
        return;
    }

    try {
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            });
        });

        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        // Add marker for current location
        if (currentLocationMarker) {
            map.removeLayer(currentLocationMarker);
        }

        currentLocationMarker = L.marker([lat, lon], {
            icon: createCustomIcon('📍', '#3b82f6')
        }).addTo(map);

        currentLocationMarker.bindPopup('Votre position actuelle').openPopup();
        map.setView([lat, lon], 15);

        console.log('User location:', lat, lon);
    } catch (error) {
        console.log('Could not get location, using default view');
        // Keep default view if geolocation fails
    }
}

// Setup Geolocation Button
function setupGeolocation() {
    const pickMyLocationBtn = document.getElementById('pickMyLocationBtn');
    if (pickMyLocationBtn) {
        pickMyLocationBtn.addEventListener('click', pickMyLocation);
    }
}

// Pick My Location and Auto-populate Address
async function pickMyLocation() {
    const btn = document.getElementById('pickMyLocationBtn');
    const input = document.getElementById('pickupAddress');
    const originalText = btn.innerHTML;

    if (!navigator.geolocation) {
        alert('La géolocalisation n\'est pas supportée par votre navigateur');
        return;
    }

    try {
        // Show loading state
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>';

        // Get current position
        const position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            });
        });

        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        // Store coordinates
        pickupCoords = { lat, lon };

        // Reverse geocode to get address
        const address = await reverseGeocode(lat, lon);

        // Update input field with address
        input.value = address;

        // Update map marker
        if (pickupMarker) {
            map.removeLayer(pickupMarker);
        }

        pickupMarker = L.marker([lat, lon], {
            icon: createCustomIcon('📍', '#22c55e')
        }).addTo(map);

        pickupMarker.bindPopup(`<b>Départ</b><br>${address}`).openPopup();
        map.setView([lat, lon], 15);

        // Update route if dropoff is set
        if (dropoffCoords) {
            updateRoute();
        }

        console.log('Location picked:', address);
    } catch (error) {
        console.error('Location pick error:', error);

        let errorMessage = 'Impossible d\'obtenir votre position.\n\n';

        if (error.code === 1) {
            errorMessage += '❌ Permission refusée.\nAutorisez l\'accès à votre position dans les paramètres du navigateur.';
        } else if (error.code === 2) {
            errorMessage += '❌ Position non disponible.\nVérifiez votre connexion GPS/WiFi.';
        } else if (error.code === 3) {
            errorMessage += '❌ Délai dépassé.\nRéessayez.';
        } else {
            errorMessage += '❌ ' + error.message;
        }

        // Check if HTTPS (geolocation requires HTTPS except on localhost)
        if (window.location.protocol !== 'https:' &&
            window.location.hostname !== 'localhost' &&
            window.location.hostname !== '127.0.0.1') {
            errorMessage += '\n\n⚠️ Note: La géolocalisation nécessite HTTPS.';
        }

        alert(errorMessage);
    } finally {
        // Restore button state
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Reverse Geocode - Convert coordinates to address
async function reverseGeocode(lat, lon) {
    try {
        console.log('Reverse geocoding:', lat, lon);

        // Note: Browser automatically sends User-Agent and Referer headers
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=fr`
        );

        console.log('Reverse geocode response:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('Reverse geocode result:', data.display_name);

        if (data && data.display_name) {
            return data.display_name;
        }

        return `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    } catch (error) {
        console.error('Reverse geocoding error:', error);
        return `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    }
}

// Setup Autocomplete
function setupAutocomplete() {
    const pickupInput = document.getElementById('pickupAddress');
    const dropoffInput = document.getElementById('dropoffAddress');
    const pickupDropdown = document.getElementById('pickupAutocomplete');
    const dropoffDropdown = document.getElementById('dropoffAutocomplete');

    // Pickup address autocomplete
    pickupInput.addEventListener('input', (e) => {
        handleAutocomplete(e.target.value, pickupDropdown, 'pickup');
    });

    pickupInput.addEventListener('focus', () => {
        if (pickupInput.value.length > 2) {
            pickupDropdown.classList.add('show');
        }
    });

    // Dropoff address autocomplete
    dropoffInput.addEventListener('input', (e) => {
        handleAutocomplete(e.target.value, dropoffDropdown, 'dropoff');
    });

    dropoffInput.addEventListener('focus', () => {
        if (dropoffInput.value.length > 2) {
            dropoffDropdown.classList.add('show');
        }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!pickupInput.contains(e.target) && !pickupDropdown.contains(e.target)) {
            pickupDropdown.classList.remove('show');
        }
        if (!dropoffInput.contains(e.target) && !dropoffDropdown.contains(e.target)) {
            dropoffDropdown.classList.remove('show');
        }
    });
}

// Handle Autocomplete Search
function handleAutocomplete(query, dropdown, type) {
    // Clear previous timeout
    if (autocompleteTimeout) {
        clearTimeout(autocompleteTimeout);
    }

    // Hide dropdown if query is too short
    if (query.length < 3) {
        dropdown.classList.remove('show');
        return;
    }

    // Show loading
    dropdown.innerHTML = '<div class="autocomplete-loading">Recherche...</div>';
    dropdown.classList.add('show');

    // Debounce search
    autocompleteTimeout = setTimeout(async () => {
        await searchPlaces(query, dropdown, type);
    }, 300);
}

// Search Places using Nominatim
async function searchPlaces(query, dropdown, type) {
    try {
        // Build search URL with user's location for better results
        let url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&addressdetails=1&limit=8&accept-language=fr`;

        // If we have pickup coordinates, use them to prioritize nearby results
        if (pickupCoords && pickupCoords.lat && pickupCoords.lon) {
            // Create a viewbox around user's location (approx 50km radius)
            const lat = pickupCoords.lat;
            const lon = pickupCoords.lon;
            const delta = 0.5; // ~50km at equator
            const viewbox = `${lon - delta},${lat + delta},${lon + delta},${lat - delta}`;
            url += `&viewbox=${viewbox}&bounded=0`;
            console.log('Searching near user location:', lat, lon);
        } else if (currentLocationMarker) {
            // Fallback: use current location marker position
            const latlng = currentLocationMarker.getLatLng();
            const delta = 0.5;
            const viewbox = `${latlng.lng - delta},${latlng.lat + delta},${latlng.lng + delta},${latlng.lat - delta}`;
            url += `&viewbox=${viewbox}&bounded=0`;
            console.log('Searching near current location marker:', latlng.lat, latlng.lng);
        }

        console.log('Searching places for:', query);

        // Note: Browser automatically sends User-Agent and Referer headers
        // JavaScript cannot override User-Agent (security restriction)
        const response = await fetch(url);

        console.log('Search response status:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const places = await response.json();
        console.log('Found places:', places.length);

        if (!places || places.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-loading">Aucun résultat trouvé. Essayez un autre lieu.</div>';
            return;
        }

        // Build dropdown HTML
        let html = '';
        places.forEach(place => {
            const icon = getPlaceIcon(place.type);
            const name = place.name || place.display_name.split(',')[0];
            const address = place.display_name;

            html += `
                <div class="autocomplete-item" data-lat="${place.lat}" data-lon="${place.lon}" data-address="${address}" data-type="${type}">
                    <div class="autocomplete-icon">${icon}</div>
                    <div class="autocomplete-text">
                        <div class="autocomplete-name">${name}</div>
                        <div class="autocomplete-address">${address}</div>
                    </div>
                </div>
            `;
        });

        dropdown.innerHTML = html;

        // Add click listeners to items
        dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => selectPlace(item));
        });

    } catch (error) {
        console.error('Place search error:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });

        let errorMsg = 'Impossible de rechercher.';
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            errorMsg = 'Erreur réseau. Vérifiez votre connexion.';
            console.error('This might be a CORS or CSP issue blocking Nominatim API');
        }

        dropdown.innerHTML = `<div class="autocomplete-loading">${errorMsg}</div>`;
    }
}

// Get Place Icon based on type
function getPlaceIcon(type) {
    const icons = {
        'hospital': '🏥',
        'clinic': '🏥',
        'pharmacy': '💊',
        'house': '🏠',
        'building': '🏢',
        'school': '🏫',
        'restaurant': '🍽️',
        'hotel': '🏨',
        'airport': '✈️',
        'bus_station': '🚌',
        'default': '📍'
    };
    return icons[type] || icons['default'];
}

// Select Place from Autocomplete
function selectPlace(item) {
    const lat = parseFloat(item.dataset.lat);
    const lon = parseFloat(item.dataset.lon);
    const address = item.dataset.address;
    const type = item.dataset.type;

    if (type === 'pickup') {
        // Update pickup
        document.getElementById('pickupAddress').value = address;
        document.getElementById('pickupAutocomplete').classList.remove('show');
        pickupCoords = { lat, lon };

        // Update marker
        if (pickupMarker) {
            map.removeLayer(pickupMarker);
        }
        pickupMarker = L.marker([lat, lon], {
            icon: createCustomIcon('📍', '#22c55e')
        }).addTo(map);
        pickupMarker.bindPopup(`<b>Départ</b><br>${address}`);

    } else {
        // Update dropoff
        document.getElementById('dropoffAddress').value = address;
        document.getElementById('dropoffAutocomplete').classList.remove('show');
        dropoffCoords = { lat, lon };

        // Update marker
        if (dropoffMarker) {
            map.removeLayer(dropoffMarker);
        }
        dropoffMarker = L.marker([lat, lon], {
            icon: createCustomIcon('🏁', '#ef4444')
        }).addTo(map);
        dropoffMarker.bindPopup(`<b>Destination</b><br>${address}`);
    }

    // Fit map to show both markers
    if (pickupCoords && dropoffCoords) {
        const bounds = L.latLngBounds(
            [pickupCoords.lat, pickupCoords.lon],
            [dropoffCoords.lat, dropoffCoords.lon]
        );
        map.fitBounds(bounds, { padding: [50, 50] });
        updateRoute();
    } else if (type === 'pickup' && pickupCoords) {
        map.setView([lat, lon], 15);
    } else if (type === 'dropoff' && dropoffCoords) {
        map.setView([lat, lon], 15);
    }
}

// Update Route between pickup and dropoff
async function updateRoute() {
    if (!pickupCoords || !dropoffCoords) return;

    try {
        // Remove existing route line
        if (routeLine) {
            map.removeLayer(routeLine);
        }

        // Get route from OSRM (Open Source Routing Machine)
        const url = `https://router.project-osrm.org/route/v1/driving/${pickupCoords.lon},${pickupCoords.lat};${dropoffCoords.lon},${dropoffCoords.lat}?overview=full&geometries=geojson`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.code === 'Ok' && data.routes.length > 0) {
            const route = data.routes[0];
            const coordinates = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);

            // Draw route on map
            routeLine = L.polyline(coordinates, {
                color: '#000000',
                weight: 4,
                opacity: 0.7
            }).addTo(map);

            // Calculate distance and duration
            const distanceKm = (route.distance / 1000).toFixed(1);
            const durationMin = Math.round(route.duration / 60);

            // Estimate cost (basic formula: base fare + distance rate)
            const baseFare = 1000; // XOF
            const perKmRate = 200; // XOF
            const estimatedCost = Math.round(baseFare + (distanceKm * perKmRate));

            // Update route info card
            document.getElementById('routeDistance').textContent = `${distanceKm} km`;
            document.getElementById('routeDuration').textContent = `${durationMin} min`;
            document.getElementById('estimatedCost').textContent = `${estimatedCost.toLocaleString()} XOF`;
            document.getElementById('routeInfoCard').classList.add('show');

            console.log('Route updated:', { distanceKm, durationMin, estimatedCost });
        }
    } catch (error) {
        console.error('Route calculation error:', error);
    }
}

// Setup Form Selections
function setupFormSelections() {
    // Pre-select ambulance and high urgency for emergency transport
    const ambulanceType = document.querySelector('[data-type="ambulance"]');
    if (ambulanceType) {
        selectTransportType('ambulance');
    }

    const highUrgency = document.querySelector('[data-urgency="high"]');
    if (highUrgency) {
        selectUrgency('high');
    }
}

// Select Transport Type
function selectTransportType(type) {
    selectedType = type;

    // Update UI
    document.querySelectorAll('.transport-type').forEach(el => {
        el.classList.remove('selected');
    });

    const selected = document.querySelector(`[data-type="${type}"]`);
    if (selected) {
        selected.classList.add('selected');
    }

    // Update hidden input
    document.getElementById('transportType').value = type;
}

// Select Urgency Level
function selectUrgency(level) {
    selectedUrgency = level;

    // Update UI
    document.querySelectorAll('.urgency-option').forEach(el => {
        el.classList.remove('selected');
    });

    const selected = document.querySelector(`[data-urgency="${level}"]`);
    if (selected) {
        selected.classList.add('selected');
    }

    // Update hidden input
    document.getElementById('urgencyLevel').value = level;
}

// Submit Transport Request
async function submitTransportRequest(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const submitBtn = document.getElementById('submitBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');

    // Validation
    if (!selectedType) {
        alert('Veuillez sélectionner un type de transport');
        return;
    }

    if (!selectedUrgency) {
        alert('Veuillez sélectionner le niveau d\'urgence');
        return;
    }

    // Map urgency values to API expected values
    const urgencyMap = {
        'low': 'routine',
        'medium': 'urgent',
        'high': 'emergency'
    };

    // Update urgency value in form
    const mappedUrgency = urgencyMap[selectedUrgency] || 'routine';
    formData.set('urgency', mappedUrgency);
    console.log('Mapped urgency:', selectedUrgency, '→', mappedUrgency);

    // Add coordinates if available
    if (pickupCoords) {
        formData.append('pickup_latitude', pickupCoords.lat);
        formData.append('pickup_longitude', pickupCoords.lon);
    }

    if (dropoffCoords) {
        formData.append('dropoff_latitude', dropoffCoords.lat);
        formData.append('dropoff_longitude', dropoffCoords.lon);
    }

    try {
        // Show loading
        submitBtn.disabled = true;
        submitBtn.textContent = 'Envoi en cours...';
        loadingOverlay.classList.add('show');

        // Log form data for debugging
        console.log('=== Submitting Transport Request ===');
        console.log('Form data contents:');
        for (const [key, value] of formData.entries()) {
            console.log(`  ${key}: ${value}`);
        }

        // Submit request
        const response = await fetch('/api/v1/transport/requests/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            },
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            console.log('Transport request created:', data);

            // Show success message
            alert('Demande de transport envoyée avec succès! Recherche de chauffeurs disponibles...');

            // Redirect to tracking page
            window.location.href = `/api/v1/transport/tracking/${data.id}/`;
        } else {
            const error = await response.json();
            console.error('Request error:', error);
            console.error('Response status:', response.status);

            // Show detailed error message
            let errorMessage = 'Erreur lors de l\'envoi de la demande.\n\n';
            if (error.detail) {
                errorMessage += error.detail;
            } else if (typeof error === 'object') {
                // Show all field errors
                for (const [field, messages] of Object.entries(error)) {
                    errorMessage += `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}\n`;
                }
            } else {
                errorMessage += error;
            }

            alert(errorMessage);
        }
    } catch (error) {
        console.error('Submit error:', error);
        alert('Erreur de connexion. Veuillez vérifier votre connexion Internet.');
    } finally {
        // Hide loading
        submitBtn.disabled = false;
        submitBtn.textContent = 'Demander un transport';
        loadingOverlay.classList.remove('show');
    }
}

// Export functions to global scope
window.selectTransportType = selectTransportType;
window.selectUrgency = selectUrgency;
window.submitTransportRequest = submitTransportRequest;

