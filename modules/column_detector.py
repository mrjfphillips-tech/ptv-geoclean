"""
Column Auto-Detection Module
Automatically matches uploaded file columns to required GeoClean fields
using fuzzy string matching and common naming patterns.
"""

from typing import Dict, List, Optional
from rapidfuzz import fuzz, process
import pandas as pd
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

    # Words that indicate a column is NOT an address field — if a column's
    # non-matching words contain these, it's probably something else entirely.
    # e.g., "Order Number" has "order" which signals it's an order field, not a street number.
    NON_ADDRESS_INDICATORS = {
        'order', 'tracking', 'phone', 'email', 'date', 'time', 'timestamp',
        'id', 'code', 'status', 'type', 'flag', 'count', 'total', 'amount',
        'price', 'cost', 'weight', 'volume', 'quantity', 'qty', 'service',
        'delivery', 'default', 'schedule', 'hub', 'origin', 'box', 'millis',
        'timezone', 'tz', 'created', 'updated', 'modified', 'version',
    }

    # For these fields, require stronger evidence before matching
    # (these are the ones most prone to false positives)
    STRICT_FIELDS = {'number', 'city', 'street', 'state', 'neighborhood', 'postal_code', 'country'}

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
                    # For strict fields, verify the match isn't a false positive
                    # e.g., "default delivery date" contains "delivery" but isn't a street
                    if field in STRICT_FIELDS:
                        col_words = set(re.split(r'[\s_\-./]+', col_norm))
                        if col_words & NON_ADDRESS_INDICATORS:
                            # Has disqualifying words — only match if the FULL pattern matches
                            if pattern != col_norm:
                                continue
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
                # For strict fields, check if non-matching words are "non-address" indicators
                # e.g., "Order Number" → col_words = {order, number} → "order" is a non-address indicator
                if field in STRICT_FIELDS:
                    non_match_words = col_words - set(p for pattern in patterns for p in re.split(r'[\s_\-./]+', pattern))
                    if non_match_words & NON_ADDRESS_INDICATORS:
                        continue  # Skip this column for this field entirely

                for pattern in patterns:
                    pattern_words = set(re.split(r'[\s_\-./]+', pattern))
                    # If any word in the column matches any word in the pattern
                    common = col_words & pattern_words
                    if common:
                        # For strict fields, require the PRIMARY word to match, not just a qualifier
                        # e.g., for field "city", the word "city" itself must be in common, not just "customer"
                        if field in STRICT_FIELDS:
                            # The field name itself (or a core synonym) must be the matching word
                            core_words = set(re.split(r'[\s_\-./]+', field))  # e.g., {'city'}, {'number'}
                            if not (common & core_words) and not any(p == col_norm for p in patterns):
                                # Check if any of the common words is actually the field's semantic name
                                field_semantic = {field, field + 's'}  # "city", "cities" etc.
                                if not (common & field_semantic):
                                    continue  # Skip — the match is on a qualifier, not the field name

                        # Score based on how many words match
                        score = 75 + (len(common) / max(len(col_words), len(pattern_words))) * 20
                        if score > best_score:
                            best_score = score
                            best_match = col
                        break

            # Strategy 4: Fuzzy match against all patterns (lower threshold)
            if best_score < MIN_MATCH_SCORE:
                # For strict fields, require higher fuzzy threshold to avoid false positives
                fuzzy_threshold = 80 if field in STRICT_FIELDS else MIN_MATCH_SCORE

                result = process.extractOne(col_norm, patterns, scorer=fuzz.ratio)
                if result and result[1] > best_score and result[1] >= fuzzy_threshold:
                    best_score = result[1]
                    best_match = col

                # Also try token_sort_ratio for multi-word columns
                result2 = process.extractOne(col_norm, patterns, scorer=fuzz.token_sort_ratio)
                if result2 and result2[1] > best_score and result2[1] >= fuzzy_threshold:
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


