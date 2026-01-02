"""
Context processors to inject data into all templates
"""
from decimal import Decimal
from django.conf import settings
from currency_converter.services import CurrencyConverterService


def platform_settings(request):
    """Make platform settings available to all templates"""
    default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'XOF')
    default_fee_setting = f'DEFAULT_CONSULTATION_FEE_{default_currency}'
    default_fee = getattr(settings, default_fee_setting, 3500)
    
    return {
        'DEFAULT_CURRENCY': default_currency,
        'DEFAULT_CONSULTATION_FEE': default_fee,
        'CONTACT_EMAIL': getattr(settings, 'CONTACT_EMAIL', 'contacts@bintacura.org'),
        'NO_REPLY_EMAIL': getattr(settings, 'NO_REPLY_EMAIL', 'no-reply@bintacura.org'),
    }


def currency_context(request):
    """
    Inject currency-related context into all templates
    Provides participant's preferred currency and conversion utilities
    """
    context = {
        'participant_currency': 'XOF',  # Default
        'currency_symbol': 'FCFA',
        'currency_service': CurrencyConverterService,
        'currency_converter': CurrencyConverterService,
    }

    if request.user.is_authenticated:
        try:
            # Get participant's currency using phone number as PRIMARY source
            from core.phone_currency_mapper import PhoneCurrencyMapper
            participant_currency = PhoneCurrencyMapper.get_participant_currency(request.user)

            context['participant_currency'] = participant_currency

            # Get currency symbol
            currencies = CurrencyConverterService.get_supported_currencies()
            for curr in currencies:
                if curr['code'] == participant_currency:
                    context['currency_symbol'] = curr['symbol']
                    break

        except Exception as e:
            # Fallback to defaults if any error
            pass

    return context


def wallet_context(request):
    """
    Inject wallet balance into all templates for authenticated users
    """
    context = {
        'wallet_balance': Decimal('0.00'),
        'wallet_currency': 'XOF',
        'wallet_available': False,
    }

    if request.user.is_authenticated:
        try:
            from core.models import Wallet
            wallet = Wallet.objects.get(participant=request.user)
            context['wallet_balance'] = wallet.balance
            context['wallet_currency'] = wallet.currency
            context['wallet_available'] = wallet.status == 'active'
        except Wallet.DoesNotExist:
            pass
        except Exception:
            pass

    return context


def subscription_context(request):
    """
    Inject subscription status and activation code info into templates
    for hospitals, pharmacies, and insurance companies
    """
    context = {
        'has_subscription_model': False,
        'subscription_status': 'not_applicable',
        'has_valid_subscription': True,
        'identifier': None,
        'activation_code': None,
        'activation_expires_at': None,
        'days_until_expiry': None,
        'show_renewal_warning': False,
        'show_expiry_alert': False,
        'is_in_grace_period': False,
    }
    
    if request.user.is_authenticated:
        try:
            participant = request.user  # request.user is Participant model (AUTH_USER_MODEL)
            
            # Check subscription for main organization roles
            if participant.role in ['hospital', 'pharmacy', 'insurance_company']:
                subscription_data = participant.get_subscription_data()
                
                if subscription_data:
                    context['has_subscription_model'] = True
                    context['subscription_status'] = participant.get_subscription_status()
                    context['has_valid_subscription'] = participant.has_valid_subscription()
                    context['identifier'] = subscription_data.identifier
                    context['activation_code'] = subscription_data.activation_code
                    context['activation_expires_at'] = subscription_data.activation_code_expires_at
                    context['days_until_expiry'] = subscription_data.days_until_expiry()
                    
                    # Set warning flags
                    days_left = subscription_data.days_until_expiry()
                    if days_left is not None:
                        context['show_renewal_warning'] = days_left <= 30 and days_left > 0
                        context['show_expiry_alert'] = days_left <= 7 and days_left > 0
                    
                    context['is_in_grace_period'] = context['subscription_status'] == 'grace_period'
            
            # Check subscription for staff roles (cascade from parent organization)
            elif participant.role in ['hospital_staff', 'pharmacy_staff', 'insurance_company_staff']:
                staff_profile = None
                
                # Get staff profile
                if participant.role == 'hospital_staff':
                    from hospital.models import HospitalStaff
                    try:
                        staff_profile = HospitalStaff.objects.select_related('hospital').get(staff_participant=participant)
                    except HospitalStaff.DoesNotExist:
                        pass
                elif participant.role == 'pharmacy_staff':
                    from pharmacy.models import PharmacyStaff
                    try:
                        staff_profile = PharmacyStaff.objects.select_related('pharmacy').get(staff_participant=participant)
                    except PharmacyStaff.DoesNotExist:
                        pass
                elif participant.role == 'insurance_company_staff':
                    from insurance.models import InsuranceStaff
                    try:
                        staff_profile = InsuranceStaff.objects.select_related('insurance_company').get(staff_participant=participant)
                    except InsuranceStaff.DoesNotExist:
                        pass
                
                if staff_profile:
                    context['is_staff_member'] = True
                    context['has_subscription_model'] = True
                    context['subscription_status'] = staff_profile.get_parent_subscription_status()
                    context['has_valid_subscription'] = staff_profile.has_parent_subscription_access()
                    context['parent_organization_name'] = staff_profile.get_parent_organization_name() if hasattr(staff_profile, 'get_parent_organization_name') else 'Organization'
                    
                    # Get parent's subscription data if available
                    parent_participant = None
                    if hasattr(staff_profile, 'hospital'):
                        parent_participant = staff_profile.hospital
                    elif hasattr(staff_profile, 'pharmacy'):
                        parent_participant = staff_profile.pharmacy
                    elif hasattr(staff_profile, 'insurance_company'):
                        parent_participant = staff_profile.insurance_company
                    
                    if parent_participant:
                        subscription_data = parent_participant.get_subscription_data()
                        if subscription_data:
                            context['activation_expires_at'] = subscription_data.activation_code_expires_at
                            context['days_until_expiry'] = subscription_data.days_until_expiry()
                            
                            days_left = subscription_data.days_until_expiry()
                            if days_left is not None:
                                context['show_renewal_warning'] = days_left <= 30 and days_left > 0
                                context['show_expiry_alert'] = days_left <= 7 and days_left > 0
                            
                            context['is_in_grace_period'] = context['subscription_status'] == 'grace_period'
        
        except Exception:
            pass
    
    return context
