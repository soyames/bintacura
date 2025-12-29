document.addEventListener('DOMContentLoaded', function() {
    const countryCodeSelect = document.getElementById('country_code');
    const phonePrefixSpan = document.getElementById('phone_prefix');
    const roleSelect = document.querySelector('select[name="role"]');
    const firstNameInput = document.querySelector('input[name="first_name"]');

    // Handle country code phone prefix update
    if (countryCodeSelect && phonePrefixSpan) {
        countryCodeSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const phoneCode = selectedOption.getAttribute('data-code');

            if (phoneCode) {
                phonePrefixSpan.textContent = phoneCode;
            } else {
                phonePrefixSpan.textContent = '+---';
            }
        });
    }

    // Handle first_name field enable/disable based on role selection
    if (roleSelect && firstNameInput) {
        roleSelect.addEventListener('change', function() {
            const selectedRole = this.value;
            const organizationRoles = ['pharmacy', 'insurance_company', 'hospital'];

            if (organizationRoles.includes(selectedRole)) {
                // Disable first_name for organization accounts
                firstNameInput.disabled = true;
                firstNameInput.required = false;
                firstNameInput.value = '';
                firstNameInput.placeholder = 'Non requis pour les organisations';
                firstNameInput.style.opacity = '0.5';
                firstNameInput.style.cursor = 'not-allowed';
            } else {
                // Enable first_name for individual accounts (patient, doctor)
                firstNameInput.disabled = false;
                firstNameInput.required = true;
                firstNameInput.placeholder = 'Prénom(s)';
                firstNameInput.style.opacity = '1';
                firstNameInput.style.cursor = 'text';
            }
        });
    }
});
