"""
Pipeline Module
Processes each row of input data through the full geocoding pipeline.

Steps per row:
1. Parse address (detect apartment)
2. Geocode base address
3. Reverse geocode coordinates
4. Attempt entrance detection
5. Apply confidence scoring
6. Determine final output
"""

from typing import Dict, List, Optional
from .address_parser import parse_address
from .geocoder import geocode_address, geocode_fields, GeocodingError
from .reverse_geocoder import reverse_geocode, ReverseGeocodingError
from .entrance_finder import find_entrance
from .confidence import score_result, determine_output_strategy
from .country_logic import apply_country_adjustments, validate_postal_code


def process_row(
    address: str = '',
    street: str = '',
    city: str = '',
    state: str = '',
    postal_code: str = '',
    country: str = '',
    country_code: str = '',
) -> Dict:
    """
    Process a single address row through the full pipeline.

    Accepts either a full address string OR separate fields.

    Returns:
        Complete result dictionary with all geocoding outputs and confidence.
    """
    # Combine fields if no full address provided
    if not address and (street or city):
        parts = [p for p in [street, city, state, postal_code, country] if p.strip()]
        address = ', '.join(parts)

    if not address or not address.strip():
        return _empty_result(address)

    # Step 1: Parse address (detect apartment/unit)
    parsed = parse_address(address)
    base_address = parsed['base_address']
    is_multi_unit = parsed['is_multi_unit']
    unit_text = parsed['unit_text']

    # Step 2: Geocode base address
    error_msg = ''
    try:
        geocode_results = geocode_address(base_address, country_code=country_code or None)
    except GeocodingError as e:
        geocode_results = []
        error_msg = str(e)

    if not geocode_results:
        error_reason = error_msg if error_msg else 'No geocoding results returned'
        return _build_result(
            original_address=address,
            base_address=base_address,
            unit_text=unit_text,
            is_multi_unit=is_multi_unit,
            postal_code=postal_code,
            city=city,
            country_code=country_code,
            error=error_reason,
        )

    best = geocode_results[0]
    lat = best['lat']
    lon = best['lon']
    geocode_score = best['score']
    match_type = best['match_type']
    geocoded_postal = best.get('postal_code', '')
    geocoded_country = best.get('country_code', '') or country_code

    # Step 3: Reverse geocode to standardize address
    reverse_result = {'formatted_address': '', 'postal_code': '', 'city': '', 'district': '', 'country': '', 'country_code': ''}
    try:
        reverse_result = reverse_geocode(lat, lon)
    except ReverseGeocodingError:
        pass

    # Use best available postal code
    final_postal = geocoded_postal or reverse_result.get('postal_code', '') or postal_code
    final_city = reverse_result.get('city', '') or city
    final_district = reverse_result.get('district', '')
    final_country = reverse_result.get('country', '') or country
    final_country_code = reverse_result.get('country_code', '') or geocoded_country

    # Step 4: Attempt entrance detection
    entrance = find_entrance(lat, lon)
    has_entrance = entrance['precision'] == 'Entrance'

    # Use entrance coordinates if found
    final_lat = entrance['lat']
    final_lon = entrance['lon']
    precision = entrance['precision']

    # Step 5: Apply confidence scoring
    # Check if postal codes match
    postal_matches = False
    if postal_code and final_postal:
        postal_matches = postal_code.strip().replace(' ', '').lower() == final_postal.strip().replace(' ', '').lower()

    # Check if reverse geocode confirms the address
    reverse_confirms = bool(reverse_result.get('formatted_address'))

    confidence = score_result(
        geocode_score=geocode_score,
        match_type=match_type,
        has_postal_code=bool(final_postal),
        postal_code_matches=postal_matches,
        has_entrance=has_entrance,
        is_multi_unit=is_multi_unit,
        reverse_geocode_matches=reverse_confirms,
        country_code=final_country_code,
    )

    # Step 6: Determine output strategy
    strategy = determine_output_strategy(
        confidence['confidence_score'],
        has_entrance,
        bool(final_postal),
    )

    # Apply country-specific adjustments
    country_adjusted = apply_country_adjustments(
        {'city': final_city, 'district': final_district, 'postal_code': final_postal},
        final_country_code,
        input_city=city,
    )

    return {
        'original_address': address,
        'base_address': base_address,
        'unit_text': unit_text,
        'is_multi_unit': is_multi_unit,
        'latitude': final_lat,
        'longitude': final_lon,
        'precision': precision,
        'formatted_address': reverse_result.get('formatted_address', '') or best.get('address', ''),
        'postal_code': country_adjusted.get('postal_code', final_postal),
        'city': country_adjusted.get('city', final_city),
        'district': country_adjusted.get('district', final_district),
        'country': final_country,
        'country_code': final_country_code,
        'confidence_score': confidence['confidence_score'],
        'confidence_level': confidence['confidence_level'],
        'output_strategy': strategy,
        'needs_review': confidence['needs_review'],
        'recommendation': confidence['recommendation'],
        'entrance_source': entrance.get('source', ''),
        'entrance_type': entrance.get('entrance_type', ''),
        'geocode_alternatives': geocode_results[1:],  # other results for review
    }


