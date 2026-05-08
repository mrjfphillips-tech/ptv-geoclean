# GeoClean — Fuzzy Geocoding with Confidence

**Clean Data. Smart Locations. Optimized Deliveries.**

GeoClean converts messy global address data into OptiFlow-ready geographic output with confidence scoring. Upload a spreadsheet with addresses, get back clean coordinates ready for route optimization.

## Features

- 🚛 **PTV Developer Geocoding** — Road-access coordinates optimized for OptiFlow routing
- 🌍 **Global coverage** — 360 million points across 100+ countries
- 🔍 **Country-constrained search** — Finds addresses within the correct region
- 📊 **Confidence scoring** — High/Medium/Low with recommendations
- 🏢 **Apartment/unit detection** — Separates unit info from base address
- 🔄 **Smart retry** — Simplified address variants for failed geocodes
- ⚡ **Parallel processing** — 10x faster with concurrent API calls
- 💾 **Result caching** — Duplicate addresses only geocode once
- 📥 **OptiFlow-ready export** — Exact column headers OptiFlow expects

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env and add your API keys
cp .env.example .env

# Run the app
streamlit run app.py
```

## API Keys Required

| Key | Source | Purpose |
|-----|--------|---------|
| `PTV_DEVELOPER_API_KEY` | [developer.myptv.com](https://developer.myptv.com) | Primary geocoder (best for OptiFlow) |
| `AZURE_MAPS_KEY` | [Azure Portal](https://portal.azure.com) | Fallback geocoder |

## Geocoding Priority Chain

1. **PTV Developer** — Road-access coordinates, same data as OptiFlow
2. **PTV Places** — Business/POI name search
3. **Azure Maps** — General-purpose fallback
4. **Nominatim (OSM)** — Free, always available

## OptiFlow Export Format

The output Excel file includes an "OptiFlow Import" sheet with exact headers:
`id | street | city | zipcode | country | service time | volume | timewindows day 1 | latitude | longitude`

Plus all original columns from the customer's uploaded file.

## Project Structure

```
geoclean/
├── app.py                    # Streamlit UI
├── config.py                 # API key configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Template for API keys
├── .streamlit/config.toml    # Streamlit theme
├── modules/
│   ├── pipeline.py           # Main geocoding pipeline
│   ├── ptv_geocoder.py       # PTV Developer API integration
│   ├── geocoder.py           # Azure Maps integration
│   ├── fallback_geocoder.py  # Nominatim fallback
│   ├── confidence.py         # Confidence scoring model
│   ├── column_detector.py    # Auto-detect column mappings
│   ├── country_resolver.py   # Country name → ISO code
│   ├── address_normalizer.py # Address cleaning & postal extraction
│   ├── address_cleaner.py    # Pre-cleaning & retry variants
│   ├── address_parser.py     # Apartment/unit detection
│   ├── phone_detector.py     # Country detection from phone numbers
│   ├── cache.py              # Result caching
│   ├── exporter.py           # OptiFlow Excel export
│   ├── verifier.py           # Coordinate verification
│   ├── entrance_finder.py    # Building entrance detection (OSM)
│   ├── reverse_geocoder.py   # Reverse geocoding
│   ├── country_logic.py      # Country-specific adjustments
│   └── template.py           # Download template generation
└── logo.png, upload_icon.png, etc.  # UI assets
```

## Contributing

1. Clone the repo
2. Create a branch for your changes
3. Make changes and test locally
4. Push and create a pull request
