"""
Address Decomposer Module
Orchestrates reverse geocoding to decompose combined addresses into structured
address components when lat/lon coordinates are available (Single_Cell_Condition).
"""

import logging
import math
from typing import Callable, Dict, List, Optional, Tuple

from modules.ptv_geocoder import reverse_geocode_batch_ptv, reverse_geocode_ptv
from modules.reverse_geocoder import reverse_geocode as reverse_geocode_azure, ReverseGeocodingError

logger = logging.getLogger(__name__)


def validate_coordinate(lat, lon) -> Tuple[bool, str]:
    """
    Validate a single coordinate pair for reverse geocoding eligibility.

    Args:
        lat: Latitude value (expected numeric, but may be any type)
        lon: Longitude value (expected numeric, but may be any type)

    Returns:
        Tuple of (is_valid, reason_if_invalid):
            - (True, '') if coordinates are valid
            - (False, reason) if coordinates are invalid

    Validation rules:
        - lat must be numeric and in [-90, 90]
        - lon must be numeric and in [-180, 180]
        - (0, 0) is treated as invalid (Null Island)
        - NaN, None, empty string are invalid
    """
    # Check for None
    if lat is None or lon is None:
        return (False, "non_numeric")

    # Check for empty string
    if isinstance(lat, str) or isinstance(lon, str):
        # Allow numeric strings by attempting conversion
        try:
            lat = float(lat) if isinstance(lat, str) else lat
            lon = float(lon) if isinstance(lon, str) else lon
        except (ValueError, TypeError):
            return (False, "non_numeric")
        # After conversion, empty strings would have raised ValueError above
        # but check explicitly for empty before conversion
        # (already handled by the try/except since float('') raises ValueError)

    # Check for non-numeric types (must be int or float after string conversion)
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return (False, "non_numeric")

    # Check for NaN
    if math.isnan(lat) or math.isnan(lon):
        return (False, "non_numeric")

    # Check for infinity
    if math.isinf(lat) or math.isinf(lon):
        return (False, "out_of_range")

    # Check latitude range [-90, 90]
    if lat < -90 or lat > 90:
        return (False, "out_of_range")

    # Check longitude range [-180, 180]
    if lon < -180 or lon > 180:
        return (False, "out_of_range")

    # Check for (0, 0) — Null Island
    if lat == 0.0 and lon == 0.0:
        return (False, "zero_zero")

    return (True, "")


def _confidence_level_from_score(score: float) -> str:
    """Map a numeric confidence score to a human-readable level."""
    if score >= 0.75:
        return "High"
    elif score >= 0.50:
        return "Medium"
    else:
        return "Low"


def _extract_confidence_score(reverse_result: dict, source: str) -> float:
    """
    Extract a confidence/quality score from an API response.

    PTV responses may include a 'quality' dict with 'totalScore' (0-100 scale).
    Azure responses may include a 'matchConfidence' field or similar.
    Returns a float in [0.0, 1.0], defaulting to 0.5 if no score is found.
    """
    if source == "PTV":
        # PTV quality comes from the location's quality.totalScore (0–100)
        quality = reverse_result.get("quality", {})
        if isinstance(quality, dict):
            total_score = quality.get("totalScore")
            if total_score is not None:
                try:
                    score = float(total_score)
                    # PTV uses 0–100 scale; normalize to 0.0–1.0
                    return max(0.0, min(1.0, score / 100.0))
                except (ValueError, TypeError):
                    pass
    elif source == "Azure":
        # Azure may include matchConfidence as a float 0-1
        match_confidence = reverse_result.get("matchConfidence")
        if match_confidence is not None:
            try:
                score = float(match_confidence)
                return max(0.0, min(1.0, score))
            except (ValueError, TypeError):
                pass

    # Default when no score available
    return 0.5


