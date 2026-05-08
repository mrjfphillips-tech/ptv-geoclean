"""
Exporter Module
Outputs clean Excel files formatted for OptiFlow routing systems.
Includes an OptiFlow-ready sheet with exact column headers that OptiFlow expects.

OptiFlow Order Excel column headers (from PTV OptiFlow Knowledge Base):
- Location ID: unique key per location
- Location Name: name of the location
- Location Street: street address with house number
- Location City: city
- Location Zipcode: postal/zip code
- Location Country: ISO 2-letter country code (e.g., MX, US, DE)
- Latitude: decimal latitude
- Longitude: decimal longitude
"""

import pandas as pd
from typing import List, Dict
from io import BytesIO


# OptiFlow output columns (exact headers OptiFlow expects)
OPTIFLOW_HEADERS = {
    'Location ID': '',
    'Location Name': 'formatted_address',
    'Location Street': 'base_address',
    'Location City': 'city',
    'Location Zipcode': 'postal_code',
    'Location Country': 'country_code',
    'Latitude': 'latitude',
    'Longitude': 'longitude',
}

# Full GeoClean output columns (for the detailed results sheet)
GEOCLEAN_COLUMNS = [
    'original_address',
    'base_address',
    'unit_text',
    'is_multi_unit',
    'existing_lat',
    'existing_lon',
    'latitude',
    'longitude',
    'precision',
    'formatted_address',
    'postal_code',
    'city',
    'district',
    'country',
    'country_code',
    'confidence_score',
    'confidence_level',
    'output_strategy',
    'geocoding_source',
    'needs_review',
    'recommendation',
]


