// Appointment Booking with Queue Management and Payment Integration
// BINTACURA Platform

// BINTACURA Appointment Booking System
// Version: 2.0 - Updated for core API (2025-12-09)
console.log('📋 Loading appointment_booking.js v2.0 (Core API)');

class AppointmentBooking {
    constructor() {
        const platformSettings = window.BINTACURA_SETTINGS || {};
        this.currentStep = 1;
        this.selectedDoctor = null;
        this.selectedHospital = null;
        this.selectedServices = [];
        this.selectedDate = null;
        this.selectedTime = null;
        this.consultationFee = platformSettings.DEFAULT_CONSULTATION_FEE || 3500;
        this.localConsultationFee = 0;
        this.localCurrency = platformSettings.DEFAULT_CURRENCY || 'XOF';
        this.totalAmount = 0;
        this.bookingType = 'doctor'; // 'doctor' or 'hospital'
    }

    async init() {
        console.log('🚀 AppointmentBooking.init() called');
        console.log('Booking type:', this.bookingType);
        console.log('doctorGrid element:', document.getElementById('doctorGrid'));
        
        await this.loadConsultationFee();
        this.setupEventListeners();
        this.setMinDate();
        
        // Always try to load doctors if the grid exists
        const doctorGrid = document.getElementById('doctorGrid');
        if (doctorGrid) {
            console.log('Doctor grid found, loading doctors...');
            await this.loadDoctors();
        } else {
            console.log('Doctor grid not found, skipping doctor load');
        }
    }

    async loadConsultationFee() {
        try {
            const response = await fetch('/api/v1/core/system/consultation-fee/');
            const data = await response.json();
            
            if (data.fee_eur || data.base_fee_eur) {
                this.consultationFee = parseFloat(data.fee_eur || data.base_fee_eur);
            }
            
            if ((data.fee_local || data.local_fee) && data.currency) {
                this.localConsultationFee = parseFloat(data.fee_local || data.local_fee);
                this.localCurrency = data.currency;
            }
            
            this.updateFeeDisplay();
        } catch (error) {
            console.error('Error loading consultation fee:', error);
        }
    }

    updateFeeDisplay() {
        const feeElement = document.getElementById('consultationFee');
        if (feeElement) {
            const currencySymbol = this.getCurrencySymbol(this.localCurrency);
            feeElement.textContent = `${currencySymbol}${this.formatAmount(this.localConsultationFee)}`;
        }
    }

    setupEventListeners() {
        const appointmentDate = document.getElementById('appointmentDate');
        if (appointmentDate) {
            appointmentDate.addEventListener('change', () => this.loadTimeSlots());
        }

        const serviceSelect = document.getElementById('additionalServices');
        if (serviceSelect) {
            serviceSelect.addEventListener('change', (e) => this.handleServiceSelection(e));
        }

        document.addEventListener('click', (e) => {
            const doctorCard = e.target.closest('.doctor-card[data-doctor-id]');
            if (doctorCard) {
                const doctorId = doctorCard.getAttribute('data-doctor-id');
                this.selectDoctor(doctorId);
                return;
            }

            const hospitalCard = e.target.closest('.hospital-card[data-hospital-id]');
            if (hospitalCard) {
                const hospitalId = hospitalCard.getAttribute('data-hospital-id');
                this.selectHospital(hospitalId);
                return;
            }
        });
    }

