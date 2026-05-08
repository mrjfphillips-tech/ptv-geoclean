"""
GeoClean — Streamlit Application
Fuzzy Geocoding with Confidence for OptiFlow

Upload messy address data → get clean, confidence-scored geographic output.
"""

import streamlit as st
import pandas as pd
import os
from modules.pipeline import process_row, process_dataframe
from modules.exporter import export_to_excel, results_to_dataframe
from modules.address_parser import parse_address
from modules.verifier import verify_coordinates, has_existing_coordinates
from modules.column_detector import detect_columns, get_detection_summary, has_minimum_fields, get_mode
from modules.template import generate_template
from config import AZURE_MAPS_KEY

# Check PTV key availability
PTV_KEY_AVAILABLE = bool(os.environ.get("PTV_DEVELOPER_API_KEY", ""))


def _empty_result_for_error(address: str, error: str) -> dict:
    """Create an error result dict when parallel processing fails."""
    return {
        'original_address': address,
        'base_address': '', 'unit_text': '', 'is_multi_unit': False,
        'latitude': 0.0, 'longitude': 0.0, 'precision': '',
        'formatted_address': '', 'postal_code': '', 'city': '',
        'district': '', 'country': '', 'country_code': '',
        'confidence_score': 0.0, 'confidence_level': 'Low',
        'output_strategy': 'review', 'needs_review': True,
        'recommendation': f'Processing error: {error}',
        'entrance_source': '', 'entrance_type': '',
        'geocode_alternatives': [], 'geocoding_source': 'Error',
        'verification_status': 'error', 'verification_message': error,
        'distance_from_existing': 0,
        'map_link_existing': '', 'map_link_suggested': '', 'map_link_compare': '',
    }


# ─── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GeoClean — Smart Locations",
    page_icon="📍",
    layout="wide",
)

# ─── Header ────────────────────────────────────────────────────────────────────

col_logo, col_title = st.columns([1, 3])
with col_logo:
    st.image("logo.png", width=200)
with col_title:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Clean Data. Smart Locations. Optimized Deliveries.")

# Check API key
if not AZURE_MAPS_KEY:
    st.warning("⚠️ **Azure Maps API key not configured.** Create a `.env` file in the geoclean folder with:\n```\nAZURE_MAPS_KEY=your-key-here\n```")

if PTV_KEY_AVAILABLE:
    st.success("✅ **PTV Developer Geocoding** active — coordinates optimized for OptiFlow routing")
else:
    st.info("💡 Add `PTV_DEVELOPER_API_KEY` to `.env` for PTV-native geocoding (best for OptiFlow)")

