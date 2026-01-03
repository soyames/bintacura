/**
 * Map Search JavaScript
 * Leaflet map integration for provider search
 */

let map;
let markers = [];
let userMarker = null;
let userLat = null;
let userLng = null;

// Initialize map on page load
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    setupEventListeners();
});

/**
 * Initialize Leaflet map
 */
function initMap() {
    // Default center (Cotonou, Benin)
    const defaultLat = 6.3703;
    const defaultLng = 2.3912;
    const defaultZoom = 12;
    
    // Create map
    map = L.map('map').setView([defaultLat, defaultLng], defaultZoom);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Hide loading
    document.getElementById('map-loading').classList.add('hidden');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Use my location button
    document.getElementById('use-my-location').addEventListener('click', getUserLocation);
    
    // Radius slider
    const radiusSlider = document.getElementById('radius');
    radiusSlider.addEventListener('input', function() {
        document.querySelector('.radius-value').textContent = this.value + ' km';
    });
    
    // Rating filter buttons
    const starButtons = document.querySelectorAll('.star-btn');
    starButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const rating = parseInt(this.dataset.rating);
            const currentRating = parseInt(document.getElementById('min-rating').value);
            
            if (currentRating === rating) {
                // Deselect
                document.getElementById('min-rating').value = 0;
                document.querySelector('.rating-text').textContent = 'Toutes';
                starButtons.forEach(b => {
                    b.classList.remove('active');
                    b.querySelector('i').classList.remove('fas');
                    b.querySelector('i').classList.add('far');
                });
            } else {
                // Select
                document.getElementById('min-rating').value = rating;
                document.querySelector('.rating-text').textContent = rating + '+ étoiles';
                starButtons.forEach(b => {
                    const btnRating = parseInt(b.dataset.rating);
                    if (btnRating <= rating) {
                        b.classList.add('active');
                        b.querySelector('i').classList.remove('far');
                        b.querySelector('i').classList.add('fas');
                    } else {
                        b.classList.remove('active');
                        b.querySelector('i').classList.remove('fas');
                        b.querySelector('i').classList.add('far');
                    }
                });
            }
        });
    });
    
    // Apply filters button
    document.getElementById('apply-filters').addEventListener('click', searchProviders);
    
    // Reset filters button
    document.getElementById('reset-filters').addEventListener('click', resetFilters);
    
    // Enter key in search inputs
    document.getElementById('search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') searchProviders();
    });
    
    document.getElementById('location-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') geocodeAddress();
    });
}

/**
 * Get user's current location
 */
function getUserLocation() {
    const btn = document.getElementById('use-my-location');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;
    
    if (!navigator.geolocation) {
        alert('La géolocalisation n\'est pas supportée par votre navigateur');
        btn.innerHTML = '<i class="fas fa-crosshairs"></i>';
        btn.disabled = false;
        return;
    }
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            userLat = position.coords.latitude;
            userLng = position.coords.longitude;
            
            // Update map
            map.setView([userLat, userLng], 13);
            
            // Add or update user marker
            if (userMarker) {
                map.removeLayer(userMarker);
            }
            
            userMarker = L.marker([userLat, userLng], {
                icon: L.divIcon({
                    className: 'user-location-marker',
                    html: '<i class="fas fa-user-circle" style="color: #3498db; font-size: 30px;"></i>',
                    iconSize: [30, 30]
                })
            }).addTo(map);
            
            userMarker.bindPopup('Votre position').openPopup();
            
            // Update location input with reverse geocoding
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${userLat}&lon=${userLng}`)
                .then(response => response.json())
                .then(data => {
                    const address = data.display_name;
                    document.getElementById('location-search').value = address;
                })
                .catch(err => console.error('Reverse geocoding failed:', err));
            
            btn.innerHTML = '<i class="fas fa-crosshairs"></i>';
            btn.disabled = false;
            
            // Automatically search
            searchProviders();
        },
        function(error) {
            alert('Impossible d\'obtenir votre position: ' + error.message);
            btn.innerHTML = '<i class="fas fa-crosshairs"></i>';
            btn.disabled = false;
        }
    );
}

/**
 * Geocode address from input
 */
function geocodeAddress() {
    const address = document.getElementById('location-search').value.trim();
    if (!address) return;
    
    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1`)
        .then(response => response.json())
        .then(data => {
            if (data.length > 0) {
                userLat = parseFloat(data[0].lat);
                userLng = parseFloat(data[0].lon);
                
                map.setView([userLat, userLng], 13);
                
                if (userMarker) {
                    map.removeLayer(userMarker);
                }
                
                userMarker = L.marker([userLat, userLng], {
                    icon: L.divIcon({
                        className: 'user-location-marker',
                        html: '<i class="fas fa-map-marker-alt" style="color: #e74c3c; font-size: 30px;"></i>',
                        iconSize: [30, 30]
                    })
                }).addTo(map);
                
                userMarker.bindPopup(address).openPopup();
                
                // Automatically search
                searchProviders();
            } else {
                alert('Adresse introuvable');
            }
        })
        .catch(err => {
            console.error('Geocoding failed:', err);
            alert('Erreur lors de la recherche de l\'adresse');
        });
}

