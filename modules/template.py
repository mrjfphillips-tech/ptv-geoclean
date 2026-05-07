"""
Template Generator Module
Creates a downloadable Excel template with OptiFlow-required columns,
instructions, and example data for customers with unstructured address data.
"""

import pandas as pd
from io import BytesIO


def generate_template() -> BytesIO:
    """
    Generate an OptiFlow-ready Excel template with:
    - Data sheet with correct column headers and 3 example rows
    - Instructions sheet explaining each column
    - Returns a BytesIO buffer ready for download.
    """
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # ─── Data Sheet ────────────────────────────────────────────────────
        data = {
            'Location ID': ['LOC001', 'LOC002', 'LOC003'],
            'Location Name': ['Warehouse Lima Centro', 'Customer ABC', 'Store XYZ'],
            'Street': ['Av. Javier Prado 4200', '123 Main Street', 'Calle Los Olivos 345'],
            'Number': ['', '4B', ''],
            'Neighborhood': ['San Isidro', '', 'Miraflores'],
            'City': ['Lima', 'New York', 'Lima'],
            'State': ['Lima', 'NY', 'Lima'],
            'Zip Code': ['15036', '10001', '15074'],
            'Country': ['Peru', 'United States', 'Peru'],
            'Latitude': [-12.0875, 40.7484, -12.1200],
            'Longitude': [-77.0012, -73.9967, -77.0300],
            'Order ID': ['ORD-001', 'ORD-002', 'ORD-003'],
            'Depot Name': ['CD Callao', 'NYC Depot', 'CD Callao'],
            'Type of Order': ['Delivery', 'Delivery', 'Pickup'],
            '# of SKUs (Boxes, Pallets, etc)': [5, 2, 8],
            'Weight (kg)': [120.5, 45.0, 200.0],
            'Vol (m3)': [1.5, 0.5, 2.8],
            'Service Time (in min)': [15, 10, 20],
            'Time Window': ['08:00-12:00', '09:00-17:00', '06:00-10:00'],
            'Route ID': ['', '', ''],
            'Vehicle ID': ['', '', ''],
            'Stop Sequence': ['', '', ''],
            'Delivery Date': ['2026-05-15', '2026-05-15', '2026-05-16'],
            'Arrival Time': ['', '', ''],
            'Departure Time': ['', '', ''],
        }
        df_data = pd.DataFrame(data)
        df_data.to_excel(writer, sheet_name='Orders', index=False)

        # ─── Instructions Sheet ────────────────────────────────────────────
        instructions = {
            'Column': [
                'Location ID',
                'Location Name',
                'Street',
                'Number',
                'Neighborhood',
                'City',
                'State',
                'Zip Code',
                'Country',
                'Latitude',
                'Longitude',
                'Order ID',
                'Depot Name',
                'Type of Order',
                '# of SKUs (Boxes, Pallets, etc)',
                'Weight (kg)',
                'Vol (m3)',
                'Service Time (in min)',
                'Time Window',
                'Route ID',
                'Vehicle ID',
                'Stop Sequence',
                'Delivery Date',
                'Arrival Time',
                'Departure Time',
            ],
            'Required': [
                'Yes',
                'Yes',
                'Yes',
                'Optional',
                'Optional',
                'Yes',
                'Optional',
                'Recommended',
                'Yes',
                'Optional*',
                'Optional*',
                'Yes',
                'Yes',
                'Yes',
                'Optional',
                'Optional',
                'Optional',
                'Recommended',
                'Recommended',
                'Optional',
                'Optional',
                'Optional',
                'Recommended',
                'Optional',
                'Optional',
            ],
            'Description': [
                'Unique identifier for the delivery/pickup location. Used to group orders at the same address.',
                'Human-readable name for the location (store name, customer name, warehouse name).',
                'Street address including avenue/road name. Do NOT include apartment/unit here if possible.',
                'House or building number. Can be left empty if included in Street.',
                'Neighborhood, district, or suburb. Helps with geocoding accuracy in Latin America.',
                'City or municipality name. REQUIRED for geocoding.',
                'State, province, or region. Helps disambiguate cities with the same name.',
                'Postal/ZIP code. Strongly recommended — improves geocoding confidence significantly.',
                'Country name or ISO 2-letter code (e.g., "Peru" or "PE"). REQUIRED.',
                '*If you already have coordinates, include them. GeoClean will VERIFY them. If blank, GeoClean will geocode.',
                '*If you already have coordinates, include them. GeoClean will VERIFY them. If blank, GeoClean will geocode.',
                'Unique order identifier. Each row = one order.',
                'Name of the depot/warehouse this order ships from or returns to.',
                '"Delivery" or "Pickup". Determines routing direction.',
                'Number of items (boxes, pallets, cases). Used for vehicle capacity planning.',
                'Total weight in kilograms. Used for vehicle weight capacity.',
                'Total volume in cubic meters. Used for vehicle volume capacity.',
                'Expected time at the stop in minutes (loading/unloading). Affects route timing.',
                'Delivery time window in format HH:MM-HH:MM (e.g., "08:00-12:00"). Critical for routing.',
                'Leave blank — assigned by OptiFlow during optimization.',
                'Leave blank — assigned by OptiFlow during optimization.',
                'Leave blank — assigned by OptiFlow during optimization.',
                'Date of delivery/pickup in YYYY-MM-DD format.',
                'Leave blank — calculated by OptiFlow.',
                'Leave blank — calculated by OptiFlow.',
            ],
            'Example': [
                'LOC001',
                'Warehouse Lima Centro',
                'Av. Javier Prado 4200',
                '4B',
                'San Isidro',
                'Lima',
                'Lima',
                '15036',
                'Peru',
                '-12.0875',
                '-77.0012',
                'ORD-001',
                'CD Callao',
                'Delivery',
                '5',
                '120.5',
                '1.5',
                '15',
                '08:00-12:00',
                '(auto)',
                '(auto)',
                '(auto)',
                '2026-05-15',
                '(auto)',
                '(auto)',
            ],
        }
        df_instructions = pd.DataFrame(instructions)
        df_instructions.to_excel(writer, sheet_name='Instructions', index=False)

        # ─── Notes Sheet ───────────────────────────────────────────────────
        notes = {
            'Topic': [
                'About This Template',
                'Geocoding',
                'Apartments & Units',
                'International Addresses',
                'Time Windows',
                'Multiple Orders Same Location',
                'What GeoClean Does',
            ],
            'Details': [
                'This template contains the columns required by PTV OptiFlow for route optimization. Fill in your delivery/pickup data and upload to GeoClean for address verification and geocoding.',
                'If you have Latitude/Longitude already, GeoClean will VERIFY them (not replace). If coordinates are missing or blank, GeoClean will geocode from the address fields.',
                'If an address includes an apartment, unit, or floor (e.g., "Dpto 802"), GeoClean will automatically detect and separate it. The geocoding uses the base building address for accuracy.',
                'GeoClean supports addresses worldwide. Use the local language for street names. Always include Country. Postal codes are validated per country format.',
                'Format: HH:MM-HH:MM using 24-hour time. Example: "08:00-12:00" means delivery must arrive between 8am and noon. Multiple windows not supported in this template.',
                'Use the same Location ID for orders going to the same physical address. This ensures OptiFlow groups them on the same route stop.',
                'GeoClean processes this file to: (1) verify/geocode all addresses, (2) detect apartments, (3) score confidence, (4) flag errors with map links, (5) export a clean file ready for OptiFlow import.',
            ],
        }
        df_notes = pd.DataFrame(notes)
        df_notes.to_excel(writer, sheet_name='Notes', index=False)

    buffer.seek(0)
    return buffer
