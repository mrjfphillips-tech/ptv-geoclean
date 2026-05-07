"""
Entrance Finder Module
Attempts to locate building entrance coordinates using OpenStreetMap Overpass API.
Falls back to original geocode coordinates if no entrance data is found.
"""

import requests
from typing import Dict, Optional
import math


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT = 10  # seconds
SEARCH_RADIUS_METERS = 50  # search radius around the geocoded point


def find_entrance(lat: float, lon: float) -> Dict:
    """
    Attempt to find a building entrance near the given coordinates.

    Priority logic:
        1. OSM entrance=main
        2. OSM entrance=yes
        3. OSM parking_entrance (amenity=parking_entrance)
        4. Fallback to input coordinates

    Args:
        lat: Latitude of the geocoded building
        lon: Longitude of the geocoded building

    Returns:
        Dictionary with:
            - lat: Entrance latitude
            - lon: Entrance longitude
            - precision: "Entrance" or "Building"
            - source: "OSM" or "Fallback"
            - entrance_type: Specific type found (e.g., "main", "yes", "parking")
    """
    # Try OSM Overpass API for entrance nodes
    try:
        entrances = _query_osm_entrances(lat, lon, SEARCH_RADIUS_METERS)

        if entrances:
            # Priority 1: entrance=main
            main_entrances = [e for e in entrances if e.get('type') == 'main']
            if main_entrances:
                best = _closest(lat, lon, main_entrances)
                return {
                    'lat': best['lat'],
                    'lon': best['lon'],
                    'precision': 'Entrance',
                    'source': 'OSM',
                    'entrance_type': 'main',
                }

            # Priority 2: entrance=yes
            yes_entrances = [e for e in entrances if e.get('type') == 'yes']
            if yes_entrances:
                best = _closest(lat, lon, yes_entrances)
                return {
                    'lat': best['lat'],
                    'lon': best['lon'],
                    'precision': 'Entrance',
                    'source': 'OSM',
                    'entrance_type': 'yes',
                }

            # Priority 3: any other entrance type
            best = _closest(lat, lon, entrances)
            return {
                'lat': best['lat'],
                'lon': best['lon'],
                'precision': 'Entrance',
                'source': 'OSM',
                'entrance_type': best.get('type', 'unknown'),
            }

    except Exception:
        # OSM query failed — fall through to fallback
        pass

    # Fallback: return original coordinates
    return {
        'lat': lat,
        'lon': lon,
        'precision': 'Building',
        'source': 'Fallback',
        'entrance_type': '',
    }


def _query_osm_entrances(lat: float, lon: float, radius: int) -> list:
    """
    Query OpenStreetMap Overpass API for entrance nodes near coordinates.
    """
    query = f"""
    [out:json][timeout:{OVERPASS_TIMEOUT}];
    (
      node["entrance"](around:{radius},{lat},{lon});
      node["amenity"="parking_entrance"](around:{radius},{lat},{lon});
    );
    out body;
    """

    try:
        response = requests.post(
            OVERPASS_URL,
            data={'data': query},
            timeout=OVERPASS_TIMEOUT + 5,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        return []

    elements = data.get('elements', [])
    entrances = []

    for el in elements:
        if el.get('type') == 'node' and 'lat' in el and 'lon' in el:
            tags = el.get('tags', {})
            entrance_type = tags.get('entrance', '')
            if not entrance_type and tags.get('amenity') == 'parking_entrance':
                entrance_type = 'parking'

            entrances.append({
                'lat': el['lat'],
                'lon': el['lon'],
                'type': entrance_type or 'yes',
            })

    return entrances


def _closest(lat: float, lon: float, points: list) -> dict:
    """Find the closest point to the reference coordinates."""
    if not points:
        return {'lat': lat, 'lon': lon, 'type': ''}

    def distance(p):
        dlat = p['lat'] - lat
        dlon = p['lon'] - lon
        return math.sqrt(dlat * dlat + dlon * dlon)

    return min(points, key=distance)


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== GeoClean Entrance Finder Test ===\n")

    test_coords = [
        (-12.0875, -77.0012, "Lima office building"),
        (40.7484, -73.9857, "Empire State Building, NYC"),
        (51.5014, -0.1419, "Buckingham Palace, London"),
    ]

    for lat, lon, label in test_coords:
        print(f"Location: {label} ({lat}, {lon})")
        result = find_entrance(lat, lon)
        print(f"  Result: lat={result['lat']:.6f}, lon={result['lon']:.6f}")
        print(f"  Precision: {result['precision']}, Source: {result['source']}")
        if result['entrance_type']:
            print(f"  Entrance type: {result['entrance_type']}")
        print()
