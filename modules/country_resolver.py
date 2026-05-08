"""
Country Resolver Module
Converts any country representation (name, code, abbreviation, Spanish/local name)
to a consistent ISO 3166-1 alpha-2 country code.

This is critical for constraining geocoding searches to the correct country.
"""

import re
from typing import Optional


# Comprehensive mapping: lowercase variants → ISO 2-letter code
# Includes English, Spanish, Portuguese, French, German, local names, and common abbreviations
COUNTRY_MAP = {
    # A
    'afghanistan': 'AF', 'albania': 'AL', 'algeria': 'DZ', 'andorra': 'AD',
    'angola': 'AO', 'argentina': 'AR', 'armenia': 'AM', 'australia': 'AU',
    'austria': 'AT', 'azerbaijan': 'AZ',
    # B
    'bahamas': 'BS', 'bahrain': 'BH', 'bangladesh': 'BD', 'barbados': 'BB',
    'belarus': 'BY', 'belgium': 'BE', 'belize': 'BZ', 'benin': 'BJ',
    'bhutan': 'BT', 'bolivia': 'BO', 'bosnia': 'BA', 'botswana': 'BW',
    'brazil': 'BR', 'brunei': 'BN', 'bulgaria': 'BG', 'burkina faso': 'BF',
    # C
    'cambodia': 'KH', 'cameroon': 'CM', 'canada': 'CA', 'chile': 'CL',
    'china': 'CN', 'colombia': 'CO', 'congo': 'CD', 'costa rica': 'CR',
    'croatia': 'HR', 'cuba': 'CU', 'cyprus': 'CY', 'czech republic': 'CZ',
    'czechia': 'CZ',
    # D
    'denmark': 'DK', 'dominican republic': 'DO', 'dominica': 'DM',
    # E
    'ecuador': 'EC', 'egypt': 'EG', 'el salvador': 'SV', 'estonia': 'EE',
    'ethiopia': 'ET',
    # F
    'fiji': 'FJ', 'finland': 'FI', 'france': 'FR',
    # G
    'gabon': 'GA', 'gambia': 'GM', 'georgia': 'GE', 'germany': 'DE',
    'ghana': 'GH', 'greece': 'GR', 'guatemala': 'GT', 'guinea': 'GN',
    'guyana': 'GY',
    # H
    'haiti': 'HT', 'honduras': 'HN', 'hong kong': 'HK', 'hungary': 'HU',
    # I
    'iceland': 'IS', 'india': 'IN', 'indonesia': 'ID', 'iran': 'IR',
    'iraq': 'IQ', 'ireland': 'IE', 'israel': 'IL', 'italy': 'IT',
    'ivory coast': 'CI',
    # J
    'jamaica': 'JM', 'japan': 'JP', 'jordan': 'JO',
    # K
    'kazakhstan': 'KZ', 'kenya': 'KE', 'kuwait': 'KW', 'kyrgyzstan': 'KG',
    # L
    'laos': 'LA', 'latvia': 'LV', 'lebanon': 'LB', 'libya': 'LY',
    'liechtenstein': 'LI', 'lithuania': 'LT', 'luxembourg': 'LU',
    # M
    'madagascar': 'MG', 'malawi': 'MW', 'malaysia': 'MY', 'mali': 'ML',
    'malta': 'MT', 'mauritius': 'MU', 'mexico': 'MX', 'moldova': 'MD',
    'monaco': 'MC', 'mongolia': 'MN', 'montenegro': 'ME', 'morocco': 'MA',
    'mozambique': 'MZ', 'myanmar': 'MM',
    # N
    'namibia': 'NA', 'nepal': 'NP', 'netherlands': 'NL', 'new zealand': 'NZ',
    'nicaragua': 'NI', 'niger': 'NE', 'nigeria': 'NG', 'north korea': 'KP',
    'norway': 'NO',
    # O
    'oman': 'OM',
    # P
    'pakistan': 'PK', 'panama': 'PA', 'papua new guinea': 'PG',
    'paraguay': 'PY', 'peru': 'PE', 'philippines': 'PH', 'poland': 'PL',
    'portugal': 'PT', 'puerto rico': 'PR',
    # Q
    'qatar': 'QA',
    # R
    'romania': 'RO', 'russia': 'RU', 'rwanda': 'RW',
    # S
    'saudi arabia': 'SA', 'senegal': 'SN', 'serbia': 'RS', 'singapore': 'SG',
    'slovakia': 'SK', 'slovenia': 'SI', 'somalia': 'SO', 'south africa': 'ZA',
    'south korea': 'KR', 'spain': 'ES', 'sri lanka': 'LK', 'sudan': 'SD',
    'sweden': 'SE', 'switzerland': 'CH', 'syria': 'SY',
    # T
    'taiwan': 'TW', 'tanzania': 'TZ', 'thailand': 'TH', 'togo': 'TG',
    'trinidad': 'TT', 'trinidad and tobago': 'TT', 'tunisia': 'TN',
    'turkey': 'TR', 'turkmenistan': 'TM',
    # U
    'uganda': 'UG', 'ukraine': 'UA', 'united arab emirates': 'AE',
    'united kingdom': 'GB', 'united states': 'US', 'uruguay': 'UY',
    'uzbekistan': 'UZ',
    # V
    'venezuela': 'VE', 'vietnam': 'VN',
    # Y
    'yemen': 'YE',
    # Z
    'zambia': 'ZM', 'zimbabwe': 'ZW',

    # ─── Spanish names ─────────────────────────────────────────────────────
    'alemania': 'DE', 'argentina': 'AR', 'brasil': 'BR', 'canadá': 'CA',
    'chile': 'CL', 'china': 'CN', 'colombia': 'CO', 'corea del sur': 'KR',
    'costa rica': 'CR', 'cuba': 'CU', 'dinamarca': 'DK', 'ecuador': 'EC',
    'egipto': 'EG', 'emiratos árabes unidos': 'AE', 'españa': 'ES',
    'estados unidos': 'US', 'filipinas': 'PH', 'finlandia': 'FI',
    'francia': 'FR', 'grecia': 'GR', 'guatemala': 'GT', 'holanda': 'NL',
    'honduras': 'HN', 'hungría': 'HU', 'india': 'IN', 'indonesia': 'ID',
    'irlanda': 'IE', 'italia': 'IT', 'japón': 'JP', 'japon': 'JP',
    'kenia': 'KE', 'marruecos': 'MA', 'méxico': 'MX', 'nicaragua': 'NI',
    'noruega': 'NO', 'nueva zelanda': 'NZ', 'países bajos': 'NL',
    'panamá': 'PA', 'paraguay': 'PY', 'perú': 'PE', 'polonia': 'PL',
    'portugal': 'PT', 'reino unido': 'GB', 'república dominicana': 'DO',
    'republica dominicana': 'DO', 'rumania': 'RO', 'rusia': 'RU',
    'sudáfrica': 'ZA', 'sudafrica': 'ZA', 'suecia': 'SE', 'suiza': 'CH',
    'tailandia': 'TH', 'turquía': 'TR', 'turquia': 'TR', 'uruguay': 'UY',
    'venezuela': 'VE',

    # ─── German names ──────────────────────────────────────────────────────
    'deutschland': 'DE', 'frankreich': 'FR', 'großbritannien': 'GB',
    'grossbritannien': 'GB', 'italien': 'IT', 'niederlande': 'NL',
    'österreich': 'AT', 'osterreich': 'AT', 'schweiz': 'CH',
    'spanien': 'ES', 'vereinigte staaten': 'US', 'belgien': 'BE',
    'dänemark': 'DK', 'danemark': 'DK', 'finnland': 'FI',
    'griechenland': 'GR', 'irland': 'IE', 'norwegen': 'NO',
    'polen': 'PL', 'portugal': 'PT', 'rumänien': 'RO', 'rumanien': 'RO',
    'schweden': 'SE', 'tschechien': 'CZ', 'türkei': 'TR', 'turkei': 'TR',
    'ungarn': 'HU',

    # ─── Portuguese names ──────────────────────────────────────────────────
    'alemanha': 'DE', 'espanha': 'ES', 'estados unidos': 'US',
    'frança': 'FR', 'franca': 'FR', 'inglaterra': 'GB', 'itália': 'IT',
    'japão': 'JP', 'japao': 'JP', 'nova zelândia': 'NZ',
    'países baixos': 'NL', 'paises baixos': 'NL', 'polônia': 'PL',
    'polonia': 'PL', 'suécia': 'SE', 'suecia': 'SE', 'suíça': 'CH',
    'suica': 'CH',

    # ─── French names ──────────────────────────────────────────────────────
    'allemagne': 'DE', 'angleterre': 'GB', 'belgique': 'BE',
    'espagne': 'ES', 'états-unis': 'US', 'etats-unis': 'US',
    'italie': 'IT', 'pays-bas': 'NL', 'royaume-uni': 'GB',
    'suisse': 'CH',

    # ─── Common abbreviations and variants ─────────────────────────────────
    'us': 'US', 'usa': 'US', 'u.s.': 'US', 'u.s.a.': 'US',
    'uk': 'GB', 'u.k.': 'GB', 'gb': 'GB', 'great britain': 'GB',
    'england': 'GB', 'scotland': 'GB', 'wales': 'GB',
    'uae': 'AE', 'u.a.e.': 'AE',
    'rsa': 'ZA', 'rok': 'KR', 'prc': 'CN', 'roc': 'TW',
    'holland': 'NL', 'the netherlands': 'NL',
    'ivory coast': 'CI', "cote d'ivoire": 'CI', 'côte d\'ivoire': 'CI',
    'czech': 'CZ', 'slovak': 'SK',
    'bosnia and herzegovina': 'BA', 'bosnia-herzegovina': 'BA',
}

