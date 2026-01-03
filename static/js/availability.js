// Availability Calendar Management
let currentWeekStart = new Date();
currentWeekStart.setHours(0, 0, 0, 0);
currentWeekStart.setDate(currentWeekStart.getDate() - currentWeekStart.getDay() + 1);

// Initialize calendar
document.addEventListener('DOMContentLoaded', function() {
    renderWeeklyCalendar();
    loadWeekStats();
});

// Render weekly calendar
function renderWeeklyCalendar() {
    const calendar = document.getElementById('weeklyCalendar');
    if (!calendar) return;
    
    calendar.innerHTML = '';
    
    // Header row
    const headers = ['Heure', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
    headers.forEach((day, index) => {
        const header = document.createElement('div');
        header.className = 'calendar-header';
        if (index > 0) {
            const date = new Date(currentWeekStart);
            date.setDate(date.getDate() + (index - 1));
            const isToday = date.toDateString() === new Date().toDateString();
            if (isToday) header.classList.add('today');
            header.innerHTML = `${day}<br><small>${date.getDate()}/${date.getMonth() + 1}</small>`;
        } else {
            header.textContent = day;
        }
        calendar.appendChild(header);
    });
    
    // Time slots (8h to 19h)
    for (let hour = 8; hour <= 19; hour++) {
        const timeSlot = document.createElement('div');
        timeSlot.className = 'time-slot';
        timeSlot.textContent = `${hour}:00`;
        calendar.appendChild(timeSlot);
        
        // Days
        for (let day = 0; day < 7; day++) {
            const cell = document.createElement('div');
            cell.className = 'calendar-cell';
            cell.dataset.day = day;
            cell.dataset.hour = hour;
            cell.onclick = () => handleSlotClick(day, hour);
            calendar.appendChild(cell);
        }
    }
    
    loadSlots();
}

// Load existing slots from backend
async function loadSlots() {
    try {
        const startDate = currentWeekStart.toISOString().split('T')[0];
        const endDate = new Date(currentWeekStart);
        endDate.setDate(endDate.getDate() + 6);
        
        const response = await fetch(`/api/doctor/availability-slots/?start_date=${startDate}&end_date=${endDate.toISOString().split('T')[0]}`);
        const data = await response.json();
        
        data.results.forEach(slot => {
            const slotDate = new Date(slot.start_time);
            const dayOfWeek = (slotDate.getDay() + 6) % 7;
            const hour = slotDate.getHours();
            
            const cell = document.querySelector(`.calendar-cell[data-day="${dayOfWeek}"][data-hour="${hour}"]`);
            if (cell) {
                if (slot.is_booked) {
                    cell.classList.add('booked');
                    cell.innerHTML = '<div class="slot-info">Réservé</div>';
                } else if (slot.is_blocked) {
                    cell.classList.add('blocked');
                    cell.innerHTML = '<div class="slot-info">Bloqué</div>';
                } else {
                    cell.classList.add('available');
                    cell.innerHTML = '<div class="slot-info">Disponible</div>';
                }
                cell.dataset.slotId = slot.uid;
            }
        });
    } catch (error) {
        console.error('Error loading slots:', error);
    }
}

// Load week statistics
async function loadWeekStats() {
    try {
        const startDate = currentWeekStart.toISOString().split('T')[0];
        const response = await fetch(`/api/doctor/availability-stats/?week_start=${startDate}`);
        const data = await response.json();
        
        document.getElementById('totalSlots').textContent = data.total || 0;
        document.getElementById('bookedSlots').textContent = data.booked || 0;
        document.getElementById('availableSlots').textContent = data.available || 0;
        document.getElementById('blockedSlots').textContent = data.blocked || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Handle slot click
function handleSlotClick(day, hour) {
    const cell = document.querySelector(`.calendar-cell[data-day="${day}"][data-hour="${hour}"]`);
    if (cell.classList.contains('booked') || cell.classList.contains('blocked')) {
        return;
    }
    
    if (cell.dataset.slotId) {
        if (confirm('Voulez-vous supprimer ce créneau?')) {
            deleteSlot(cell.dataset.slotId);
        }
    } else {
        createQuickSlot(day, hour);
    }
}

// Create quick slot
async function createQuickSlot(day, hour) {
    const slotDate = new Date(currentWeekStart);
    slotDate.setDate(slotDate.getDate() + day);
    slotDate.setHours(hour, 0, 0, 0);
    
    const endTime = new Date(slotDate);
    endTime.setMinutes(30);
    
    try {
        const response = await fetch('/api/doctor/availability-slots/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                start_time: slotDate.toISOString(),
                end_time: endTime.toISOString(),
                consultation_type: 'cabinet'
            })
        });
        
        if (response.ok) {
            showNotification('Créneau créé avec succès', 'success');
            renderWeeklyCalendar();
        }
    } catch (error) {
        showNotification('Erreur lors de la création', 'error');
    }
}

// Delete slot
async function deleteSlot(slotId) {
    try {
        const response = await fetch(`/api/doctor/availability-slots/${slotId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (response.ok) {
            showNotification('Créneau supprimé', 'success');
            renderWeeklyCalendar();
        }
    } catch (error) {
        showNotification('Erreur lors de la suppression', 'error');
    }
}

// Navigation
function previousWeek() {
    currentWeekStart.setDate(currentWeekStart.getDate() - 7);
    renderWeeklyCalendar();
    loadWeekStats();
}

function nextWeek() {
    currentWeekStart.setDate(currentWeekStart.getDate() + 7);
    renderWeeklyCalendar();
    loadWeekStats();
}

function goToToday() {
    currentWeekStart = new Date();
    currentWeekStart.setHours(0, 0, 0, 0);
    currentWeekStart.setDate(currentWeekStart.getDate() - currentWeekStart.getDay() + 1);
    renderWeeklyCalendar();
    loadWeekStats();
}

// Modal functions
function openBulkSlotModal() {
    document.getElementById('bulkSlotModal').style.display = 'block';
}

function closeBulkSlotModal() {
    document.getElementById('bulkSlotModal').style.display = 'none';
}

function openBlockTimeModal() {
    document.getElementById('blockTimeModal').style.display = 'block';
}

function closeBlockTimeModal() {
    document.getElementById('blockTimeModal').style.display = 'none';
}

// Bulk slot creation
document.getElementById('bulkSlotForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const days = formData.getAll('days');
    
    const data = {
        start_date: formData.get('start_date'),
        end_date: formData.get('end_date'),
        days: days.map(Number),
        start_time: formData.get('start_time'),
        end_time: formData.get('end_time'),
        slot_duration: parseInt(formData.get('slot_duration')),
        consultation_type: formData.get('consultation_type')
    };
    
    try {
        const response = await fetch('/api/doctor/bulk-create-slots/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`${result.created} créneaux créés avec succès`, 'success');
            closeBulkSlotModal();
            renderWeeklyCalendar();
        }
    } catch (error) {
        showNotification('Erreur lors de la création', 'error');
    }
});

// Block time
document.getElementById('blockTimeForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const data = {
        reason: formData.get('reason'),
        start_datetime: formData.get('start_datetime'),
        end_datetime: formData.get('end_datetime')
    };
    
    try {
        const response = await fetch('/api/doctor/block-time/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            showNotification('Temps bloqué avec succès', 'success');
            closeBlockTimeModal();
            renderWeeklyCalendar();
        }
    } catch (error) {
        showNotification('Erreur lors du blocage', 'error');
    }
});

// Utility functions
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

function showNotification(message, type) {
    // Implement notification display
    alert(message);
}
