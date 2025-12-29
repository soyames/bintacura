from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)


class CurrencyConverterService:  # Service class for CurrencyConverter operations
    
    BASE_CURRENCY = 'XOF'
    
    STATIC_RATES = {
        'XOF': Decimal('1.00'),
        'XAF': Decimal('1.00'),
        'USD': Decimal('0.00167'),
        'EUR': Decimal('0.00153'),
        'GBP': Decimal('0.00132'),
        'NGN': Decimal('2.33'),
        'GHS': Decimal('0.02'),
        'KES': Decimal('0.242'),
        'ZAR': Decimal('0.0308'),
        'MAD': Decimal('0.0167'),
        'TND': Decimal('0.00517'),
        'EGP': Decimal('0.0817'),
    }
    
    CURRENCY_SYMBOLS = {
        'EUR': '€',
        'USD': '$',
        'GBP': '£',
        'XOF': 'CFA',
        'XAF': 'FCFA',
        'NGN': '₦',
        'GHS': 'GH₵',
        'KES': 'KSh',
        'ZAR': 'R',
        'MAD': 'MAD',
        'TND': 'TND',
        'EGP': 'E£',
    }
    
    COUNTRY_CURRENCY_MAP = {
        'BJ': 'XOF', 'BF': 'XOF', 'CI': 'XOF', 'GW': 'XOF',
        'ML': 'XOF', 'NE': 'XOF', 'SN': 'XOF', 'TG': 'XOF',
        'CM': 'XAF', 'CF': 'XAF', 'TD': 'XAF', 'CG': 'XAF',
        'GQ': 'XAF', 'GA': 'XAF',
        'NG': 'NGN', 'GH': 'GHS', 'KE': 'KES', 'ZA': 'ZAR',
        'EG': 'EGP', 'MA': 'MAD', 'TN': 'TND',
        'FR': 'EUR', 'DE': 'EUR', 'IT': 'EUR', 'ES': 'EUR',
        'PT': 'EUR', 'BE': 'EUR', 'NL': 'EUR', 'AT': 'EUR',
        'IE': 'EUR', 'GR': 'EUR',
        'GB': 'GBP', 'US': 'USD',
    }
    
    @classmethod
    def get_rate(cls, from_currency: str, to_currency: str) -> Decimal:
        if from_currency == to_currency:
            return Decimal('1.00')
        
        cache_key = f'exchange_rate_{from_currency}_{to_currency}'
        cached_rate = cache.get(cache_key)
        if cached_rate:
            return Decimal(str(cached_rate))
        
        try:
            from .models import ExchangeRate
            db_rate = ExchangeRate.get_latest_rate(from_currency, to_currency)
            if db_rate:
                cache.set(cache_key, str(db_rate.rate), timeout=3600)
                return db_rate.rate
        except Exception as e:
            logger.warning(f"Database rate fetch failed: {e}")
        
        try:
            rate = cls._fetch_rate_from_api(from_currency, to_currency)
            if rate:
                cache.set(cache_key, str(rate), timeout=3600)
                cls._save_rate_to_db(from_currency, to_currency, rate, 'API')
                return rate
        except Exception as e:
            logger.warning(f"API fetch failed: {e}, using static rates")
        
        return cls._calculate_static_rate(from_currency, to_currency)
    
    @classmethod
    def _calculate_static_rate(cls, from_currency: str, to_currency: str) -> Decimal:
        from_rate = cls.STATIC_RATES.get(from_currency)
        to_rate = cls.STATIC_RATES.get(to_currency)
        
        if not from_rate or not to_rate:
            raise ValueError(f"Unsupported currency: {from_currency} or {to_currency}")
        
        rate = to_rate / from_rate
        return rate.quantize(Decimal('0.0001'))
    
    @classmethod
    def _fetch_rate_from_api(cls, from_currency: str, to_currency: str):
        api_key = getattr(settings, 'EXCHANGE_RATE_API_KEY', None)
        if not api_key:
            return None
        
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('result') == 'success':
                return Decimal(str(data['conversion_rate']))
        
        return None
    
    @classmethod
    def _save_rate_to_db(cls, from_currency: str, to_currency: str, rate: Decimal, source: str):
        try:
            from .models import ExchangeRate
            ExchangeRate.objects.create(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                source=source
            )
        except Exception as e:
            logger.error(f"Failed to save rate to database: {e}")
    
    @classmethod
    def convert(cls, amount, from_currency: str, to_currency: str):
        """
        Convert amount between currencies.
        Returns dict with conversion details for audit trail.
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        rate = cls.get_rate(from_currency, to_currency)
        converted = amount * rate
        
        if to_currency in ['XOF', 'XAF', 'NGN', 'KES']:
            converted = converted.quantize(Decimal('1'))
        else:
            converted = converted.quantize(Decimal('0.01'))
        
        return {
            'original_amount': amount,
            'converted_amount': converted,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': rate,
        }
    
    @classmethod
    def format_amount(cls, amount, currency: str) -> str:
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        symbol = cls.CURRENCY_SYMBOLS.get(currency, currency)
        
        if currency in ['XOF', 'XAF']:
            formatted = f"{amount:,.0f}".replace(',', ' ')
            return f"{formatted} {symbol}"
        elif currency in ['EUR', 'GBP']:
            return f"{symbol}{amount:,.2f}"
        else:
            return f"{symbol}{amount:,.2f}"
    
    @classmethod
    def get_participant_currency(cls, participant) -> str:
        """
        Get participant's local currency for all transactions and payments.
        PLATFORM POLICY:
        1. Always use participant's local currency (from phone/geolocation)
        2. If local currency not in supported list -> try online rates
        3. If online rates unavailable -> fallback to XOF (platform base currency)
        4. Applies consistently across all instances (online/offline)
        """
        try:
            local_currency = None
            detection_method = None
            
            if hasattr(participant, 'phone_number') and participant.phone_number:
                country_code = cls._extract_country_from_phone(participant.phone_number)
                if country_code:
                    local_currency = cls.COUNTRY_CURRENCY_MAP.get(country_code)
                    detection_method = f'phone_number (country: {country_code})'
            
            if not local_currency and hasattr(participant, 'country') and participant.country:
                local_currency = cls.COUNTRY_CURRENCY_MAP.get(participant.country.upper())
                detection_method = f'geolocation (country: {participant.country.upper()})'
            
            if local_currency:
                if local_currency in cls.STATIC_RATES:
                    logger.info(f"Using supported local currency {local_currency} via {detection_method}")
                    return local_currency
                
                logger.info(f"Currency {local_currency} not in static rates, checking online rates via {detection_method}")
                if cls._is_currency_available_online(local_currency):
                    logger.info(f"Using online exchange rate for {local_currency}")
                    return local_currency
                else:
                    logger.warning(f"Currency {local_currency} unavailable online, falling back to XOF")
            else:
                logger.warning(f"Could not determine local currency for participant, using XOF")
            
        except Exception as e:
            logger.error(f"Error determining participant currency: {e}, falling back to XOF")
        
        return cls.BASE_CURRENCY
    
    @classmethod
    def _extract_country_from_phone(cls, phone_number: str) -> str:
        """Extract country code from phone number"""
        phone_str = str(phone_number).replace('+', '').replace(' ', '')
        
        country_prefixes = {
            '229': 'BJ', '226': 'BF', '225': 'CI', '245': 'GW',
            '223': 'ML', '227': 'NE', '221': 'SN', '228': 'TG',
            '237': 'CM', '236': 'CF', '235': 'TD', '242': 'CG',
            '240': 'GQ', '241': 'GA',
            '234': 'NG', '233': 'GH', '254': 'KE', '27': 'ZA',
            '20': 'EG', '212': 'MA', '216': 'TN',
            '33': 'FR', '49': 'DE', '39': 'IT', '34': 'ES',
            '44': 'GB', '1': 'US',
        }
        
        for prefix, country in country_prefixes.items():
            if phone_str.startswith(prefix):
                return country
        
        return None
    
    @classmethod
    def _is_currency_available_online(cls, currency_code: str) -> bool:
        """Check if currency is available via online API"""
        try:
            rate = cls._fetch_rate_from_api(cls.BASE_CURRENCY, currency_code)
            return rate is not None
        except Exception:
            return False
    
    @classmethod
    def get_currency_from_country(cls, country_code: str) -> str:
        """Get currency for country code, fallback to USD if not supported"""
        currency = cls.COUNTRY_CURRENCY_MAP.get(country_code.upper())
        if currency and currency in cls.STATIC_RATES:
            return currency
        return cls.BASE_CURRENCY
    
    @classmethod
    def get_supported_currencies(cls):  # Get supported currencies
        return list(cls.STATIC_RATES.keys())
    
    @classmethod
    def convert_to_local_currency(cls, amount_xof, participant) -> tuple:
        """
        Convert XOF amount to participant's local currency for ALL transactions and payments.
        Returns: (converted_amount, local_currency_code)
        
        PLATFORM POLICY ENFORCEMENT:
        1. All transactions MUST use participant's local currency
        2. Works consistently across all instances (online/offline with sync)
        3. Fallback to XOF only if local currency completely unavailable
        
        This ensures price transparency and local market compliance.
        """
        local_currency = cls.get_participant_currency(participant)
        
        if not isinstance(amount_xof, Decimal):
            amount_xof = Decimal(str(amount_xof))
        
        if local_currency == cls.BASE_CURRENCY:
            logger.debug(f"Using base currency XOF for transaction: {amount_xof}")
            return amount_xof, local_currency
        
        converted_amount = cls.convert(amount_xof, cls.BASE_CURRENCY, local_currency)
        logger.debug(f"Converted {amount_xof} XOF to {converted_amount} {local_currency}")
        return converted_amount, local_currency
    
    @classmethod
    def convert_from_local_currency(cls, amount_local, local_currency) -> Decimal:
        """
        Convert from participant's local currency back to XOF (base currency).
        Used for storing transaction amounts in database.
        """
        if local_currency == cls.BASE_CURRENCY:
            return Decimal(str(amount_local)) if not isinstance(amount_local, Decimal) else amount_local
        
        return cls.convert(amount_local, local_currency, cls.BASE_CURRENCY)
    
    @classmethod
    def get_country_from_phone(cls, phone_number: str):
        """Extract country code from phone number (used by orchestration service)"""
        return cls._extract_country_from_phone(phone_number)
    
    @classmethod
    def get_country_from_coordinates(cls, longitude: float, latitude: float):
        """
        Get country code from GPS coordinates.
        Note: Requires reverse geocoding service or database.
        For now returns None, can be enhanced with geopy or similar.
        """
        # TODO: Implement reverse geocoding
        # Can use geopy, Google Maps API, or offline database
        logger.warning("GPS-based country resolution not yet implemented")
        return None
    
    @classmethod
    def get_currency_for_country(cls, country_code: str) -> str:
        """Get currency code for a given country code"""
        return cls.get_currency_from_country(country_code)
