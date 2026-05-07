"""
Country-Aware Logic Module
Handles country-specific postal code formats and geocoding adjustments.
Treats postal code as a global field — does not assume US ZIP format.
"""

import re
from typing import Dict, Optional


# Country-specific postal code patterns
POSTAL_PATTERNS = {
    'PE': r'^\d{5}$',                          # Peru: 5 digits (e.g., 15036)
    'US': r'^\d{5}(-\d{4})?$',                 # US: ZIP (e.g., 10001 or 10001-1234)
    'CA': r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$',      # Canada: A1A 1A1
    'GB': r'^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$',  # UK: SW1A 2AA
    'DE': r'^\d{5}$',                          # Germany: 5 digits
    'FR': r'^\d{5}$',                          # France: 5 digits
    'NL': r'^\d{4}\s?[A-Z]{2}$',              # Netherlands: 1234 AB
    'BE': r'^\d{4}$',                          # Belgium: 4 digits
    'BR': r'^\d{5}-?\d{3}$',                   # Brazil: 12345-678
    'MX': r'^\d{5}$',                          # Mexico: 5 digits
    'CO': r'^\d{6}$',                          # Colombia: 6 digits
    'CL': r'^\d{7}$',                          # Chile: 7 digits
    'AU': r'^\d{4}$',                          # Australia: 4 digits
    'JP': r'^\d{3}-?\d{4}$',                   # Japan: 123-4567
}

# Peru-specific districts in Lima
LIMA_DISTRICTS = [
    'Miraflores', 'San Isidro', 'Surco', 'Santiago de Surco', 'La Molina',
    'San Borja', 'Barranco', 'Jesús María', 'Lince', 'Magdalena',
    'Pueblo Libre', 'San Miguel', 'Breña', 'Rimac', 'Cercado de Lima',
    'Lima', 'Ate', 'Santa Anita', 'El Agustino', 'San Juan de Lurigancho',
    'Comas', 'Los Olivos', 'Independencia', 'San Martín de Porres',
    'Callao', 'La Victoria', 'Surquillo', 'Chorrillos', 'Villa El Salvador',
    'Villa María del Triunfo', 'San Juan de Miraflores', 'Lurín',
    'Pachacámac', 'Chaclacayo', 'Chosica', 'Carabayllo', 'Puente Piedra',
]


def validate_postal_code(postal_code: str, country_code: str) -> bool:
    """
    Validate a postal code against the expected format for a country.

    Args:
        postal_code: The postal code string to validate.
        country_code: ISO 3166-1 alpha-2 country code.

    Returns:
        True if the postal code matches the expected format.
    """
    if not postal_code or not country_code:
        return False

    pattern = POSTAL_PATTERNS.get(country_code.upper())
    if not pattern:
        # Unknown country — accept any non-empty postal code
        return bool(postal_code.strip())

    return bool(re.match(pattern, postal_code.strip().upper()))


def detect_country_from_postal(postal_code: str) -> Optional[str]:
    """
    Attempt to detect the country from a postal code format.
    Returns the most likely country code, or None if ambiguous.
    """
    if not postal_code:
        return None

    pc = postal_code.strip().upper()

    # UK format is distinctive
    if re.match(r'^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$', pc):
        return 'GB'

    # Canadian format is distinctive
    if re.match(r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$', pc):
        return 'CA'

    # Netherlands format
    if re.match(r'^\d{4}\s?[A-Z]{2}$', pc):
        return 'NL'

    # Brazil format
    if re.match(r'^\d{5}-\d{3}$', pc):
        return 'BR'

    # Japan format
    if re.match(r'^\d{3}-\d{4}$', pc):
        return 'JP'

    # 5-digit codes are ambiguous (US, DE, FR, PE, MX)
    # Cannot determine without additional context
    return None


def apply_country_adjustments(
    result: Dict,
    country_code: str,
    input_city: str = '',
) -> Dict:
    """
    Apply country-specific adjustments to a geocoding result.

    For Peru:
        - Prioritize district matching
        - Ensure city = "Lima" when address is in Lima metropolitan area

    Args:
        result: The geocoding result dictionary to adjust.
        country_code: ISO country code.
        input_city: The city from the input data (for validation).

    Returns:
        Adjusted result dictionary.
    """
    adjusted = dict(result)

    if country_code.upper() == 'PE':
        adjusted = _adjust_peru(adjusted, input_city)

    return adjusted


def _adjust_peru(result: Dict, input_city: str = '') -> Dict:
    """Apply Peru-specific adjustments."""
    city = result.get('city', '')
    district = result.get('district', '')

    # If the district is a known Lima district, ensure city = Lima
    if district:
        for lima_dist in LIMA_DISTRICTS:
            if lima_dist.lower() in district.lower() or district.lower() in lima_dist.lower():
                result['city'] = 'Lima'
                result['district'] = district
                break

    # If city matches a Lima district name, swap city/district
    if city and not district:
        for lima_dist in LIMA_DISTRICTS:
            if lima_dist.lower() == city.lower():
                result['district'] = city
                result['city'] = 'Lima'
                break

    # If input explicitly says Lima, enforce it
    if input_city and 'lima' in input_city.lower():
        result['city'] = 'Lima'

    return result


def get_postal_code_display(postal_code: str, country_code: str) -> str:
    """
    Format a postal code for display according to country conventions.
    """
    if not postal_code:
        return ''

    pc = postal_code.strip()

    if country_code == 'GB':
        # UK: ensure space before last 3 characters
        pc = pc.replace(' ', '')
        if len(pc) > 3:
            return pc[:-3] + ' ' + pc[-3:]
    elif country_code == 'CA':
        # Canada: ensure space in middle
        pc = pc.replace(' ', '')
        if len(pc) == 6:
            return pc[:3] + ' ' + pc[3:]
    elif country_code == 'BR':
        # Brazil: ensure hyphen
        pc = pc.replace('-', '')
        if len(pc) == 8:
            return pc[:5] + '-' + pc[5:]

    return pc


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== GeoClean Country Logic Test ===\n")

    # Postal code validation
    tests = [
        ('15036', 'PE', True),
        ('10001', 'US', True),
        ('M5V 2T6', 'CA', True),
        ('SW1A 2AA', 'GB', True),
        ('12345', 'DE', True),
        ('1234 AB', 'NL', True),
        ('ABC', 'US', False),
    ]

    print("Postal Code Validation:")
    for pc, cc, expected in tests:
        result = validate_postal_code(pc, cc)
        status = '✅' if result == expected else '❌'
        print(f"  {status} {pc} ({cc}) → {result}")

    print("\nCountry Detection:")
    detect_tests = ['SW1A 2AA', 'M5V 2T6', '1234 AB', '12345-678', '10001']
    for pc in detect_tests:
        detected = detect_country_from_postal(pc)
        print(f"  {pc} → {detected or 'ambiguous'}")

    print("\nPeru Adjustments:")
    test_result = {'city': 'San Isidro', 'district': '', 'postal_code': '15036'}
    adjusted = apply_country_adjustments(test_result, 'PE', 'Lima')
    print(f"  Input city='San Isidro' → city='{adjusted['city']}', district='{adjusted['district']}'")