/**
 * Search providers with filters
 */
function searchProviders() {
    const search = document.getElementById('search').value;
    const specialty = document.getElementById('specialty').value;
    const minRating = document.getElementById('min-rating').value;
    const radius = document.getElementById('radius').value;
    
    // Build query parameters
    const params = new URLSearchParams({
        search: search,
        specialty: specialty,
        min_rating: minRating,
        radius: radius
    });
    
    if (userLat && userLng) {
        params.append('lat', userLat);
        params.append('lng', userLng);
    }
    
    // Show loading
    document.getElementById('map-loading').classList.remove('hidden');
    
    // Fetch results
    fetch(`/core/api/map-search/?${params.toString()}`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
    })
    .then(response => response.json())
    .then(data => {
        displayResults(data.providers);
        document.getElementById('map-loading').classList.add('hidden');
    })
    .catch(error => {
        console.error('Search failed:', error);
        alert('Erreur lors de la recherche');
        document.getElementById('map-loading').classList.add('hidden');
    });
}

/**
 * Display search results on map and list
 */
function displayResults(providers) {
    // Clear existing markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    // Update count
    document.querySelector('.result-count').textContent = providers.length;
    
    // Clear results list
    const resultsList = document.getElementById('results-list');
    resultsList.innerHTML = '';
    
    if (providers.length === 0) {
        resultsList.innerHTML = '<p class="no-results"><i class="fas fa-info-circle"></i> Aucun résultat trouvé</p>';
        return;
    }
    
    // Add markers and list items
    providers.forEach((provider, index) => {
        // Create marker
        const marker = L.marker([provider.latitude, provider.longitude], {
            icon: L.divIcon({
                className: 'provider-marker',
                html: provider.role === 'hospital' 
                    ? '<i class="fas fa-hospital" style="color: #e74c3c; font-size: 24px;"></i>'
                    : '<i class="fas fa-user-md" style="color: #3498db; font-size: 24px;"></i>',
                iconSize: [30, 30]
            })
        }).addTo(map);
        
        // Popup content
        const popupContent = `
            <div class="provider-popup">
                <h5>${provider.name}</h5>
                ${provider.specialty ? `<div class="specialty"><i class="fas fa-stethoscope"></i> ${provider.specialty}</div>` : ''}
                ${provider.distance ? `<div class="info-row"><i class="fas fa-map-marker-alt"></i> ${provider.distance} km</div>` : ''}
                <div class="info-row rating">
                    <i class="fas fa-star"></i> ${provider.rating.toFixed(1)} (${provider.review_count} avis)
                </div>
                ${provider.consultation_fee ? `<div class="info-row"><i class="fas fa-money-bill-wave"></i> ${provider.consultation_fee} FCFA</div>` : ''}
                <div class="info-row"><i class="fas fa-phone"></i> ${provider.phone || 'N/A'}</div>
                <a href="/doctor/${provider.id}/" class="btn-view">Voir le profil</a>
            </div>
        `;
        
        marker.bindPopup(popupContent);
        markers.push(marker);
        
        // Create list item
        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `
            <h4>${provider.name}</h4>
            ${provider.specialty ? `<div class="specialty"><i class="fas fa-stethoscope"></i> ${provider.specialty}</div>` : ''}
            ${provider.distance ? `<div class="distance"><i class="fas fa-map-marker-alt"></i> À ${provider.distance} km</div>` : ''}
            <div class="rating">
                <span class="stars">${'★'.repeat(Math.floor(provider.rating))}${'☆'.repeat(5 - Math.floor(provider.rating))}</span>
                ${provider.rating.toFixed(1)} (${provider.review_count} avis)
            </div>
            <div class="address"><i class="fas fa-map-pin"></i> ${provider.address || provider.city}</div>
        `;
        
        // Click to center on map
        card.addEventListener('click', function() {
            map.setView([provider.latitude, provider.longitude], 15);
            marker.openPopup();
            
            // Highlight card
            document.querySelectorAll('.result-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
        });
        
        resultsList.appendChild(card);
    });
    
    // Fit map to markers
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

/**
 * Reset all filters
 */
function resetFilters() {
    document.getElementById('search').value = '';
    document.getElementById('location-search').value = '';
    document.getElementById('specialty').value = '';
    document.getElementById('min-rating').value = 0;
    document.getElementById('radius').value = 50;
    document.querySelector('.radius-value').textContent = '50 km';
    document.querySelector('.rating-text').textContent = 'Toutes';
    
    // Reset star buttons
    document.querySelectorAll('.star-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.querySelector('i').classList.remove('fas');
        btn.querySelector('i').classList.add('far');
    });
    
    // Clear user location
    userLat = null;
    userLng = null;
    if (userMarker) {
        map.removeLayer(userMarker);
        userMarker = null;
    }
    
    // Clear results
    document.getElementById('results-list').innerHTML = '<p class="no-results"><i class="fas fa-info-circle"></i> Utilisez les filtres pour rechercher</p>';
    document.querySelector('.result-count').textContent = '0';
    
    // Clear markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    // Reset map view
    map.setView([6.3703, 2.3912], 12);
}
