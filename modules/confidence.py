"""
Confidence Scoring Module
Applies a multi-factor confidence model to geocoding results.
Determines whether output is high-confidence or needs review.
"""

from typing import Dict, Optional


# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.75
MEDIUM_CONFIDENCE_THRESHOLD = 0.50
REVIEW_THRESHOLD = 0.50


def score_result(
    geocode_score: float = 0.0,
    match_type: str = '',
    has_postal_code: bool = False,
    postal_code_matches: bool = False,
    has_entrance: bool = False,
    is_multi_unit: bool = False,
    reverse_geocode_matches: bool = False,
    country_code: str = '',
) -> Dict:
    """
    Calculate a confidence score for a geocoding result.

    Scoring factors (weighted):
        - Azure geocode score (0-1): 30%
        - Match type quality: 20%
        - Postal code available and matches: 20%
        - Reverse geocode confirms address: 15%
        - Entrance precision: 10%
        - Multi-unit penalty: 5%

    Args:
        geocode_score: Raw score from Azure Maps (0-1)
        match_type: Azure match type (e.g., "Point Address", "Address Range")
        has_postal_code: Whether a postal code was found
        postal_code_matches: Whether input postal code matches geocoded postal code
        has_entrance: Whether an entrance was found (vs building fallback)
        is_multi_unit: Whether the address is an apartment/unit
        reverse_geocode_matches: Whether reverse geocode confirms the forward result
        country_code: ISO country code for country-specific adjustments

    Returns:
        Dictionary with:
            - confidence_score: Float 0-1
            - confidence_level: "High", "Medium", or "Low"
            - needs_review: Boolean
            - factors: Dict of individual factor scores
            - recommendation: String describing the output quality
    """
    factors = {}

    # Factor 1: Azure geocode score (30%)
    factors['geocode_score'] = min(1.0, geocode_score)

    # Factor 2: Match type quality (20%)
    match_type_scores = {
        'Point Address': 1.0,
        'Address Range': 0.7,
        'Street': 0.5,
        'Cross Street': 0.4,
        'Geography': 0.3,
        'POI': 0.6,
    }
    factors['match_type'] = match_type_scores.get(match_type, 0.3)

    # Factor 3: Postal code (20%)
    if postal_code_matches:
        factors['postal_code'] = 1.0
    elif has_postal_code:
        factors['postal_code'] = 0.6
    else:
        factors['postal_code'] = 0.0

    # Factor 4: Reverse geocode confirmation (15%)
    factors['reverse_confirm'] = 1.0 if reverse_geocode_matches else 0.3

    # Factor 5: Entrance precision (10%)
    factors['entrance'] = 1.0 if has_entrance else 0.5

    # Factor 6: Multi-unit handling (5%)
    # Multi-unit addresses are inherently less precise at the coordinate level
    factors['multi_unit'] = 0.4 if is_multi_unit else 1.0

    # Weighted calculation
    weights = {
        'geocode_score': 0.30,
        'match_type': 0.20,
        'postal_code': 0.20,
        'reverse_confirm': 0.15,
        'entrance': 0.10,
        'multi_unit': 0.05,
    }

    confidence_score = sum(factors[k] * weights[k] for k in weights)
    confidence_score = round(min(1.0, max(0.0, confidence_score)), 4)

    # Determine level
    if confidence_score >= HIGH_CONFIDENCE_THRESHOLD:
        level = 'High'
    elif confidence_score >= MEDIUM_CONFIDENCE_THRESHOLD:
        level = 'Medium'
    else:
        level = 'Low'

    needs_review = confidence_score < REVIEW_THRESHOLD

    # Recommendation
    if confidence_score >= HIGH_CONFIDENCE_THRESHOLD:
        recommendation = "Use coordinates directly for routing."
    elif has_postal_code and confidence_score >= MEDIUM_CONFIDENCE_THRESHOLD:
        recommendation = "Coordinates usable; postal code available as fallback."
    elif has_postal_code:
        recommendation = "Use postal code centroid for routing. Coordinates unreliable."
    else:
        recommendation = "Manual review required. Insufficient data for reliable geocoding."

    return {
        'confidence_score': confidence_score,
        'confidence_level': level,
        'needs_review': needs_review,
        'factors': factors,
        'recommendation': recommendation,
    }


def determine_output_strategy(
    confidence_score: float,
    has_entrance: bool,
    has_postal_code: bool,
) -> str:
    """
    Determine which output to use for routing.

    Returns one of:
        - "entrance_coords": Use entrance lat/lon
        - "building_coords": Use building lat/lon
        - "postal_code": Use postal code centroid
        - "review": Flag for manual review
    """
    if has_entrance and confidence_score >= HIGH_CONFIDENCE_THRESHOLD:
        return "entrance_coords"
    elif confidence_score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "building_coords"
    elif has_postal_code:
        return "postal_code"
    else:
        return "review"


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== GeoClean Confidence Scoring Test ===\n")

    scenarios = [
        ("Perfect match", dict(geocode_score=0.95, match_type='Point Address', has_postal_code=True, postal_code_matches=True, has_entrance=True, is_multi_unit=False, reverse_geocode_matches=True)),
        ("Good match, no entrance", dict(geocode_score=0.85, match_type='Point Address', has_postal_code=True, postal_code_matches=True, has_entrance=False, is_multi_unit=False, reverse_geocode_matches=True)),
        ("Apartment, medium match", dict(geocode_score=0.70, match_type='Address Range', has_postal_code=True, postal_code_matches=False, has_entrance=False, is_multi_unit=True, reverse_geocode_matches=False)),
        ("Poor match, has postal", dict(geocode_score=0.30, match_type='Geography', has_postal_code=True, postal_code_matches=False, has_entrance=False, is_multi_unit=False, reverse_geocode_matches=False)),
        ("No data", dict(geocode_score=0.10, match_type='', has_postal_code=False, postal_code_matches=False, has_entrance=False, is_multi_unit=False, reverse_geocode_matches=False)),
    ]

    for name, kwargs in scenarios:
        result = score_result(**kwargs)
        strategy = determine_output_strategy(result['confidence_score'], kwargs['has_entrance'], kwargs['has_postal_code'])
        print(f"{result['confidence_level']:6s} ({result['confidence_score']:.2f}) | {name}")
        print(f"       Strategy: {strategy}")
        print(f"       {result['recommendation']}")
        print()