def _build_decompose_result(prep: dict, reverse_result: dict, source: str = "PTV") -> dict:
    """
    Build a standard GeoClean result dict from a reverse geocode response,
    focused on address decomposition rather than coordinate verification.

    The result preserves the original combined address and populates structured
    address fields from the reverse geocode response. Original coordinates are
    preserved as-is (they are the source of truth, not being snapped).

    Args:
        prep: Prepared row dict with keys like 'addr', 'existing_lat',
              'existing_lon', '_original_row', etc.
        reverse_result: Raw API response dict from PTV or Azure reverse geocode.
        source: Provider identifier - "PTV" or "Azure".

    Returns:
        Standard GeoClean result dict with decomposed address fields.
    """
    # Extract the original combined address from the prep row
    original_address = prep.get("addr", "") or prep.get("original_address", "") or ""

    # Preserve original coordinates as-is (source of truth)
    lat = prep.get("existing_lat", 0.0)
    lon = prep.get("existing_lon", 0.0)

    # Extract address fields from reverse geocode result based on source
    if source == "PTV":
        street_name = reverse_result.get("street", "")
        house_number = reverse_result.get("house_number", "")
        city = reverse_result.get("city", "")
        state = reverse_result.get("state", "")
        postal_code = reverse_result.get("postal_code", "")
        country_code = reverse_result.get("country_code", "")
        country = reverse_result.get("country", "")
        district = reverse_result.get("district", "")
        formatted_address = reverse_result.get("formatted_address", "")
    elif source == "Azure":
        street_name = reverse_result.get("street", "")
        house_number = reverse_result.get("street_number", "")
        city = reverse_result.get("city", "")
        state = reverse_result.get("state", "")
        postal_code = reverse_result.get("postal_code", "")
        country_code = reverse_result.get("country_code", "")
        country = reverse_result.get("country", "")
        district = reverse_result.get("district", "")
        formatted_address = reverse_result.get("formatted_address", "")
    else:
        # Unknown source — attempt generic field extraction
        street_name = reverse_result.get("street", "")
        house_number = reverse_result.get("house_number", "") or reverse_result.get("street_number", "")
        city = reverse_result.get("city", "")
        state = reverse_result.get("state", "")
        postal_code = reverse_result.get("postal_code", "")
        country_code = reverse_result.get("country_code", "")
        country = reverse_result.get("country", "")
        district = reverse_result.get("district", "")
        formatted_address = reverse_result.get("formatted_address", "")

    # Ensure all fields are strings, never None
    street_name = street_name if street_name is not None else ""
    house_number = house_number if house_number is not None else ""
    city = city if city is not None else ""
    state = state if state is not None else ""
    postal_code = postal_code if postal_code is not None else ""
    country_code = country_code if country_code is not None else ""
    country = country if country is not None else ""
    district = district if district is not None else ""
    formatted_address = formatted_address if formatted_address is not None else ""

    # Combine street + houseNumber into a single street field
    if street_name and house_number:
        street = f"{street_name} {house_number}"
    elif street_name:
        street = street_name
    elif house_number:
        street = house_number
    else:
        street = ""

    # Confidence scoring
    confidence_score = _extract_confidence_score(reverse_result, source)
    confidence_level = _confidence_level_from_score(confidence_score)

    # Determine if review is needed (sparse data from API)
    critical_fields_present = bool(street or city or postal_code)
    needs_review = not critical_fields_present

    # Build recommendation message
    if needs_review:
        recommendation = "Reverse geocode returned sparse data — manual review recommended."
    else:
        recommendation = f"Address decomposed from coordinates via {source} reverse geocode."

    # Build map link for existing coordinates
    map_link_existing = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else ""

    return {
        # Identity
        "original_address": original_address,
        "base_address": original_address,
        "unit_text": "",
        "is_multi_unit": False,

        # Coordinates (kept as-is from input — these are authoritative)
        "latitude": lat,
        "longitude": lon,
        "existing_lat": lat,
        "existing_lon": lon,

        # Decomposed address fields (from reverse geocoding)
        "formatted_address": formatted_address,
        "street": street,
        "postal_code": postal_code,
        "city": city,
        "state": state,
        "district": district,
        "country": country,
        "country_code": country_code,

        # Scoring and metadata
        "precision": "Reverse Geocode",
        "confidence_score": confidence_score,
        "confidence_level": confidence_level,
        "output_strategy": "decomposed_address",
        "needs_review": needs_review,
        "recommendation": recommendation,
        "geocoding_source": "Reverse Geocode (Lat/Long)",

        # Verification (minimal — coords are the source of truth)
        "verification_status": "source_coords",
        "verification_message": "Coordinates used as source for address decomposition.",
        "distance_from_existing": 0,
        "map_link_existing": map_link_existing,
        "map_link_suggested": "",
        "map_link_compare": "",

        # Passthrough
        "_original_row": prep.get("_original_row", {}),

        # Geocode alternatives (empty for this path)
        "entrance_source": "",
        "entrance_type": "",
        "geocode_alternatives": [],
    }


def _batch_result_to_reverse_result(batch_item: dict) -> dict:
    """
    Convert a PTV batch reverse geocode result item into the format expected
    by _build_decompose_result (matching reverse_geocode_ptv output format).

    The batch results from _get_reverse_batch_results have a different field
    structure (e.g. 'municipality' instead of 'city', 'address' instead of
    'formatted_address', 'ptv_quality_score' as raw 0-100 value).
    """
    return {
        "street": batch_item.get("street", ""),
        "house_number": batch_item.get("house_number", ""),
        "city": batch_item.get("municipality", "") or batch_item.get("city", ""),
        "state": batch_item.get("state", ""),
        "postal_code": batch_item.get("postal_code", ""),
        "country_code": batch_item.get("country_code", ""),
        "country": batch_item.get("country", ""),
        "district": batch_item.get("district", ""),
        "formatted_address": batch_item.get("address", "") or batch_item.get("formatted_address", ""),
        "quality": {"totalScore": batch_item.get("ptv_quality_score", None)},
    }