# Valid ISO 3166-1 alpha-2 codes (for direct validation)
VALID_ISO_CODES = {
    'AF', 'AL', 'DZ', 'AD', 'AO', 'AG', 'AR', 'AM', 'AU', 'AT', 'AZ',
    'BS', 'BH', 'BD', 'BB', 'BY', 'BE', 'BZ', 'BJ', 'BT', 'BO', 'BA',
    'BW', 'BR', 'BN', 'BG', 'BF', 'BI', 'KH', 'CM', 'CA', 'CV', 'CF',
    'TD', 'CL', 'CN', 'CO', 'KM', 'CD', 'CG', 'CR', 'CI', 'HR', 'CU',
    'CY', 'CZ', 'DK', 'DJ', 'DM', 'DO', 'EC', 'EG', 'SV', 'GQ', 'ER',
    'EE', 'ET', 'FJ', 'FI', 'FR', 'GA', 'GM', 'GE', 'DE', 'GH', 'GR',
    'GD', 'GT', 'GN', 'GW', 'GY', 'HT', 'HN', 'HK', 'HU', 'IS', 'IN',
    'ID', 'IR', 'IQ', 'IE', 'IL', 'IT', 'JM', 'JP', 'JO', 'KZ', 'KE',
    'KI', 'KP', 'KR', 'KW', 'KG', 'LA', 'LV', 'LB', 'LS', 'LR', 'LY',
    'LI', 'LT', 'LU', 'MG', 'MW', 'MY', 'MV', 'ML', 'MT', 'MH', 'MR',
    'MU', 'MX', 'FM', 'MD', 'MC', 'MN', 'ME', 'MA', 'MZ', 'MM', 'NA',
    'NR', 'NP', 'NL', 'NZ', 'NI', 'NE', 'NG', 'NO', 'OM', 'PK', 'PW',
    'PA', 'PG', 'PY', 'PE', 'PH', 'PL', 'PT', 'PR', 'QA', 'RO', 'RU',
    'RW', 'KN', 'LC', 'VC', 'WS', 'SM', 'ST', 'SA', 'SN', 'RS', 'SC',
    'SL', 'SG', 'SK', 'SI', 'SB', 'SO', 'ZA', 'ES', 'LK', 'SD', 'SR',
    'SZ', 'SE', 'CH', 'SY', 'TW', 'TJ', 'TZ', 'TH', 'TL', 'TG', 'TO',
    'TT', 'TN', 'TR', 'TM', 'TV', 'UG', 'UA', 'AE', 'GB', 'US', 'UY',
    'UZ', 'VU', 'VE', 'VN', 'YE', 'ZM', 'ZW',
}


