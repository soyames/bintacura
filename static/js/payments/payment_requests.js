document.addEventListener('DOMContentLoaded', function() {
    const confirmForms = document.querySelectorAll('.inline-form');
    
    confirmForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const action = this.querySelector('input[name="action"]').value;
            
            if (action === 'confirm') {
                const confirmed = confirm('Confirmer que vous avez reçu ce paiement en espèces?');
                if (!confirmed) {
                    e.preventDefault();
                }
            } else if (action === 'cancel') {
                const notes = this.querySelector('textarea[name="notes"]').value;
                if (!notes.trim()) {
                    e.preventDefault();
                    alert('Veuillez indiquer la raison de l\'annulation');
                    return;
                }
                const confirmed = confirm('Êtes-vous sûr de vouloir annuler cette demande?');
                if (!confirmed) {
                    e.preventDefault();
                }
            }
        });
    });
    
    setInterval(function() {
        window.location.reload();
    }, 60000);
});
