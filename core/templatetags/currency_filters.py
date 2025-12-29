from django import template
from decimal import Decimal
from currency_converter.services import CurrencyConverterService

register = template.Library()

@register.filter(name='convert_currency')
def convert_currency(amount, currencies):
    if not amount or not currencies:
        return amount

    try:
        from_currency, to_currency = currencies.split(':')
        amount_decimal = Decimal(str(amount))
        converted = CurrencyConverterService.convert(amount_decimal, from_currency.strip(), to_currency.strip())
        return converted
    except Exception:
        return amount

@register.filter(name='format_currency')
def format_currency(amount, currency='EUR'):
    if amount is None:
        return '0.00'

    try:
        amount_decimal = Decimal(str(amount))
        return CurrencyConverterService.format_amount(amount_decimal, currency)
    except Exception:
        return f"{amount} {currency}"

@register.filter(name='user_currency')
def user_currency(amount, user):
    if amount is None:
        return '0.00'

    base_currency = CurrencyConverterService.BASE_CURRENCY

    if not user or not user.is_authenticated:
        currency = base_currency
    else:
        currency = getattr(user, 'preferred_currency', None)
        if not currency and hasattr(user, 'country') and user.country:
            currency = CurrencyConverterService.get_currency_from_country(user.country)
        if not currency:
            currency = base_currency

    try:
        amount_decimal = Decimal(str(amount))
        converted = CurrencyConverterService.convert(amount_decimal, base_currency, currency)
        return CurrencyConverterService.format_amount(converted, currency)
    except Exception:
        return f"{amount} {base_currency}"

@register.simple_tag
def convert_and_format(amount, from_currency='EUR', to_currency=None, user=None):
    if amount is None:
        return '0.00'

    base_currency = CurrencyConverterService.BASE_CURRENCY

    if to_currency is None and user and user.is_authenticated:
        to_currency = getattr(user, 'preferred_currency', None)
        if not to_currency and hasattr(user, 'country') and user.country:
            to_currency = CurrencyConverterService.get_currency_from_country(user.country)
        if not to_currency:
            to_currency = base_currency
    elif to_currency is None:
        to_currency = base_currency

    try:
        amount_decimal = Decimal(str(amount))
        converted = CurrencyConverterService.convert(amount_decimal, from_currency, to_currency)
        return CurrencyConverterService.format_amount(converted, to_currency)
    except Exception:
        return f"{amount} {from_currency}"

@register.simple_tag
def currency_symbol(currency_code):
    try:
        currencies = CurrencyConverterService.get_supported_currencies()
        for curr in currencies:
            if curr['code'] == currency_code:
                return curr['symbol']
        return currency_code
    except Exception:
        return currency_code

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='get_dict_item')
def get_dict_item(dictionary, key):
    """Get an item from a dictionary using a variable key"""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)
