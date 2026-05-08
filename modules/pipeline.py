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
from .fallback_geocoder import geocode_with_fallbacks
from .reverse_geocoder import reverse_geocode, ReverseGeocodingError
from .entrance_finder import find_entrance
from .confidence import score_result, determine_output_strategy
from .country_logic import apply_country_adjustments, validate_postal_code
from .address_normalizer import normalize_address, extract_postal_code, build_geocoding_query, assess_optiflow_readiness, split_neighborhood_postal
from .cache import geocode_cache
from .address_cleaner import clean_address, generate_retry_variants, detect_country_from_address
from .phone_detector import detect_country_from_phone
from .country_resolver import resolve_country_code


def process_row(
    address: str = '',
    street: str = '',
    city: str = '',
    state: str = '',
    postal_code: str = '',
    country: str = '',
    country_code: str = '',
    phone: str = '',
) -> Dict:
    """
    Process a single address row through the pipeline.
    
    Smart fill logic: each geocoder fills what it can. Subsequent services
    are ONLY called for fields that are still blank. If PTV returns everything,
    no other services are called.

    Features:
    - Address pre-cleaning (fix typos, remove noise)
    - Result caching (identical addresses only geocode once)
    - Country detection from phone numbers and address patterns
    - Smart retry with simplified address variants
    - Progressive field filling (only call APIs for missing data)

    Returns:
        Complete result dictionary with all geocoding outputs and confidence.
    """
    # Combine fields if no full address provided
    if not address and (street or city):
        parts = [p for p in [street, city, state, postal_code, country] if p.strip()]
        address = ', '.join(parts)

    if not address or not address.strip():
        return _empty_result(address)

    # ─── Pre-processing: Clean address and detect country ──────────────────
    address = clean_address(address)

    # Detect country from phone number if not provided
    if not country_code and phone:
        phone_info = detect_country_from_phone(phone)
        if phone_info['country_code'] and phone_info['confidence'] in ('high', 'low'):
            country_code = phone_info['country_code']

    # Detect country from address content if still not provided
    if not country_code and not country:
        inferred_country = detect_country_from_address(address)
        if inferred_country:
            country_code = inferred_country

    # ─── Check cache first ─────────────────────────────────────────────────
    cached = geocode_cache.get(address, country_code)
    if cached:
        return cached

    # Extract postal code from mixed fields if not provided
    if not postal_code:
        extracted = extract_postal_code(address, country_code)
        if extracted:
            postal_code = extracted

    # Step 1: Parse address (detect apartment/unit)
    parsed = parse_address(address)
    base_address = normalize_address(parsed['base_address'])
    is_multi_unit = parsed['is_multi_unit']
    unit_text = parsed['unit_text']

    # Try to extract postal code from base address if still not found
    if not postal_code:
        extracted_postal = extract_postal_code(base_address, country_code)
        if extracted_postal:
            postal_code = extracted_postal

    # ─── Step 2: Geocode — fill fields progressively ───────────────────────
    # Each source fills what it can. We only call the next source if key fields are missing.
    # KEY PRINCIPLE: Use country + city as CONSTRAINTS, not just part of the query.
    # This ensures we find the address WITHIN the correct region, not globally.
    
    from .ptv_geocoder import geocode_ptv, PTV_API_KEY

    # Track what we have
    lat = 0.0
    lon = 0.0
    geocode_score = 0.0
    match_type = ''
    formatted_address = ''
    final_postal = postal_code
    final_city = city
    final_district = ''
    final_country = country
    final_country_code = country_code
    geocoding_source = 'None'
    geocode_results = []
    error_msg = ''
    ptv_has_road_access = False

    # Build a region-constrained query
    # Strategy: Send the street/address as the search text, but use country_code as a FILTER
    # This tells PTV "find this address, but ONLY look in this country"
    search_query = base_address
    
    # If we have separate city/state but they're not already in the address, append them
    # This helps PTV narrow down within the country
    addr_lower = base_address.lower()
    if city and city.lower() not in addr_lower:
        search_query = f"{base_address}, {city}"
    if state and state.lower() not in addr_lower and state.lower() not in (city or '').lower():
        search_query = f"{search_query}, {state}"
    if country and not country_code and country.lower() not in addr_lower:
        search_query = f"{search_query}, {country}"

    # Determine the country code to use as a FILTER (not part of query text)
    # This is CRITICAL — it constrains PTV to search only within this country
    filter_country = country_code
    if not filter_country and country:
        # Use the comprehensive country resolver
        filter_country = resolve_country_code(country) or ''
    if not filter_country:
        # Try to detect from the address itself
        filter_country = resolve_country_code(address) or ''
        if not filter_country:
            filter_country = detect_country_from_address(f"{base_address}, {city}") or ''

    # ── Pass 1: PTV Developer (best for OptiFlow) ──
    if PTV_API_KEY:
        geocode_results = geocode_ptv(search_query, country_code=filter_country or None)
        if geocode_results:
            best = geocode_results[0]
            lat = best['lat']
            lon = best['lon']
            geocode_score = best['score']
            match_type = best['match_type']
            geocoding_source = 'PTV'
            
            # Fill fields from PTV response
            if best.get('address'):
                formatted_address = best['address']
            if best.get('postal_code'):
                final_postal = best['postal_code']
            if best.get('municipality'):
                final_city = best['municipality']
            if best.get('district'):
                final_district = best['district']
            if best.get('country_code'):
                final_country_code = best['country_code']
            
            # PTV's roadAccessPosition is already the optimal routing point
            if best.get('road_access_lat') and best['road_access_lat'] != 0.0:
                ptv_has_road_access = True

    # ── Pass 2: Azure Maps (only if PTV didn't return coords) ──
    if lat == 0.0 and lon == 0.0:
        try:
            azure_results = geocode_address(search_query, country_code=filter_country or None)
            if azure_results:
                geocode_results = azure_results
                best = azure_results[0]
                lat = best['lat']
                lon = best['lon']
                geocode_score = best['score']
                match_type = best['match_type']
                geocoding_source = 'Azure Maps'
                
                if not formatted_address and best.get('address'):
                    formatted_address = best['address']
                if not final_postal and best.get('postal_code'):
                    final_postal = best['postal_code']
                if not final_city and best.get('municipality'):
                    final_city = best['municipality']
                if best.get('country_code'):
                    final_country_code = best['country_code']
        except GeocodingError as e:
            error_msg = str(e)

    # ── Pass 3: HERE / Nominatim (only if still no coords) ──
    if lat == 0.0 and lon == 0.0:
        fallback_results = geocode_with_fallbacks(
            search_query,
            country_code=filter_country or None,
            azure_results=None,
        )
        if fallback_results:
            geocode_results = fallback_results
            best = fallback_results[0]
            lat = best['lat']
            lon = best['lon']
            geocode_score = best['score']
            match_type = best['match_type']
            geocoding_source = best.get('source', 'Fallback')
            
            if not formatted_address and best.get('address'):
                formatted_address = best['address']
            if not final_postal and best.get('postal_code'):
                final_postal = best['postal_code']
            if not final_city and best.get('municipality'):
                final_city = best['municipality']
            if best.get('country_code'):
                final_country_code = best['country_code']

    # If still no coordinates, try smart retry with simplified variants
    if lat == 0.0 and lon == 0.0:
        retry_variants = generate_retry_variants(search_query)
        for variant in retry_variants:
            if PTV_API_KEY:
                retry_results = geocode_ptv(variant, country_code=filter_country or None)
                if retry_results:
                    best = retry_results[0]
                    lat = best['lat']
                    lon = best['lon']
                    geocode_score = best['score']
                    match_type = best['match_type']
                    geocoding_source = 'PTV (retry)'
                    geocode_results = retry_results
                    if best.get('address'):
                        formatted_address = best['address']
                    if best.get('postal_code'):
                        final_postal = best['postal_code']
                    if best.get('municipality'):
                        final_city = best['municipality']
                    if best.get('country_code'):
                        final_country_code = best['country_code']
                    if best.get('road_access_lat') and best['road_access_lat'] != 0.0:
                        ptv_has_road_access = True
                    break

        # If retry with PTV failed, try PTV Places API (for business/POI names)
        # This handles cases like "Walmart Supercenter" or "Bodega Aurrera" in a specific city
        if lat == 0.0 and lon == 0.0 and PTV_API_KEY:
            from .ptv_geocoder import search_places_ptv
            
            # Build a places search query
            places_query = base_address
            if city:
                places_query = f"{base_address} {city}"
            
            places_results = search_places_ptv(places_query, country_code=filter_country or None)
            if places_results:
                best = places_results[0]
                lat = best['lat']
                lon = best['lon']
                geocode_score = best['score']
                match_type = best['match_type']
                geocoding_source = 'PTV Places'
                geocode_results = places_results
                if best.get('address'):
                    formatted_address = best['address']
                if best.get('postal_code'):
                    final_postal = best['postal_code']
                if best.get('municipality'):
                    final_city = best['municipality']
                if best.get('country_code'):
                    final_country_code = best['country_code']
                if best.get('road_access_lat') and best['road_access_lat'] != 0.0:
                    ptv_has_road_access = True
            else:
                # Last resort: try geocoding with just city + country for a centroid
                if city and filter_country:
                    city_only = f"{city}, {country}" if country else city
                    city_results = geocode_ptv(city_only, country_code=filter_country)
                    if city_results:
                        best = city_results[0]
                        lat = best['lat']
                        lon = best['lon']
                        geocode_score = 0.4  # Low score — city centroid only
                        match_type = 'City'
                        geocoding_source = 'PTV (city centroid)'
                        geocode_results = city_results
                        if best.get('postal_code'):
                            final_postal = best['postal_code']
                        if best.get('municipality'):
                            final_city = best['municipality']
                        if best.get('country_code'):
                            final_country_code = best['country_code']

    # If STILL no coordinates after retry, return error result
    if lat == 0.0 and lon == 0.0:
        error_reason = error_msg if error_msg else 'No geocoding results returned'
        result = _build_result(
            original_address=address,
            base_address=base_address,
            unit_text=unit_text,
            is_multi_unit=is_multi_unit,
            postal_code=final_postal,
            city=final_city,
            country_code=final_country_code,
            error=error_reason,
        )
        geocode_cache.put(address, country_code, result)
        return result

    # ─── Step 3: Reverse geocode — ONLY if we're missing key fields ────────
    reverse_confirms = False
    if not formatted_address or not final_postal or not final_city:
        try:
            reverse_result = reverse_geocode(lat, lon)
            if reverse_result:
                reverse_confirms = True
                if not formatted_address:
                    formatted_address = reverse_result.get('formatted_address', '')
                if not final_postal:
                    final_postal = reverse_result.get('postal_code', '')
                if not final_city:
                    final_city = reverse_result.get('city', '')
                if not final_district:
                    final_district = reverse_result.get('district', '')
                if not final_country:
                    final_country = reverse_result.get('country', '')
                if not final_country_code:
                    final_country_code = reverse_result.get('country_code', '')
        except ReverseGeocodingError:
            pass
    else:
        # PTV/Azure already gave us everything — skip reverse geocode
        reverse_confirms = True

    # ─── Step 4: Entrance detection — ONLY if we don't have road access ────
    precision = 'Building'
    entrance_source = ''
    entrance_type = ''
    final_lat = lat
    final_lon = lon

    if ptv_has_road_access:
        # PTV already gave us roadAccessPosition — that IS the entrance/road point
        precision = 'Road Access'
        entrance_source = 'PTV'
    elif geocode_score >= 0.9 and match_type in ('Exact Address', 'Point Address'):
        # High-confidence exact match — skip slow OSM entrance lookup
        precision = 'Building'
    else:
        # Only call entrance finder for lower-confidence results where it might help
        # AND only if the match is at least street-level
        if geocode_score >= 0.5:
            entrance = find_entrance(lat, lon)
            if entrance['precision'] == 'Entrance':
                final_lat = entrance['lat']
                final_lon = entrance['lon']
                precision = 'Entrance'
                entrance_source = entrance.get('source', '')
                entrance_type = entrance.get('entrance_type', '')

    has_entrance = precision in ('Entrance', 'Road Access')

    # ─── Step 5: Confidence scoring ────────────────────────────────────────
    postal_matches = False
    if postal_code and final_postal:
        # Normalize for comparison: strip spaces, lowercase, compare base (ignore ZIP+4 extension)
        input_clean = postal_code.strip().replace(' ', '').replace('-', '').lower()
        output_clean = final_postal.strip().replace(' ', '').replace('-', '').lower()
        # Match if one starts with the other (handles "37803" vs "37803-2565")
        postal_matches = input_clean.startswith(output_clean) or output_clean.startswith(input_clean)

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

    # Override: If PTV returned good result with road access, force High confidence
    # PTV's road-access coordinates are pre-validated for routing — trust them
    if geocoding_source in ('PTV', 'PTV (retry)') and ptv_has_road_access:
        if geocode_score >= 0.80:
            confidence['confidence_score'] = max(confidence['confidence_score'], 0.92)
            confidence['confidence_level'] = 'High'
            confidence['needs_review'] = False
            confidence['recommendation'] = 'PTV exact match with road-access coordinates. Use directly for routing.'
        elif geocode_score >= 0.60:
            confidence['confidence_score'] = max(confidence['confidence_score'], 0.78)
            confidence['confidence_level'] = 'High'
            confidence['needs_review'] = False
            confidence['recommendation'] = 'PTV match with road-access coordinates. Coordinates reliable for routing.'
    elif geocoding_source in ('PTV', 'PTV (retry)') and geocode_score >= 0.80:
        # PTV returned good score but no road access (rare)
        confidence['confidence_score'] = max(confidence['confidence_score'], 0.76)
        confidence['confidence_level'] = 'High'
        confidence['needs_review'] = False
        confidence['recommendation'] = 'PTV high-quality match. Coordinates suitable for routing.'

    # ─── Step 6: Output strategy ──────────────────────────────────────────
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

    result = {
        'original_address': address,
        'base_address': base_address,
        'unit_text': unit_text,
        'is_multi_unit': is_multi_unit,
        'latitude': final_lat,
        'longitude': final_lon,
        'precision': precision,
        'formatted_address': formatted_address,
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
        'entrance_source': entrance_source,
        'entrance_type': entrance_type,
        'geocode_alternatives': geocode_results[1:] if geocode_results else [],
        'geocoding_source': geocoding_source,
    }

    # Final check: OptiFlow readiness
    readiness = assess_optiflow_readiness(
        result['latitude'], result['longitude'],
        result['postal_code'], result['confidence_score'], result['confidence_level']
    )
    result['optiflow_ready'] = readiness['optiflow_ready']
    result['routing_method'] = readiness['routing_method']

    # If not ready but we have a postal code, try geocoding the postal code for a centroid
    if not readiness['optiflow_ready'] and final_postal:
        try:
            postal_results = geocode_with_fallbacks(f"{final_postal}, {country or city}", country_code=country_code)
            if postal_results:
                result['latitude'] = postal_results[0]['lat']
                result['longitude'] = postal_results[0]['lon']
                result['precision'] = 'Postal Centroid'
                result['confidence_level'] = 'Medium'
                result['confidence_score'] = 0.55
                result['optiflow_ready'] = True
                result['routing_method'] = 'postal_centroid'
                result['recommendation'] = f"Used postal code {final_postal} centroid (address geocoding insufficient)"
        except Exception:
            pass

    # Cache the result for future lookups
    geocode_cache.put(address, country_code, result)

    return result


def process_dataframe(df, address_col: str = 'address', **field_cols) -> List[Dict]:
    """
    Process an entire DataFrame through the pipeline.

    Args:
        df: pandas DataFrame with address data.
        address_col: Column name containing the full address (if available).
        **field_cols: Mapping of field names to column names.

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

        def _clean(v): return '' if v in ('nan', 'None') else v
        result = process_row(
            address=_clean(address),
            street=_clean(street),
            city=_clean(city),
            state=_clean(state),
            postal_code=_clean(postal),
            country=_clean(country),
            country_code=_clean(cc),
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
