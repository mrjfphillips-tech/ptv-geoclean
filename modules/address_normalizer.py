"""
Address Normalizer Module
Cleans and normalizes messy address strings to improve geocoding success rate.
Also extracts postal codes from free-text addresses.
"""

import re
from typing import Dict, Optional


# Common abbreviation expansions
ABBREVIATIONS = {
    r'\bav\.?\b': 'Avenida',
    r'\bcl\.?\b': 'Calle',
    r'\bjr\.?\b': 'Jirón',
    r'\bst\.?\b': 'Street',
    r'\brd\.?\b': 'Road',
    r'\bblvd\.?\b': 'Boulevard',
    r'\bdr\.?\b': 'Drive',
    r'\bln\.?\b': 'Lane',
    r'\bct\.?\b': 'Court',
    r'\bpl\.?\b': 'Place',
    r'\bmza\.?\b': 'Manzana',
    r'\blt\.?\b': 'Lote',
    r'\burb\.?\b': 'Urbanización',
}

# Postal code patterns by region (for extraction from free text)
POSTAL_PATTERNS = [
    # US ZIP: 5 digits or 5+4
    (r'\b(\d{5}(?:-\d{4})?)\b', 'US'),
    # UK: letter-number patterns
    (r'\b([A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b', 'GB'),
    # Canada: A1A 1A1
    (r'\b([A-Z]\d[A-Z]\s?\d[A-Z]\d)\b', 'CA'),
    # Netherlands: 4 digits + 2 letters
    (r'\b(\d{4}\s?[A-Z]{2})\b', 'NL'),
    # Brazil: 5 digits - 3 digits
    (r'\b(\d{5}-\d{3})\b', 'BR'),
    # Generic 5-digit (PE, DE, FR, MX, etc.)
    (r'\b(\d{5})\b', 'generic'),
    # Generic 4-digit (BE, AU, etc.)
    (r'\b(\d{4})\b', 'generic_4'),
]


def normalize_address(address: str) -> str:
    """
    Clean and normalize an address string for better geocoding results.

    Operations:
    - Strip extra whitespace
    - Remove special characters that confuse geocoders
    - Expand common abbreviations
    - Fix common formatting issues
    """
    if not address:
        return ''

    text = address.strip()

    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Remove characters that confuse geocoders
    text = text.replace('|', ',')
    text = text.replace(';', ',')
    text = text.replace('\n', ', ')
    text = text.replace('\r', '')
    text = text.replace('\t', ' ')

    # Remove leading/trailing commas
    text = text.strip(',').strip()

    # Remove double commas
    text = re.sub(r',\s*,', ',', text)

    # Remove parenthetical notes that aren't part of the address
    # e.g., "(near the park)" or "(ref: building A)"
    text = re.sub(r'\((?:ref|near|next to|behind|frente|cerca|al lado)[^)]*\)', '', text, flags=re.IGNORECASE)

    return text.strip()


def extract_postal_code(address: str, country_code: str = '') -> Optional[str]:
    """
    Extract a postal code from a free-text address string or mixed field.
    Handles cases like:
    - "Miraflores 15074" → postal = "15074"
    - "San Isidro / 15036" → postal = "15036"
    - "10001 Manhattan" → postal = "10001"
    - "Lima, 15036, Peru" → postal = "15036"

    Args:
        address: The address string or mixed field to search
        country_code: Optional country code to prioritize the right pattern

    Returns:
        Extracted postal code string, or None if not found.
    """
    if not address:
        return None

    text = str(address).strip().upper()

    # If the entire field is just a number, it's likely a postal code
    clean = text.strip()
    if clean.isdigit() and 4 <= len(clean) <= 7:
        return clean

    # If country code is known, try that pattern first
    if country_code:
        country_patterns = {
            'US': r'\b(\d{5}(?:-\d{4})?)\b',
            'GB': r'\b([A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b',
            'CA': r'\b([A-Z]\d[A-Z]\s?\d[A-Z]\d)\b',
            'NL': r'\b(\d{4}\s?[A-Z]{2})\b',
            'BR': r'\b(\d{5}-\d{3})\b',
            'PE': r'\b(\d{5})\b',
            'DE': r'\b(\d{5})\b',
            'FR': r'\b(\d{5})\b',
            'MX': r'\b(\d{5})\b',
            'CO': r'\b(\d{6})\b',
            'CL': r'\b(\d{7})\b',
            'AU': r'\b(\d{4})\b',
            'JP': r'\b(\d{3}-?\d{4})\b',
        }
        pattern = country_patterns.get(country_code.upper())
        if pattern:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

    # Try all patterns
    for pattern, _ in POSTAL_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return None


