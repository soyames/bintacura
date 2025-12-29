"""
Context processors to inject data into all templates
"""
from decimal import Decimal
from currency_converter.services import CurrencyConverterService


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