def process_dataframe(df, address_col: str = 'address', **field_cols) -> List[Dict]:
    """
    Process an entire DataFrame through the pipeline.

    Args:
        df: pandas DataFrame with address data.
        address_col: Column name containing the full address (if available).
        **field_cols: Mapping of field names to column names:
            street_col, city_col, state_col, postal_col, country_col, country_code_col

    Returns:
        List of result dictionaries, one per row.
    """
    results = []

    street_col = field_cols.get('street_col', '')
    city_col = field_cols.get('city_col', '')
    state_col = field_cols.get('state_col', '')
    postal_col = field_cols.get('postal_col', '')
    country_col = field_cols.get('country_col', '')
    country_code_col = field_cols.get('country_code_col', '')

    for _, row in df.iterrows():
        address = str(row.get(address_col, '')) if address_col in df.columns else ''
        street = str(row.get(street_col, '')) if street_col and street_col in df.columns else ''
        city = str(row.get(city_col, '')) if city_col and city_col in df.columns else ''
        state = str(row.get(state_col, '')) if state_col and state_col in df.columns else ''
        postal = str(row.get(postal_col, '')) if postal_col and postal_col in df.columns else ''
        country = str(row.get(country_col, '')) if country_col and country_col in df.columns else ''
        cc = str(row.get(country_code_col, '')) if country_code_col and country_code_col in df.columns else ''

        # Clean nan values
        for var_name in ['address', 'street', 'city', 'state', 'postal', 'country', 'cc']:
            val = locals()[var_name]
            if val == 'nan' or val == 'None':
                locals()[var_name] = ''

        result = process_row(
            address=address,
            street=street,
            city=city,
            state=state,
            postal_code=postal,
            country=country,
            country_code=cc,
        )
        results.append(result)

    return results


def _empty_result(address: str = '') -> Dict:
    """Return an empty/error result for rows that can't be processed."""
    reason = 'No address data provided.' if not address else f'Geocoding failed for: "{address[:80]}"'
    return {
        'original_address': address or '',
        'base_address': '',
        'unit_text': '',
        'is_multi_unit': False,
        'latitude': 0.0,
        'longitude': 0.0,
        'precision': '',
        'formatted_address': '',
        'postal_code': '',
        'city': '',
        'district': '',
        'country': '',
        'country_code': '',
        'confidence_score': 0.0,
        'confidence_level': 'Low',
        'output_strategy': 'review',
        'needs_review': True,
        'recommendation': reason,
        'entrance_source': '',
        'entrance_type': '',
        'geocode_alternatives': [],
    }


def _build_result(original_address='', base_address='', unit_text='', is_multi_unit=False, postal_code='', city='', country_code='', error='') -> Dict:
    """Build a partial result when geocoding fails but some data is available."""
    result = _empty_result(original_address)
    result['base_address'] = base_address
    result['unit_text'] = unit_text
    result['is_multi_unit'] = is_multi_unit
    result['postal_code'] = postal_code
    result['city'] = city
    result['country_code'] = country_code
    if postal_code:
        result['output_strategy'] = 'postal_code'
        result['recommendation'] = f'Geocoding failed ({error}). Use postal code for routing.'
    else:
        result['recommendation'] = f'Geocoding failed ({error}). Manual review required.'
    return result
