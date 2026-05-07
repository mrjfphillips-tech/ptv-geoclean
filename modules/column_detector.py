"""
Column Auto-Detection Module
Automatically matches uploaded file columns to required GeoClean fields
using fuzzy string matching and common naming patterns.
"""

from typing import Dict, List, Optional
from rapidfuzz import fuzz, process


# Required fields and their common column name variations
FIELD_PATTERNS: Dict[str, List[str]] = {
    'address': [
        'address', 'full address', 'full_address', 'freeform address',
        'location', 'delivery address', 'ship to', 'ship_to',
        'direccion', 'dirección', 'adresse', 'endereço',
    ],
    'street': [
        'street', 'street address', 'street_address', 'address line 1',
        'address_line_1', 'addr1', 'line1', 'calle', 'rue', 'straße', 'strasse',
        'road', 'avenue', 'av', 'avenida',
    ],
    'number': [
        'number', 'house number', 'house_number', 'street number',
        'street_number', 'no', 'num', 'número', 'numero',
    ],
    'neighborhood': [
        'neighborhood', 'neighbourhood', 'barrio', 'colonia',
        'district', 'suburb', 'bairro', 'quartier',
    ],
    'city': [
        'city', 'municipality', 'town', 'ciudad', 'ville', 'stadt',
        'cidade', 'localidad', 'locality', 'place',
    ],
    'state': [
        'state', 'province', 'region', 'estado', 'département',
        'bundesland', 'county', 'subdivision', 'dept',
    ],
    'postal_code': [
        'zip', 'zip code', 'zip_code', 'zipcode', 'postal', 'postal code',
        'postal_code', 'postcode', 'post code', 'plz', 'cep', 'cp',
        'código postal', 'codigo postal',
    ],
    'country': [
        'country', 'country name', 'country_name', 'nation',
        'país', 'pais', 'pays', 'land',
    ],
    'latitude': [
        'latitude', 'lat', 'y', 'coord_lat', 'geo_lat',
        'latitud', 'breitengrad',
    ],
    'longitude': [
        'longitude', 'lon', 'lng', 'long', 'x', 'coord_lon', 'geo_lon',
        'longitud', 'längengrad',
    ],
}

# Minimum fuzzy match score to consider a match
MIN_MATCH_SCORE = 70


def detect_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """
    Auto-detect which uploaded columns map to which GeoClean fields.

    Args:
        columns: List of column names from the uploaded file.

    Returns:
        Dictionary mapping field names to detected column names.
        None value means the field was not detected.
    """
    detected: Dict[str, Optional[str]] = {}
    used_columns: set = set()

    # Normalize column names for matching
    col_lower = {col: col.lower().strip() for col in columns}

    for field, patterns in FIELD_PATTERNS.items():
        best_match: Optional[str] = None
        best_score: float = 0

        for col, col_norm in col_lower.items():
            if col in used_columns:
                continue

            # Skip columns that look like IDs or sequence numbers
            if any(skip in col_norm for skip in ['id', 'sequence', 'route', 'vehicle', 'order', 'depot', 'test']):
                if field not in ('address',):  # Only skip for non-address fields too
                    continue
                # For address field, definitely skip ID columns
                if 'id' in col_norm:
                    continue

            # Exact match (case-insensitive)
            if col_norm in patterns:
                best_match = col
                best_score = 100
                break

            # Check if column contains a pattern keyword
            for pattern in patterns:
                if pattern in col_norm or col_norm in pattern:
                    score = fuzz.ratio(col_norm, pattern)
                    if score > best_score:
                        best_score = score
                        best_match = col
                    break

            # Fuzzy match against all patterns
            if best_score < MIN_MATCH_SCORE:
                result = process.extractOne(col_norm, patterns, scorer=fuzz.ratio)
                if result and result[1] > best_score:
                    best_score = result[1]
                    best_match = col

        if best_match and best_score >= MIN_MATCH_SCORE:
            detected[field] = best_match
            used_columns.add(best_match)
        else:
            detected[field] = None

    return detected


def get_detection_summary(detected: Dict[str, Optional[str]]) -> Dict[str, str]:
    """
    Generate a human-readable summary of what was detected.

    Returns:
        Dictionary with field names as keys and status strings as values.
    """
    summary = {}
    for field, col in detected.items():
        if col:
            summary[field] = f"✅ {col}"
        else:
            summary[field] = "❌ Not found"
    return summary


def has_minimum_fields(detected: Dict[str, Optional[str]]) -> bool:
    """
    Check if enough fields were detected to run geocoding.
    Needs at minimum: (address) OR (street + city) OR (latitude + longitude)
    """
    has_full_address = detected.get('address') is not None
    has_street_city = detected.get('street') is not None and detected.get('city') is not None
    has_coords = detected.get('latitude') is not None and detected.get('longitude') is not None

    return has_full_address or has_street_city or has_coords


def get_mode(detected: Dict[str, Optional[str]]) -> str:
    """
    Determine the processing mode based on detected columns.

    Returns:
        "verify" — has existing lat/lon, will verify against geocode
        "geocode" — no existing coords, will geocode from address
        "insufficient" — not enough data to process
    """
    has_coords = detected.get('latitude') is not None and detected.get('longitude') is not None
    has_address = (
        detected.get('address') is not None or
        (detected.get('street') is not None and detected.get('city') is not None)
    )

    if has_coords and has_address:
        return "verify"
    elif has_address:
        return "geocode"
    elif has_coords:
        return "verify"  # Can reverse-geocode to verify
    else:
        return "insufficient"


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Column Auto-Detection Test ===\n")

    # Test with your actual file columns
    test_columns = [
        'Location ID', 'Location Name', 'Street', 'Number', 'Neighborhood',
        'City', 'State', 'Zip Code', 'Country', 'Latitude', 'Longitude',
        'Order ID', 'Depot Name', 'Type of Order', '# of SKUs (Boxes, Pallets, etc)',
        'Weight (kg)', 'Vol (m3)', 'Service Time (in min)', 'Time Window',
        'Route ID', 'Vehicle ID', 'Stop Sequence', 'Delivery Date',
        'Arrival Time', 'Departure Time', 'test 1', 'test 2', 'test 3',
    ]

    detected = detect_columns(test_columns)
    mode = get_mode(detected)
    summary = get_detection_summary(detected)

    print(f"Mode: {mode}\n")
    print("Detected mappings:")
    for field, status in summary.items():
        print(f"  {field:15s} → {status}")

    print(f"\nMinimum fields met: {has_minimum_fields(detected)}")
