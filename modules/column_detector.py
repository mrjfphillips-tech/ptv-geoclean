"""
Column Auto-Detection Module
Automatically matches uploaded file columns to required GeoClean fields
using fuzzy string matching and common naming patterns.
"""

from typing import Dict, List, Optional
from rapidfuzz import fuzz, process
import re


# Required fields and their common column name variations
FIELD_PATTERNS: Dict[str, List[str]] = {
    'address': [
        'address', 'full address', 'full_address', 'freeform address',
        'location', 'delivery address', 'ship to', 'ship_to',
        'direccion', 'dirección', 'adresse', 'endereço',
        'location address', 'customer address', 'order address',
        'destination address', 'dest address', 'ship address',
        'location name', 'site address',
    ],
    'street': [
        'street', 'street address', 'street_address', 'address line 1',
        'address_line_1', 'addr1', 'line1', 'calle', 'rue', 'straße', 'strasse',
        'road', 'avenue', 'av', 'avenida',
        'location street', 'delivery street', 'ship street',
        'address 1', 'address1', 'street name',
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
        'location city', 'delivery city', 'ship city', 'dest city',
        'destination city', 'customer city', 'order city',
    ],
    'state': [
        'state', 'province', 'region', 'estado', 'département',
        'bundesland', 'county', 'subdivision', 'dept',
        'location state', 'delivery state', 'ship state',
    ],
    'postal_code': [
        'zip', 'zip code', 'zip_code', 'zipcode', 'postal', 'postal code',
        'postal_code', 'postcode', 'post code', 'plz', 'cep', 'cp',
        'código postal', 'codigo postal',
        'location zip', 'delivery zip', 'ship zip', 'dest zip',
        'location postal', 'delivery postal',
    ],
    'country': [
        'country', 'country name', 'country_name', 'nation',
        'país', 'pais', 'pays', 'land',
        'location country', 'delivery country', 'ship country',
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

    Uses multiple strategies:
    1. Exact match (case-insensitive)
    2. Column CONTAINS a keyword (e.g., "location city" contains "city")
    3. Keyword CONTAINS the column (e.g., "full address" contains "address")
    4. Fuzzy match as fallback

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

    # Skip patterns — only skip columns that are PURELY these (not compound names)
    skip_exact = {'id', 'row', 'index', 'seq', 'sequence'}

    for field, patterns in FIELD_PATTERNS.items():
        best_match: Optional[str] = None
        best_score: float = 0

        for col, col_norm in col_lower.items():
            if col in used_columns:
                continue

            # Only skip if the column name IS exactly an ID-like word
            if col_norm in skip_exact:
                continue

            # Strategy 1: Exact match (case-insensitive)
            if col_norm in patterns:
                best_match = col
                best_score = 100
                break

            # Strategy 2: Column contains a pattern keyword
            # e.g., "location city" contains "city", "delivery address" contains "address"
            for pattern in patterns:
                # Check if pattern is a word within the column name
                if pattern in col_norm:
                    score = 85 + (len(pattern) / len(col_norm)) * 15  # Longer match = higher score
                    if score > best_score:
                        best_score = score
                        best_match = col
                    break
                # Check if column name is within the pattern
                # e.g., col="city" is within pattern="city"
                if col_norm in pattern:
                    score = 80 + (len(col_norm) / len(pattern)) * 15
                    if score > best_score:
                        best_score = score
                        best_match = col
                    break

            # Strategy 3: Word-level matching
            # Split column into words and check if any word matches a pattern
            if best_score < 80:
                col_words = set(re.split(r'[\s_\-./]+', col_norm))
                for pattern in patterns:
                    pattern_words = set(re.split(r'[\s_\-./]+', pattern))
                    # If any word in the column matches any word in the pattern
                    common = col_words & pattern_words
                    if common:
                        # Score based on how many words match
                        score = 75 + (len(common) / max(len(col_words), len(pattern_words))) * 20
                        if score > best_score:
                            best_score = score
                            best_match = col
                        break

            # Strategy 4: Fuzzy match against all patterns (lower threshold)
            if best_score < MIN_MATCH_SCORE:
                result = process.extractOne(col_norm, patterns, scorer=fuzz.ratio)
                if result and result[1] > best_score:
                    best_score = result[1]
                    best_match = col

                # Also try token_sort_ratio for multi-word columns
                result2 = process.extractOne(col_norm, patterns, scorer=fuzz.token_sort_ratio)
                if result2 and result2[1] > best_score:
                    best_score = result2[1]
                    best_match = col

        if best_match and best_score >= 65:  # Lowered threshold from 70 to 65
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