# ─── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("settings_icon.png", width=160)
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
    - 🚛 PTV Developer geocoding (OptiFlow-native)
    - 🗺️ Azure Maps fuzzy geocoding
    - 🔄 Reverse geocode standardization
    - 🚪 Building entrance detection
    - 📊 Confidence scoring
    - 🌍 International address support

    **Geocoding Priority:**
    1. PTV Developer (road-access coords)
    2. Azure Maps
    3. HERE (if configured)
    4. Nominatim (OSM fallback)
    """)

# ─── File Upload ───────────────────────────────────────────────────────────────

import base64

# Custom CSS for styling
st.markdown("""
<style>
    /* Global font size increase */
    html, body, [class*="css"] {
        font-size: 1.1rem !important;
    }
    
    /* Sidebar text larger */
    [data-testid="stSidebar"] {
        font-size: 1.05rem !important;
    }
    [data-testid="stSidebar"] label {
        font-size: 1.05rem !important;
    }
    
    /* Make input fields lighter so they stand out */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    [data-testid="stFileUploader"] {
        background-color: #1a2332 !important;
        border: 1px solid #2d4a5e !important;
        font-size: 1.1rem !important;
    }
    
    /* Input labels larger */
    .stTextInput label, .stSelectbox label, .stMultiSelect label {
        font-size: 1.1rem !important;
    }
    
    /* Larger font for captions and labels */
    .big-caption {
        font-size: 1.2rem !important;
        color: #00d4ff !important;
        margin-top: 0.5rem;
    }
    
    /* Regular captions bigger */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-size: 1.0rem !important;
    }
    
    /* Center content vertically in columns */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    /* Style the file uploader drop zone */
    [data-testid="stFileUploader"] section {
        background-color: #1a2332 !important;
        border: 2px dashed #2d4a5e !important;
        border-radius: 8px;
    }
    
    /* Make buttons more visible */
    .stButton > button[kind="primary"] {
        font-size: 1.3rem !important;
        font-weight: bold !important;
        background-color: #1a2332 !important;
        border: 1px solid #2d4a5e !important;
        color: #00d4ff !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #243447 !important;
        border-color: #00d4ff !important;
    }
    .stButton > button {
        font-size: 1.1rem !important;
    }
    
    /* Markdown text larger */
    .stMarkdown p, .stMarkdown li {
        font-size: 1.1rem !important;
    }
    
    /* Expander text */
    .streamlit-expanderHeader {
        font-size: 1.1rem !important;
    }
    
    /* Data editor / table text */
    [data-testid="stDataFrame"] {
        font-size: 1.0rem !important;
    }
    
    /* Download buttons */
    .stDownloadButton > button {
        font-size: 1.1rem !important;
    }
    
    /* Sidebar collapsed — show settings gear icon */
    [data-testid="collapsedControl"] {
        background-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%2300d4ff"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.49.49 0 0 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6A3.61 3.61 0 0 1 8.4 12 3.61 3.61 0 0 1 12 8.4a3.61 3.61 0 0 1 3.6 3.6 3.61 3.61 0 0 1-3.6 3.6z"/></svg>') !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: 24px !important;
        min-height: 40px !important;
    }
