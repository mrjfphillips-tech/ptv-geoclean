"""
Exporter Module
Outputs clean Excel files formatted for OptiFlow routing systems.
Includes confidence coloring and review flags.
"""

import pandas as pd
from typing import List, Dict
from io import BytesIO


# OptiFlow output columns
OPTIFLOW_COLUMNS = [
    'original_address',
    'base_address',
    'unit_text',
    'is_multi_unit',
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
    'needs_review',
    'recommendation',
]


def results_to_dataframe(results: List[Dict]) -> pd.DataFrame:
    """
    Convert a list of pipeline results to a pandas DataFrame.

    Args:
        results: List of result dictionaries from the pipeline.

    Returns:
        DataFrame with OptiFlow-ready columns.
    """
    rows = []
    for r in results:
        row = {
            'original_address': r.get('original_address', ''),
            'base_address': r.get('base_address', ''),
            'unit_text': r.get('unit_text', ''),
            'is_multi_unit': r.get('is_multi_unit', False),
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
            'needs_review': r.get('needs_review', True),
            'recommendation': r.get('recommendation', ''),
        }
        rows.append(row)

    df = pd.DataFrame(rows, columns=OPTIFLOW_COLUMNS)
    return df


def export_to_excel(results: List[Dict], filepath: str = None) -> BytesIO:
    """
    Export results to an Excel file with formatting.

    Args:
        results: List of pipeline result dictionaries.
        filepath: Optional file path to save. If None, returns BytesIO buffer.

    Returns:
        BytesIO buffer containing the Excel file (for Streamlit download).
    """
    df = results_to_dataframe(results)

    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Main results sheet
        df.to_excel(writer, sheet_name='Geocoded Results', index=False)

        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Addresses',
                'High Confidence',
                'Medium Confidence',
                'Low Confidence',
                'Needs Review',
                'Multi-Unit Addresses',
                'Entrance Found',
                'Postal Code Available',
            ],
            'Count': [
                len(df),
                len(df[df['confidence_level'] == 'High']),
                len(df[df['confidence_level'] == 'Medium']),
                len(df[df['confidence_level'] == 'Low']),
                len(df[df['needs_review'] == True]),
                len(df[df['is_multi_unit'] == True]),
                len(df[df['precision'] == 'Entrance']),
                len(df[df['postal_code'] != '']),
            ],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Review sheet (only items needing review)
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
