document.addEventListener('DOMContentLoaded', function() {
    const surveyForm = document.getElementById('surveyForm');
    
    if (surveyForm) {
        surveyForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitBtn = surveyForm.querySelector('.submit-btn');
            const originalText = submitBtn.textContent;
            
            submitBtn.textContent = 'Submitting...';
            submitBtn.disabled = true;
            
            const formData = new FormData(surveyForm);
            
            fetch(surveyForm.action || window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => {
                if (response.ok) {
                    window.location.href = response.url || '/survey/thank-you/';
                } else {
                    return response.json();
                }
            })
            .then(data => {
                if (data && data.error) {
                    alert('Error: ' + data.error);
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            });
        });
    }
    
    const priceInput = document.getElementById('suggested_price');
    if (priceInput) {
        priceInput.addEventListener('input', function() {
            if (this.value && parseFloat(this.value) < 0) {
                this.value = 0;
            }
        });
    }
});
