// Price Comparison JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const searchBtn = document.getElementById('search-btn');
    const resetBtn = document.getElementById('reset-btn');
    const specialtyFilter = document.getElementById('specialty-filter');
    const locationFilter = document.getElementById('location-filter');
    const sortFilter = document.getElementById('sort-filter');
    
    const statisticsSection = document.getElementById('statistics-section');
    const loadingSpinner = document.getElementById('loading-spinner');
    const noResults = document.getElementById('no-results');
    const resultsGrid = document.getElementById('results-grid');
    
    // Event Listeners
    searchBtn.addEventListener('click', performSearch);
    resetBtn.addEventListener('click', resetFilters);
    
    // Allow Enter key in location input
    locationFilter.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    function performSearch() {
        const params = new URLSearchParams({
            specialty: specialtyFilter.value,
            location: locationFilter.value.trim(),
            sort_by: sortFilter.value
        });
        
        // Show loading
        loadingSpinner.style.display = 'block';
        statisticsSection.style.display = 'none';
        noResults.style.display = 'none';
        resultsGrid.innerHTML = '';
        
        // Fetch results
        fetch(`/core/api/price-comparison/?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            loadingSpinner.style.display = 'none';
            
            if (data.success && data.results.length > 0) {
                displayStatistics(data.statistics);
                displayResults(data.results);
            } else {
                noResults.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingSpinner.style.display = 'none';
            alert('Erreur lors de la récupération des résultats');
        });
    }
    
    function displayStatistics(stats) {
        document.getElementById('avg-price').textContent = formatCurrency(stats.avg_price, stats.currency);
        document.getElementById('min-price').textContent = formatCurrency(stats.min_price, stats.currency);
        document.getElementById('max-price').textContent = formatCurrency(stats.max_price, stats.currency);
        document.getElementById('total-count').textContent = stats.count;
        
        statisticsSection.style.display = 'block';
    }
    
    function displayResults(results) {
        resultsGrid.innerHTML = '';
        
        results.forEach(provider => {
            const card = createResultCard(provider);
            resultsGrid.appendChild(card);
        });
    }
    
    function createResultCard(provider) {
        const template = document.getElementById('result-card-template');
        const card = template.content.cloneNode(true);
        
        // Provider info
        card.querySelector('.provider-name').textContent = provider.name;
        card.querySelector('.provider-specialty').textContent = provider.specialty;
        
        // Rating
        const starsContainer = card.querySelector('.stars');
        starsContainer.innerHTML = generateStars(provider.rating);
        card.querySelector('.rating-text').textContent = `${provider.rating.toFixed(1)} (${provider.total_reviews} avis)`;
        
        // Location
        card.querySelector('.location-text').textContent = provider.location;
        
        // Experience
        const experience = provider.years_of_experience > 0 
            ? `${provider.years_of_experience} ans d'expérience`
            : 'Expérience non spécifiée';
        card.querySelector('.experience-text').textContent = experience;
        
        // Phone
        card.querySelector('.phone-text').textContent = provider.phone || 'Non disponible';
        
        // Price
        card.querySelector('.price-value').textContent = formatCurrency(provider.consultation_fee, provider.currency);
        
        // Book button
        const bookBtn = card.querySelector('.btn-book');
        bookBtn.addEventListener('click', () => {
            window.location.href = `/patient/book-appointment/?doctor_id=${provider.uid}`;
        });
        
        return card;
    }
    
    function generateStars(rating) {
        const fullStars = Math.floor(rating);
        const halfStar = rating % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);
        
        let starsHTML = '';
        
        for (let i = 0; i < fullStars; i++) {
            starsHTML += '<i class="fas fa-star"></i>';
        }
        
        if (halfStar) {
            starsHTML += '<i class="fas fa-star-half-alt"></i>';
        }
        
        for (let i = 0; i < emptyStars; i++) {
            starsHTML += '<i class="far fa-star"></i>';
        }
        
        return starsHTML;
    }
    
    function formatCurrency(amount, currency) {
        const formatted = new Intl.NumberFormat('fr-FR').format(amount);
        return `${formatted} ${currency}`;
    }
    
    function resetFilters() {
        specialtyFilter.value = '';
        locationFilter.value = '';
        sortFilter.value = 'price_asc';
        
        statisticsSection.style.display = 'none';
        noResults.style.display = 'none';
        resultsGrid.innerHTML = '';
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
});
