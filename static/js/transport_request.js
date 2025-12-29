let selectedType = null;
let selectedUrgency = null;
let map = null;
let pickupMarker = null;
let dropoffMarker = null;
let routeLine = null;
let pickupCoords = null;
let dropoffCoords = null;
let currentLocationMarker = null;
let autocompleteTimeout = null;

function initTransportPage() {
    initMap();
    setupAddressAutocomplete();
    setupGeolocation();
    loadRecentRequests();

    // Ensure map renders properly after page load
    setTimeout(() => {
        if (map) {
            map.invalidateSize();
        }
    }, 200);
}

function initMap() {
    if (map) return;
    
    map = L.map('routeMap', {
        center: [6.1319, 1.2228],
        zoom: 13,
        zoomControl: true
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    window.pickupIcon = L.divIcon({
        className: 'custom-marker pickup-marker',
        html: '<div style="background: #22c55e; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);"><span style="font-size: 16px;">📍</span></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });

    window.dropoffIcon = L.divIcon({
        className: 'custom-marker dropoff-marker',
        html: '<div style="background: #ef4444; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);"><span style="font-size: 16px;">🏁</span></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });

    window.currentLocationIcon = L.divIcon({
        className: 'custom-marker current-location-marker',
        html: '<div style="background: #3b82f6; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3); animation: pulse 2s infinite;"></div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    getUserLocation();
}

function setupGeolocation() {
    const pickMyLocationBtn = document.getElementById('pickMyLocationBtn');
    if (pickMyLocationBtn) {
        pickMyLocationBtn.addEventListener('click', pickMyLocation);
    }
}

async function getUserLocation() {
    try {
        const position = await window.BINTACURAGeolocation.getCurrentPosition({
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        });

        const lat = position.latitude;
        const lon = position.longitude;

        if (currentLocationMarker) {
            map.removeLayer(currentLocationMarker);
        }

        currentLocationMarker = L.marker([lat, lon], {
            icon: window.currentLocationIcon
        }).addTo(map).bindPopup('Ma position actuelle');

        map.setView([lat, lon], 14);

    } catch (error) {
        console.error('Geolocation error:', error.message);
        alert('Impossible d\'obtenir votre position: ' + error.message);
    }
}

async function pickMyLocation() {
    const btn = document.getElementById('pickMyLocationBtn');

    try {
        await window.BINTACURAGeolocation.getPositionWithFeedback({
            button: btn,
            onSuccess: async (position) => {
                const lat = position.latitude;
                const lon = position.longitude;

                pickupCoords = { lat, lon };

                const address = await reverseGeocode(lat, lon);
                document.getElementById('pickupAddress').value = address;

                if (pickupMarker) {
                    map.removeLayer(pickupMarker);
                }

                pickupMarker = L.marker([lat, lon], {
                    icon: window.pickupIcon
                }).addTo(map).bindPopup(`<b>Depart</b><br>${address}`).openPopup();

                map.setView([lat, lon], 14);

                const dropoffAddress = document.getElementById('dropoffAddress').value;
                if (dropoffAddress) {
                    await updateMapRoute();
                }
            },
            onError: (errorMsg) => {
                alert(errorMsg);
            }
        });
    } catch (error) {
        console.error('Geolocation error:', error);
    }
}

async function reverseGeocode(lat, lon) {
    try {
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`
        );
        const data = await response.json();
        
        if (data && data.display_name) {
            return data.display_name;
        }
        return `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    } catch (error) {
        console.error('Reverse geocoding error:', error);
        return `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    }
}

async function geocodeAddress(address) {
    try {
        const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=5`
        );
        const data = await response.json();
        
        if (data && data.length > 0) {
            return data.map(item => ({
                lat: parseFloat(item.lat),
                lon: parseFloat(item.lon),
                display_name: item.display_name,
                address: item.address
            }));
        }
        return [];
    } catch (error) {
        console.error('Geocoding error:', error);
        return [];
    }
}

function setupAddressAutocomplete() {
    const pickupInput = document.getElementById('pickupAddress');
    const dropoffInput = document.getElementById('dropoffAddress');
    
    setupAutocompleteField(pickupInput, 'pickup');
    setupAutocompleteField(dropoffInput, 'dropoff');
    
    pickupInput.addEventListener('blur', () => {
        setTimeout(() => {
            const container = document.getElementById('pickup-autocomplete');
            if (container) container.remove();
        }, 200);
        
        if (pickupInput.value && dropoffInput.value) {
            updateMapRoute();
        }
    });
    
    dropoffInput.addEventListener('blur', () => {
        setTimeout(() => {
            const container = document.getElementById('dropoff-autocomplete');
            if (container) container.remove();
        }, 200);
        
        if (pickupInput.value && dropoffInput.value) {
            updateMapRoute();
        }
    });
}

function setupAutocompleteField(input, type) {
    input.addEventListener('input', async (e) => {
        const value = e.target.value.trim();
        
        if (autocompleteTimeout) {
            clearTimeout(autocompleteTimeout);
        }
        
        const containerId = `${type}-autocomplete`;
        let container = document.getElementById(containerId);
        
        if (value.length < 3) {
            if (container) container.remove();
            return;
        }
        
        autocompleteTimeout = setTimeout(async () => {
            const results = await geocodeAddress(value);
            
            if (!container) {
                container = document.createElement('div');
                container.id = containerId;
                container.className = 'autocomplete-dropdown';
                input.parentElement.style.position = 'relative';
                input.parentElement.appendChild(container);
            }
            
            if (results.length === 0) {
                container.innerHTML = '<div class="autocomplete-item">Aucun résultat trouvé</div>';
                return;
            }
            
            container.innerHTML = results.map(result => `
                <div class="autocomplete-item" data-lat="${result.lat}" data-lon="${result.lon}" data-display="${result.display_name}">
                    <div class="autocomplete-icon">📍</div>
                    <div class="autocomplete-text">
                        <div class="autocomplete-name">${result.display_name.split(',')[0]}</div>
                        <div class="autocomplete-address">${result.display_name}</div>
                    </div>
                </div>
            `).join('');
            
            container.querySelectorAll('.autocomplete-item').forEach(item => {
                item.addEventListener('click', () => {
                    const lat = parseFloat(item.dataset.lat);
                    const lon = parseFloat(item.dataset.lon);
                    const displayName = item.dataset.display;
                    
                    input.value = displayName;
                    
                    if (type === 'pickup') {
                        pickupCoords = { lat, lon };
                        
                        if (pickupMarker) {
                            map.removeLayer(pickupMarker);
                        }
                        
                        pickupMarker = L.marker([lat, lon], { 
                            icon: window.pickupIcon 
                        }).addTo(map).bindPopup(`<b>Départ</b><br>${displayName}`);
                    } else {
                        dropoffCoords = { lat, lon };
                        
                        if (dropoffMarker) {
                            map.removeLayer(dropoffMarker);
                        }
                        
                        dropoffMarker = L.marker([lat, lon], { 
                            icon: window.dropoffIcon 
                        }).addTo(map).bindPopup(`<b>Destination</b><br>${displayName}`);
                    }
                    
                    container.remove();
                    
                    if (pickupCoords && dropoffCoords) {
                        updateMapRoute();
                    }
                });
            });
        }, 500);
    });
}

async function getRoute(pickup, dropoff) {
    try {
        const response = await fetch(
            `https://router.project-osrm.org/route/v1/driving/${pickup.lon},${pickup.lat};${dropoff.lon},${dropoff.lat}?overview=full&geometries=geojson`
        );
        const data = await response.json();
        
        if (data && data.routes && data.routes.length > 0) {
            return {
                geometry: data.routes[0].geometry,
                distance: data.routes[0].distance / 1000,
                duration: data.routes[0].duration / 60
            };
        }
        return null;
    } catch (error) {
        console.error('Routing error:', error);
        return null;
    }
}

async function updateMapRoute() {
    if (!pickupCoords || !dropoffCoords) {
        return;
    }

    if (!map) {
        initMap();
    }

    if (routeLine) map.removeLayer(routeLine);
    document.getElementById('routeInfo').style.display = 'none';

    try {
        const route = await getRoute(pickupCoords, dropoffCoords);
        
        if (route) {
            const coordinates = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);
            routeLine = L.polyline(coordinates, {
                color: '#3b82f6',
                weight: 5,
                opacity: 0.7
            }).addTo(map);

            const bounds = L.latLngBounds([
                [pickupCoords.lat, pickupCoords.lon],
                [dropoffCoords.lat, dropoffCoords.lon]
            ]);
            map.fitBounds(bounds, { padding: [50, 50] });

            const distance = route.distance.toFixed(2);
            const duration = Math.round(route.duration);
            const baseCost = selectedType === 'ambulance' ? 5000 : 3000;
            const costPerKm = selectedType === 'ambulance' ? 250 : 150;
            const estimatedCost = (baseCost + (route.distance * costPerKm)).toFixed(0);

            document.getElementById('routeDistance').textContent = `${distance} km`;
            document.getElementById('routeDuration').textContent = `${duration} min`;
            document.getElementById('estimatedCost').textContent = `${estimatedCost} XOF`;
            document.getElementById('routeInfo').style.display = 'block';
        } else {
            const bounds = L.latLngBounds([
                [pickupCoords.lat, pickupCoords.lon],
                [dropoffCoords.lat, dropoffCoords.lon]
            ]);
            map.fitBounds(bounds, { padding: [50, 50] });
            
            const distance = map.distance(
                [pickupCoords.lat, pickupCoords.lon], 
                [dropoffCoords.lat, dropoffCoords.lon]
            ) / 1000;
            document.getElementById('routeDistance').textContent = `~${distance.toFixed(2)} km`;
            document.getElementById('routeDuration').textContent = 'Non calculé';
            document.getElementById('estimatedCost').textContent = 'À confirmer';
            document.getElementById('routeInfo').style.display = 'block';
        }
    } catch (error) {
        console.error('Error updating map:', error);
    }
}

function selectTransportType(type) {
    selectedType = type;
    document.querySelectorAll('.transport-type').forEach(el => el.classList.remove('selected'));
    document.querySelector(`[data-type="${type}"]`).classList.add('selected');
    document.getElementById('transportType').value = type;
    
    if (pickupCoords && dropoffCoords) {
        updateMapRoute();
    }
}

function selectUrgency(level) {
    selectedUrgency = level;
    document.querySelectorAll('.urgency-option').forEach(el => el.classList.remove('selected'));
    document.querySelector(`[data-urgency="${level}"]`).classList.add('selected');
    document.getElementById('urgencyLevel').value = level;
}

async function submitTransportRequest(event) {
    event.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Envoi en cours...';

    const urgencyMapping = {
        'low': 'routine',
        'medium': 'scheduled',
        'high': 'emergency'
    };

    const urgencyValue = document.getElementById('urgencyLevel').value;

    const formData = {
        transport_type: document.getElementById('transportType').value,
        urgency: urgencyMapping[urgencyValue] || 'scheduled',
        pickup_address: document.getElementById('pickupAddress').value,
        dropoff_address: document.getElementById('dropoffAddress').value,
        scheduled_pickup_time: document.getElementById('scheduledTime').value,
        companion_count: parseInt(document.getElementById('passengers').value) - 1,
        patient_notes: document.getElementById('notes').value
    };

    if (pickupCoords) {
        formData.pickup_latitude = pickupCoords.lat;
        formData.pickup_longitude = pickupCoords.lon;
    }

    if (dropoffCoords) {
        formData.dropoff_latitude = dropoffCoords.lat;
        formData.dropoff_longitude = dropoffCoords.lon;
    }

    try {
        const response = await fetchApi('transport/requests/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            alert('Demande de transport envoyée avec succès!');
            document.getElementById('transportForm').reset();
            selectedType = null;
            selectedUrgency = null;
            pickupCoords = null;
            dropoffCoords = null;
            
            if (pickupMarker) map.removeLayer(pickupMarker);
            if (dropoffMarker) map.removeLayer(dropoffMarker);
            if (routeLine) map.removeLayer(routeLine);
            document.getElementById('routeInfo').style.display = 'none';
            
            document.querySelectorAll('.transport-type, .urgency-option').forEach(el =>
                el.classList.remove('selected')
            );
            loadRecentRequests();
        } else {
            alert('Erreur: ' + (data.detail || data.error || JSON.stringify(data)));
        }
    } catch (error) {
        console.error('Error submitting transport request:', error);
        alert('Erreur de connexion au serveur');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Soumettre la demande';
    }
}

async function loadRecentRequests() {
    try {
        const response = await fetchApi('transport/requests/');
        
        if (!response.ok) {
            throw new Error('Failed to load requests');
        }
        
        const data = await response.json();
        const container = document.getElementById('recentRequests');

        if (!data || !data.results || data.results.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">Aucune demande récente</p>';
            return;
        }

        const requests = data.results || data;
        const recentRequests = Array.isArray(requests) ? requests.slice(0, 5) : [];

        container.innerHTML = recentRequests.map(request => {
            const date = new Date(request.created_at);
            const formattedDate = date.toLocaleDateString('fr-FR');

            return `
                <div class="request-item">
                    <div class="request-header">
                        <span class="request-id">#${request.request_number || request.id}</span>
                        <span class="request-status status-${request.status}">${getStatusText(request.status)}</span>
                    </div>
                    <div class="request-details">
                        ${request.pickup_address} → ${request.dropoff_address}<br>
                        <small>${formattedDate}</small>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading recent requests:', error);
        document.getElementById('recentRequests').innerHTML = 
            '<p style="color: #999; text-align: center; padding: 20px;">Erreur de chargement</p>';
    }
}

function getStatusText(status) {
    const statusTexts = {
        'pending': 'En attente',
        'driver_assigned': 'Chauffeur assigné',
        'en_route': 'En route',
        'arrived': 'Arrivé',
        'in_transit': 'En transit',
        'completed': 'Terminé',
        'cancelled': 'Annulé',
        'confirmed': 'Confirmé',
        'in_progress': 'En cours'
    };
    return statusTexts[status] || status;
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

document.addEventListener('DOMContentLoaded', initTransportPage);

