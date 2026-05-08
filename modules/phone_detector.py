"""
Phone Number Detector Module
Extracts country information from phone numbers to help with geocoding.
Handles messy formats: multiple numbers separated by /, spaces, dashes, parentheses.
"""

import re
from typing import Dict, Optional, List


# Country codes mapped to ISO 2-letter codes
# Ordered by specificity (longer codes first to avoid false matches)
COUNTRY_CODES = {
    '1684': 'AS',   # American Samoa
    '1787': 'PR',   # Puerto Rico
    '1939': 'PR',   # Puerto Rico
    '355': 'AL',    # Albania
    '213': 'DZ',    # Algeria
    '376': 'AD',    # Andorra
    '244': 'AO',    # Angola
    '54': 'AR',     # Argentina
    '61': 'AU',     # Australia
    '43': 'AT',     # Austria
    '32': 'BE',     # Belgium
    '591': 'BO',    # Bolivia
    '55': 'BR',     # Brazil
    '56': 'CL',     # Chile
    '86': 'CN',     # China
    '57': 'CO',     # Colombia
    '506': 'CR',    # Costa Rica
    '53': 'CU',     # Cuba
    '45': 'DK',     # Denmark
    '593': 'EC',    # Ecuador
    '20': 'EG',     # Egypt
    '503': 'SV',    # El Salvador
    '358': 'FI',    # Finland
    '33': 'FR',     # France
    '49': 'DE',     # Germany
    '30': 'GR',     # Greece
    '502': 'GT',    # Guatemala
    '504': 'HN',    # Honduras
    '852': 'HK',    # Hong Kong
    '36': 'HU',     # Hungary
    '91': 'IN',     # India
    '62': 'ID',     # Indonesia
    '353': 'IE',    # Ireland
    '972': 'IL',    # Israel
    '39': 'IT',     # Italy
    '81': 'JP',     # Japan
    '254': 'KE',    # Kenya
    '52': 'MX',     # Mexico
    '212': 'MA',    # Morocco
    '31': 'NL',     # Netherlands
    '64': 'NZ',     # New Zealand
    '234': 'NG',    # Nigeria
    '47': 'NO',     # Norway
    '507': 'PA',    # Panama
    '595': 'PY',    # Paraguay
    '51': 'PE',     # Peru
    '63': 'PH',     # Philippines
    '48': 'PL',     # Poland
    '351': 'PT',    # Portugal
    '40': 'RO',     # Romania
    '7': 'RU',      # Russia
    '966': 'SA',    # Saudi Arabia
    '65': 'SG',     # Singapore
    '27': 'ZA',     # South Africa
    '82': 'KR',     # South Korea
    '34': 'ES',     # Spain
    '46': 'SE',     # Sweden
    '41': 'CH',     # Switzerland
    '66': 'TH',     # Thailand
    '90': 'TR',     # Turkey
    '971': 'AE',    # UAE
    '44': 'GB',     # United Kingdom
    '1': 'US',      # United States / Canada
    '598': 'UY',    # Uruguay
    '58': 'VE',     # Venezuela
    '84': 'VN',     # Vietnam
    '237': 'CM',    # Cameroon
}

