"""
Address Pre-Cleaning Module
Fixes common data entry errors before geocoding to improve hit rate.
Also provides simplified address variants for retry attempts.
"""

import re
from typing import List, Optional


def clean_address(address: str) -> str:
    """
    Fix common data entry errors and noise in address strings.
    Applied BEFORE geocoding to improve first-pass success rate.
    """
    if not address:
        return ''

    text = address.strip()

    # Remove common noise prefixes/suffixes
    noise_patterns = [
        r'^(attn|attention|c/o|care of|deliver to|ship to)[:\s]+',
        r'\b(ref|reference|acct|account)[:\s#]*[\w-]+',
        r'\(.*?(phone|tel|fax|ext|mobile|cell).*?\)',
        r'(?:phone|tel|fax|mobile|cell)[:\s]*[\d\s\-\+\(\)]+$',
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Fix common typos in address keywords
    typo_fixes = {
        r'\bstreeet\b': 'Street',
        r'\bstret\b': 'Street',
        r'\bstreet\b': 'Street',
        r'\bavenue\b': 'Avenue',
        r'\bavnue\b': 'Avenue',
        r'\bavenu\b': 'Avenue',
        r'\bboulevard\b': 'Boulevard',
        r'\bblvd\b': 'Boulevard',
        r'\bdrive\b': 'Drive',
        r'\bdrve\b': 'Drive',
        r'\broad\b': 'Road',
        r'\blane\b': 'Lane',
        r'\bcourt\b': 'Court',
        r'\bcircle\b': 'Circle',
        r'\bplace\b': 'Place',
        r'\bway\b': 'Way',
    }
    for pattern, replacement in typo_fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Remove excessive punctuation
    text = re.sub(r'[#]+', '', text)  # Remove # signs (often noise)
    text = re.sub(r'\s{2,}', ' ', text)  # Collapse multiple spaces
    text = re.sub(r',{2,}', ',', text)  # Collapse multiple commas
    text = text.strip(' ,.-;:')

    # Fix transposed/doubled characters in numbers
    # e.g., "123 45" → "12345" if it looks like a postal code at the end
    # (handled by postal extractor, not here)

    return text.strip()


def generate_retry_variants(address: str) -> List[str]:
    """
    Generate simplified address variants for retry when the original fails.
    Each variant removes one layer of complexity.

    Returns list of progressively simpler addresses to try.
    """
    variants = []

    # Variant 1: Remove apartment/unit info
    unit_patterns = [
        r'\b(?:apt|apartment|unit|suite|ste|#|room|rm|floor|fl)\s*[#.]?\s*\w+',
        r'\b(?:dpto|depto|departamento|torre|int|oficina|piso)\s*[#.]?\s*\w+',
    ]
    simplified = address
    for pattern in unit_patterns:
        simplified = re.sub(pattern, '', simplified, flags=re.IGNORECASE)
    simplified = re.sub(r'\s{2,}', ' ', simplified).strip(' ,')
    if simplified != address and simplified:
        variants.append(simplified)

    # Variant 2: Remove parenthetical content
    no_parens = re.sub(r'\([^)]*\)', '', address)
    no_parens = re.sub(r'\s{2,}', ' ', no_parens).strip(' ,')
    if no_parens != address and no_parens and no_parens not in variants:
        variants.append(no_parens)

    # Variant 3: Just street + city (drop state, postal, country)
    # Split on commas and take first 2 parts
    parts = [p.strip() for p in address.split(',') if p.strip()]
    if len(parts) >= 2:
        short = f"{parts[0]}, {parts[1]}"
        if short not in variants:
            variants.append(short)

    # Variant 4: Just the first part (street only)
    if parts:
        street_only = parts[0].strip()
        if len(street_only) > 5 and street_only not in variants:
            variants.append(street_only)

    return variants


def detect_country_from_address(address: str) -> Optional[str]:
    """
    Try to infer country from address content when no country column exists.
    Uses postal code format, city names, and address patterns.
    """
    if not address:
        return None

    text = address.lower()

    # US indicators
    us_states = [
        'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
        'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
        'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
        'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
        'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
        'new hampshire', 'new jersey', 'new mexico', 'new york',
        'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
        'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
        'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
        'west virginia', 'wisconsin', 'wyoming',
    ]
    us_abbrevs = [
        'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
        'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
        'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
        'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
        'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy',
    ]

    # Check for US state names
    for state in us_states:
        if state in text:
            return 'US'

    # Check for US state abbreviations (at word boundary, after comma)
    for abbr in us_abbrevs:
        if re.search(rf',\s*{abbr}\b', text):
            return 'US'

    # US ZIP code pattern
    if re.search(r'\b\d{5}(-\d{4})?\b', text):
        # Could be US or other 5-digit countries, but US is most common
        return 'US'

    # UK indicators
    if re.search(r'\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b', address):
        return 'GB'
    if any(x in text for x in ['united kingdom', 'england', 'scotland', 'wales', 'london']):
        return 'GB'

    # Germany
    if any(x in text for x in ['deutschland', 'germany', 'straße', 'strasse']):
        return 'DE'

    # Peru
    if any(x in text for x in ['peru', 'perú', 'lima', 'miraflores', 'surco']):
        return 'PE'

    # Mexico
    if any(x in text for x in ['mexico', 'méxico', 'colonia', 'delegación']):
        return 'MX'

    # Colombia
    if any(x in text for x in ['colombia', 'bogotá', 'bogota', 'medellín', 'medellin']):
        return 'CO'

    # Brazil
    if any(x in text for x in ['brasil', 'brazil', 'são paulo', 'rio de janeiro']):
        return 'BR'

    # France
    if any(x in text for x in ['france', 'paris', 'lyon', 'marseille', 'rue']):
        return 'FR'

    # Canada
    if re.search(r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b', address):
        return 'CA'

    return None


def detect_duplicates(addresses: List[str]) -> dict:
    """
    Find duplicate or near-duplicate addresses in a list.
    Returns a dict mapping normalized address → list of original indices.
    """
    from collections import defaultdict

    normalized_map = defaultdict(list)

    for idx, addr in enumerate(addresses):
        if not addr:
            continue
        # Normalize: lowercase, remove extra spaces, remove punctuation
        norm = re.sub(r'[^\w\s]', '', addr.lower())
        norm = re.sub(r'\s+', ' ', norm).strip()
        normalized_map[norm].append(idx)

    # Only return groups with duplicates
    return {k: v for k, v in normalized_map.items() if len(v) > 1}


def detect_outliers(results: List[dict], threshold_km: float = 500) -> List[int]:
    """
    Find results that are geographic outliers compared to the majority.
    If 95% of results are in one region and a few are far away, flag them.

    Returns list of indices that are outliers.
    """
    import math

    # Collect valid coordinates
    coords = []
    for i, r in enumerate(results):
        lat = r.get('latitude', 0.0)
        lon = r.get('longitude', 0.0)
        if lat != 0.0 and lon != 0.0:
            coords.append((i, lat, lon))

    if len(coords) < 10:
        return []  # Not enough data to detect outliers

    # Calculate centroid of all points
    avg_lat = sum(c[1] for c in coords) / len(coords)
    avg_lon = sum(c[2] for c in coords) / len(coords)

    # Calculate distance from centroid for each point
    def haversine_km(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    distances = [(idx, haversine_km(lat, lon, avg_lat, avg_lon)) for idx, lat, lon in coords]

    # Find the 90th percentile distance
    sorted_dists = sorted(d[1] for d in distances)
    p90 = sorted_dists[int(len(sorted_dists) * 0.9)]

    # Flag anything more than 3x the 90th percentile OR beyond threshold_km
    outlier_threshold = max(threshold_km, p90 * 3)
    outliers = [idx for idx, dist in distances if dist > outlier_threshold]

    return outliers
