"""
Phone Number to Currency and Country Mapper
Extracts country code from phone numbers to determine currency and location
"""
import re
from typing import Optional, Tuple


class PhoneCurrencyMapper:
    """Maps phone number country codes to currency and country"""

    # Country code to (Currency, Country ISO Code, Country Name) mapping
    PHONE_CODE_MAP = {
        # West Africa (XOF - CFA Franc UEMOA)
        '229': ('XOF', 'BJ', 'Benin'),
        '225': ('XOF', 'CI', "Côte d'Ivoire"),
        '228': ('XOF', 'TG', 'Togo'),
        '226': ('XOF', 'BF', 'Burkina Faso'),
        '223': ('XOF', 'ML', 'Mali'),
        '227': ('XOF', 'NE', 'Niger'),
        '221': ('XOF', 'SN', 'Senegal'),
        '245': ('XOF', 'GW', 'Guinea-Bissau'),

        # Central Africa (XAF - CFA Franc CEMAC)
        '237': ('XAF', 'CM', 'Cameroon'),
        '241': ('XAF', 'GA', 'Gabon'),
        '242': ('XAF', 'CG', 'Congo'),
        '235': ('XAF', 'TD', 'Chad'),
        '236': ('XAF', 'CF', 'Central African Republic'),
        '240': ('XAF', 'GQ', 'Equatorial Guinea'),

        # Other African Countries
        '234': ('NGN', 'NG', 'Nigeria'),
        '233': ('GHS', 'GH', 'Ghana'),
        '254': ('KES', 'KE', 'Kenya'),
        '255': ('TZS', 'TZ', 'Tanzania'),
        '256': ('UGX', 'UG', 'Uganda'),
        '27': ('ZAR', 'ZA', 'South Africa'),
        '20': ('EGP', 'EG', 'Egypt'),
        '212': ('MAD', 'MA', 'Morocco'),
        '213': ('DZD', 'DZ', 'Algeria'),
        '216': ('TND', 'TN', 'Tunisia'),

        # Europe
        '33': ('EUR', 'FR', 'France'),
        '49': ('EUR', 'DE', 'Germany'),
        '39': ('EUR', 'IT', 'Italy'),
        '34': ('EUR', 'ES', 'Spain'),
        '351': ('EUR', 'PT', 'Portugal'),
        '32': ('EUR', 'BE', 'Belgium'),
        '31': ('EUR', 'NL', 'Netherlands'),
        '43': ('EUR', 'AT', 'Austria'),
        '44': ('GBP', 'GB', 'United Kingdom'),
        '41': ('CHF', 'CH', 'Switzerland'),
        '46': ('SEK', 'SE', 'Sweden'),
        '47': ('NOK', 'NO', 'Norway'),

        # Americas
        '1': ('USD', 'US', 'United States/Canada'),
        '52': ('MXN', 'MX', 'Mexico'),
        '55': ('BRL', 'BR', 'Brazil'),
        '54': ('ARS', 'AR', 'Argentina'),
        '56': ('CLP', 'CL', 'Chile'),
        '57': ('COP', 'CO', 'Colombia'),

        # Asia
        '86': ('CNY', 'CN', 'China'),
        '81': ('JPY', 'JP', 'Japan'),
        '91': ('INR', 'IN', 'India'),
        '82': ('KRW', 'KR', 'South Korea'),
        '65': ('SGD', 'SG', 'Singapore'),
        '60': ('MYR', 'MY', 'Malaysia'),
        '66': ('THB', 'TH', 'Thailand'),
        '84': ('VND', 'VN', 'Vietnam'),
        '63': ('PHP', 'PH', 'Philippines'),
        '62': ('IDR', 'ID', 'Indonesia'),
        '971': ('AED', 'AE', 'UAE'),
        '966': ('SAR', 'SA', 'Saudi Arabia'),
        '972': ('ILS', 'IL', 'Israel'),

        # Oceania
        '61': ('AUD', 'AU', 'Australia'),
        '64': ('NZD', 'NZ', 'New Zealand'),
    }

    @classmethod
    def extract_country_code(cls, phone_number: str) -> Optional[str]:
        """
        Extract country code from phone number
        Handles various formats: +229..., 00229..., 229...
        """
        if not phone_number:
            return None

        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', str(phone_number))

        # Remove leading + or 00
        if cleaned.startswith('+'):
            cleaned = cleaned[1:]
        elif cleaned.startswith('00'):
            cleaned = cleaned[2:]

        # Try to match country codes from longest to shortest
        # This handles codes like 1 (US) vs 971 (UAE)
        for code in sorted(cls.PHONE_CODE_MAP.keys(), key=len, reverse=True):
            if cleaned.startswith(code):
                return code

        return None

    @classmethod
    def get_currency_from_phone(cls, phone_number: str) -> Optional[str]:
        """Get currency code from phone number"""
        country_code = cls.extract_country_code(phone_number)
        if country_code and country_code in cls.PHONE_CODE_MAP:
            return cls.PHONE_CODE_MAP[country_code][0]
        return None

    @classmethod
    def get_country_from_phone(cls, phone_number: str) -> Optional[str]:
        """Get country ISO code from phone number"""
        country_code = cls.extract_country_code(phone_number)
        if country_code and country_code in cls.PHONE_CODE_MAP:
            return cls.PHONE_CODE_MAP[country_code][1]
        return None

    @classmethod
    def get_location_info_from_phone(cls, phone_number: str) -> Optional[Tuple[str, str, str]]:
        """
        Get full location info from phone number
        Returns: (currency, country_code, country_name) or None
        """
        country_code = cls.extract_country_code(phone_number)
        if country_code and country_code in cls.PHONE_CODE_MAP:
            return cls.PHONE_CODE_MAP[country_code]
        return None

    @classmethod
    def get_participant_currency(cls, participant) -> str:
        """
        Determine participant's currency with priority:
        1. Phone number country code (PRIMARY)
        2. Preferred currency field
        3. Country field
        4. Default to XOF
        """
        # Priority 1: Phone number (MOST ACCURATE)
        if hasattr(participant, 'phone') and participant.phone:
            phone_currency = cls.get_currency_from_phone(participant.phone)
            if phone_currency:
                return phone_currency

        # Priority 2: Explicit preference
        if hasattr(participant, 'preferred_currency') and participant.preferred_currency:
            return participant.preferred_currency

        # Priority 3: Country field
        if hasattr(participant, 'country') and participant.country:
            from core.geolocation_service import GeolocationService
            country_currency = GeolocationService.COUNTRY_TO_CURRENCY.get(participant.country)
            if country_currency:
                return country_currency

        # Default
        return 'XOF'

    @classmethod
    def get_participant_country(cls, participant) -> Optional[str]:
        """
        Determine participant's country with priority:
        1. Phone number country code (PRIMARY)
        2. Country field
        3. None
        """
        # Priority 1: Phone number
        if hasattr(participant, 'phone') and participant.phone:
            phone_country = cls.get_country_from_phone(participant.phone)
            if phone_country:
                return phone_country

        # Priority 2: Country field
        if hasattr(participant, 'country') and participant.country:
            return participant.country

        return None