</style>
""", unsafe_allow_html=True)

col_upload_img, col_upload_widget = st.columns([1, 5])
with col_upload_img:
    st.image("upload_icon.png", width=140)
with col_upload_widget:
    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="File should contain address data in one or more columns",
        label_visibility="collapsed",
    )
    st.markdown('<p class="big-caption">Drag & drop or click to browse — CSV, XLSX, XLS</p>', unsafe_allow_html=True)
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

        col1, col2 = st.columns([1, 5])
        with col1:
            st.image("geocode_icon.png", width=140)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            run_button = st.button("Run Geocoding", type="primary", use_container_width=True)
            st.markdown(f'<p class="big-caption">Will process {len(df)} addresses using PTV Developer + fallback geocoders</p>', unsafe_allow_html=True)

        if run_button:
            if not AZURE_MAPS_KEY and not PTV_KEY_AVAILABLE:
                st.error("Cannot run without API keys. Set AZURE_MAPS_KEY or PTV_DEVELOPER_API_KEY in .env")
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                from modules.address_normalizer import split_neighborhood_postal

                # Prepare all rows first (fast, no API calls)
                progress = st.progress(0, text="Preparing addresses...")
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
                _neighborhood_col = d.get('neighborhood', '')

                def clean(v): return '' if str(v) in ('nan', 'None', 'NaN', '') else str(v)

                def prepare_row(row):
                    """Extract and clean fields from a DataFrame row."""
                    addr = clean(str(row.get(_address_col, '')) if _address_col and _address_col in df.columns else '')
                    street_val = clean(str(row.get(_street_col, '')) if _street_col and _street_col in df.columns else '')
                    number_val = clean(str(row.get(_number_col, '')) if _number_col and _number_col in df.columns else '')
                    city_val = clean(str(row.get(_city_col, '')) if _city_col and _city_col in df.columns else '')
                    state_val = clean(str(row.get(_state_col, '')) if _state_col and _state_col in df.columns else '')
                    postal_val = clean(str(row.get(_postal_col, '')) if _postal_col and _postal_col in df.columns else '')
                    country_val = clean(str(row.get(_country_col, '')) if _country_col and _country_col in df.columns else '')
                    cc = clean(str(row.get(country_code_col, '')) if country_code_col and country_code_col in df.columns else '')
                    neighborhood_val = clean(str(row.get(_neighborhood_col, '')) if _neighborhood_col and _neighborhood_col in df.columns else '')

                    # PRIORITY: If street has a value, use it as the geocoding address
                    # "Location Name" is often a business name, not a geocodable address
                    if street_val and addr and street_val != addr:
                        # Street is the real address; addr is likely a location/business name
                        # Use street for geocoding
                        addr = street_val
                        street_val = ''  # Don't double-pass it

                    # Smart split neighborhood
                    if neighborhood_val:
                        split = split_neighborhood_postal(neighborhood_val, cc or country_val[:2] if country_val else '')
                        if split['postal_code'] and not postal_val:
                            postal_val = split['postal_code']
                        if split['neighborhood']:
                            neighborhood_val = split['neighborhood']

                    # Check if postal_val is mixed
                    if postal_val and not postal_val.replace('-', '').replace(' ', '').isdigit():
                        split = split_neighborhood_postal(postal_val, cc or '')
                        if split['postal_code']:
                            postal_val = split['postal_code']

                    # Combine street + number
                    if number_val and street_val:
                        street_val = f"{street_val} {number_val}"

                    # Existing coordinates
                    existing_lat, existing_lon = 0.0, 0.0
                    try:
                        if _lat_col and _lat_col in df.columns:
                            existing_lat = float(row.get(_lat_col, 0))
                        if _lon_col and _lon_col in df.columns:
                            existing_lon = float(row.get(_lon_col, 0))
                    except (ValueError, TypeError):
                        pass

                    return {
                        'addr': addr, 'street': street_val, 'city': city_val,
                        'state': state_val, 'postal': postal_val, 'country': country_val,
                        'cc': cc, 'existing_lat': existing_lat, 'existing_lon': existing_lon,
                        '_original_row': {k: str(v) if str(v) not in ('nan', 'None', 'NaN') else '' for k, v in row.items()},
                    }

                def geocode_one(prepared):
                    """Geocode a single prepared row."""
                    result = process_row(
                        address=prepared['addr'],
                        street=prepared['street'],
                        city=prepared['city'],
                        state=prepared['state'],
                        postal_code=prepared['postal'],
                        country=prepared['country'],
                        country_code=prepared['cc'],
                    )

                    # Carry through original row data for the export
                    result['_original_row'] = prepared.get('_original_row', {})

                    # Verification mode
                    existing_lat = prepared['existing_lat']
                    existing_lon = prepared['existing_lon']
                    if has_existing_coordinates(existing_lat, existing_lon):
                        verification = verify_coordinates(
                            existing_lat, existing_lon,
                            result.get('latitude', 0.0), result.get('longitude', 0.0),
                            address=prepared['addr'],
                        )
                        result['verification_status'] = verification['status']
                        result['verification_message'] = verification['message']
                        result['distance_from_existing'] = verification['distance_meters']
                        result['map_link_existing'] = verification['map_link_existing']
                        result['map_link_suggested'] = verification['map_link_suggested']
                        result['map_link_compare'] = verification['map_link_compare']
                        result['existing_lat'] = existing_lat
                        result['existing_lon'] = existing_lon

                        if verification['use_existing']:
                            result['latitude'] = existing_lat
                            result['longitude'] = existing_lon
                            if verification['status'] == 'verified':
                                result['confidence_level'] = 'High'
                                result['confidence_score'] = 0.95
                                result['recommendation'] = 'Existing coordinates verified ✓'
                        else:
                            result['recommendation'] = verification['message']
                    else:
                        result['verification_status'] = 'new_geocode'
                        result['verification_message'] = 'No existing coordinates — geocoded fresh'
                        result['distance_from_existing'] = 0
                        result['map_link_existing'] = ''
                        result['map_link_suggested'] = ''
                        result['map_link_compare'] = ''

                    return result

                # Prepare all rows
                prepared_rows = []
                for _, row in df.iterrows():
                    prepared_rows.append(prepare_row(row))

                # Process in parallel (10 concurrent threads)
                import time as _time
                progress.progress(0, text="Geocoding addresses (parallel)...")
                results = [None] * len(prepared_rows)
                completed = 0
                start_time = _time.time()

                with ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_idx = {
                        executor.submit(geocode_one, prep): idx
                        for idx, prep in enumerate(prepared_rows)
                    }
                    for future in as_completed(future_to_idx):
                        idx = future_to_idx[future]
                        try:
                            results[idx] = future.result()
                        except Exception as e:
                            results[idx] = _empty_result_for_error(prepared_rows[idx]['addr'], str(e))
                        completed += 1
                        if completed % 5 == 0 or completed == len(prepared_rows):
                            elapsed = _time.time() - start_time
                            rate = completed / elapsed if elapsed > 0 else 0
                            remaining = (len(prepared_rows) - completed) / rate if rate > 0 else 0
                            eta_str = f"~{int(remaining)}s remaining" if remaining > 0 else "finishing..."
                            progress.progress(
                                completed / len(prepared_rows),
                                text=f"Processing {completed}/{len(prepared_rows)} — {eta_str}"
                            )

                # Post-processing: detect outliers
                from modules.address_cleaner import detect_outliers
                outlier_indices = detect_outliers(results)
                for idx in outlier_indices:
                    if results[idx]:
                        results[idx]['needs_review'] = True
                        results[idx]['recommendation'] = f"⚠️ Geographic outlier detected — verify location. {results[idx].get('recommendation', '')}"

                # Show cache stats
                from modules.cache import geocode_cache
                cache_stats = geocode_cache.stats
                elapsed_total = _time.time() - start_time

                progress.empty()
                st.success(f"✅ Processed **{len(results)} addresses** in {elapsed_total:.1f}s")
                if cache_stats['hits'] > 0:
                    st.info(f"⚡ Cache saved {cache_stats['hits']} duplicate API calls ({cache_stats['hit_rate']}% hit rate)")
                if outlier_indices:
                    st.warning(f"🌍 {len(outlier_indices)} geographic outlier(s) flagged for review")

                # Store results in session state
                st.session_state['results'] = results
                st.session_state['results'] = results

        # ─── Results Display ───────────────────────────────────────────────────

        if 'results' in st.session_state:
            results = st.session_state['results']
            result_df = results_to_dataframe(results)

            st.markdown("---")
            st.header("📊 Results")

            # Summary metrics — clickable to filter
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                high = len(result_df[result_df['confidence_level'] == 'High'])
                if st.button(f"🟢 **{high}**\n\nHigh Confidence", key="btn_high", use_container_width=True):
                    st.session_state['quick_filter'] = 'high'
            with col2:
                med = len(result_df[result_df['confidence_level'] == 'Medium'])
                if st.button(f"🟡 **{med}**\n\nMedium", key="btn_med", use_container_width=True):
                    st.session_state['quick_filter'] = 'medium'
            with col3:
                low = len(result_df[result_df['confidence_level'] == 'Low'])
                if st.button(f"🔴 **{low}**\n\nLow", key="btn_low", use_container_width=True):
                    st.session_state['quick_filter'] = 'low'
            with col4:
                review = len(result_df[result_df['needs_review'] == True])
                if st.button(f"⚠️ **{review}**\n\nNeeds Review", key="btn_review", use_container_width=True):
                    st.session_state['quick_filter'] = 'review'
            with col5:
                entrances = len(result_df[result_df['precision'] == 'Entrance'])
                if st.button(f"🚪 **{entrances}**\n\nEntrances", key="btn_entrance", use_container_width=True):
                    st.session_state['quick_filter'] = 'entrance'

            # Determine default filter based on quick filter button clicks
            quick = st.session_state.get('quick_filter', 'all')
            if quick == 'high':
                default_levels = ['High']
                default_strategies = ['entrance_coords', 'building_coords', 'postal_code', 'review']
            elif quick == 'medium':
                default_levels = ['Medium']
                default_strategies = ['entrance_coords', 'building_coords', 'postal_code', 'review']
            elif quick == 'low':
                default_levels = ['Low']
                default_strategies = ['entrance_coords', 'building_coords', 'postal_code', 'review']
            elif quick == 'review':
                # Filter by needs_review flag, not by strategy
                default_levels = ['High', 'Medium', 'Low']
                default_strategies = ['entrance_coords', 'building_coords', 'postal_code', 'review']
            elif quick == 'entrance':
                default_levels = ['High', 'Medium', 'Low']
                default_strategies = ['entrance_coords']
            else:
                default_levels = ['High', 'Medium', 'Low']
                default_strategies = ['entrance_coords', 'building_coords', 'postal_code', 'review']

            # Show "All" reset button if filtered
            if quick != 'all':
                if st.button("↩️ Show All Results", key="btn_all"):
                    st.session_state['quick_filter'] = 'all'
                    st.rerun()

            # Filter
            st.subheader("Filter Results")
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                level_filter = st.multiselect(
                    "Confidence Level",
                    options=['High', 'Medium', 'Low'],
                    default=default_levels,
                )
            with filter_col2:
                strategy_filter = st.multiselect(
                    "Output Strategy",
                    options=['entrance_coords', 'building_coords', 'postal_code', 'review'],
                    default=default_strategies,
                )

            filtered_df = result_df[
                (result_df['confidence_level'].isin(level_filter)) &
                (result_df['output_strategy'].isin(strategy_filter))
            ]

            # Apply needs_review filter if that button was clicked
            if quick == 'review':
                filtered_df = filtered_df[filtered_df['needs_review'] == True]

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
| **formatted_address** | Standardized address returned by geocoding |
| **existing_lat** | Original latitude from your file (before any changes) |
| **existing_lon** | Original longitude from your file (before any changes) |
| **latitude** | Final latitude to use for routing (may differ from existing if error found) |
| **longitude** | Final longitude to use for routing (may differ from existing if error found) |
| **postal_code** | Postal/ZIP code (verified or extracted) |
| **confidence_score** | 0.0–1.0 score based on geocode quality, match type, postal code, and verification |
| **confidence_level** | 🟢 High (≥0.75) = use directly · 🟡 Medium (0.50–0.74) = usable with caution · 🔴 Low (<0.50) = needs review |
| **precision** | "Entrance" = building entrance found · "Building" = building centroid |
| **output_strategy** | What to use: entrance_coords, building_coords, postal_code, or review |
| **recommendation** | Human-readable explanation of why confidence is at this level and what changed |
| **geocoding_source** | Which geocoder provided the result: PTV, Azure Maps, HERE, or Nominatim |
| **needs_review** | TRUE = manual verification recommended before using in routing |
""")

            display_cols = [
                'original_address', 'formatted_address',
                'city', 'country_code', 'postal_code',
                'existing_lat', 'existing_lon',
                'latitude', 'longitude',
                'confidence_score', 'confidence_level',
                'precision', 'output_strategy', 'geocoding_source', 'recommendation', 'needs_review',
            ]
            # Only show columns that exist in the dataframe
            display_cols = [c for c in display_cols if c in filtered_df.columns]
            display_df = filtered_df[display_cols].copy()

            st.caption("💡 You can edit cells directly in the table below. Changes will be included in the export.")
            edited_df = st.data_editor(
                display_df,
                use_container_width=True,
                height=400,
                num_rows="fixed",
                key="results_editor",
            )

            # If user made edits, update the results in session state
            if edited_df is not None:
                # Merge edits back into the full result_df
                for col in ['latitude', 'longitude', 'confidence_level', 'output_strategy', 'needs_review']:
                    if col in edited_df.columns and col in result_df.columns:
                        result_df.loc[edited_df.index, col] = edited_df[col]
                st.session_state['edited_result_df'] = result_df

            # ─── Download ──────────────────────────────────────────────────────

            st.markdown("---")
            st.subheader("📥 Export to OptiFlow")

            # Always show the required fields inputs — user can edit them freely
            st.markdown("**OptiFlow requires the following fields. Enter default values for the output file:**")

            # Detect which fields are available from the uploaded data
            has_service_time = False
            has_volume = False
            has_timewindows = False

            if df is not None:
                df_cols_lower = [c.lower() for c in df.columns]
                has_service_time = any('service' in c and 'time' in c for c in df_cols_lower)
                has_volume = any('volume' in c or 'vol' in c for c in df_cols_lower)
                has_timewindows = any('time' in c and 'window' in c for c in df_cols_lower)

            exp_col1, exp_col2, exp_col3 = st.columns(3)

            with exp_col1:
                if has_service_time:
                    st.markdown("✅ **Service Time** — found in upload")
                svc_time_val = st.text_input(
                    "Service Time (hh:mm)",
                    value="00:05",
                    help="How long each stop takes to execute. Example: 00:05 = 5 minutes, 00:15 = 15 minutes, 01:00 = 1 hour",
                    key="export_svc_time",
                )

            with exp_col2:
                if has_volume:
                    st.markdown("✅ **Volume** — found in upload")
                vol_val = st.text_input(
                    "Volume (litres)",
                    value="1",
                    help="Volume of each order in litres. Used for vehicle capacity planning in OptiFlow.",
                    key="export_volume",
                )

            with exp_col3:
                if has_timewindows:
                    st.markdown("✅ **Time Windows** — found in upload")
                tw_val = st.text_input(
                    "Time Windows",
                    value="08:00 - 18:00",
                    help="Hours when deliveries can be made. Format: 08:00 - 18:00. Multiple windows: 08:00 - 12:00 & 13:00 - 18:00",
                    key="export_timewindow",
                )

            st.markdown("")

            # Generate export with the user's values
            # Use the RAW results (not the DataFrame) so _original_row data is preserved
            export_results = st.session_state.get('results', results)

            excel_buffer = export_to_excel(
                export_results,
                service_time=svc_time_val,
                volume=vol_val,
                timewindow=tw_val,
            )
            st.download_button(
                label="⬇️ Download Excel (OptiFlow-ready)",
                data=excel_buffer,
                file_name="geoclean_optiflow_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

else:
    # No file uploaded — show single address test
    st.markdown("---")

    col_test_img, col_test_input = st.columns([1, 5])
    with col_test_img:
        st.image("test_address_icon.png", width=140)
    with col_test_input:
        st.markdown('<p class="big-caption">Enter an address to test</p>', unsafe_allow_html=True)
        test_address = st.text_input(
            "Enter an address to test",
            value="451 holland springs drive, maryville, tn",
            help="Try any address worldwide — US, Peru, UK, Germany, etc.",
            label_visibility="collapsed",
        )

    col_geo_img, col_geo_btn = st.columns([1, 5])
    with col_geo_img:
        st.image("geocode_icon.png", width=140)
    with col_geo_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        geocode_clicked = st.button("Run Geocoding", type="primary", use_container_width=True)

    if geocode_clicked:
        with st.spinner("Geocoding..."):
            result = process_row(address=test_address)

        col1, col2 = st.columns(2)
        with col1:
            # Address parsing
            parsed = parse_address(test_address)
            if parsed['is_multi_unit']:
                st.info(f"🏢 **Multi-unit detected**\n\nUnit: `{parsed['unit_text']}`\n\nBase: `{parsed['base_address']}`")
            else:
                st.success("✅ Single address (no unit detected)")

            # Coordinates
            st.markdown("**📍 Coordinates:**")
            st.code(f"Latitude:  {result['latitude']}\nLongitude: {result['longitude']}")

            # Confidence
            level = result['confidence_level']
            score = result['confidence_score']
            emoji = "🟢" if level == "High" else "🟡" if level == "Medium" else "🔴"
            st.markdown(f"**Confidence:** {emoji} {level} ({score:.2f})")

        with col2:
            # Results
            st.markdown("**📋 Full Result:**")
            st.markdown(f"- **Formatted:** {result.get('formatted_address', '')}")
            st.markdown(f"- **Postal Code:** {result.get('postal_code', '') or 'not found'}")
            st.markdown(f"- **City:** {result.get('city', '')}")
            st.markdown(f"- **Country:** {result.get('country', '')} ({result.get('country_code', '')})")
            st.markdown(f"- **Precision:** {result.get('precision', '')}")
            st.markdown(f"- **Strategy:** {result.get('output_strategy', '')}")
            st.markdown(f"- **Recommendation:** {result.get('recommendation', '')}")

            # Map link
            if result['latitude'] != 0.0:
                map_url = f"https://www.google.com/maps?q={result['latitude']},{result['longitude']}"
                st.markdown(f"[🗺️ View on Google Maps]({map_url})")
