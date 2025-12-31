"""
Region-specific configuration for BINTACURA multi-region deployment
"""

# Supported regions and their configurations
REGIONS = {
    'default': {
        'name': 'Central Hub',
        'code': 'central',
        'country_code': 'XX',
        'domain': 'BINTACURA.com',
        'timezone': 'UTC',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['stripe', 'fedapay'],
        'default_consultation_fee': 5000,  # XOF
    },
    'mali': {
        'name': 'Mali',
        'code': 'ml',
        'country_code': 'ML',
        'domain': 'ml.BINTACURA.com',
        'timezone': 'Africa/Bamako',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'orange_money', 'wave'],
        'default_consultation_fee': 5000,  # ~8 USD
    },
    'senegal': {
        'name': 'Senegal',
        'code': 'sn',
        'country_code': 'SN',
        'domain': 'sn.BINTACURA.com',
        'timezone': 'Africa/Dakar',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'orange_money', 'wave'],
        'default_consultation_fee': 6000,  # ~10 USD
    },
    'benin': {
        'name': 'Benin',
        'code': 'bj',
        'country_code': 'BJ',
        'domain': 'bj.BINTACURA.com',
        'timezone': 'Africa/Porto-Novo',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'mtn_mobile_money'],
        'default_consultation_fee': 5500,  # ~9 USD
    },
    'burkina_faso': {
        'name': 'Burkina Faso',
        'code': 'bf',
        'country_code': 'BF',
        'domain': 'bf.BINTACURA.com',
        'timezone': 'Africa/Ouagadougou',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'orange_money'],
        'default_consultation_fee': 4500,  # ~7.5 USD
    },
    'cote_divoire': {
        'name': "Côte d'Ivoire",
        'code': 'ci',
        'country_code': 'CI',
        'domain': 'ci.BINTACURA.com',
        'timezone': 'Africa/Abidjan',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'orange_money', 'mtn_mobile_money'],
        'default_consultation_fee': 7000,  # ~12 USD
    },
    'niger': {
        'name': 'Niger',
        'code': 'ne',
        'country_code': 'NE',
        'domain': 'ne.BINTACURA.com',
        'timezone': 'Africa/Niamey',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'orange_money'],
        'default_consultation_fee': 4000,  # ~6.5 USD
    },
    'togo': {
        'name': 'Togo',
        'code': 'tg',
        'country_code': 'TG',
        'domain': 'tg.BINTACURA.com',
        'timezone': 'Africa/Lome',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'tmoney'],
        'default_consultation_fee': 5000,  # ~8 USD
    },
    'guinea_bissau': {
        'name': 'Guinea-Bissau',
        'code': 'gw',
        'country_code': 'GW',
        'domain': 'gw.BINTACURA.com',
        'timezone': 'Africa/Bissau',
        'language': 'pt',
        'currency': 'XOF',
        'payment_providers': ['fedapay'],
        'default_consultation_fee': 4500,  # ~7.5 USD
    },
}

# Phone country code to region mapping
PHONE_TO_REGION = {
    '+223': 'mali',
    '+221': 'senegal',
    '+229': 'benin',
    '+226': 'burkina_faso',
    '+225': 'cote_divoire',
    '+227': 'niger',
    '+228': 'togo',
    '+245': 'guinea_bissau',
}


def get_region_config(region_code='default'):
    """
    Get configuration for a specific region
    """
    return REGIONS.get(region_code, REGIONS['default'])


def get_region_from_domain(domain):
    """
    Determine region from domain name
    """
    for region_code, config in REGIONS.items():
        if config['domain'] in domain:
            return region_code
    return 'default'


def get_region_from_phone(phone_number):
    """
    Determine region from phone number country code
    """
    if not phone_number:
        return 'default'
    
    phone_str = str(phone_number).strip()
    for country_code, region in PHONE_TO_REGION.items():
        if phone_str.startswith(country_code):
            return region
    
    return 'default'


def get_consultation_fee(region_code='default', currency='XOF'):
    """
    Get default consultation fee for a region in specified currency
    Returns fee in XOF by default, converts if different currency requested
    """
    region = get_region_config(region_code)
    base_fee = region.get('default_consultation_fee', 5000)
    
    if currency == 'XOF' or currency == region.get('currency'):
        return base_fee
    
    # If currency conversion needed, use currency converter
    from currency_converter.services import CurrencyConverterService
    try:
        converter = CurrencyConverterService()
        converted = converter.convert(base_fee, 'XOF', currency)
        return converted
    except Exception:
        return base_fee


def get_all_regions():
    """
    Get list of all supported regions
    """
    return list(REGIONS.keys())


def is_region_supported(region_code):
    """
    Check if a region is supported
    """
    return region_code in REGIONS