# US area codes mapped to states (subset of most common)
US_AREA_CODES = {
    '201': 'NJ', '202': 'DC', '203': 'CT', '205': 'AL', '206': 'WA',
    '207': 'ME', '208': 'ID', '209': 'CA', '210': 'TX', '212': 'NY',
    '213': 'CA', '214': 'TX', '215': 'PA', '216': 'OH', '217': 'IL',
    '218': 'MN', '219': 'IN', '224': 'IL', '225': 'LA', '228': 'MS',
    '229': 'GA', '231': 'MI', '234': 'OH', '239': 'FL', '240': 'MD',
    '248': 'MI', '251': 'AL', '252': 'NC', '253': 'WA', '254': 'TX',
    '256': 'AL', '260': 'IN', '262': 'WI', '267': 'PA', '269': 'MI',
    '270': 'KY', '276': 'VA', '281': 'TX', '301': 'MD', '302': 'DE',
    '303': 'CO', '304': 'WV', '305': 'FL', '307': 'WY', '308': 'NE',
    '309': 'IL', '310': 'CA', '312': 'IL', '313': 'MI', '314': 'MO',
    '315': 'NY', '316': 'KS', '317': 'IN', '318': 'LA', '319': 'IA',
    '320': 'MN', '321': 'FL', '323': 'CA', '325': 'TX', '330': 'OH',
    '331': 'IL', '334': 'AL', '336': 'NC', '337': 'LA', '339': 'MA',
    '340': 'VI', '346': 'TX', '347': 'NY', '351': 'MA', '352': 'FL',
    '360': 'WA', '361': 'TX', '385': 'UT', '386': 'FL', '401': 'RI',
    '402': 'NE', '404': 'GA', '405': 'OK', '406': 'MT', '407': 'FL',
    '408': 'CA', '409': 'TX', '410': 'MD', '412': 'PA', '413': 'MA',
    '414': 'WI', '415': 'CA', '417': 'MO', '419': 'OH', '423': 'TN',
    '424': 'CA', '425': 'WA', '430': 'TX', '432': 'TX', '434': 'VA',
    '435': 'UT', '440': 'OH', '442': 'CA', '443': 'MD', '469': 'TX',
    '470': 'GA', '475': 'CT', '478': 'GA', '479': 'AR', '480': 'AZ',
    '484': 'PA', '501': 'AR', '502': 'KY', '503': 'OR', '504': 'LA',
    '505': 'NM', '507': 'MN', '508': 'MA', '509': 'WA', '510': 'CA',
    '512': 'TX', '513': 'OH', '515': 'IA', '516': 'NY', '517': 'MI',
    '518': 'NY', '520': 'AZ', '530': 'CA', '531': 'NE', '534': 'WI',
    '539': 'OK', '540': 'VA', '541': 'OR', '551': 'NJ', '559': 'CA',
    '561': 'FL', '562': 'CA', '563': 'IA', '567': 'OH', '570': 'PA',
    '571': 'VA', '573': 'MO', '574': 'IN', '575': 'NM', '580': 'OK',
    '585': 'NY', '586': 'MI', '601': 'MS', '602': 'AZ', '603': 'NH',
    '605': 'SD', '606': 'KY', '607': 'NY', '608': 'WI', '609': 'NJ',
    '610': 'PA', '612': 'MN', '614': 'OH', '615': 'TN', '616': 'MI',
    '617': 'MA', '618': 'IL', '619': 'CA', '620': 'KS', '623': 'AZ',
    '626': 'CA', '628': 'CA', '629': 'TN', '630': 'IL', '631': 'NY',
    '636': 'MO', '641': 'IA', '646': 'NY', '650': 'CA', '651': 'MN',
    '657': 'CA', '660': 'MO', '661': 'CA', '662': 'MS', '667': 'MD',
    '669': 'CA', '678': 'GA', '681': 'WV', '682': 'TX', '701': 'ND',
    '702': 'NV', '703': 'VA', '704': 'NC', '706': 'GA', '707': 'CA',
    '708': 'IL', '712': 'IA', '713': 'TX', '714': 'CA', '715': 'WI',
    '716': 'NY', '717': 'PA', '718': 'NY', '719': 'CO', '720': 'CO',
    '724': 'PA', '725': 'NV', '727': 'FL', '731': 'TN', '732': 'NJ',
    '734': 'MI', '737': 'TX', '740': 'OH', '743': 'NC', '747': 'CA',
    '754': 'FL', '757': 'VA', '760': 'CA', '762': 'GA', '763': 'MN',
    '765': 'IN', '769': 'MS', '770': 'GA', '772': 'FL', '773': 'IL',
    '774': 'MA', '775': 'NV', '779': 'IL', '781': 'MA', '785': 'KS',
    '786': 'FL', '801': 'UT', '802': 'VT', '803': 'SC', '804': 'VA',
    '805': 'CA', '806': 'TX', '808': 'HI', '810': 'MI', '812': 'IN',
    '813': 'FL', '814': 'PA', '815': 'IL', '816': 'MO', '817': 'TX',
    '818': 'CA', '828': 'NC', '830': 'TX', '831': 'CA', '832': 'TX',
    '843': 'SC', '845': 'NY', '847': 'IL', '848': 'NJ', '850': 'FL',
    '856': 'NJ', '857': 'MA', '858': 'CA', '859': 'KY', '860': 'CT',
    '862': 'NJ', '863': 'FL', '864': 'SC', '865': 'TN', '870': 'AR',
    '872': 'IL', '878': 'PA', '901': 'TN', '903': 'TX', '904': 'FL',
    '906': 'MI', '907': 'AK', '908': 'NJ', '909': 'CA', '910': 'NC',
    '912': 'GA', '913': 'KS', '914': 'NY', '915': 'TX', '916': 'CA',
    '917': 'NY', '918': 'OK', '919': 'NC', '920': 'WI', '925': 'CA',
    '928': 'AZ', '929': 'NY', '931': 'TN', '936': 'TX', '937': 'OH',
    '938': 'AL', '940': 'TX', '941': 'FL', '947': 'MI', '949': 'CA',
    '951': 'CA', '952': 'MN', '954': 'FL', '956': 'TX', '959': 'CT',
    '970': 'CO', '971': 'OR', '972': 'TX', '973': 'NJ', '978': 'MA',
    '979': 'TX', '980': 'NC', '984': 'NC', '985': 'LA',
}


