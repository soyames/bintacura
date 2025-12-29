// Staff Management JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const addStaffBtn = document.getElementById('addStaffBtn');
    const staffModal = document.getElementById('staffModal');
    const staffForm = document.getElementById('staffForm');
    const closeModalBtns = document.querySelectorAll('.close-modal, .cancel-btn');

    // Open add staff modal
    if (addStaffBtn) {
        addStaffBtn.addEventListener('click', function() {
            document.getElementById('modalTitle').textContent = 'Add New Staff';
            staffForm.reset();
            document.getElementById('staffId').value = '';
            staffModal.classList.add('active');
        });
    }

    // Close modal
    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            staffModal.classList.remove('active');
        });
    });

    // Close modal on outside click
    staffModal.addEventListener('click', function(e) {
        if (e.target === staffModal) {
            staffModal.classList.remove('active');
        }
    });

    // Edit staff
    document.querySelectorAll('.edit-staff').forEach(btn => {
        btn.addEventListener('click', async function() {
            const staffId = this.dataset.id;
            try {
                const response = await fetch(`/api/pharmacy/staff/${staffId}/`);
                const data = await response.json();
                
                document.getElementById('modalTitle').textContent = 'Edit Staff';
                document.getElementById('staffId').value = data.id;
                document.getElementById('firstName').value = data.participant.first_name;
                document.getElementById('lastName').value = data.participant.last_name;
                document.getElementById('phoneNumber').value = data.participant.phone_number;
                document.getElementById('email').value = data.participant.email || '';
                document.getElementById('role').value = data.role;
                document.getElementById('counterNumber').value = data.counter?.id || '';
                
                // Set permissions
                document.querySelector('[name="can_process_orders"]').checked = data.permissions.can_process_orders;
                document.querySelector('[name="can_manage_inventory"]').checked = data.permissions.can_manage_inventory;
                document.querySelector('[name="can_view_reports"]').checked = data.permissions.can_view_reports;
                document.querySelector('[name="can_manage_staff"]').checked = data.permissions.can_manage_staff;
                
                staffModal.classList.add('active');
            } catch (error) {
                console.error('Error loading staff data:', error);
                alert('Failed to load staff data');
            }
        });
    });

    // Toggle staff status
    document.querySelectorAll('.toggle-status').forEach(btn => {
        btn.addEventListener('click', async function() {
            const staffId = this.dataset.id;
            const isActive = this.dataset.active === 'True';
            const action = isActive ? 'deactivate' : 'activate';
            
            if (confirm(`Are you sure you want to ${action} this staff member?`)) {
                try {
                    const response = await fetch(`/api/pharmacy/staff/${staffId}/`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({ is_active: !isActive })
                    });
                    
                    if (response.ok) {
                        location.reload();
                    } else {
                        alert('Failed to update staff status');
                    }
                } catch (error) {
                    console.error('Error updating staff status:', error);
                    alert('Failed to update staff status');
                }
            }
        });
    });

    // Submit staff form
    staffForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const staffId = document.getElementById('staffId').value;
        const formData = {
            first_name: document.getElementById('firstName').value,
            last_name: document.getElementById('lastName').value,
            phone_number: document.getElementById('phoneNumber').value,
            email: document.getElementById('email').value || null,
            role: document.getElementById('role').value,
            counter_id: document.getElementById('counterNumber').value || null,
            permissions: {
                can_process_orders: document.querySelector('[name="can_process_orders"]').checked,
                can_manage_inventory: document.querySelector('[name="can_manage_inventory"]').checked,
                can_view_reports: document.querySelector('[name="can_view_reports"]').checked,
                can_manage_staff: document.querySelector('[name="can_manage_staff"]').checked
            }
        };

        try {
            const url = staffId ? `/api/pharmacy/staff/${staffId}/` : '/api/pharmacy/staff/';
            const method = staffId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                location.reload();
            } else {
                const error = await response.json();
                alert('Error: ' + (error.detail || 'Failed to save staff'));
            }
        } catch (error) {
            console.error('Error saving staff:', error);
            alert('Failed to save staff');
        }
    });
});

// Utility function to get CSRF token
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