def results_to_dataframe(results: List[Dict]) -> pd.DataFrame:
    """
    Convert a list of pipeline results to a pandas DataFrame.

    Args:
        results: List of result dictionaries from the pipeline.

    Returns:
        DataFrame with all GeoClean columns.
    """
    rows = []
    for r in results:
        row = {
            'original_address': r.get('original_address', ''),
            'base_address': r.get('base_address', ''),
            'unit_text': r.get('unit_text', ''),
            'is_multi_unit': r.get('is_multi_unit', False),
            'existing_lat': r.get('existing_lat', ''),
            'existing_lon': r.get('existing_lon', ''),
            'latitude': r.get('latitude', 0.0),
            'longitude': r.get('longitude', 0.0),
            'precision': r.get('precision', ''),
            'formatted_address': r.get('formatted_address', ''),
            'postal_code': r.get('postal_code', ''),
            'city': r.get('city', ''),
            'district': r.get('district', ''),
            'country': r.get('country', ''),
            'country_code': r.get('country_code', ''),
            'confidence_score': r.get('confidence_score', 0.0),
            'confidence_level': r.get('confidence_level', 'Low'),
            'output_strategy': r.get('output_strategy', 'review'),
            'geocoding_source': r.get('geocoding_source', ''),
            'needs_review': r.get('needs_review', True),
            'recommendation': r.get('recommendation', ''),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    # Only include columns that exist
    cols = [c for c in GEOCLEAN_COLUMNS if c in df.columns]
    return df[cols]


def results_to_optiflow_dataframe(results: List[Dict],
                                  service_time: str = '00:05',
                                  volume: str = '1',
                                  timewindow: str = '08:00 - 18:00') -> pd.DataFrame:
    """
    Convert results to a DataFrame with OptiFlow column headers PLUS all original data.
    
    The output includes:
    1. Required OptiFlow columns (id, street, city, zipcode, country, service time, volume, timewindows)
    2. Geocoded lat/lon
    3. ALL original columns from the customer's uploaded file (preserved as-is)
    
    Original data takes priority — if the customer provided a value, it's kept.
    GeoClean only fills in what was missing (geocoded address, postal code, country code, coordinates).
    """
    svc_patterns = ['service time', 'service_time', 'servicetime', 'svc time']
    vol_patterns = ['volume', 'vol', 'litres', 'liters', 'capacity']
    tw_patterns = ['timewindow', 'time window', 'timewindows', 'time_window', 'timewindows day']
    id_patterns = ['id', 'order id', 'order_id', 'orderid']

    def _find_original_value(original_row: dict, patterns: list) -> str:
        """Find a value in the original row by matching column name patterns."""
        if not original_row:
            return ''
        for key in original_row:
            key_lower = key.lower().strip()
            for pattern in patterns:
                if pattern in key_lower:
                    val = original_row[key]
                    if val and str(val).strip() and str(val) not in ('nan', 'None', ''):
                        return str(val).strip()
        return ''

    rows = []
    for i, r in enumerate(results):
        original_row = r.get('_original_row', {})

        # Start with ALL original columns (preserve customer data)
        row = {}
        for key, val in original_row.items():
            if val and str(val) not in ('nan', 'None', ''):
                row[key] = val

        # Now overlay/add the required OptiFlow columns with geocoded data
        # These use the OptiFlow-expected header names
        street = r.get('base_address', '') or r.get('original_address', '')
        city_val = r.get('city', '')
        zipcode = r.get('postal_code', '')
        country_code = r.get('country_code', '')
        lat = r.get('latitude', 0.0)
        lon = r.get('longitude', 0.0)

        # For required fields: use original if available, else geocoded, else default
        orig_svc = _find_original_value(original_row, svc_patterns)
        orig_vol = _find_original_value(original_row, vol_patterns)
        orig_tw = _find_original_value(original_row, tw_patterns)
        orig_id = _find_original_value(original_row, id_patterns)

        # Set the OptiFlow required columns (these override any similarly-named original columns)
        row['id'] = orig_id or f"Order {i + 1}"
        row['street'] = street
        row['city'] = city_val
        row['zipcode'] = zipcode
        row['country'] = country_code
        row['service time'] = orig_svc or service_time or '00:05'
        row['volume'] = orig_vol or volume or '1'
        row['timewindows day 1'] = orig_tw or timewindow or '08:00 - 18:00'

        # Add geocoded coordinates
        if lat != 0.0 and lon != 0.0:
            row['latitude'] = lat
            row['longitude'] = lon

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Reorder columns: OptiFlow required first, then lat/lon, then all others
    priority_cols = ['id', 'street', 'city', 'zipcode', 'country',
                     'service time', 'volume', 'timewindows day 1',
                     'latitude', 'longitude']
    
    # Build final column order: priority columns first, then remaining original columns
    final_cols = [c for c in priority_cols if c in df.columns]
    remaining = [c for c in df.columns if c not in final_cols]
    final_cols.extend(remaining)

    return df[final_cols]


def export_to_excel(results: List[Dict], filepath: str = None,
                    service_time: str = '00:05', volume: str = '1',
                    timewindow: str = '08:00 - 18:00') -> BytesIO:
    """
    Export results to an Excel file with multiple sheets:
    1. "OptiFlow Import" — exact headers OptiFlow expects (upload directly)
    2. "Geocoded Results" — full GeoClean output with all details
    3. "Summary" — statistics
    4. "Needs Review" — only items flagged for review

    Args:
        results: List of pipeline result dictionaries.
        filepath: Optional file path to save. If None, returns BytesIO buffer.
        service_time: Default service time for OptiFlow (hh:mm format).
        volume: Default volume for OptiFlow (litres).
        timewindow: Default time window for OptiFlow.

    Returns:
        BytesIO buffer containing the Excel file (for Streamlit download).
    """
    df = results_to_dataframe(results)
    optiflow_df = results_to_optiflow_dataframe(results, service_time, volume, timewindow)

    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Sheet 1: OptiFlow-ready import (exact headers from OptiFlow example file)
        optiflow_df.to_excel(writer, sheet_name='OptiFlow Import', index=False)

        # Add the description row (row 2 with # prefix) that OptiFlow expects
        ws = writer.sheets['OptiFlow Import']
        descriptions = {
            'A': '#(optional)\nThe unique identification of the order',
            'B': '(required)\nStreet and number',
            'C': '(required)\nCity name',
            'D': '(required)\nPostal code',
            'E': '(required)\nCountry code (e.g. BE, NL, FR, MX, US)',
            'F': '(required)\nService time (hh:mm)',
            'G': '(required)\nVolume in litres',
            'H': '(optional)\nTimewindows (e.g. 08:00 - 18:00)',
        }
        # Insert description row after header
        ws.insert_rows(2)
        for col_letter, desc in descriptions.items():
            ws[f'{col_letter}2'] = desc

        # Sheet 2: Full GeoClean results
        df.to_excel(writer, sheet_name='Geocoded Results', index=False)

        # Sheet 3: Summary
        summary_data = {
            'Metric': [
                'Total Addresses',
                'Successfully Geocoded',
                'High Confidence',
                'Medium Confidence',
                'Low Confidence',
                'Needs Review',
                'Multi-Unit Addresses',
                'Road Access Found',
                'Postal Code Available',
                'Geocoding Source: PTV',
                'Geocoding Source: Azure',
                'Geocoding Source: Nominatim',
            ],
            'Count': [
                len(df),
                len(optiflow_df),
                len(df[df['confidence_level'] == 'High']),
                len(df[df['confidence_level'] == 'Medium']),
                len(df[df['confidence_level'] == 'Low']),
                len(df[df['needs_review'] == True]),
                len(df[df['is_multi_unit'] == True]),
                len(df[df['precision'].isin(['Road Access', 'Entrance'])]),
                len(df[df['postal_code'] != '']),
                len(df[df['geocoding_source'].str.contains('PTV', na=False)]),
                len(df[df['geocoding_source'].str.contains('Azure', na=False)]),
                len(df[df['geocoding_source'].str.contains('Nominatim', na=False)]),
            ],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Sheet 4: Review items only
        review_df = df[df['needs_review'] == True]
        if not review_df.empty:
            review_df.to_excel(writer, sheet_name='Needs Review', index=False)

    buffer.seek(0)

    if filepath:
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
        buffer.seek(0)

    return buffer


# ─── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== GeoClean Exporter Test ===\n")

    sample_results = [
        {
            'original_address': 'Av. Javier Prado 4200 Dpto 802, Lima',
            'base_address': 'Av. Javier Prado 4200, Lima',
            'unit_text': 'Dpto 802',
            'is_multi_unit': True,
            'latitude': -12.0875,
            'longitude': -77.0012,
            'precision': 'Building',
            'formatted_address': 'Avenida Javier Prado 4200, San Isidro, Lima',
            'postal_code': '15036',
            'city': 'Lima',
            'district': 'San Isidro',
            'country': 'Peru',
            'country_code': 'PE',
            'confidence_score': 0.72,
            'confidence_level': 'Medium',
            'output_strategy': 'building_coords',
            'needs_review': False,
            'recommendation': 'Coordinates usable; postal code available as fallback.',
        },
        {
            'original_address': '123 Main St, New York, NY 10001',
            'base_address': '123 Main St, New York, NY 10001',
            'unit_text': '',
            'is_multi_unit': False,
            'latitude': 40.7484,
            'longitude': -73.9967,
            'precision': 'Entrance',
            'formatted_address': '123 Main Street, New York, NY 10001',
            'postal_code': '10001',
            'city': 'New York',
            'district': 'Manhattan',
            'country': 'United States',
            'country_code': 'US',
            'confidence_score': 0.92,
            'confidence_level': 'High',
            'output_strategy': 'entrance_coords',
            'needs_review': False,
            'recommendation': 'Use coordinates directly for routing.',
        },
    ]

    buffer = export_to_excel(sample_results)
    print(f"Excel generated: {len(buffer.getvalue())} bytes")
    print(f"Columns: {OPTIFLOW_COLUMNS}")

    df = results_to_dataframe(sample_results)
    print(f"\nDataFrame shape: {df.shape}")
    print(df[['original_address', 'confidence_level', 'output_strategy']].to_string())