def detect_country_from_phone(phone_field: str) -> Dict[str, Optional[str]]:
    """
    Extract country information from a phone number field.
    Handles messy formats: multiple numbers, separators, parentheses, etc.

    Args:
        phone_field: Raw phone field content (may contain multiple numbers, /, etc.)

    Returns:
        Dictionary with:
            - country_code: ISO 2-letter code (e.g., "PE", "US") or None
            - country_name: Full country name or None
            - region_hint: State/region if detectable (US area codes) or None
            - cleaned_phone: First cleaned phone number
            - confidence: "high" (explicit +country code) or "low" (inferred)
    """
    if not phone_field:
        return _empty_phone_result()

    text = str(phone_field).strip()
    if not text or text.lower() in ('nan', 'none', 'n/a', '-'):
        return _empty_phone_result()

    # Split on common separators for multiple numbers
    # e.g., "555-1234 / 555-5678" or "555-1234; 555-5678"
    numbers = re.split(r'[/;|]', text)
    first_number = numbers[0].strip()

    # Clean the number: remove everything except digits and +
    cleaned = re.sub(r'[^\d+]', '', first_number)

    # If starts with +, extract country code
    if cleaned.startswith('+'):
        digits = cleaned[1:]  # Remove the +
        return _match_country_code(digits)

    # If starts with 00 (international prefix in many countries)
    if cleaned.startswith('00') and len(cleaned) > 4:
        digits = cleaned[2:]
        return _match_country_code(digits)

    # If starts with 011 (US international prefix)
    if cleaned.startswith('011') and len(cleaned) > 5:
        digits = cleaned[3:]
        return _match_country_code(digits)

    # No explicit country code — try to infer from length and pattern
    # 10 digits starting with area code → likely US/Canada
    if len(cleaned) == 10 and cleaned[0] in '2345678':
        area_code = cleaned[:3]
        state = US_AREA_CODES.get(area_code)
        return {
            'country_code': 'US',
            'country_name': 'United States',
            'region_hint': state,
            'cleaned_phone': cleaned,
            'confidence': 'low',
        }

    # 11 digits starting with 1 → US/Canada with country code
    if len(cleaned) == 11 and cleaned[0] == '1':
        area_code = cleaned[1:4]
        state = US_AREA_CODES.get(area_code)
        return {
            'country_code': 'US',
            'country_name': 'United States',
            'region_hint': state,
            'cleaned_phone': cleaned,
            'confidence': 'high',
        }

    # 9 digits starting with 9 → likely Peru mobile
    if len(cleaned) == 9 and cleaned[0] == '9':
        return {
            'country_code': 'PE',
            'country_name': 'Peru',
            'region_hint': None,
            'cleaned_phone': cleaned,
            'confidence': 'low',
        }

    # Can't determine
    return {
        'country_code': None,
        'country_name': None,
        'region_hint': None,
        'cleaned_phone': cleaned,
        'confidence': 'none',
    }


def _match_country_code(digits: str) -> Dict[str, Optional[str]]:
    """Match digits against known country codes (longest match first)."""
    # Try 4-digit, then 3-digit, then 2-digit, then 1-digit codes
    for length in [4, 3, 2, 1]:
        prefix = digits[:length]
        if prefix in COUNTRY_CODES:
            cc = COUNTRY_CODES[prefix]
            # For US/Canada, try to get area code
            region = None
            if cc == 'US' and len(digits) >= 4:
                area_code = digits[length:length + 3] if len(digits) > length + 2 else None
                if area_code and area_code in US_AREA_CODES:
                    region = US_AREA_CODES[area_code]

            return {
                'country_code': cc,
                'country_name': _country_name(cc),
                'region_hint': region,
                'cleaned_phone': digits,
                'confidence': 'high',
            }

    return _empty_phone_result()


def _country_name(code: str) -> str:
    """Get country name from ISO code."""
    names = {
        'US': 'United States', 'PE': 'Peru', 'GB': 'United Kingdom',
        'DE': 'Germany', 'FR': 'France', 'ES': 'Spain', 'IT': 'Italy',
        'NL': 'Netherlands', 'BE': 'Belgium', 'BR': 'Brazil',
        'MX': 'Mexico', 'CO': 'Colombia', 'CL': 'Chile', 'AR': 'Argentina',
        'CA': 'Canada', 'AU': 'Australia', 'JP': 'Japan', 'CN': 'China',
        'IN': 'India', 'ZA': 'South Africa', 'AE': 'UAE',
    }
    return names.get(code, code)


def _empty_phone_result() -> Dict[str, Optional[str]]:
    return {
        'country_code': None,
        'country_name': None,
        'region_hint': None,
        'cleaned_phone': '',
        'confidence': 'none',
    }


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Phone Detector Test ===\n")

    tests = [
        "+51 987 654 321",
        "+1 (615) 555-1234",
        "615-555-1234",
        "+44 20 7946 0958",
        "987654321 / 912345678",
        "+49 30 12345678",
        "(01) 555-1234",
        "+51-1-4567890",
        "None",
        "",
        "555.123.4567",
    ]

    for t in tests:
        r = detect_country_from_phone(t)
        cc = r['country_code'] or '??'
        conf = r['confidence']
        region = f" ({r['region_hint']})" if r['region_hint'] else ''
        print(f"  {t:30s} → {cc}{region:6s} [{conf}]")