def resolve_country_code(country_value: str) -> Optional[str]:
    """
    Convert any country representation to ISO 3166-1 alpha-2 code.
    
    Handles:
    - ISO codes directly ("MX", "US", "GB")
    - English names ("Mexico", "United States")
    - Spanish names ("México", "Estados Unidos")
    - German names ("Deutschland", "Frankreich")
    - Portuguese names ("Alemanha", "Brasil")
    - French names ("Allemagne", "Royaume-Uni")
    - Common abbreviations ("USA", "UK", "UAE")
    - Mixed case, extra spaces, accents
    
    Args:
        country_value: Any string representing a country
        
    Returns:
        ISO 2-letter code (uppercase) or None if unrecognized
    """
    if not country_value:
        return None
    
    text = country_value.strip()
    
    # If it's already a valid 2-letter ISO code
    if len(text) == 2 and text.upper() in VALID_ISO_CODES:
        return text.upper()
    
    # If it's a 3-letter code, try common ones
    three_letter = {
        'USA': 'US', 'GBR': 'GB', 'DEU': 'DE', 'FRA': 'FR', 'ESP': 'ES',
        'ITA': 'IT', 'NLD': 'NL', 'BEL': 'BE', 'AUT': 'AT', 'CHE': 'CH',
        'MEX': 'MX', 'BRA': 'BR', 'ARG': 'AR', 'COL': 'CO', 'PER': 'PE',
        'CHL': 'CL', 'CAN': 'CA', 'AUS': 'AU', 'JPN': 'JP', 'CHN': 'CN',
        'IND': 'IN', 'ZAF': 'ZA', 'ARE': 'AE', 'SAU': 'SA', 'KOR': 'KR',
        'TUR': 'TR', 'POL': 'PL', 'ROU': 'RO', 'UKR': 'UA', 'RUS': 'RU',
        'PRT': 'PT', 'SWE': 'SE', 'NOR': 'NO', 'DNK': 'DK', 'FIN': 'FI',
        'IRL': 'IE', 'CZE': 'CZ', 'HUN': 'HU', 'GRC': 'GR', 'BGR': 'BG',
        'HRV': 'HR', 'SVK': 'SK', 'SVN': 'SI', 'LTU': 'LT', 'LVA': 'LV',
        'EST': 'EE', 'ECU': 'EC', 'BOL': 'BO', 'PRY': 'PY', 'URY': 'UY',
        'VEN': 'VE', 'CRI': 'CR', 'PAN': 'PA', 'GTM': 'GT', 'HND': 'HN',
        'SLV': 'SV', 'NIC': 'NI', 'DOM': 'DO', 'CUB': 'CU', 'JAM': 'JM',
        'TTO': 'TT', 'PRI': 'PR', 'NGA': 'NG', 'KEN': 'KE', 'GHA': 'GH',
        'EGY': 'EG', 'MAR': 'MA', 'TUN': 'TN', 'THA': 'TH', 'IDN': 'ID',
        'PHL': 'PH', 'VNM': 'VN', 'MYS': 'MY', 'SGP': 'SG', 'NZL': 'NZ',
        'PAK': 'PK', 'BGD': 'BD', 'LKA': 'LK',
    }
    if len(text) == 3 and text.upper() in three_letter:
        return three_letter[text.upper()]
    
    # Normalize: lowercase, strip accents for lookup
    normalized = text.lower().strip()
    # Remove common prefixes
    normalized = re.sub(r'^(the|la|el|le|les|los|las|das|die|der)\s+', '', normalized)
    
    # Direct lookup
    if normalized in COUNTRY_MAP:
        return COUNTRY_MAP[normalized]
    
    # Try without accents (simple ASCII folding)
    ascii_text = normalized
    accent_map = str.maketrans('áàâãäéèêëíìîïóòôõöúùûüñçý', 'aaaaaeeeeiiiiooooouuuuncy')
    ascii_text = normalized.translate(accent_map)
    if ascii_text in COUNTRY_MAP:
        return COUNTRY_MAP[ascii_text]
    
    # Try partial match (for cases like "Mexico City" → "Mexico")
    for name, code in COUNTRY_MAP.items():
        if name in normalized or normalized in name:
            return code
    
    return None
