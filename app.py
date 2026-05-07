"""
GeoClean — Streamlit Application
Fuzzy Geocoding with Confidence for OptiFlow

Upload messy address data → get clean, confidence-scored geographic output.
"""

import streamlit as st
import pandas as pd
from modules.pipeline import process_row, process_dataframe
from modules.exporter import export_to_excel, results_to_dataframe
from modules.address_parser import parse_address
from modules.verifier import verify_coordinates, has_existing_coordinates
from modules.column_detector import detect_columns, get_detection_summary, has_minimum_fields, get_mode
from modules.template import generate_template
from config import AZURE_MAPS_KEY


# ─── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GeoClean — Fuzzy Geocoding",
    page_icon="🌍",
    layout="wide",
)

# ─── Header ────────────────────────────────────────────────────────────────────

st.title("🌍 GeoClean")
st.caption("Fuzzy Geocoding with Confidence — Convert messy addresses to OptiFlow-ready output")

# Check API key
if not AZURE_MAPS_KEY:
    st.warning("⚠️ **Azure Maps API key not configured.** Create a `.env` file in the geoclean folder with:\n```\nAZURE_MAPS_KEY=your-key-here\n```")

# ─── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown("---")

    # Column mapping
    st.subheader("Column Mapping")
    address_col = st.text_input("Full address column", value="", help="Column with the complete address string (leave empty if using separate fields)")
    street_col = st.text_input("Street column", value="Street", help="Street address column")
    city_col = st.text_input("City column", value="City")
    state_col = st.text_input("State/Province column", value="State")
    postal_col = st.text_input("Postal code column", value="Zip Code")
    country_col = st.text_input("Country column", value="Country")
    country_code_col = st.text_input("Country code column (optional)", value="", help="ISO 2-letter code (e.g., PE, US, GB)")

    st.markdown("---")
    st.subheader("Existing Coordinates")
    lat_col = st.text_input("Latitude column", value="Latitude", help="If your data already has lat/lon, GeoClean will VERIFY instead of geocode")
    lon_col = st.text_input("Longitude column", value="Longitude", help="Existing longitude column")

    st.markdown("---")
    st.subheader("About")
    st.markdown("""
    **GeoClean** processes messy address data into clean, confidence-scored geographic output for routing systems.

    Features:
    - 🏢 Apartment/unit detection
    - 🗺️ Azure Maps fuzzy geocoding
    - 🔄 Reverse geocode standardization
    - 🚪 Building entrance detection
    - 📊 Confidence scoring
    - 🌍 International address support
    """)

# ─── File Upload ───────────────────────────────────────────────────────────────

st.header("📁 Upload Address Data")

col_upload, col_template = st.columns([3, 1])
with col_upload:
    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="File should contain address data in one or more columns"
    )
with col_template:
    st.markdown("<br>", unsafe_allow_html=True)
    template_buffer = generate_template()
    st.download_button(
        label="📥 Download Template",
        data=template_buffer,
        file_name="GeoClean_OptiFlow_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Download a blank template with all OptiFlow-required columns and instructions",
    )

