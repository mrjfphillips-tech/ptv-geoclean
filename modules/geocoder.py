"""
Geocoder Module
Performs fuzzy geocoding using Azure Maps Fuzzy Search API.
Accepts partial address input and returns top results with scores.
"""

import requests
from typing import List, Dict, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AZURE_MAPS_KEY, AZURE_MAPS_BASE_URL, DEFAULT_RESULT_LIMIT, REQUEST_TIMEOUT_SECONDS


class GeocodingError(Exception):
    """Raised when geocoding fails."""
    pass


def geocode_address(
    query: str,
    country_code: Optional[str] = None,
    limit: int = DEFAULT_RESULT_LIMIT,
) -> List[Dict]:
    """
    Geocode an address using Azure Maps Fuzzy Search.

    Args:
        query: The address string to geocode (can be partial/messy).
        country_code: Optional ISO 3166-1 alpha-2 country code to bias results.
        limit: Maximum number of results to return (default 3).

    Returns:
        List of result dictionaries, each containing:
            - name: Display name from Azure
            - address: Formatted address string
            - lat: Latitude
            - lon: Longitude
            - score: Azure confidence score (0-1)
            - match_type: Type of match (e.g., "Point Address", "Address Range")
            - postal_code: Postal code if available

    Raises:
        GeocodingError: If the API call fails or returns an error.
    """
    if not AZURE_MAPS_KEY:
        raise GeocodingError(
            "AZURE_MAPS_KEY not configured. Set it in .env or environment variables."
        )

    if not query or not query.strip():
        return []

    url = f"{AZURE_MAPS_BASE_URL}/search/fuzzy/json"
    params = {
        'api-version': '1.0',
        'query': query.strip(),
        'limit': limit,
        'typeahead': 'false',
    }

    if country_code:
        params['countrySet'] = country_code.upper()

    # Try subscription-key auth first, then x-ms-client-id header auth
    headers = {}
    if len(AZURE_MAPS_KEY) > 50:
        # Likely an Entra/AAD token or shared key — use header auth
        headers['subscription-key'] = AZURE_MAPS_KEY
    else:
        params['subscription-key'] = AZURE_MAPS_KEY

    try:
        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise GeocodingError(f"Azure Maps request timed out after {REQUEST_TIMEOUT_SECONDS}s")
    except requests.exceptions.ConnectionError:
        raise GeocodingError("Cannot connect to Azure Maps API. Check network connection.")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 'unknown'
        if status == 401:
            raise GeocodingError("Azure Maps API key is invalid or expired.")
        elif status == 403:
            raise GeocodingError("Azure Maps API key does not have permission for this operation.")
        elif status == 429:
            raise GeocodingError("Azure Maps rate limit exceeded. Try again later.")
        else:
            raise GeocodingError(f"Azure Maps API error (HTTP {status}): {e}")

    data = response.json()
    results = data.get('results', [])

    if not results:
        return []

    parsed_results = []
    for r in results[:limit]:
        position = r.get('position', {})
        address_obj = r.get('address', {})

        # Build formatted address from components
        formatted = address_obj.get('freeformAddress', '')
        if not formatted:
            parts = [
                address_obj.get('streetNumber', ''),
                address_obj.get('streetName', ''),
                address_obj.get('municipality', ''),
                address_obj.get('countrySubdivision', ''),
                address_obj.get('postalCode', ''),
                address_obj.get('country', ''),
            ]
            formatted = ', '.join(p for p in parts if p)

        parsed_results.append({
            'name': r.get('poi', {}).get('name', '') or formatted[:60],
            'address': formatted,
            'lat': position.get('lat', 0.0),
            'lon': position.get('lon', 0.0),
            'score': round(r.get('score', 0.0), 4),
            'match_type': r.get('type', 'Unknown'),
            'postal_code': address_obj.get('postalCode', ''),
            'country_code': address_obj.get('countryCode', ''),
            'municipality': address_obj.get('municipality', ''),
        })

    return parsed_results


def geocode_fields(
    street: str = '',
    city: str = '',
    state: str = '',
    postal_code: str = '',
    country: str = '',
    country_code: Optional[str] = None,
) -> List[Dict]:
    """
    Geocode from separate address fields by combining into a query string.

    Args:
        street: Street address
        city: City/municipality
        state: State/province/region
        postal_code: Postal/ZIP code
        country: Country name
        country_code: ISO country code for biasing

    Returns:
        Same as geocode_address()
    """
    parts = [p.strip() for p in [street, city, state, postal_code, country] if p.strip()]
    query = ', '.join(parts)
    return geocode_address(query, country_code=country_code)


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== GeoClean Geocoder Test ===\n")

    if not AZURE_MAPS_KEY:
        print("⚠ AZURE_MAPS_KEY not set. Create a .env file with:")
        print("  AZURE_MAPS_KEY=your-key-here")
        print("\nRunning in dry-run mode (no API calls).\n")
    else:
        test_queries = [
            "Av. Javier Prado 4200, Lima, Peru",
            "123 Main St, New York, NY",
            "10 Downing Street, London",
        ]

        for q in test_queries:
            print(f"Query: {q}")
            try:
                results = geocode_address(q)
                if results:
                    for i, r in enumerate(results):
                        print(f"  [{i+1}] {r['address']}")
                        print(f"      lat={r['lat']}, lon={r['lon']}, score={r['score']}")
                        print(f"      type={r['match_type']}, postal={r['postal_code']}")
                else:
                    print("  No results found.")
            except GeocodingError as e:
                print(f"  ERROR: {e}")
            print()