def get_mode(
    detected: Dict[str, Optional[str]],
    mapping: Optional[Dict[str, str]] = None,
    df: Optional[pd.DataFrame] = None,
) -> str:
    """
    Determine the processing mode based on detected columns.

    Mode priority (highest to lowest):
        "decompose" — lat/lon + combined address + no structured fields → reverse geocode to extract components
        "verify" — has existing lat/lon, will verify against geocode
        "geocode" — no existing coords, will geocode from address
        "insufficient" — not enough data to process

    Args:
        detected: Dictionary of auto-detected column mappings.
        mapping: Optional finalized column mapping dict (with user overrides).
                 Required for "decompose" mode detection.
        df: Optional uploaded DataFrame. Required for "decompose" mode detection.

    Returns:
        One of "decompose", "verify", "geocode", or "insufficient".
    """
    # Check for decompose mode (highest priority) when mapping and df are provided
    if mapping is not None and df is not None:
        if is_single_cell_condition(mapping, df):
            return "decompose"

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


def _is_mapped(mapping: Dict[str, str], field: str) -> bool:
    """
    Check if a field is considered "mapped" in the column mapping dict.
    A field is unmapped if it is absent, None, empty string, or "(none)".
    """
    value = mapping.get(field)
    if value is None:
        return False
    if isinstance(value, str) and (value.strip() == "" or value.strip().lower() == "(none)"):
        return False
    return True


def _column_has_valid_values(df: pd.DataFrame, col_name: str) -> bool:
    """
    Check if a column in the DataFrame has at least one non-empty, non-NaN value.
    """
    if col_name not in df.columns:
        return False
    series = df[col_name]
    # Drop NaN/None values, then check for non-empty strings
    for val in series.dropna():
        if isinstance(val, str):
            if val.strip() != "":
                return True
        else:
            # Numeric or other non-null value counts as valid
            return True
    return False


def _column_has_valid_numeric(df: pd.DataFrame, col_name: str) -> bool:
    """
    Check if a column has at least one valid numeric value.
    """
    if col_name not in df.columns:
        return False
    series = pd.to_numeric(df[col_name], errors='coerce')
    return series.notna().any()


def is_single_cell_condition(mapping: Dict[str, str], df: pd.DataFrame) -> bool:
    """
    Determine if the Single_Cell_Condition is met:
    - Latitude column is mapped and contains at least one valid numeric value
    - Longitude column is mapped and contains at least one valid numeric value
    - Address column is mapped and contains at least one non-empty, non-NaN value
    - NO separate street, city, state, or postal_code columns are mapped
      (or their mapped columns contain only empty/NaN values)

    A column is considered "unmapped" if its mapping value is None, empty string,
    or "(none)" (case-insensitive).

    Args:
        mapping: The finalized column mapping dict from the UI (keys: 'latitude',
                 'longitude', 'address', 'street', 'city', 'state', 'postal_code')
        df: The uploaded DataFrame

    Returns:
        True if Single_Cell_Condition is met.
    """
    # Check latitude is mapped with valid numeric values
    if not _is_mapped(mapping, 'latitude'):
        return False
    if not _column_has_valid_numeric(df, mapping['latitude']):
        return False

    # Check longitude is mapped with valid numeric values
    if not _is_mapped(mapping, 'longitude'):
        return False
    if not _column_has_valid_numeric(df, mapping['longitude']):
        return False

    # Check address is mapped with at least one non-empty value
    if not _is_mapped(mapping, 'address'):
        return False
    if not _column_has_valid_values(df, mapping['address']):
        return False

    # Check NO separate structured fields are mapped
    structured_fields = ['street', 'city', 'state', 'postal_code']
    for field in structured_fields:
        if _is_mapped(mapping, field):
            # Field is mapped — check if it has actual non-empty values
            col_name = mapping[field]
            if _column_has_valid_values(df, col_name):
                return False

    return True


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
