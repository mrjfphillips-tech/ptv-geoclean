"""
Address Parser Module
Detects and separates apartment/unit information from address strings.
Supports multilingual unit keywords for international addresses.
"""

import re
from typing import Dict


# Unit keywords in multiple languages (case-insensitive matching)
UNIT_KEYWORDS = [
    # English
    r'apt\.?', r'apartment', r'unit', r'suite', r'ste\.?', r'#',
    r'flat', r'room', r'rm\.?', r'floor', r'fl\.?',
    # Spanish / Latin America
    r'dpto\.?', r'depto\.?', r'departamento', r'torre', r'int\.?',
    r'oficina', r'of\.?', r'piso', r'local', r'interior',
    # Portuguese
    r'apto\.?', r'apartamento', r'bloco', r'sala',
    # French
    r'appt\.?', r'appartement', r'étage', r'bureau',
    # German
    r'wohnung', r'whg\.?', r'og\.?', r'etage',
]

# Build a single regex pattern that captures the unit keyword + number/identifier
_kw_pattern = '|'.join(UNIT_KEYWORDS)
UNIT_REGEX = re.compile(
    r'[,\s]*\b(' + _kw_pattern + r')\s*[#.\-:]?\s*(\w+(?:\s*\w*)?)',
    re.IGNORECASE
)


def parse_address(raw_address: str) -> Dict[str, object]:
    """
    Parse a raw address string to detect and separate unit/apartment information.

    Args:
        raw_address: The full address string, potentially containing unit info.

    Returns:
        Dictionary with:
            - is_multi_unit (bool): Whether a unit/apartment was detected
            - unit_text (str): The extracted unit portion (e.g., "Dpto 802")
            - base_address (str): The address without the unit portion

    Example:
        >>> parse_address("Av. Javier Prado 4200 Dpto 802, Lima")
        {'is_multi_unit': True, 'unit_text': 'Dpto 802', 'base_address': 'Av. Javier Prado 4200, Lima'}
    """
    if not raw_address or not raw_address.strip():
        return {
            'is_multi_unit': False,
            'unit_text': '',
            'base_address': raw_address or '',
        }

    address = raw_address.strip()

    # Try to find a unit keyword match
    match = UNIT_REGEX.search(address)

    if match:
        unit_text = match.group(0).strip().lstrip(',').strip()
        # Remove the unit portion from the address
        base_address = address[:match.start()] + address[match.end():]
        # Clean up extra commas, spaces
        base_address = re.sub(r'\s*,\s*,\s*', ', ', base_address)
        base_address = re.sub(r'\s{2,}', ' ', base_address).strip()
        base_address = base_address.strip(',').strip()

        return {
            'is_multi_unit': True,
            'unit_text': unit_text,
            'base_address': base_address,
        }

    # Check for hash-number pattern (e.g., "#802")
    hash_match = re.search(r'[,\s]+#\s*(\w+)', address)
    if hash_match:
        unit_text = hash_match.group(0).strip().lstrip(',').strip()
        base_address = address[:hash_match.start()] + address[hash_match.end():]
        base_address = re.sub(r'\s*,\s*,\s*', ', ', base_address).strip().strip(',').strip()
        return {
            'is_multi_unit': True,
            'unit_text': unit_text,
            'base_address': base_address,
        }

    return {
        'is_multi_unit': False,
        'unit_text': '',
        'base_address': address,
    }


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        "Av. Javier Prado 4200 Dpto 802, Lima",
        "123 Main St Apt 4B, New York, NY 10001",
        "456 Oak Ave Suite 200, Toronto, ON M5V 2T6",
        "10 Downing Street, London SW1A 2AA",
        "Calle Los Olivos 345 Torre B Int 1201, Lima",
        "Rua Augusta 1500 Apto 42, São Paulo",
        "Hauptstraße 15 Whg 3, Berlin",
        "Simple address with no unit, Paris",
    ]

    for addr in tests:
        result = parse_address(addr)
        status = "✅" if result['is_multi_unit'] else "—"
        print(f"{status} {addr}")
        print(f"   base: {result['base_address']}")
        if result['unit_text']:
            print(f"   unit: {result['unit_text']}")
        print()