    setMinDate() {
        const dateInput = document.getElementById('appointmentDate');
        if (dateInput) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            dateInput.min = tomorrow.toISOString().split('T')[0];
        }
    }

    async loadDoctors(specialty = '') {
        const grid = document.getElementById('doctorGrid');
        if (!grid) {
            console.error('Doctor grid element not found!');
            return;
        }

        grid.innerHTML = '<p class="loading-message">🔄 Chargement des médecins...</p>';

        try {
            let url = '/api/v1/doctor/data/';
            if (specialty) {
                url += `?specialty=${specialty}`;
            }

            console.log('Fetching doctors from:', url);
            const response = await fetch(url);
            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers.get('content-type'));
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Response error:', errorText);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received data:', data);
            console.log('Data type:', typeof data);
            console.log('Has results:', data.results ? 'yes' : 'no');
            console.log('Results length:', data.results ? data.results.length : 'N/A');
            
            const doctors = data.results || data;
            console.log('Doctors array:', doctors);
            console.log('Doctors count:', Array.isArray(doctors) ? doctors.length : 'not an array');

            if (!doctors || !Array.isArray(doctors) || doctors.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state">
                        <div style="font-size: 48px; margin-bottom: 10px;">👨‍⚕️</div>
                        <p>Aucun médecin disponible</p>
                        <p style="font-size: 12px; color: #999;">Veuillez vérifier votre connexion ou réessayer plus tard</p>
                    </div>
                `;
                return;
            }

            console.log('Creating doctor cards for', doctors.length, 'doctors');
            const cards = doctors.map(doctor => this.createDoctorCard(doctor)).join('');
            console.log('Cards HTML length:', cards.length);
            grid.innerHTML = cards;
            console.log('Doctor cards rendered successfully');
        } catch (error) {
            console.error('Error loading doctors:', error);
            console.error('Error stack:', error.stack);
            grid.innerHTML = `
                <div class="error-message" style="text-align: center; padding: 40px;">
                    <div style="font-size: 48px;">⚠️</div>
                    <p>Erreur de chargement des médecins</p>
                    <p style="font-size: 14px; color: #666; margin: 10px 0;">${error.message}</p>
                    <button onclick="appointmentBooking.loadDoctors()" class="btn-retry" style="margin-top: 15px; padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">🔄 Réessayer</button>
                </div>
            `;
        }
    }

    async loadHospitals(search = '') {
        const grid = document.getElementById('hospitalGrid');
        if (!grid) return;

        grid.innerHTML = '<p class="loading-message">🔄 Chargement des hôpitaux...</p>';

        try {
            let url = '/api/v1/core/participants/?role=hospital';
            if (search) {
                url += `&search=${encodeURIComponent(search)}`;
            }

            const response = await fetch(url);
            const data = await response.json();
            const hospitals = data.results || data;

            if (!hospitals || hospitals.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state">
                        <div style="font-size: 48px; margin-bottom: 10px;">🏥</div>
                        <p>Aucun hôpital disponible</p>
                    </div>
                `;
                return;
            }

            grid.innerHTML = hospitals.map(hospital => this.createHospitalCard(hospital)).join('');
        } catch (error) {
            console.error('Error loading hospitals:', error);
            grid.innerHTML = `
                <div class="error-message">
                    <div style="font-size: 48px;">⚠️</div>
                    <p>Erreur de chargement</p>
                    <button onclick="appointmentBooking.loadHospitals()" class="btn-retry">🔄 Réessayer</button>
                </div>
            `;
        }
    }

    createDoctorCard(doctor) {
        const currencySymbol = this.getCurrencySymbol(this.localCurrency);
        const hasServices = doctor.services && doctor.services.length > 0;
        const doctorName = doctor.participant ? doctor.participant.full_name : 'Médecin';
        const doctorId = doctor.participant ? doctor.participant.uid : doctor.id;
        const specialty = doctor.specialization_display || doctor.specialization || 'Médecin Généraliste';
        const doctorFee = doctor.consultation_fee || 0;
        const consultationFee = doctorFee > 0 ? doctorFee : this.localConsultationFee || 0;

        // Calculate rating display
        const rating = parseFloat(doctor.rating) || 0;
        const totalReviews = parseInt(doctor.total_reviews) || 0;
        const fullStars = Math.floor(rating);
        const starsDisplay = '⭐'.repeat(fullStars);

        let ratingText = '';
        if (totalReviews > 0) {
            ratingText = `${starsDisplay} ${rating.toFixed(1)}/5 <span style="font-size: 0.9em; color: #7f8c8d;">· ${totalReviews} avis</span>`;
        } else {
            ratingText = '<span style="color: #7f8c8d; font-size: 0.9em;">Nouveau médecin</span>';
        }

        return `
            <div class="doctor-card" data-doctor-id="${doctorId}" data-doctor-name="Dr. ${doctorName}">
                <div class="doctor-avatar">👨‍⚕️</div>
                <div class="doctor-name">Dr. ${doctorName}</div>
                <div class="doctor-specialty">${specialty}</div>
                <div class="doctor-fee">Consultation: ${currencySymbol}${this.formatAmount(consultationFee)}</div>
                ${hasServices ? `<div class="doctor-services">${doctor.services.length} service(s) disponible(s)</div>` : ''}
                <div class="doctor-rating">${ratingText}</div>
            </div>
        `;
    }

    createHospitalCard(hospital) {
        const currencySymbol = this.getCurrencySymbol(this.localCurrency);
        const hospitalFee = hospital.consultation_fee || 0;
        const consultationFee = hospitalFee > 0 ? hospitalFee : this.localConsultationFee || 0;
        
        // Calculate rating display
        const rating = parseFloat(hospital.rating) || 0;
        const totalReviews = parseInt(hospital.total_reviews) || 0;
        const fullStars = Math.floor(rating);
        const starsDisplay = '⭐'.repeat(fullStars);

        let ratingText = '';
        if (totalReviews > 0) {
            ratingText = `${starsDisplay} ${rating.toFixed(1)}/5 <span style="font-size: 0.9em; color: #7f8c8d;">· ${totalReviews} avis</span>`;
        } else {
            ratingText = '<span style="color: #7f8c8d; font-size: 0.9em;">Nouvel hôpital</span>';
        }

        return `
            <div class="hospital-card" data-hospital-id="${hospital.participant_id}" data-hospital-name="${hospital.provider_name}">
                <div class="hospital-avatar">🏥</div>
                <div class="hospital-name">${hospital.provider_name}</div>
                <div class="hospital-address">${hospital.address || ''}</div>
                <div class="hospital-phone">${hospital.phone_number || ''}</div>
                <div class="hospital-fee">Consultation: ${currencySymbol}${this.formatAmount(consultationFee)}</div>
                <div class="hospital-rating">${ratingText}</div>
            </div>
        `;
    }

    async selectDoctor(doctorId) {
        this.selectedDoctor = doctorId;
        
        const doctorCard = document.querySelector(`.doctor-card[data-doctor-id="${doctorId}"]`);
        if (doctorCard) {
            this.selectedDoctorName = doctorCard.getAttribute('data-doctor-name');
            
            document.querySelectorAll('.doctor-card').forEach(card => card.classList.remove('selected'));
            doctorCard.classList.add('selected');
        }
        
        this.bookingType = 'doctor';

        await this.loadParticipantServices(doctorId);
        
        this.calculateTotalAmount();
        
        this.enableNextStep();
    }

    async selectHospital(hospitalId) {
        this.selectedHospital = hospitalId;
        
        const hospitalCard = document.querySelector(`.hospital-card[data-hospital-id="${hospitalId}"]`);
        if (hospitalCard) {
            this.selectedHospitalName = hospitalCard.getAttribute('data-hospital-name');
            
            document.querySelectorAll('.hospital-card').forEach(card => card.classList.remove('selected'));
            hospitalCard.classList.add('selected');
        }
        
        this.bookingType = 'hospital';

        await this.loadParticipantServices(hospitalId);
        
        this.calculateTotalAmount();
        
        this.enableNextStep();
    }

    async loadParticipantServices(participantId) {
        try {
            const response = await fetch(`/api/v1/core/participants/${participantId}/services/`);
            const data = await response.json();
            
            const servicesSelect = document.getElementById('additionalServices');
            if (servicesSelect && data.success && data.services && data.services.length > 0) {
                servicesSelect.innerHTML = '<option value="">Aucun service supplémentaire</option>' +
                    data.services.map(service => 
                        `<option value="${service.id}" data-price="${service.price}" data-currency="${service.currency}">
                            ${service.name} - ${this.getCurrencySymbol(service.currency)}${service.price}
                        </option>`
                    ).join('');
                document.getElementById('servicesSection').style.display = 'block';
            } else {
                document.getElementById('servicesSection').style.display = 'none';
            }
        } catch (error) {
            console.error('Error loading participant services:', error);
            document.getElementById('servicesSection').style.display = 'none';
        }
    }

    handleServiceSelection(event) {
        const selectedOptions = Array.from(event.target.selectedOptions);
        this.selectedServices = selectedOptions.map(option => ({
            id: option.value,
            price: parseFloat(option.getAttribute('data-price')),
            currency: option.getAttribute('data-currency')
        }));
        
        this.calculateTotalAmount();
    }

    async calculateTotalAmount() {
        let total = this.localConsultationFee;
        
        for (const service of this.selectedServices) {
            if (service.currency !== this.localCurrency) {
                // Convert to local currency
                const converted = await this.convertCurrency(service.price, service.currency, this.localCurrency);
                total += converted;
            } else {
                total += service.price;
            }
        }
        
        this.totalAmount = total;
        this.updateTotalDisplay();
    }

    async convertCurrency(amount, fromCurrency, toCurrency) {
        try {
            const response = await fetch('/api/v1/core/system/convert-currency/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    amount: amount,
                    from_currency: fromCurrency,
                    to_currency: toCurrency
                })
            });
            
            const data = await response.json();
            return data.converted_amount || amount;
        } catch (error) {
            console.error('Error converting currency:', error);
            return amount;
        }
    }

    updateTotalDisplay() {
        const totalElement = document.getElementById('totalAmount');
        if (totalElement) {
            const currencySymbol = this.getCurrencySymbol(this.localCurrency);
            totalElement.textContent = `${currencySymbol}${this.formatAmount(this.totalAmount)}`;
        }
    }

    async loadTimeSlots() {
        const slotsContainer = document.getElementById('timeSlots');
        if (!slotsContainer) return;

        const participantId = this.selectedDoctor || this.selectedHospital;
        const selectedDate = document.getElementById('appointmentDate').value;

        if (!participantId || !selectedDate) {
            slotsContainer.innerHTML = '<p class="info-message">Sélectionnez un médecin/hôpital et une date</p>';
            return;
        }

        slotsContainer.innerHTML = '<p class="loading-message">🔄 Chargement des créneaux...</p>';

        try {
            const participantType = this.selectedDoctor ? 'doctor_id' : 'hospital_id';
            const response = await fetch(`/patient/api/available-slots/?${participantType}=${participantId}&date=${selectedDate}`);
            const data = await response.json();

            if (!data.success || !data.slots || data.slots.length === 0) {
                slotsContainer.innerHTML = `
                    <div class="empty-state">
                        <div style="font-size: 32px;">📅</div>
                        <p>${data.message || 'Aucun créneau disponible'}</p>
                    </div>
                `;
                return;
            }

            const availableSlots = data.slots.filter(slot => slot.available);
            if (availableSlots.length === 0) {
                slotsContainer.innerHTML = `
                    <div class="empty-state">
                        <div style="font-size: 32px;">📅</div>
                        <p>Tous les créneaux sont réservés pour cette date</p>
                    </div>
                `;
                return;
            }

            slotsContainer.innerHTML = availableSlots.map(slot => 
                `<div class="time-slot" onclick="appointmentBooking.selectTime('${slot.time}')">${slot.time}</div>`
            ).join('');
        } catch (error) {
            console.error('Error loading time slots:', error);
            slotsContainer.innerHTML = '<p class="error-message">Erreur de chargement des créneaux</p>';
        }
    }

    selectTime(time) {
        this.selectedTime = time;
        
        // Find and mark the selected time slot
        document.querySelectorAll('.time-slot').forEach(slot => {
            slot.classList.remove('selected');
            if (slot.textContent.trim() === time) {
                slot.classList.add('selected');
            }
        });
        
        // Enable next step button if we're on step 2
        if (this.currentStep === 2) {
            this.enableNextStep();
        }
    }

    async submitBooking() {
        if (!this.validateBooking()) {
            return;
        }

        // Get payment method first
        const paymentMethod = await this.showPaymentMethodDialog();
        
        if (!paymentMethod) {
            return; // User cancelled
        }

        const bookingData = {
            participant_id: this.selectedDoctor || this.selectedHospital,
            appointment_date: document.getElementById('appointmentDate').value,
            appointment_time: this.selectedTime,
            type: 'consultation',
            reason: document.querySelector('[name="reason"]').value,
            symptoms: document.querySelector('[name="notes"]').value || '',
            payment_method: paymentMethod === 'cash' ? 'onsite' : 'online',
            additional_service_ids: this.selectedServices.map(s => s.id).filter(id => id)
        };

        try {
            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '⏳ Réservation en cours...';
            }

            // Use queue management API endpoint for booking with payment and queue
            const response = await fetch('/api/v1/queue/book-appointment/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify(bookingData)
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // If online payment, redirect to FedaPay
                if (paymentMethod === 'online' && data.payment_url) {
                    alert(`✅ Rendez-vous créé!\n\nVous allez être redirigé vers la page de paiement FedaPay.`);
                    // Redirect to FedaPay payment page
                    window.location.href = data.payment_url;
                    return;
                }
                
                // For cash payment, show confirmation
                const queueInfo = data.queue_number ? 
                    `\n\nNuméro de file: ${data.queue_number}\nPosition: ${data.queue_position ? data.queue_position.people_ahead + ' personne(s) devant vous' : ''}\nTemps d'attente estimé: ${data.estimated_wait_time || 0} minutes` : '';
                
                const receiptMsg = data.receipt_download_url ? 
                    `\n\nReceipt: ${data.receipt_number}\nUn reçu sera téléchargé automatiquement.` : '';
                
                alert(`✅ Rendez-vous confirmé!${queueInfo}\n\nMéthode de paiement: Sur place (Cash)${receiptMsg}`);
                
                if (data.receipt_download_url) {
                    window.open(data.receipt_download_url, '_blank');
                    setTimeout(() => {
                        window.location.href = '/patient/my-appointments/';
                    }, 2000);
                } else {
                    window.location.href = '/patient/my-appointments/';
                }
            } else {
                const errorMsg = data.error || 'Impossible de créer le rendez-vous';
                
                // Check for insufficient balance
                if (errorMsg.includes('Insufficient') || errorMsg.includes('insuffisant')) {
                    if (confirm('Solde insuffisant. Voulez-vous recharger votre wallet?')) {
                        window.location.href = '/patient/wallet/';
                        return;
                    }
                }
                
                alert('Erreur: ' + errorMsg);
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Confirmer le rendez-vous';
                }
            }
        } catch (error) {
            console.error('Error submitting booking:', error);
            alert('Erreur de connexion. Veuillez réessayer.');
            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Confirmer le rendez-vous';
            }
        }
    }

    showPaymentMethodDialog() {
        return new Promise((resolve) => {
            const dialog = document.createElement('div');
            dialog.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;
            
            dialog.innerHTML = `
                <div style="background: white; padding: 30px; border-radius: 15px; max-width: 400px; width: 90%; position: relative;">
                    <button onclick="this.closest('div').parentElement.parentElement.remove(); window.paymentChoice(null);" 
                            style="position: absolute; top: 10px; right: 10px; width: 35px; height: 35px; border: none; background: #f5f5f5; color: #666; border-radius: 50%; cursor: pointer; font-size: 20px; line-height: 1; display: flex; align-items: center; justify-content: center; transition: all 0.2s;"
                            onmouseover="this.style.background='#e0e0e0'" 
                            onmouseout="this.style.background='#f5f5f5'"
                            title="Fermer">
                        ×
                    </button>
                    <h3 style="margin-bottom: 15px; color: #2d3748; padding-right: 40px;">Choisir le mode de paiement</h3>
                    
                    <!-- Fee Information Notice -->
                    <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 13px; color: #856404;">
                        <strong>ℹ️ Informations sur les frais :</strong>
                        <ul style="margin: 8px 0 0 0; padding-left: 20px;">
                            <li>Frais de plateforme: <strong>1% du montant</strong></li>
                            <li>Paiement en ligne: <strong>Des frais de passerelle supplémentaires peuvent s'appliquer</strong></li>
                            <li>Paiement sur place: <strong>Aucun frais supplémentaire</strong></li>
                        </ul>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; gap: 15px;">
                        <button onclick="this.closest('div').parentElement.parentElement.remove(); window.paymentChoice('online');" 
                                style="padding: 15px; border: 2px solid #4CAF50; background: #4CAF50; color: white; border-radius: 8px; cursor: pointer; font-size: 16px; transition: all 0.2s;"
                                onmouseover="this.style.background='#45a049'" 
                                onmouseout="this.style.background='#4CAF50'">
                            💳 Payer En ligne (avec FedaPay)
                        </button>
                        <button onclick="this.closest('div').parentElement.parentElement.remove(); window.paymentChoice('cash');" 
                                style="padding: 15px; border: 2px solid #2196F3; background: #2196F3; color: white; border-radius: 8px; cursor: pointer; font-size: 16px; transition: all 0.2s;"
                                onmouseover="this.style.background='#0b7dda'" 
                                onmouseout="this.style.background='#2196F3'">
                            💵 Payer sur place (Cash)
                        </button>
                    </div>
                </div>
            `;
            
            window.paymentChoice = (choice) => {
                resolve(choice);
                delete window.paymentChoice;
            };
            
            document.body.appendChild(dialog);
        });
    }

    validateBooking() {
        if (!this.selectedDoctor && !this.selectedHospital) {
            alert('Veuillez sélectionner un médecin ou un hôpital');
            return false;
        }

        if (!this.selectedTime) {
            alert('Veuillez sélectionner un créneau horaire');
            return false;
        }

        const date = document.getElementById('appointmentDate').value;
        if (!date) {
            alert('Veuillez sélectionner une date');
            return false;
        }

        const reason = document.querySelector('[name="reason"]').value;
        if (!reason) {
            alert('Veuillez indiquer la raison de la consultation');
            return false;
        }

        return true;
    }

    formatAmount(amount) {
        return amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    }

    getCurrencySymbol(currency) {
        const symbols = {
            'EUR': '€',
            'USD': '$',
            'GBP': '£',
            'XAF': 'CFA',
            'XOF': 'CFA',
            'NGN': '₦',
            'GHS': '₵'
        };
        return symbols[currency] || currency + ' ';
    }

    getCookie(name) {
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

    enableNextStep() {
        const nextBtn = document.querySelector('.btn-next');
        if (nextBtn) {
            nextBtn.disabled = false;
            nextBtn.classList.remove('disabled');
        }
    }

    nextStep() {
        if (this.currentStep === 1 && !this.selectedDoctor && !this.selectedHospital) {
            alert('Veuillez sélectionner un prestataire');
            return;
        }

        if (this.currentStep === 2) {
            const date = document.getElementById('appointmentDate').value;
            if (!date || !this.selectedTime) {
                alert('Veuillez sélectionner une date et un créneau horaire');
                return;
            }
        }

        this.currentStep++;
        this.updateStepVisibility();
        this.updateNavigationButtons();
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStepVisibility();
            this.updateNavigationButtons();
        }
    }

    updateNavigationButtons() {
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const submitBtn = document.getElementById('submitBtn');

        // Show/hide previous button
        if (prevBtn) {
            prevBtn.style.display = this.currentStep > 1 ? 'inline-block' : 'none';
        }

        // Show next or submit button
        if (this.currentStep === 3) {
            if (nextBtn) nextBtn.style.display = 'none';
            if (submitBtn) submitBtn.style.display = 'inline-block';
        } else {
            if (nextBtn) nextBtn.style.display = 'inline-block';
            if (submitBtn) submitBtn.style.display = 'none';
        }
    }

    updateStepVisibility() {
        // Hide all steps
        document.querySelectorAll('.booking-step').forEach(step => {
            step.style.display = 'none';
            step.classList.remove('active');
        });

        // Show current step
        const currentStepElement = document.querySelector(`.booking-step[data-step="${this.currentStep}"]`);
        if (currentStepElement) {
            currentStepElement.style.display = 'block';
            currentStepElement.classList.add('active');
        }

        // Update step indicators
        document.querySelectorAll('.step').forEach((indicator, index) => {
            if (index + 1 < this.currentStep) {
                indicator.classList.add('completed');
                indicator.classList.remove('active');
            } else if (index + 1 === this.currentStep) {
                indicator.classList.add('active');
                indicator.classList.remove('completed');
            } else {
                indicator.classList.remove('active', 'completed');
            }
        });
    }
}

// Initialize appointment booking
const appointmentBooking = new AppointmentBooking();

// Auto-init on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM loaded, initializing appointment booking...');
        appointmentBooking.init();
    });
} else {
    console.log('DOM already loaded, initializing appointment booking...');
    appointmentBooking.init();
}

