from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class SubscriptionAccessMiddleware(MiddlewareMixin):
    """
    Middleware to restrict access based on subscription status for hospitals,
    pharmacies, and insurance companies.
    """
    
    # URLs that are always accessible (even with expired subscription)
    ALLOWED_PATHS = [
        '/auth/',
        '/accounts/login/',
        '/accounts/logout/',
        '/api/auth/',
        '/media/',
        '/static/',
        '/subscription/',
        '/activation-code/',
        '/profile/',
        '/settings/',
        '/notifications/',
        '/support/',
        '/admin/',  # Admin panel always accessible
        '/super-admin/',  # Super admin always accessible
    ]
    
    # Features that require active subscription
    RESTRICTED_FEATURES = [
        '/appointments/',
        '/patients/',
        '/staff/',
        '/inventory/',
        '/prescriptions/',
        '/billing/',
        '/claims/',
        '/reports/',
        '/analytics/',
        '/departments/',
        '/equipment/',
        '/beds/',
        '/admissions/',
        '/pharmacy/',
        '/insurance/',
    ]
    
    def process_request(self, request):
        """Check subscription status before processing request"""
        
        # Skip for non-authenticated participants
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        participant = request.user  # request.user is actually Participant model (AUTH_USER_MODEL)
        
        # Check subscription for main organization roles
        if participant.role in ['hospital', 'pharmacy', 'insurance_company']:
            # Main organization - check their subscription
            path = request.path
            if any(path.startswith(allowed) for allowed in self.ALLOWED_PATHS):
                return None
            
            is_restricted = any(path.startswith(restricted) for restricted in self.RESTRICTED_FEATURES)
            
            if not is_restricted:
                return None
            
            if not participant.has_valid_subscription():
                return self._handle_expired_subscription(request, participant, is_staff=False)
        
        # Check subscription for staff roles (cascade from parent organization)
        elif participant.role in ['hospital_staff', 'pharmacy_staff', 'insurance_company_staff']:
            # Staff member - check parent organization's subscription
            staff_profile = self._get_staff_profile(participant)
            
            if not staff_profile:
                return None  # No staff profile found, allow access
            
            path = request.path
            if any(path.startswith(allowed) for allowed in self.ALLOWED_PATHS):
                return None
            
            is_restricted = any(path.startswith(restricted) for restricted in self.RESTRICTED_FEATURES)
            
            if not is_restricted:
                return None
            
            # Check parent organization's subscription
            if not staff_profile.has_parent_subscription_access():
                return self._handle_expired_subscription(request, participant, is_staff=True)
        
        return None
    
    def _get_staff_profile(self, participant):
        """Get staff profile based on role to check parent organization subscription"""
        try:
            if participant.role == 'hospital_staff':
                from hospital.models import HospitalStaff
                return HospitalStaff.objects.select_related('hospital').get(staff_participant=participant)
            elif participant.role == 'pharmacy_staff':
                from pharmacy.models import PharmacyStaff
                return PharmacyStaff.objects.select_related('pharmacy').get(staff_participant=participant)
            elif participant.role == 'insurance_company_staff':
                from insurance.models import InsuranceStaff
                return InsuranceStaff.objects.select_related('insurance_company').get(staff_participant=participant)
        except Exception as e:
            # Staff profile not found or error occurred
            pass
        return None
    
    def _handle_expired_subscription(self, request, participant, is_staff=False):
        """Handle requests from participants with expired subscriptions"""
        
        # Get subscription status
        if is_staff:
            staff_profile = self._get_staff_profile(participant)
            status = staff_profile.get_parent_subscription_status() if staff_profile else 'unknown'
            message = self._get_staff_message(status)
        else:
            status = participant.get_subscription_status()
            message = self._get_organization_message(status)
        
        # Return JSON for API requests
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'subscription_required',
                'message': message,
                'status': status,
                'is_staff_cascade': is_staff,
                'subscription_url': '/subscription/renew/' if not is_staff else '/subscription/status/',
            }, status=402)  # 402 Payment Required
        
        # Redirect to subscription page for web requests
        request.session['subscription_warning'] = message
        return redirect('/subscription/status/')
    
    def _get_organization_message(self, status):
        """Get message for organization account"""
        messages = {
            'expired': 'Votre abonnement a expiré. Veuillez renouveler pour continuer à utiliser toutes les fonctionnalités.',
            'grace_period': 'Votre abonnement a expiré. Vous êtes en période de grâce (30 jours). Veuillez renouveler rapidement.',
            'expiring_soon': 'Votre abonnement expire bientôt. Renouvelez-le pour éviter toute interruption de service.',
            'pending_activation': 'Votre compte nécessite l\'activation. Veuillez vérifier votre email pour le code d\'activation.',
            'pending_verification': 'Votre compte est en attente de vérification par notre équipe.',
        }
        return messages.get(status, 'Accès limité. Veuillez vérifier votre statut d\'abonnement.')
    
    def _get_staff_message(self, parent_status):
        """Get message for staff member"""
        if parent_status == 'expired':
            return 'L\'abonnement de votre organisation a expiré. Fonctionnalités limitées jusqu\'au renouvellement.'
        elif parent_status == 'grace_period':
            return 'L\'abonnement de votre organisation est en période de grâce. Contactez votre administrateur.'
        return 'Accès limité. L\'abonnement de votre organisation doit être renouvelé.'
