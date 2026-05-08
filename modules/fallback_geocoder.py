"""
Fallback Geocoder Module
Provides multiple geocoding sources with intelligent fallback.

Priority chain:
  PTV Developer (best for OptiFlow — uses roadAccessPosition)
  → Azure Maps (good general-purpose)
  → HERE (if API key configured)
  → Nominatim (free, always available)
"""

import requests
import time
from typing import List, Dict, Optional
import os
from .ptv_geocoder import geocode_ptv, PTV_API_KEY


# HERE API key (optional — free tier gives 1000 requests/day)
HERE_API_KEY = os.getenv("HERE_API_KEY", "")

# Rate limiting for Nominatim (max 1 request per second per their policy)
_last_nominatim_call = 0.0


def geocode_nominatim(
    query: str,
    country_code: Optional[str] = None,
    limit: int = 3,
) -> List[Dict]:
    """
    Geocode using OpenStreetMap Nominatim (free, no API key needed).
    Rate limited to 1 request/second per Nominatim usage policy.

    Args:
        query: Address string to geocode
        country_code: Optional ISO 2-letter country code
        limit: Max results

    Returns:
        List of result dicts with: name, address, lat, lon, score, match_type, postal_code
    """
    global _last_nominatim_call

    # Respect rate limit (1 req/sec)
    elapsed = time.time() - _last_nominatim_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': query,
        'format': 'json',
        'addressdetails': 1,
        'limit': limit,
    }
    if country_code:
        params['countrycodes'] = country_code.lower()

    headers = {
        'User-Agent': 'GeoClean/1.0 (PTV Logistics geocoding tool)',
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        _last_nominatim_call = time.time()
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    data = response.json()
    if not data:
        return []

    results = []
    for r in data[:limit]:
        addr = r.get('address', {})
        results.append({
            'name': r.get('display_name', '')[:60],
            'address': r.get('display_name', ''),
            'lat': float(r.get('lat', 0)),
            'lon': float(r.get('lon', 0)),
            'score': _nominatim_importance_to_score(float(r.get('importance', 0))),
            'match_type': r.get('type', 'Unknown').replace('_', ' ').title(),
            'postal_code': addr.get('postcode', ''),
            'country_code': addr.get('country_code', '').upper(),
            'municipality': addr.get('city', '') or addr.get('town', '') or addr.get('village', ''),
            'source': 'Nominatim',
        })

    return results


def geocode_here(
    query: str,
    country_code: Optional[str] = None,
    limit: int = 3,
) -> List[Dict]:
    """
    Geocode using HERE Geocoding API.
    Requires HERE_API_KEY environment variable.
    Free tier: 1000 requests/day.

    Args:
        query: Address string to geocode
        country_code: Optional ISO 2-letter country code
        limit: Max results

    Returns:
        List of result dicts matching the standard format.
    """
    if not HERE_API_KEY:
        return []

    url = "https://geocode.search.hereapi.com/v1/geocode"
    params = {
        'q': query,
        'limit': limit,
        'apiKey': HERE_API_KEY,
    }
    if country_code:
        params['in'] = f'countryCode:{country_code.upper()}'

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    data = response.json()
    items = data.get('items', [])
    if not items:
        return []

    results = []
    for item in items[:limit]:
        position = item.get('position', {})
        address = item.get('address', {})
        scoring = item.get('scoring', {})

        results.append({
            'name': item.get('title', '')[:60],
            'address': address.get('label', ''),
            'lat': position.get('lat', 0.0),
            'lon': position.get('lng', 0.0),
            'score': scoring.get('queryScore', 0.5),
            'match_type': item.get('resultType', 'Unknown').replace('_', ' ').title(),
            'postal_code': address.get('postalCode', ''),
            'country_code': address.get('countryCode', ''),
            'municipality': address.get('city', ''),
            'source': 'HERE',
        })

    return results


def geocode_with_fallbacks(
    query: str,
    country_code: Optional[str] = None,
    limit: int = 3,
    azure_results: Optional[List[Dict]] = None,
) -> List[Dict]:
    """
    Try multiple geocoding sources and return the best results.

    Priority:
    1. PTV Developer (includes HERE data internally)
    2. Azure Maps results (passed in, already attempted)
    3. Nominatim (OSM — good for POIs and business names, always available)

    Note: HERE is NOT used as a separate fallback because PTV already
    uses HERE data internally.

    Args:
        query: Address to geocode
        country_code: Optional country code
        limit: Max results per source
        azure_results: Results from Azure Maps (may be empty)

    Returns:
        Best available results with 'source' field indicating which service provided them.
    """
    # Try PTV Developer first (best for OptiFlow routing, includes HERE data)
    if PTV_API_KEY:
        ptv_results = geocode_ptv(query, country_code, limit)
        if ptv_results:
            return ptv_results

    # If Azure returned good results, use them
    if azure_results:
        for r in azure_results:
            r['source'] = r.get('source', 'Azure Maps')
        return azure_results

    # Fall back to Nominatim (free, always available, good for POIs)
    nominatim_results = geocode_nominatim(query, country_code, limit)
    if nominatim_results:
        return nominatim_results

    return []


def _nominatim_importance_to_score(importance: float) -> float:
    """
    Convert Nominatim's 'importance' field (0-1, typically 0.1-0.8)
    to a confidence score comparable to Azure Maps.
    """
    # Nominatim importance is lower than Azure scores, so scale up
    return min(1.0, importance * 1.3)


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Fallback Geocoder Test ===\n")

    test_queries = [
        ("Av. Javier Prado 4200, Lima, Peru", "PE"),
        ("123 Main Street, New York", "US"),
        ("10 Downing Street, London", "GB"),
    ]

    for query, cc in test_queries:
        print(f"Query: {query} ({cc})")

        # Test Nominatim
        results = geocode_nominatim(query, cc)
        if results:
            r = results[0]
            print(f"  Nominatim: {r['lat']:.4f}, {r['lon']:.4f} | score={r['score']:.2f} | {r['address'][:60]}")
        else:
            print(f"  Nominatim: No results")

        # Test HERE (only if key configured)
        if HERE_API_KEY:
            results = geocode_here(query, cc)
            if results:
                r = results[0]
                print(f"  HERE: {r['lat']:.4f}, {r['lon']:.4f} | score={r['score']:.2f} | {r['address'][:60]}")
            else:
                print(f"  HERE: No results")
        else:
            print(f"  HERE: Skipped (no API key)")

        print()