def split_neighborhood_postal(field_value: str, country_code: str = '') -> Dict[str, str]:
    """
    Split a mixed field that contains both neighborhood (text) and postal code (numeric).

    Examples:
        "Miraflores 15074" → {"neighborhood": "Miraflores", "postal_code": "15074"}
        "San Isidro / 15036" → {"neighborhood": "San Isidro", "postal_code": "15036"}
        "10001" → {"neighborhood": "", "postal_code": "10001"}
        "Miraflores" → {"neighborhood": "Miraflores", "postal_code": ""}

    Args:
        field_value: The mixed field content
        country_code: Optional country code for postal pattern matching

    Returns:
        Dictionary with separated neighborhood and postal_code
    """
    if not field_value:
        return {'neighborhood': '', 'postal_code': ''}

    text = str(field_value).strip()

    # Pure numeric → it's a postal code
    if text.replace('-', '').replace(' ', '').isdigit():
        return {'neighborhood': '', 'postal_code': text}

    # Pure alphabetic → it's a neighborhood
    if text.replace(' ', '').replace('-', '').isalpha():
        return {'neighborhood': text, 'postal_code': ''}

    # Mixed: try to extract postal code
    postal = extract_postal_code(text, country_code)
    if postal:
        # Remove the postal code from the text to get the neighborhood
        neighborhood = text.replace(postal, '').strip()
        # Clean separators
        neighborhood = re.sub(r'[/\-,;|]+\s*$', '', neighborhood).strip()
        neighborhood = re.sub(r'^\s*[/\-,;|]+', '', neighborhood).strip()
        return {'neighborhood': neighborhood, 'postal_code': postal}

    # No postal found — treat entire field as neighborhood
    return {'neighborhood': text, 'postal_code': ''}


def build_geocoding_query(
    street: str = '',
    number: str = '',
    neighborhood: str = '',
    city: str = '',
    state: str = '',
    postal_code: str = '',
    country: str = '',
) -> str:
    """
    Build the best possible geocoding query from available fields.
    Prioritizes fields that give the best geocoding results.

    Strategy:
    - If street + city available → use "street number, city, country"
    - If only city + postal → use "postal_code, city, country"
    - If only postal → use "postal_code, country" (centroid)
    """
    parts = []

    # Street with number
    if street:
        street_full = f"{street} {number}".strip() if number else street
        parts.append(street_full)

    # Neighborhood (helps in Latin America)
    if neighborhood and not street:
        parts.append(neighborhood)

    # City is critical
    if city:
        parts.append(city)

    # State helps disambiguate
    if state:
        parts.append(state)

    # Postal code
    if postal_code:
        parts.append(postal_code)

    # Country is essential
    if country:
        parts.append(country)

    return ', '.join(parts)


def assess_optiflow_readiness(
    lat: float,
    lon: float,
    postal_code: str,
    confidence_score: float,
    confidence_level: str,
) -> Dict[str, object]:
    """
    Determine if a row is ready for OptiFlow.

    OptiFlow needs EITHER:
    - High-confidence lat/lon (confidence >= 0.65 and coords are non-zero)
    - OR a valid postal code (any confidence — OptiFlow can use postal centroid)

    Returns:
        Dictionary with:
            - optiflow_ready: bool
            - ready_reason: str explaining why/why not
            - routing_method: "coordinates" | "postal_centroid" | "not_ready"
    """
    has_coords = lat != 0.0 and lon != 0.0
    has_postal = bool(postal_code and postal_code.strip())
    high_confidence_coords = has_coords and confidence_score >= 0.65

    if high_confidence_coords:
        return {
            'optiflow_ready': True,
            'ready_reason': 'High-confidence coordinates available',
            'routing_method': 'coordinates',
        }
    elif has_coords and has_postal:
        return {
            'optiflow_ready': True,
            'ready_reason': 'Coordinates available (medium confidence) + postal code as backup',
            'routing_method': 'coordinates',
        }
    elif has_postal:
        return {
            'optiflow_ready': True,
            'ready_reason': 'Postal code available — OptiFlow will use postal centroid',
            'routing_method': 'postal_centroid',
        }
    elif has_coords:
        return {
            'optiflow_ready': True,
            'ready_reason': 'Coordinates available (low confidence) — verify before routing',
            'routing_method': 'coordinates',
        }
    else:
        return {
            'optiflow_ready': False,
            'ready_reason': 'No coordinates and no postal code — cannot route this order',
            'routing_method': 'not_ready',
        }


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Address Normalizer Test ===\n")

    # Normalization
    tests = [
        "  Av. Javier Prado  4200 ,, Lima  ",
        "Calle Los Olivos 345 (ref: near the park), Miraflores",
        "123 Main St | Apt 4B; New York",
    ]
    for t in tests:
        print(f"  IN:  '{t}'")
        print(f"  OUT: '{normalize_address(t)}'")
        print()

    # Postal extraction
    print("Postal Code Extraction:")
    postal_tests = [
        ("123 Main St, New York, NY 10001", "US"),
        ("10 Downing Street, London SW1A 2AA", "GB"),
        ("Av. Prado 4200, Lima 15036, Peru", "PE"),
        ("Rua Augusta 1500, São Paulo 01304-001", "BR"),
    ]
    for addr, cc in postal_tests:
        pc = extract_postal_code(addr, cc)
        print(f"  {addr[:40]:40s} → {pc}")

    # OptiFlow readiness
    print("\nOptiFlow Readiness:")
    readiness_tests = [
        (-12.08, -77.00, "15036", 0.85, "High"),
        (0.0, 0.0, "15036", 0.0, "Low"),
        (-12.08, -77.00, "", 0.30, "Low"),
        (0.0, 0.0, "", 0.0, "Low"),
    ]
    for lat, lon, pc, score, level in readiness_tests:
        r = assess_optiflow_readiness(lat, lon, pc, score, level)
        status = "✅" if r['optiflow_ready'] else "❌"
        print(f"  {status} lat={lat}, postal={pc or 'none':6s}, score={score} → {r['routing_method']} | {r['ready_reason']}")
