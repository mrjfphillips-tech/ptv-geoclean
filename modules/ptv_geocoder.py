"""
PTV Developer Geocoding Module
Uses the PTV Developer Geocoding & Places API for high-precision geocoding
optimized for OptiFlow routing.

Key advantages over other geocoders:
- roadAccessPosition gives the exact routable point on the road network
- Same data backbone as OptiFlow — coordinates are pre-validated for routing
- 360 million points across 100+ countries
- Quality score 0-100 with locationType classification

API Docs: https://developer.myptv.com/en/documentation/geocoding-places-api

Priority in GeoClean fallback chain:
  PTV Geocoding → Azure Maps → HERE → Nominatim
"""

import requests
from typing import List, Dict, Optional
import os
import sys

# Ensure .env is loaded (config.py handles this via dotenv)
_config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _config_dir)
from dotenv import load_dotenv
load_dotenv(os.path.join(_config_dir, '.env'))

# PTV Developer API key
PTV_API_KEY = os.getenv("PTV_DEVELOPER_API_KEY", "")

# Endpoints
PTV_GEOCODE_URL = "https://api.myptv.com/geocoding/v1/locations/by-text"
PTV_PLACES_URL = "https://api.myptv.com/geocoding/v1/places/by-text"
PTV_REVERSE_URL = "https://api.myptv.com/geocoding/v1/locations/by-position"


