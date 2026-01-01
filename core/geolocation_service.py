import requests
from typing import Optional, Tuple, Dict
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
# Google Maps removed - Using OpenStreetMap (Nominatim) and OSRM instead
# import googlemaps
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class GeolocationService:
    COUNTRY_TO_CURRENCY = {
        "GH": "GHS",
        "NG": "NGN",
        "BJ": "XOF",
        "CI": "XOF",
        "TG": "XOF",
        "BF": "XOF",
        "ML": "XOF",
        "NE": "XOF",
        "SN": "XOF",
        "GW": "XOF",
        "CM": "XAF",
        "GA": "XAF",
        "CG": "XAF",
        "TD": "XAF",
        "CF": "XAF",
        "GQ": "XAF",
        "FR": "EUR",
        "DE": "EUR",
        "IT": "EUR",
        "ES": "EUR",
        "PT": "EUR",
        "BE": "EUR",
        "NL": "EUR",
        "AT": "EUR",
        "IE": "EUR",
        "GR": "EUR",
        "FI": "EUR",
        "LU": "EUR",
        "SI": "EUR",
        "SK": "EUR",
        "EE": "EUR",
        "LV": "EUR",
        "LT": "EUR",
        "MT": "EUR",
        "CY": "EUR",
        "GB": "GBP",
        "US": "XOF",
        "CA": "CAD",
        "AU": "AUD",
        "NZ": "NZD",
        "JP": "JPY",
        "CN": "CNY",
        "IN": "INR",
        "KR": "KRW",
        "BR": "BRL",
        "MX": "MXN",
        "ZA": "ZAR",
        "RU": "RUB",
        "CH": "CHF",
        "SE": "SEK",
        "NO": "NOK",
        "DK": "DKK",
        "PL": "PLN",
        "TR": "TRY",
        "SA": "SAR",
        "AE": "AED",
        "EG": "EGP",
        "KE": "KES",
        "TZ": "TZS",
        "UG": "UGX",
        "MA": "MAD",
        "DZ": "DZD",
        "TN": "TND",
        "SG": "SGD",
        "MY": "MYR",
        "TH": "THB",
        "ID": "IDR",
        "PH": "PHP",
        "VN": "VND",
        "AR": "ARS",
        "CL": "CLP",
        "CO": "COP",
        "PE": "PEN",
        "IL": "ILS",
        "HK": "HKD",
    }

    @classmethod
    def get_currency_from_ip(cls, ip_address: str) -> str:
        if not ip_address or ip_address in ["127.0.0.1", "localhost"]:
            return "EUR"

        try:
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                country_code = data.get("countryCode")
                if country_code:
                    return cls.COUNTRY_TO_CURRENCY.get(country_code, "XOF")
        except Exception:
            pass

        return "EUR"

    @classmethod
    def get_client_ip(cls, request) -> Optional[str]:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    @classmethod
    def get_currency_for_request(cls, request) -> str:
        ip_address = cls.get_client_ip(request)
        if ip_address:
            return cls.get_currency_from_ip(ip_address)
        return "EUR"

    @classmethod
    def geocode_address(cls, address: str) -> Optional[Tuple[float, float]]:
        try:
            geolocator = Nominatim(user_agent="BINTACURA_app")
            location = geolocator.geocode(address)
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            logger.error(f"Geocoding failed for address '{address}': {str(e)}")
        return None

    @classmethod
    def reverse_geocode(cls, latitude: float, longitude: float) -> Optional[str]:
        try:
            geolocator = Nominatim(user_agent="BINTACURA_app")
            location = geolocator.reverse(f"{latitude}, {longitude}")
            if location:
                return location.address
        except Exception as e:
            logger.error(f"Reverse geocoding failed for ({latitude}, {longitude}): {str(e)}")
        return None

    @classmethod
    def calculate_distance(cls, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        try:
            distance = geodesic(coord1, coord2).kilometers
            return round(distance, 2)
        except Exception as e:
            logger.error(f"Distance calculation failed: {str(e)}")
            return 0.0

    @classmethod
    def get_directions(cls, origin: str, destination: str) -> Optional[Dict]:
        """
        Get driving directions using OSRM (Open Source Routing Machine).
        Replaces Google Maps Directions API.
        """
        try:
            # First geocode the origin and destination
            origin_coords = cls.geocode_address(origin)
            destination_coords = cls.geocode_address(destination)

            if not origin_coords or not destination_coords:
                logger.warning(f"Could not geocode origin or destination")
                return None

            # Use OSRM API for routing
            osrm_url = (
                f"https://router.project-osrm.org/route/v1/driving/"
                f"{origin_coords[1]},{origin_coords[0]};"
                f"{destination_coords[1]},{destination_coords[0]}"
                f"?overview=full&geometries=polyline"
            )

            response = requests.get(osrm_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 'Ok' and data.get('routes'):
                    route = data['routes'][0]
                    return {
                        'distance_km': route['distance'] / 1000,
                        'duration_minutes': route['duration'] / 60,
                        'start_address': origin,
                        'end_address': destination,
                        'polyline': route.get('geometry', '')
                    }
        except Exception as e:
            logger.error(f"Failed to get directions from '{origin}' to '{destination}': {str(e)}")
        return None

    @classmethod
    def geocode_with_google(cls, address: str) -> Optional[Tuple[float, float]]:
        """
        Legacy method name kept for backwards compatibility.
        Now uses OpenStreetMap Nominatim instead of Google Maps.
        """
        # Google Maps removed - using Nominatim (OpenStreetMap) instead
        return cls.geocode_address(address)

