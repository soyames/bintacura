"""
Region-specific configuration for BINTACURA multi-region deployment
"""

# Supported regions and their configurations
REGIONS = {
    'default': {
        'name': 'Central Hub',
        'code': 'central',
        'domain': 'BINTACURA.com',
        'timezone': 'UTC',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['stripe', 'fedapay'],
    },
    'mali': {
        'name': 'Mali',
        'code': 'ml',
        'domain': 'ml.BINTACURA.com',
        'timezone': 'Africa/Bamako',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'orange_money', 'wave'],
    },
    'senegal': {
        'name': 'Senegal',
        'code': 'sn',
        'domain': 'sn.BINTACURA.com',
        'timezone': 'Africa/Dakar',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'orange_money', 'wave'],
    },
    'benin': {
        'name': 'Benin',
        'code': 'bj',
        'domain': 'bj.BINTACURA.com',
        'timezone': 'Africa/Porto-Novo',
        'language': 'fr',
        'currency': 'XOF',
        'payment_providers': ['fedapay', 'mtn_mobile_money'],
    },
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