if uploaded_file:
    # Read file
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"✅ Loaded **{len(df)} rows** × {len(df.columns)} columns")

        # Auto-detect columns
        detected = detect_columns(df.columns.tolist())
        mode = get_mode(detected)

        # Build options list: ["(none)", ...all columns...]
        col_options = ["(none)"] + df.columns.tolist()

        # Show detection results with override dropdowns
        with st.expander("🔍 Column Mapping — Auto-Detected (override with dropdowns)", expanded=True):
            if mode == "verify":
                st.info("📍 **Verification Mode** — Your data has coordinates. GeoClean will verify them against geocoded results and flag discrepancies.")
            elif mode == "geocode":
                st.info("🗺️ **Geocoding Mode** — No existing coordinates found. GeoClean will geocode from address fields.")
            else:
                st.warning("⚠️ **Insufficient data** — Could not detect enough columns. Please select them below.")

            st.caption("Auto-detected columns are pre-selected. Change any dropdown to override.")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Address Fields:**")
                def _idx(field):
                    val = detected.get(field)
                    if val and val in col_options:
                        return col_options.index(val)
                    return 0

                sel_address = st.selectbox("Full Address", col_options, index=_idx('address'), key='sel_address')
                sel_street = st.selectbox("Street", col_options, index=_idx('street'), key='sel_street')
                sel_number = st.selectbox("Number", col_options, index=_idx('number'), key='sel_number')
                sel_neighborhood = st.selectbox("Neighborhood", col_options, index=_idx('neighborhood'), key='sel_neighborhood')
                sel_city = st.selectbox("City", col_options, index=_idx('city'), key='sel_city')

            with col2:
                sel_state = st.selectbox("State/Province", col_options, index=_idx('state'), key='sel_state')
                sel_postal = st.selectbox("Postal Code", col_options, index=_idx('postal_code'), key='sel_postal')
                sel_country = st.selectbox("Country", col_options, index=_idx('country'), key='sel_country')
                st.markdown("**Coordinates:**")
                sel_lat = st.selectbox("Latitude", col_options, index=_idx('latitude'), key='sel_lat')
                sel_lon = st.selectbox("Longitude", col_options, index=_idx('longitude'), key='sel_lon')

        # Store final selections (dropdown overrides auto-detect)
        def _val(sel): return sel if sel != "(none)" else ""
        st.session_state['mapping'] = {
            'address': _val(sel_address),
            'street': _val(sel_street),
            'number': _val(sel_number),
            'neighborhood': _val(sel_neighborhood),
            'city': _val(sel_city),
            'state': _val(sel_state),
            'postal_code': _val(sel_postal),
            'country': _val(sel_country),
            'latitude': _val(sel_lat),
            'longitude': _val(sel_lon),
        }

        # Data preview
        with st.expander("📋 Data Preview", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
            st.caption(f"Columns: {', '.join(df.columns.tolist())}")

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
        df = None

    if df is not None:
        st.markdown("---")

        # ─── Run Geocoding ─────────────────────────────────────────────────────

        col1, col2 = st.columns([1, 3])
        with col1:
            run_button = st.button("🚀 Run Geocoding", type="primary", use_container_width=True)
        with col2:
            st.caption(f"Will process {len(df)} addresses using Azure Maps Fuzzy Search")

        if run_button:
            if not AZURE_MAPS_KEY:
                st.error("Cannot run without Azure Maps API key. Set AZURE_MAPS_KEY in .env")
            else:
                # Process with progress bar
                progress = st.progress(0, text="Processing addresses...")
                results = []

                for i, (_, row) in enumerate(df.iterrows()):
                    # Use auto-detected columns (fall back to sidebar values)
                    d = st.session_state.get('mapping', {})
                    _address_col = d.get('address', '') or address_col
                    _street_col = d.get('street', '') or street_col
                    _number_col = d.get('number', '')
                    _city_col = d.get('city', '') or city_col
                    _state_col = d.get('state', '') or state_col
                    _postal_col = d.get('postal_code', '') or postal_col
                    _country_col = d.get('country', '') or country_col
                    _lat_col = d.get('latitude', '') or lat_col
                    _lon_col = d.get('longitude', '') or lon_col

                    # Build address from available columns
                    addr = str(row.get(_address_col, '')) if _address_col and _address_col in df.columns else ''
                    street_val = str(row.get(_street_col, '')) if _street_col and _street_col in df.columns else ''
                    number_val = str(row.get(_number_col, '')) if _number_col and _number_col in df.columns else ''
                    city_val = str(row.get(_city_col, '')) if _city_col and _city_col in df.columns else ''
                    state_val = str(row.get(_state_col, '')) if _state_col and _state_col in df.columns else ''
                    postal_val = str(row.get(_postal_col, '')) if _postal_col and _postal_col in df.columns else ''
                    country_val = str(row.get(_country_col, '')) if _country_col and _country_col in df.columns else ''
                    cc = str(row.get(country_code_col, '')) if country_code_col and country_code_col in df.columns else ''

                    # Combine street + number if both present
                    if number_val and number_val not in ('nan', 'None', '') and street_val and street_val not in ('nan', 'None', ''):
                        street_val = f"{street_val} {number_val}"

                    # Check for existing coordinates
                    existing_lat = 0.0
                    existing_lon = 0.0
                    try:
                        if _lat_col and _lat_col in df.columns:
                            existing_lat = float(row.get(_lat_col, 0))
                        if _lon_col and _lon_col in df.columns:
                            existing_lon = float(row.get(_lon_col, 0))
                    except (ValueError, TypeError):
                        existing_lat, existing_lon = 0.0, 0.0

                    # Clean nan values
                    def clean(v): return '' if str(v) in ('nan', 'None', 'NaN', '') else str(v)
                    addr = clean(addr)
                    street_val = clean(street_val)
                    city_val = clean(city_val)
                    state_val = clean(state_val)
                    postal_val = clean(postal_val)
                    country_val = clean(country_val)
                    cc = clean(cc)

                    # Run geocoding pipeline
                    result = process_row(
                        address=addr,
                        street=street_val,
                        city=city_val,
                        state=state_val,
                        postal_code=postal_val,
                        country=country_val,
                        country_code=cc,
                    )

                    # VERIFICATION MODE: if existing coords present, compare instead of replace
                    if has_existing_coordinates(existing_lat, existing_lon):
                        verification = verify_coordinates(
                            existing_lat, existing_lon,
                            result.get('latitude', 0.0), result.get('longitude', 0.0),
                            address=addr,
                        )
                        result['verification_status'] = verification['status']
                        result['verification_message'] = verification['message']
                        result['distance_from_existing'] = verification['distance_meters']
                        result['map_link_existing'] = verification['map_link_existing']
                        result['map_link_suggested'] = verification['map_link_suggested']
                        result['map_link_compare'] = verification['map_link_compare']
                        result['existing_lat'] = existing_lat
                        result['existing_lon'] = existing_lon

                        # Keep existing coords unless large discrepancy
                        if verification['use_existing']:
                            result['latitude'] = existing_lat
                            result['longitude'] = existing_lon
                            if verification['status'] == 'verified':
                                result['confidence_level'] = 'High'
                                result['confidence_score'] = 0.95
                                result['recommendation'] = 'Existing coordinates verified ✓'
                        else:
                            # Suggest new coords but don't force
                            result['recommendation'] = verification['message']
                    else:
                        result['verification_status'] = 'new_geocode'
                        result['verification_message'] = 'No existing coordinates — geocoded fresh'
                        result['distance_from_existing'] = 0
                        result['map_link_existing'] = ''
                        result['map_link_suggested'] = ''
                        result['map_link_compare'] = ''

                    results.append(result)

                    progress.progress((i + 1) / len(df), text=f"Processing {i+1}/{len(df)}...")

                progress.empty()
                st.success(f"✅ Processed **{len(results)} addresses**")

                # Store results in session state
                st.session_state['results'] = results

        # ─── Results Display ───────────────────────────────────────────────────

        if 'results' in st.session_state:
            results = st.session_state['results']
            result_df = results_to_dataframe(results)

            st.markdown("---")
            st.header("📊 Results")

            # Summary metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                high = len(result_df[result_df['confidence_level'] == 'High'])
                st.metric("🟢 High Confidence", high)
            with col2:
                med = len(result_df[result_df['confidence_level'] == 'Medium'])
                st.metric("🟡 Medium", med)
            with col3:
                low = len(result_df[result_df['confidence_level'] == 'Low'])
                st.metric("🔴 Low", low)
            with col4:
                review = len(result_df[result_df['needs_review'] == True])
                st.metric("⚠️ Needs Review", review)
            with col5:
                entrances = len(result_df[result_df['precision'] == 'Entrance'])
                st.metric("🚪 Entrances Found", entrances)

            # Filter
            st.subheader("Filter Results")
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                level_filter = st.multiselect(
                    "Confidence Level",
                    options=['High', 'Medium', 'Low'],
                    default=['High', 'Medium', 'Low'],
                )
            with filter_col2:
                strategy_filter = st.multiselect(
                    "Output Strategy",
                    options=['entrance_coords', 'building_coords', 'postal_code', 'review'],
                    default=['entrance_coords', 'building_coords', 'postal_code', 'review'],
                )

            filtered_df = result_df[
                (result_df['confidence_level'].isin(level_filter)) &
                (result_df['output_strategy'].isin(strategy_filter))
            ]

            # Color-coded results table
            def color_confidence(val):
                if val == 'High':
                    return 'background-color: rgba(34,197,94,0.2)'
                elif val == 'Medium':
                    return 'background-color: rgba(234,179,8,0.2)'
                else:
                    return 'background-color: rgba(239,68,68,0.2)'

            # Column help legend
            with st.expander("ℹ️ Column Descriptions — click to expand"):
                st.markdown("""
| Column | Description |
|--------|-------------|
| **original_address** | The raw address from your uploaded file |
| **formatted_address** | Standardized address returned by Azure Maps |
| **latitude** | Final latitude to use for routing |
| **longitude** | Final longitude to use for routing |
| **postal_code** | Postal/ZIP code (verified or extracted) |
| **confidence_score** | 0.0–1.0 score based on geocode quality, match type, postal code, and verification |
| **confidence_level** | 🟢 High (≥0.75) = use directly · 🟡 Medium (0.50–0.74) = usable with caution · 🔴 Low (<0.50) = needs review |
| **precision** | "Entrance" = building entrance found · "Building" = building centroid |
| **output_strategy** | What to use: entrance_coords, building_coords, postal_code, or review |
| **recommendation** | Human-readable explanation of why confidence is at this level |
| **needs_review** | TRUE = manual verification recommended before using in routing |
""")

            display_cols = [
                'original_address', 'formatted_address', 'latitude', 'longitude',
                'postal_code', 'confidence_score', 'confidence_level',
                'precision', 'output_strategy', 'recommendation', 'needs_review',
            ]
            display_df = filtered_df[display_cols].copy()

            st.dataframe(
                display_df.style.map(color_confidence, subset=['confidence_level']),
                use_container_width=True,
                height=400,
            )

            # ─── Download ──────────────────────────────────────────────────────

            st.markdown("---")
            st.subheader("📥 Export")

            excel_buffer = export_to_excel(results)
            st.download_button(
                label="⬇️ Download Excel (OptiFlow-ready)",
                data=excel_buffer,
                file_name="geoclean_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

else:
    # No file uploaded — show single address test
    st.markdown("---")
    st.header("🔍 Test Single Address")

    test_address = st.text_input(
        "Enter an address to test",
        value="Av. Javier Prado 4200 Dpto 802, Lima, Peru",
        help="Try any international address"
    )

    if st.button("Parse & Preview"):
        result = parse_address(test_address)
        col1, col2 = st.columns(2)
        with col1:
            st.json(result)
        with col2:
            if result['is_multi_unit']:
                st.info(f"🏢 **Multi-unit detected**\n\nUnit: `{result['unit_text']}`\n\nBase: `{result['base_address']}`")
            else:
                st.success("✅ Single address (no unit detected)")
