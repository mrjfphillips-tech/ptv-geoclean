"""
Geolocation Verifier Module
When input data already contains lat/lon, this module verifies the existing
coordinates against a fresh geocode and flags discrepancies.

Logic:
- If existing coords are within threshold of geocoded coords → "Verified"
- If they differ significantly → "Discrepancy Found" with suggestion + map link
- User decides whether to keep original or accept suggestion
"""

import math
from typing import Dict, Optional, Tuple


# Distance threshold in meters — below this, coordinates are considered matching
VERIFICATION_THRESHOLD_METERS = 150

# Large discrepancy threshold — above this, it's definitely wrong
LARGE_DISCREPANCY_METERS = 1000


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points on Earth in meters.
    Uses the Haversine formula.
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def verify_coordinates(
    existing_lat: float,
    existing_lon: float,
    geocoded_lat: float,
    geocoded_lon: float,
    address: str = '',
) -> Dict:
    """
    Compare existing coordinates against freshly geocoded coordinates.

    Args:
        existing_lat: Latitude from the input data
        existing_lon: Longitude from the input data
        geocoded_lat: Latitude from Azure Maps geocoding
        geocoded_lon: Longitude from Azure Maps geocoding
        address: Original address string (for map link)

    Returns:
        Dictionary with:
            - status: "verified" | "discrepancy" | "large_discrepancy" | "no_geocode"
            - distance_meters: Distance between the two points
            - existing_lat/lon: Original coordinates
            - suggested_lat/lon: Geocoded coordinates
            - use_existing: Whether to keep the original (True) or suggest change (False)
            - map_link_existing: Google Maps link for existing coords
            - map_link_suggested: Google Maps link for suggested coords
            - map_link_compare: Google Maps link showing both points
            - message: Human-readable explanation
    """
    # If no geocoded result available
    if geocoded_lat == 0.0 and geocoded_lon == 0.0:
        return {
            'status': 'no_geocode',
            'distance_meters': 0,
            'existing_lat': existing_lat,
            'existing_lon': existing_lon,
            'suggested_lat': existing_lat,
            'suggested_lon': existing_lon,
            'use_existing': True,
            'map_link_existing': _google_maps_link(existing_lat, existing_lon),
            'map_link_suggested': '',
            'map_link_compare': '',
            'message': 'Could not geocode address for verification. Keeping existing coordinates.',
        }

    # Calculate distance
    distance = haversine_distance(existing_lat, existing_lon, geocoded_lat, geocoded_lon)

    map_existing = _google_maps_link(existing_lat, existing_lon)
    map_suggested = _google_maps_link(geocoded_lat, geocoded_lon)
    map_compare = _google_maps_compare_link(existing_lat, existing_lon, geocoded_lat, geocoded_lon)

    if distance <= VERIFICATION_THRESHOLD_METERS:
        return {
            'status': 'verified',
            'distance_meters': round(distance, 1),
            'existing_lat': existing_lat,
            'existing_lon': existing_lon,
            'suggested_lat': geocoded_lat,
            'suggested_lon': geocoded_lon,
            'use_existing': True,
            'map_link_existing': map_existing,
            'map_link_suggested': map_suggested,
            'map_link_compare': map_compare,
            'message': f'✓ Verified — existing coordinates are within {round(distance)}m of geocoded result.',
        }
    elif distance <= LARGE_DISCREPANCY_METERS:
        return {
            'status': 'discrepancy',
            'distance_meters': round(distance, 1),
            'existing_lat': existing_lat,
            'existing_lon': existing_lon,
            'suggested_lat': geocoded_lat,
            'suggested_lon': geocoded_lon,
            'use_existing': True,  # Keep existing by default, user decides
            'map_link_existing': map_existing,
            'map_link_suggested': map_suggested,
            'map_link_compare': map_compare,
            'message': f'⚠ Discrepancy — {round(distance)}m difference. Review suggested coordinates.',
        }
    else:
        return {
            'status': 'large_discrepancy',
            'distance_meters': round(distance, 1),
            'existing_lat': existing_lat,
            'existing_lon': existing_lon,
            'suggested_lat': geocoded_lat,
            'suggested_lon': geocoded_lon,
            'use_existing': False,  # Suggest using geocoded coords
            'map_link_existing': map_existing,
            'map_link_suggested': map_suggested,
            'map_link_compare': map_compare,
            'message': f'❌ Error found — {round(distance)}m difference! Suggested coordinates likely more accurate.',
        }


def has_existing_coordinates(lat, lon) -> bool:
    """Check if a row has valid existing coordinates."""
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        # Valid lat: -90 to 90, valid lon: -180 to 180, not zero/zero
        if lat_f == 0.0 and lon_f == 0.0:
            return False
        if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
            return True
    except (ValueError, TypeError):
        pass
    return False


def _google_maps_link(lat: float, lon: float) -> str:
    """Generate a Google Maps link for a single point."""
    return f"https://www.google.com/maps?q={lat},{lon}"


def _google_maps_compare_link(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """Generate a Google Maps directions link to visualize distance between two points."""
    return f"https://www.google.com/maps/dir/{lat1},{lon1}/{lat2},{lon2}"


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== GeoClean Verifier Test ===\n")

    tests = [
        ("Same point", -12.0875, -77.0012, -12.0875, -77.0012),
        ("50m apart (verified)", -12.0875, -77.0012, -12.0879, -77.0012),
        ("500m apart (discrepancy)", -12.0875, -77.0012, -12.0920, -77.0012),
        ("5km apart (large error)", -12.0875, -77.0012, -12.1300, -77.0012),
    ]

    for name, lat1, lon1, lat2, lon2 in tests:
        result = verify_coordinates(lat1, lon1, lat2, lon2)
        print(f"{result['status']:20s} | {name}")
        print(f"  Distance: {result['distance_meters']}m")
        print(f"  {result['message']}")
        print(f"  Compare: {result['map_link_compare']}")
        print()
