"""
Reverse Geocoder Module
Converts coordinates back to a structured address using Azure Maps.
Ensures postal code extraction and handles missing fields gracefully.
"""

import requests
from typing import Dict, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AZURE_MAPS_KEY, AZURE_MAPS_BASE_URL, REQUEST_TIMEOUT_SECONDS


class ReverseGeocodingError(Exception):
    """Raised when reverse geocoding fails."""
    pass


def reverse_geocode(lat: float, lon: float) -> Dict[str, str]:
    """
    Reverse geocode coordinates to a structured address.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dictionary with:
            - formatted_address: Full formatted address string
            - postal_code: Postal/ZIP code (empty string if unavailable)
            - city: City/municipality name
            - district: District/neighborhood
            - country: Country name
            - country_code: ISO 3166-1 alpha-2 code
            - street: Street name
            - street_number: House/building number

    Raises:
        ReverseGeocodingError: If the API call fails.
    """
    if not AZURE_MAPS_KEY:
        raise ReverseGeocodingError(
            "AZURE_MAPS_KEY not configured. Set it in .env or environment variables."
        )

    url = f"{AZURE_MAPS_BASE_URL}/search/address/reverse/json"
    params = {
        'api-version': '1.0',
        'subscription-key': AZURE_MAPS_KEY,
        'query': f"{lat},{lon}",
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise ReverseGeocodingError(f"Reverse geocode timed out after {REQUEST_TIMEOUT_SECONDS}s")
    except requests.exceptions.ConnectionError:
        raise ReverseGeocodingError("Cannot connect to Azure Maps API.")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 'unknown'
        raise ReverseGeocodingError(f"Azure Maps reverse geocode error (HTTP {status})")

    data = response.json()
    addresses = data.get('addresses', [])

    if not addresses:
        return _empty_result()

    # Take the first (best) result
    addr = addresses[0].get('address', {})

    return {
        'formatted_address': addr.get('freeformAddress', ''),
        'postal_code': addr.get('postalCode', '') or addr.get('extendedPostalCode', ''),
        'city': addr.get('municipality', '') or addr.get('localName', ''),
        'district': addr.get('municipalitySubdivision', '') or addr.get('neighbourhood', ''),
        'country': addr.get('country', ''),
        'country_code': addr.get('countryCode', ''),
        'street': addr.get('streetName', ''),
        'street_number': addr.get('streetNumber', ''),
    }


def _empty_result() -> Dict[str, str]:
    """Return an empty result structure."""
    return {
        'formatted_address': '',
        'postal_code': '',
        'city': '',
        'district': '',
        'country': '',
        'country_code': '',
        'street': '',
        'street_number': '',
    }


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== GeoClean Reverse Geocoder Test ===\n")

    if not AZURE_MAPS_KEY:
        print("⚠ AZURE_MAPS_KEY not set. Skipping live test.\n")
    else:
        test_coords = [
            (-12.0875, -77.0012, "Lima, Peru"),
            (40.7128, -74.0060, "New York, USA"),
            (51.5034, -0.1276, "London, UK"),
        ]

        for lat, lon, label in test_coords:
            print(f"Coords: {lat}, {lon} ({label})")
            try:
                result = reverse_geocode(lat, lon)
                print(f"  Address: {result['formatted_address']}")
                print(f"  Postal:  {result['postal_code']}")
                print(f"  City:    {result['city']}")
                print(f"  Country: {result['country']} ({result['country_code']})")
            except ReverseGeocodingError as e:
                print(f"  ERROR: {e}")
            print()
