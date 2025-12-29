let isEditMode = false;
const originalValues = {};

window.enableEdit = function() {
    isEditMode = true;
    const form = document.getElementById('profileForm');
    const inputs = form.querySelectorAll('input, textarea');
    const formActions = document.getElementById('formActions');
    const editButton = document.getElementById('editButton');

    inputs.forEach(input => {
        if (input.name && input.type !== 'email' && !input.value.includes('@')) {
            originalValues[input.name] = input.value;
            input.disabled = false;
        }
    });

    if (formActions) {
        formActions.classList.add('active');
    }
    if (editButton) {
        editButton.style.display = 'none';
    }
};

window.cancelEdit = function() {
    isEditMode = false;
    const form = document.getElementById('profileForm');
    const inputs = form.querySelectorAll('input, textarea');
    const formActions = document.getElementById('formActions');
    const editButton = document.getElementById('editButton');

    inputs.forEach(input => {
        if (originalValues[input.name]) {
            input.value = originalValues[input.name];
        }
        input.disabled = true;
    });

    if (formActions) {
        formActions.classList.remove('active');
    }
    if (editButton) {
        editButton.style.display = 'flex';
    }
};

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

document.addEventListener('DOMContentLoaded', function() {
    const profileForm = document.getElementById('profileForm');

    if (profileForm) {
        profileForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const data = {
                action: 'update_profile',
                full_name: formData.get('full_name'),
                phone_number: formData.get('phone_number'),
                address: formData.get('address'),
                city: formData.get('city'),
                country: formData.get('country'),
                provider_name: formData.get('provider_name'),
                license_number: formData.get('license_number'),
                registration_number: formData.get('registration_number'),
                provider_email: formData.get('provider_email'),
                provider_phone: formData.get('provider_phone'),
                website: formData.get('website'),
                provider_address: formData.get('provider_address'),
                provider_city: formData.get('provider_city'),
                state: formData.get('state'),
                postal_code: formData.get('postal_code'),
                provider_country: formData.get('provider_country')
            };

            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    alert('Profil mis à jour avec succès!');
                    window.location.reload();
                } else {
                    alert('Erreur: ' + result.error);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Une erreur est survenue lors de la mise à jour du profil');
            }
        });
    }
});