def decompose_batch(
    prepared_rows: List[Dict],
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[List[Optional[Dict]], List[Tuple[int, Dict]]]:
    """
    Process rows meeting Single_Cell_Condition via reverse geocoding.

    For each row, validates coordinates, performs batch reverse geocoding via PTV,
    retries failures individually, and falls back to Azure Maps when PTV fails.

    Args:
        prepared_rows: List of dicts with keys 'existing_lat', 'existing_lon',
                       'addr', '_original_row', etc.
        progress_callback: Optional callback(done, total) for progress updates.

    Returns:
        Tuple of:
        - results: List of result dicts (same length as input). None for rows
                   that failed all reverse geocoding attempts and need forward
                   geocoding fallback.
        - fallback_rows: List of (index, prepared_row) tuples for rows that
                         need forward geocoding fallback.

    Requirements: 2.1, 2.4, 3.1, 3.4, 4.4, 4.5, 5.1, 5.2, 6.1, 6.3, 6.4
    """
    total = len(prepared_rows)
    results: List[Optional[Dict]] = [None] * total
    fallback_rows: List[Tuple[int, Dict]] = []

    # ── Step 1: Validate coordinates and separate valid/invalid rows ──
    valid_indices: List[int] = []  # indices into prepared_rows with valid coords
    invalid_indices: List[int] = []  # indices with invalid coords

    for i, row in enumerate(prepared_rows):
        lat = row.get("existing_lat")
        lon = row.get("existing_lon")
        is_valid, reason = validate_coordinate(lat, lon)

        if is_valid:
            valid_indices.append(i)
        else:
            invalid_indices.append(i)
            # Handle invalid coordinates
            raw_addr = row.get("addr")
            # Treat None, NaN (float), and non-string types as empty
            if raw_addr is None or (isinstance(raw_addr, float) and math.isnan(raw_addr)):
                addr = ""
            elif isinstance(raw_addr, str):
                addr = raw_addr.strip()
            else:
                addr = str(raw_addr).strip()
            if not addr:
                # Invalid coords + empty address: confidence=0, needs_review=True
                # (Requirement 4.4, 4.5)
                raw_orig = row.get("addr")
                original_address = "" if raw_orig is None or (isinstance(raw_orig, float) and math.isnan(raw_orig)) else (raw_orig if isinstance(raw_orig, str) else str(raw_orig))
                lat_val = row.get("existing_lat", 0.0)
                lon_val = row.get("existing_lon", 0.0)
                results[i] = {
                    "original_address": original_address,
                    "base_address": original_address,
                    "unit_text": "",
                    "is_multi_unit": False,
                    "latitude": lat_val,
                    "longitude": lon_val,
                    "existing_lat": lat_val,
                    "existing_lon": lon_val,
                    "formatted_address": "",
                    "street": "",
                    "postal_code": "",
                    "city": "",
                    "state": "",
                    "district": "",
                    "country": "",
                    "country_code": "",
                    "precision": "None",
                    "confidence_score": 0.0,
                    "confidence_level": "Low",
                    "output_strategy": "decomposed_address",
                    "needs_review": True,
                    "recommendation": f"Coordinate validation failed ({reason}) and address column is empty.",
                    "geocoding_source": "Reverse Geocode (Lat/Long)",
                    "verification_status": "invalid_coords",
                    "verification_message": f"Coordinate validation failed: {reason}",
                    "distance_from_existing": 0,
                    "map_link_existing": "",
                    "map_link_suggested": "",
                    "map_link_compare": "",
                    "_original_row": row.get("_original_row", {}),
                    "entrance_source": "",
                    "entrance_type": "",
                    "geocode_alternatives": [],
                }
            else:
                # Invalid coords but has address → forward geocode fallback
                # (Requirement 3.4, 4.5)
                fallback_rows.append((i, row))

    done_count = len(invalid_indices)
    if progress_callback:
        progress_callback(done_count, total)

    # ── Step 2: Batch reverse geocode valid coordinates via PTV ──
    if not valid_indices:
        # No valid coordinates to process
        if progress_callback:
            progress_callback(total, total)
        return results, fallback_rows

    # Build positions list for PTV batch
    positions = []
    for idx in valid_indices:
        row = prepared_rows[idx]
        positions.append({
            "latitude": float(row["existing_lat"]),
            "longitude": float(row["existing_lon"]),
        })

    # Call PTV batch reverse geocode (batch_size=500, max_concurrent=4)
    batch_results, batch_error = reverse_geocode_batch_ptv(
        positions,
        batch_size=500,
        max_concurrent_batches=4,
    )

    # ── Step 3: Process batch results, identify failures ──
    ptv_failed_indices: List[int] = []  # indices into valid_indices that failed

    for vi_pos, vi_idx in enumerate(valid_indices):
        row = prepared_rows[vi_idx]
        position_results = batch_results[vi_pos] if vi_pos < len(batch_results) else []

        if position_results and len(position_results) > 0:
            # Success — use first result from batch
            batch_item = position_results[0]
            reverse_result = _batch_result_to_reverse_result(batch_item)
            results[vi_idx] = _build_decompose_result(row, reverse_result, source="PTV")
        else:
            # PTV batch failed for this position — mark for retry
            ptv_failed_indices.append(vi_pos)

    done_count += (len(valid_indices) - len(ptv_failed_indices))
    if progress_callback:
        progress_callback(done_count, total)

    # ── Step 4: Retry PTV failures individually (up to 2 attempts), then Azure ──
    for vi_pos in ptv_failed_indices:
        vi_idx = valid_indices[vi_pos]
        row = prepared_rows[vi_idx]
        lat = float(row["existing_lat"])
        lon = float(row["existing_lon"])

        # Retry PTV individually up to 2 attempts
        ptv_success = False
        for attempt in range(2):
            ptv_result = reverse_geocode_ptv(lat, lon)
            if ptv_result:
                # reverse_geocode_ptv returns dict with fields matching
                # what _build_decompose_result expects for source="PTV"
                results[vi_idx] = _build_decompose_result(row, ptv_result, source="PTV")
                ptv_success = True
                break

        if not ptv_success:
            # Try Azure Maps fallback
            try:
                azure_result = reverse_geocode_azure(lat, lon)
                if azure_result and azure_result.get("formatted_address"):
                    results[vi_idx] = _build_decompose_result(row, azure_result, source="Azure")
                else:
                    # Azure returned empty/no result
                    _handle_reverse_geocode_failure(results, fallback_rows, vi_idx, row, "PTV and Azure returned no results")
            except (ReverseGeocodingError, Exception) as e:
                # Azure also failed
                _handle_reverse_geocode_failure(results, fallback_rows, vi_idx, row, f"PTV and Azure failed: {e}")

        done_count += 1
        if progress_callback:
            progress_callback(done_count, total)

    # Final progress update
    if progress_callback:
        progress_callback(total, total)

    return results, fallback_rows


def _handle_reverse_geocode_failure(
    results: List[Optional[Dict]],
    fallback_rows: List[Tuple[int, Dict]],
    idx: int,
    row: Dict,
    failure_reason: str,
) -> None:
    """
    Handle a row where both PTV and Azure reverse geocoding failed.

    If the row has a combined address, it is added to fallback_rows for forward
    geocoding. Otherwise, a zero-confidence review result is generated.
    """
    addr = (row.get("addr") or "").strip()
    if addr:
        # Has address text → route to forward geocoding fallback
        fallback_rows.append((idx, row))
        # results[idx] stays None to indicate it needs forward geocode
    else:
        # No address and reverse geocoding failed → zero confidence review
        original_address = row.get("addr", "") or ""
        lat_val = row.get("existing_lat", 0.0)
        lon_val = row.get("existing_lon", 0.0)
        results[idx] = {
            "original_address": original_address,
            "base_address": original_address,
            "unit_text": "",
            "is_multi_unit": False,
            "latitude": lat_val,
            "longitude": lon_val,
            "existing_lat": lat_val,
            "existing_lon": lon_val,
            "formatted_address": "",
            "street": "",
            "postal_code": "",
            "city": "",
            "state": "",
            "district": "",
            "country": "",
            "country_code": "",
            "precision": "None",
            "confidence_score": 0.0,
            "confidence_level": "Low",
            "output_strategy": "decomposed_address",
            "needs_review": True,
            "recommendation": f"Reverse geocoding failed: {failure_reason}",
            "geocoding_source": "Reverse Geocode (Lat/Long)",
            "verification_status": "reverse_geocode_failed",
            "verification_message": failure_reason,
            "distance_from_existing": 0,
            "map_link_existing": "",
            "map_link_suggested": "",
            "map_link_compare": "",
            "_original_row": row.get("_original_row", {}),
            "entrance_source": "",
            "entrance_type": "",
            "geocode_alternatives": [],
        }
