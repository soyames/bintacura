"""
Regional Service Helper - Provides regional pricing for service creation
"""
from decimal import Decimal
from core.region_config import get_region_config, get_region_from_phone, get_consultation_fee
from currency_converter.services import CurrencyConverterService


class RegionalServiceHelper:
    """Helper class for regional service pricing and currency handling"""
    
    @staticmethod
    def get_participant_region(participant):
        """
        Determine participant's region from phone number and geolocation
        """
        region_code = 'default'
        
        if participant.phone:
            region_code = get_region_from_phone(participant.phone)
        
        if region_code == 'default' and hasattr(participant, 'country_code'):
            from core.region_config import REGIONS
            for code, config in REGIONS.items():
                if config.get('country_code') == participant.country_code:
                    region_code = code
                    break
        
        return region_code
    
    @staticmethod
    def get_default_consultation_fee(participant):
        """
        Get default consultation fee for participant's region
        Returns fee in XOF cents
        """
        region_code = RegionalServiceHelper.get_participant_region(participant)
        region_config = get_region_config(region_code)
        
        # Region config has fee in XOF (major units), convert to cents
        fee_xof = region_config.get('default_consultation_fee', 5000)
        return fee_xof * 100  # Convert to cents
    
    @staticmethod
    def get_participant_currency(participant):
        """
        Get participant's local currency based on region
        """
        region_code = RegionalServiceHelper.get_participant_region(participant)
        region_config = get_region_config(region_code)
        return region_config.get('currency', 'XOF')
    
    @staticmethod
    def convert_price_to_patient_currency(price_xof_cents, patient):
        """
        Convert price from XOF cents to patient's local currency
        """
        patient_currency = RegionalServiceHelper.get_participant_currency(patient)
        
        if patient_currency == 'XOF':
            return price_xof_cents
        
        try:
            converter = CurrencyConverterService()
            # Convert cents to major units, convert currency, then back to cents
            price_xof = Decimal(price_xof_cents) / 100
            converted = converter.convert(price_xof, 'XOF', patient_currency)
            return int(converted * 100)
        except Exception:
            return price_xof_cents
    
    @staticmethod
    def format_price_display(price_cents, currency='XOF'):
        """
        Format price for display (convert cents to major units with currency symbol)
        """
        price_major = Decimal(price_cents) / 100
        
        currency_symbols = {
            'XOF': 'CFA',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
        }
        
        symbol = currency_symbols.get(currency, currency)
        
        if currency == 'XOF':
            return f"{int(price_major):,} {symbol}"
        else:
            return f"{symbol}{price_major:.2f}"
    
    @staticmethod
    def validate_service_price(price_cents, service_type):
        """
        Validate service pricing based on type and regional standards
        Returns (is_valid, error_message)
        """
        if price_cents < 0:
            return False, "Le prix ne peut pas être négatif"
        
        # Minimum prices for service types (in XOF cents)
        min_prices = {
            'consultation': 100000,  # 1000 XOF minimum
            'imaging': 500000,  # 5000 XOF minimum
            'surgery': 2000000,  # 20000 XOF minimum
            'laboratory': 200000,  # 2000 XOF minimum
            'medication': 5000,  # 50 XOF minimum
            'insurance': 100000,  # 1000 XOF minimum premium
        }
        
        min_price = min_prices.get(service_type, 0)
        if price_cents < min_price:
            min_display = RegionalServiceHelper.format_price_display(min_price)
            return False, f"Prix minimum pour ce service: {min_display}"
        
        return True, None