def geocode_ptv(
    query: str,
    country_code: Optional[str] = None,
    limit: int = 3,
) -> List[Dict]:
    """
    Forward geocode using PTV Developer Geocoding API.

    Args:
        query: Address string to geocode (free-form text)
        country_code: Optional ISO 2-letter country code to bias results
        limit: Maximum number of results to return

    Returns:
        List of result dicts matching GeoClean's standard format:
            name, address, lat, lon, score, match_type, postal_code,
            country_code, municipality, source, road_access_lat, road_access_lon
    """
    if not PTV_API_KEY:
        return []

    params = {
        'searchText': query,
        'language': 'en',
    }

    # Country filter — uses ISO 3166-1 alpha-2 codes
    if country_code:
        params['countryFilter'] = country_code.upper()

    headers = {
        'ApiKey': PTV_API_KEY,
        'Content-Type': 'application/json',
    }

    try:
        response = requests.get(
            PTV_GEOCODE_URL,
            params=params,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Log but don't crash — fallback chain will try next provider
        return []

    data = response.json()
    locations = data.get('locations', [])

    if not locations:
        return []

    results = []
    for loc in locations[:limit]:
        ref_pos = loc.get('referencePosition', {})
        road_pos = loc.get('roadAccessPosition', {})
        address = loc.get('address', {})
        quality = loc.get('quality', {})
        location_type = loc.get('locationType', 'UNKNOWN')

        # Use roadAccessPosition for routing (falls back to referencePosition)
        # roadAccessPosition is the point on the road network — ideal for OptiFlow
        lat = road_pos.get('latitude') or ref_pos.get('latitude', 0.0)
        lon = road_pos.get('longitude') or ref_pos.get('longitude', 0.0)

        # PTV quality score is 0-100, normalize to 0-1 for consistency
        total_score = quality.get('totalScore', 0)
        normalized_score = total_score / 100.0

        results.append({
            'name': loc.get('formattedAddress', '')[:60],
            'address': loc.get('formattedAddress', ''),
            'lat': lat,
            'lon': lon,
            'score': normalized_score,
            'match_type': _map_location_type(location_type),
            'postal_code': address.get('postalCode', ''),
            'country_code': address.get('countryCodeIsoAlpha2', '') or _extract_country_code(address.get('countryName', ''), country_code),
            'municipality': address.get('city', ''),
            'source': 'PTV',
            # Extra PTV-specific fields
            'road_access_lat': road_pos.get('latitude', 0.0),
            'road_access_lon': road_pos.get('longitude', 0.0),
            'reference_lat': ref_pos.get('latitude', 0.0),
            'reference_lon': ref_pos.get('longitude', 0.0),
            'location_type': location_type,
            'ptv_quality_score': total_score,
            'street': address.get('street', ''),
            'house_number': address.get('houseNumber', ''),
            'state': address.get('state', ''),
            'district': address.get('district', ''),
        })

    return results


def search_places_ptv(
    query: str,
    country_code: Optional[str] = None,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    limit: int = 3,
) -> List[Dict]:
    """
    Search for businesses/POIs using PTV Developer Places API.
    Use this when the input looks like a business name rather than a street address.

    Args:
        query: Business name or POI to search for (e.g., "Walmart", "Bodega Aurrera")
        country_code: Optional ISO 2-letter country code to filter results
        center_lat: Optional latitude to bias results toward a location
        center_lon: Optional longitude to bias results toward a location
        limit: Maximum number of results

    Returns:
        List of result dicts matching GeoClean's standard format.
    """
    if not PTV_API_KEY:
        return []

    params = {
        'searchText': query,
        'language': 'en',
    }

    if country_code:
        params['countryFilter'] = country_code.upper()

    # If we have a center point (e.g., from city geocoding), use it to bias results
    if center_lat and center_lon:
        params['center'] = f"{center_lat},{center_lon}"

    headers = {
        'ApiKey': PTV_API_KEY,
        'Content-Type': 'application/json',
    }

    try:
        response = requests.get(
            PTV_PLACES_URL,
            params=params,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    data = response.json()
    places = data.get('places', [])

    if not places:
        return []

    results = []
    for place in places[:limit]:
        ref_pos = place.get('referencePosition', {})
        road_pos = place.get('roadAccessPosition', {})
        address = place.get('address', {})
        quality = place.get('quality', {})

        lat = road_pos.get('latitude') or ref_pos.get('latitude', 0.0)
        lon = road_pos.get('longitude') or ref_pos.get('longitude', 0.0)

        # Places don't have a totalScore like locations, use distance or default high
        score = 0.85  # Default good score for a place match

        results.append({
            'name': place.get('name', '')[:60],
            'address': place.get('formattedAddress', ''),
            'lat': lat,
            'lon': lon,
            'score': score,
            'match_type': 'POI',
            'postal_code': address.get('postalCode', ''),
            'country_code': address.get('countryCodeIsoAlpha2', '') or _extract_country_code(address.get('countryName', ''), country_code),
            'municipality': address.get('city', ''),
            'source': 'PTV Places',
            'road_access_lat': road_pos.get('latitude', 0.0),
            'road_access_lon': road_pos.get('longitude', 0.0),
            'reference_lat': ref_pos.get('latitude', 0.0),
            'reference_lon': ref_pos.get('longitude', 0.0),
            'location_type': 'PLACE',
            'ptv_quality_score': quality.get('distance', 0),
            'street': address.get('street', ''),
            'house_number': address.get('houseNumber', ''),
            'state': address.get('state', ''),
            'district': address.get('district', ''),
            'place_name': place.get('name', ''),
        })

    return results


def reverse_geocode_ptv(
    lat: float,
    lon: float,
) -> Dict:
    """
    Reverse geocode using PTV Developer API.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dictionary with formatted_address, postal_code, city, district, country, country_code
        or empty dict if failed.
    """
    if not PTV_API_KEY:
        return {}

    params = {
        'latitude': lat,
        'longitude': lon,
        'language': 'en',
    }

    headers = {
        'ApiKey': PTV_API_KEY,
    }

    try:
        response = requests.get(
            PTV_REVERSE_URL,
            params=params,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return {}

    data = response.json()
    locations = data.get('locations', [])

    if not locations:
        return {}

    loc = locations[0]
    address = loc.get('address', {})

    return {
        'formatted_address': loc.get('formattedAddress', ''),
        'postal_code': address.get('postalCode', ''),
        'city': address.get('city', ''),
        'district': address.get('district', ''),
        'country': address.get('countryName', ''),
        'country_code': _extract_country_code(address.get('countryName', ''), ''),
        'street': address.get('street', ''),
        'house_number': address.get('houseNumber', ''),
        'state': address.get('state', ''),
    }


def _map_location_type(location_type: str) -> str:
    """
    Map PTV locationType to a human-readable match type.

    PTV location types:
    - EXACT_ADDRESS: Full address match with house number
    - INTERPOLATED_ADDRESS: House number interpolated between known points
    - STREET: Street-level match (no house number)
    - POSTAL_CODE_LEVEL_1-3: Postal code area
    - LOCALITY: City/town level
    - REGION: State/province level
    - COUNTRY: Country level only
    """
    type_map = {
        'EXACT_ADDRESS': 'Exact Address',
        'INTERPOLATED_ADDRESS': 'Interpolated Address',
        'STREET': 'Street',
        'POSTAL_CODE_LEVEL_1': 'Postal Code',
        'POSTAL_CODE_LEVEL_2': 'Postal Code',
        'POSTAL_CODE_LEVEL_3': 'Postal Code',
        'LOCALITY': 'City',
        'REGION': 'Region',
        'COUNTRY': 'Country',
    }
    return type_map.get(location_type, location_type.replace('_', ' ').title())


def _extract_country_code(country_name: str, fallback: Optional[str] = None) -> str:
    """Extract ISO 2-letter country code from country name."""
    if fallback:
        return fallback.upper()

    # Common country name to code mapping
    name_to_code = {
        'nederland': 'NL', 'netherlands': 'NL',
        'deutschland': 'DE', 'germany': 'DE',
        'france': 'FR', 'francia': 'FR',
        'españa': 'ES', 'spain': 'ES',
        'italia': 'IT', 'italy': 'IT',
        'united kingdom': 'GB', 'uk': 'GB',
        'united states': 'US', 'usa': 'US',
        'perú': 'PE', 'peru': 'PE',
        'brasil': 'BR', 'brazil': 'BR',
        'méxico': 'MX', 'mexico': 'MX',
        'colombia': 'CO',
        'chile': 'CL',
        'argentina': 'AR',
        'canada': 'CA',
        'australia': 'AU',
        'japan': 'JP',
        'china': 'CN',
        'india': 'IN',
        'south africa': 'ZA',
        'belgique': 'BE', 'belgium': 'BE',
        'österreich': 'AT', 'austria': 'AT',
        'schweiz': 'CH', 'switzerland': 'CH',
        'portugal': 'PT',
        'polska': 'PL', 'poland': 'PL',
    }

    if country_name:
        return name_to_code.get(country_name.lower().strip(), '')
    return ''


# ─── Batch Geocoding ───────────────────────────────────────────────────────────

import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Batch API endpoints (async)
PTV_BATCH_BY_TEXTS_URL = "https://api.myptv.com/geocoding/v1/batch/locations/by-texts"
PTV_BATCH_BY_POSITIONS_URL = "https://api.myptv.com/geocoding/v1/batch/locations/by-positions"


def _submit_batch_job(search_texts: List[str], country_code: Optional[str] = None) -> tuple:
    """
    Submit a batch geocoding job to PTV Developer.

    Args:
        search_texts: List of address strings (max 1000)
        country_code: Optional country filter applied to all addresses

    Returns:
        Tuple of (job_id_or_None, error_message_or_None).
    """
    if not PTV_API_KEY:
        return None, "PTV_DEVELOPER_API_KEY not set"

    headers = {
        'ApiKey': PTV_API_KEY,
        'Content-Type': 'application/json',
    }

    params = {}
    if country_code:
        params['countryFilter'] = country_code.upper()

    body = [{'searchText': text} for text in search_texts]

    try:
        url = PTV_BATCH_BY_TEXTS_URL
        if params:
            param_str = '&'.join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{param_str}"

        response = requests.post(
            url,
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get('id'), None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        body_preview = (e.response.text[:300] if e.response is not None else '')
        return None, f"HTTP {status} from batch API — {body_preview}"
    except requests.exceptions.RequestException as e:
        return None, str(e)


def _poll_batch_status(job_id: str, max_wait: int = 300, poll_interval: float = 2.0) -> str:
    """
    Poll a batch job until it completes or times out.

    Args:
        job_id: The batch job ID
        max_wait: Maximum seconds to wait
        poll_interval: Seconds between polls

    Returns:
        Final status string: "SUCCEEDED", "FAILED", or "TIMEOUT"
    """
    headers = {'ApiKey': PTV_API_KEY}
    status_url = f"{PTV_BATCH_BY_TEXTS_URL}/{job_id}/status"

    elapsed = 0.0
    while elapsed < max_wait:
        try:
            response = requests.get(status_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            status = data.get('status', 'UNKNOWN')

            if status in ('SUCCEEDED', 'FAILED', 'DELETED'):
                return status

            _time.sleep(poll_interval)
            elapsed += poll_interval
        except requests.exceptions.RequestException:
            _time.sleep(poll_interval)
            elapsed += poll_interval

    return 'TIMEOUT'


def _get_batch_results(job_id: str) -> List[List[Dict]]:
    """
    Retrieve results from a completed batch job.

    Args:
        job_id: The batch job ID

    Returns:
        List of result lists (one per input address), each in GeoClean standard format.
        Returns empty list on failure.
    """
    headers = {'ApiKey': PTV_API_KEY}
    results_url = f"{PTV_BATCH_BY_TEXTS_URL}/{job_id}"

    try:
        response = requests.get(results_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return []

    # Parse batch response — it's a list of results, one per input
    batch_results = []
    results_list = data.get('results', [])

    for item in results_list:
        locations = item.get('locations', [])
        parsed = []
        for loc in locations[:1]:  # Take top result only
            ref_pos = loc.get('referencePosition', {})
            road_pos = loc.get('roadAccessPosition', {})
            address = loc.get('address', {})
            quality = loc.get('quality', {})
            location_type = loc.get('locationType', 'UNKNOWN')

            lat = road_pos.get('latitude') or ref_pos.get('latitude', 0.0)
            lon = road_pos.get('longitude') or ref_pos.get('longitude', 0.0)
            total_score = quality.get('totalScore', 0)

            parsed.append({
                'name': loc.get('formattedAddress', '')[:60],
                'address': loc.get('formattedAddress', ''),
                'lat': lat,
                'lon': lon,
                'score': total_score / 100.0,
                'match_type': _map_location_type(location_type),
                'postal_code': address.get('postalCode', ''),
                'country_code': address.get('countryCodeIsoAlpha2', ''),
                'municipality': address.get('city', ''),
                'source': 'PTV Batch',
                'road_access_lat': road_pos.get('latitude', 0.0),
                'road_access_lon': road_pos.get('longitude', 0.0),
                'reference_lat': ref_pos.get('latitude', 0.0),
                'reference_lon': ref_pos.get('longitude', 0.0),
                'location_type': location_type,
                'ptv_quality_score': total_score,
                'street': address.get('street', ''),
                'house_number': address.get('houseNumber', ''),
                'state': address.get('state', ''),
                'district': address.get('district', ''),
            })
        batch_results.append(parsed)

    return batch_results


def _delete_batch_job(job_id: str) -> None:
    """Clean up a batch job after retrieving results."""
    headers = {'ApiKey': PTV_API_KEY}
    try:
        requests.delete(f"{PTV_BATCH_BY_TEXTS_URL}/{job_id}", headers=headers, timeout=10)
    except requests.exceptions.RequestException:
        pass  # Best-effort cleanup


def geocode_batch_ptv(
    queries: List[str],
    country_code: Optional[str] = None,
    batch_size: int = 500,
    max_concurrent_batches: int = 4,
    progress_callback=None,
) -> tuple:
    """
    Batch geocode multiple addresses using PTV Developer async batch API.

    Returns:
        Tuple of (results, first_error_or_None).
        results: List of result lists (one per input query).
        first_error: First submission error encountered, or None if all succeeded.
    """
    if not PTV_API_KEY or not queries:
        return [[] for _ in queries], "PTV_DEVELOPER_API_KEY not set" if not PTV_API_KEY else None

    batches = []
    for i in range(0, len(queries), batch_size):
        batches.append(queries[i:i + batch_size])

    all_results: List[List[Dict]] = [[] for _ in queries]
    completed_count = 0
    first_error: Optional[str] = None

    def process_batch(batch_idx: int, batch_queries: List[str]) -> tuple:
        job_id, err = _submit_batch_job(batch_queries, country_code)
        if not job_id:
            return (batch_idx, [[] for _ in batch_queries], err)

        status = _poll_batch_status(job_id, max_wait=45)

        if status == 'SUCCEEDED':
            results = _get_batch_results(job_id)
            _delete_batch_job(job_id)
            while len(results) < len(batch_queries):
                results.append([])
            return (batch_idx, results, None)
        else:
            _delete_batch_job(job_id)
            return (batch_idx, [[] for _ in batch_queries], f"Batch job ended with status: {status}")

    with ThreadPoolExecutor(max_workers=max_concurrent_batches) as executor:
        futures = {
            executor.submit(process_batch, idx, batch): idx
            for idx, batch in enumerate(batches)
        }

        for future in as_completed(futures):
            batch_idx, batch_results, err = future.result()
            if err and first_error is None:
                first_error = err
            start_pos = batch_idx * batch_size
            for i, result in enumerate(batch_results):
                if start_pos + i < len(all_results):
                    all_results[start_pos + i] = result

            completed_count += len(batch_results)
            if progress_callback:
                progress_callback(completed_count, len(queries))

    return all_results, first_error


# ─── Batch Reverse Geocoding (by-positions) ───────────────────────────────────

def _submit_reverse_batch_job(positions: List[Dict]) -> tuple:
    """
    Submit a batch reverse geocoding job (lat/lon → address + road-access position).

    Returns:
        Tuple of (job_id_or_None, error_message_or_None).
    """
    if not PTV_API_KEY:
        return None, "PTV_DEVELOPER_API_KEY not set"

    headers = {'ApiKey': PTV_API_KEY, 'Content-Type': 'application/json'}
    body = [{'latitude': p['latitude'], 'longitude': p['longitude']} for p in positions]

    try:
        response = requests.post(
            PTV_BATCH_BY_POSITIONS_URL,
            json=body,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get('id'), None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        preview = e.response.text[:300] if e.response is not None else ''
        return None, f"HTTP {status} from reverse batch API — {preview}"
    except requests.exceptions.RequestException as e:
        return None, str(e)


def _poll_reverse_batch_status(job_id: str, max_wait: int = 45, poll_interval: float = 2.0) -> str:
    headers = {'ApiKey': PTV_API_KEY}
    status_url = f"{PTV_BATCH_BY_POSITIONS_URL}/{job_id}/status"
    elapsed = 0.0
    while elapsed < max_wait:
        try:
            response = requests.get(status_url, headers=headers, timeout=10)
            response.raise_for_status()
            status = response.json().get('status', 'UNKNOWN')
            if status in ('SUCCEEDED', 'FAILED', 'DELETED'):
                return status
        except requests.exceptions.RequestException:
            pass
        _time.sleep(poll_interval)
        elapsed += poll_interval
    return 'TIMEOUT'


def _get_reverse_batch_results(job_id: str) -> List[List[Dict]]:
    headers = {'ApiKey': PTV_API_KEY}
    try:
        response = requests.get(f"{PTV_BATCH_BY_POSITIONS_URL}/{job_id}", headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return []

    batch_results = []
    for item in data.get('results', []):
        locations = item.get('locations', [])
        parsed = []
        for loc in locations[:1]:
            ref_pos = loc.get('referencePosition', {})
            road_pos = loc.get('roadAccessPosition', {})
            address = loc.get('address', {})
            quality = loc.get('quality', {})
            location_type = loc.get('locationType', 'UNKNOWN')

            lat = road_pos.get('latitude') or ref_pos.get('latitude', 0.0)
            lon = road_pos.get('longitude') or ref_pos.get('longitude', 0.0)
            total_score = quality.get('totalScore', 0)

            parsed.append({
                'name': loc.get('formattedAddress', '')[:60],
                'address': loc.get('formattedAddress', ''),
                'lat': lat,
                'lon': lon,
                'score': total_score / 100.0,
                'match_type': _map_location_type(location_type),
                'postal_code': address.get('postalCode', ''),
                'country_code': address.get('countryCodeIsoAlpha2', ''),
                'municipality': address.get('city', ''),
                'source': 'PTV Reverse Batch',
                'road_access_lat': road_pos.get('latitude', 0.0),
                'road_access_lon': road_pos.get('longitude', 0.0),
                'reference_lat': ref_pos.get('latitude', 0.0),
                'reference_lon': ref_pos.get('longitude', 0.0),
                'location_type': location_type,
                'ptv_quality_score': total_score,
                'street': address.get('street', ''),
                'house_number': address.get('houseNumber', ''),
                'state': address.get('state', ''),
                'district': address.get('district', ''),
            })
        batch_results.append(parsed)
    return batch_results


def _delete_reverse_batch_job(job_id: str) -> None:
    headers = {'ApiKey': PTV_API_KEY}
    try:
        requests.delete(f"{PTV_BATCH_BY_POSITIONS_URL}/{job_id}", headers=headers, timeout=10)
    except requests.exceptions.RequestException:
        pass


def reverse_geocode_batch_ptv(
    positions: List[Dict],
    batch_size: int = 500,
    max_concurrent_batches: int = 4,
    progress_callback=None,
) -> tuple:
    """
    Batch reverse geocode lat/lon positions using PTV Developer async batch API.

    Args:
        positions: List of dicts with 'latitude' and 'longitude' keys.
        batch_size: Max positions per batch job (API limit is 1000).
        max_concurrent_batches: Max simultaneous batch jobs.
        progress_callback: Optional callback(completed_count, total_count).

    Returns:
        Tuple of (results, first_error_or_None).
        results: List of result lists (one per input position).
        first_error: First submission error encountered, or None if all succeeded.
    """
    if not PTV_API_KEY or not positions:
        return [[] for _ in positions], ("PTV_DEVELOPER_API_KEY not set" if not PTV_API_KEY else None)

    batches = [(i, positions[i:i + batch_size]) for i in range(0, len(positions), batch_size)]
    all_results: List[List[Dict]] = [[] for _ in positions]
    completed_count = 0
    first_error: Optional[str] = None

    def process_batch(batch_start: int, batch_positions: List[Dict]) -> tuple:
        job_id, err = _submit_reverse_batch_job(batch_positions)
        if not job_id:
            return batch_start, [[] for _ in batch_positions], err

        status = _poll_reverse_batch_status(job_id, max_wait=45)

        if status == 'SUCCEEDED':
            batch_res = _get_reverse_batch_results(job_id)
            _delete_reverse_batch_job(job_id)
            while len(batch_res) < len(batch_positions):
                batch_res.append([])
            return batch_start, batch_res, None
        else:
            _delete_reverse_batch_job(job_id)
            return batch_start, [[] for _ in batch_positions], f"Batch ended with status: {status}"

    with ThreadPoolExecutor(max_workers=max_concurrent_batches) as executor:
        futures = {
            executor.submit(process_batch, start, batch): len(batch)
            for start, batch in batches
        }
        for future in as_completed(futures):
            batch_start, batch_res, err = future.result()
            if err and first_error is None:
                first_error = err
            for i, res in enumerate(batch_res):
                all_results[batch_start + i] = res
            completed_count += len(batch_res)
            if progress_callback:
                progress_callback(completed_count, len(positions))

    return all_results, first_error


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== PTV Developer Geocoding Test ===\n")

    if not PTV_API_KEY:
        print("⚠️  PTV_DEVELOPER_API_KEY not set in environment.")
        print("   Add it to geoclean/.env:")
        print("   PTV_DEVELOPER_API_KEY=your-key-here")
        print()
        print("   Get a free key at: https://developer.myptv.com")
        exit(0)

    test_queries = [
        ("Aan 't Verlaat 33F, Delft", "NL"),
        ("451 Holland Springs Drive, Maryville, TN", "US"),
        ("Av. Javier Prado 4200, Lima", "PE"),
        ("10 Downing Street, London", "GB"),
        ("Haid-und-Neu-Straße 15, Karlsruhe", "DE"),
    ]

    for query, cc in test_queries:
        print(f"Query: {query} ({cc})")
        results = geocode_ptv(query, cc)
        if results:
            r = results[0]
            print(f"  ✅ {r['address']}")
            print(f"     Road Access: {r['road_access_lat']:.6f}, {r['road_access_lon']:.6f}")
            print(f"     Score: {r['ptv_quality_score']}/100 | Type: {r['location_type']}")
            print(f"     Postal: {r['postal_code']}")
        else:
            print(f"  ❌ No results")
        print()
