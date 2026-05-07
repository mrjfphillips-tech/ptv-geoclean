# 🌍 GeoClean — Fuzzy Geocoding with Confidence

**Convert messy global address data into OptiFlow-ready geographic output.**

---

## What It Does

GeoClean takes a spreadsheet of addresses (messy, incomplete, international) and:

1. **Detects apartments/units** — separates "Dpto 802" from the street address
2. **Geocodes** — uses Azure Maps Fuzzy Search to find coordinates
3. **Standardizes** — reverse geocodes to get a clean, formatted address
4. **Finds entrances** — checks OpenStreetMap for building entrance points
5. **Scores confidence** — tells you how reliable each result is
6. **Exports** — produces a clean Excel file ready for OptiFlow routing

---

## Quick Start (3 steps)

### Step 1: Install

Double-click **`INSTALL.bat`**

This installs Python packages and asks for your Azure Maps API key.

### Step 2: Get an Azure Maps Key (free)

1. Go to [portal.azure.com](https://portal.azure.com)
2. Search "Azure Maps" in the top search bar
3. Click "Create" → choose your subscription → create an Azure Maps Account
4. Once created, go to **Authentication** (left sidebar)
5. Copy the **Primary Key**
6. Paste it when INSTALL.bat asks, or edit the `.env` file:
   ```
   AZURE_MAPS_KEY=your-key-here
   ```

**Free tier**: 5,000 geocoding calls per day. More than enough for testing.

### Step 3: Launch

Double-click **`LAUNCH.bat`**

Your browser opens with the GeoClean interface.

---

## How to Use

### Upload a File

- Click "Browse files" and select your CSV or Excel file
- The file should have an address column (or separate street/city/postal columns)

### Map Your Columns

- In the left sidebar, tell GeoClean which column contains the address
- If your data has separate columns (street, city, postal code), map those too

### Run Geocoding

- Click the blue **"🚀 Run Geocoding"** button
- Watch the progress bar as each address is processed
- Results appear below with confidence coloring:
  - 🟢 Green = High confidence (use directly)
  - 🟡 Yellow = Medium (usable, check if needed)
  - 🔴 Red = Low (needs manual review)

### Download Results

- Click **"⬇️ Download Excel"** to get the OptiFlow-ready output
- The Excel file has 3 sheets:
  - **Geocoded Results** — all addresses with coordinates and confidence
  - **Summary** — counts by confidence level
  - **Needs Review** — only the addresses that need manual attention

---

## Input File Format

Your file needs at minimum ONE of these:

| Option A: Single column | Option B: Separate columns |
|------------------------|---------------------------|
| `address` | `street`, `city`, `postal_code`, `country` |

**Example (Option A):**
| address |
|---------|
| Av. Javier Prado 4200 Dpto 802, Lima, Peru |
| 123 Main St Apt 4B, New York, NY 10001 |
| 10 Downing Street, London SW1A 2AA |

**Example (Option B):**
| street | city | postal_code | country |
|--------|------|-------------|---------|
| Av. Javier Prado 4200 | Lima | 15036 | Peru |
| 123 Main St | New York | 10001 | US |

---

## Output Columns

| Column | Description |
|--------|-------------|
| original_address | What you uploaded |
| base_address | Address without apartment/unit |
| unit_text | Apartment/unit portion (if detected) |
| latitude | Final latitude for routing |
| longitude | Final longitude for routing |
| precision | "Entrance" or "Building" |
| postal_code | Standardized postal code |
| confidence_score | 0.0 to 1.0 |
| confidence_level | High / Medium / Low |
| output_strategy | What to use for routing |
| needs_review | TRUE if manual check needed |

---

## Supported Countries

GeoClean works with any country Azure Maps supports. Special handling for:

- 🇵🇪 **Peru** — Lima district detection, 5-digit postal codes
- 🇺🇸 **USA** — ZIP code validation
- 🇨🇦 **Canada** — Alphanumeric postal codes (A1A 1A1)
- 🇬🇧 **UK** — Postcode format (SW1A 2AA)
- 🇩🇪 **Germany** — 5-digit PLZ
- 🇳🇱 **Netherlands** — 4-digit + 2-letter (1234 AB)
- 🇧🇷 **Brazil** — CEP format (12345-678)

---

## Distributing to Your Team

To share GeoClean with colleagues:

1. Copy the entire `geoclean/` folder to a shared drive or zip it
2. Each person runs `INSTALL.bat` once on their machine
3. They'll need their own Azure Maps key (or share one team key in the .env)
4. After install, just double-click `LAUNCH.bat` to use

**Requirements**: Python 3.10+ installed (with "Add to PATH" checked)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Install Python from python.org, check "Add to PATH" |
| "Azure Maps key invalid" | Check the key in `.env` — no quotes needed |
| "No results" for an address | Try simplifying the address, remove unit info |
| App won't open in browser | Go to http://localhost:8501 manually |
| Slow processing | Azure free tier is rate-limited. ~5 addresses/second |

---

## Architecture

```
geoclean/
├── app.py              ← Streamlit web interface
├── config.py           ← API keys and settings
├── INSTALL.bat         ← One-click setup
├── LAUNCH.bat          ← One-click launch
├── .env                ← Your API key (not shared)
├── .env.example        ← Template for new installs
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
└── modules/
    ├── address_parser.py    ← Apartment/unit detection
    ├── geocoder.py          ← Azure Maps fuzzy search
    ├── reverse_geocoder.py  ← Coordinates → address
    ├── entrance_finder.py   ← OSM entrance detection
    ├── confidence.py        ← Confidence scoring model
    ├── country_logic.py     ← International postal codes
    ├── exporter.py          ← Excel output
    └── pipeline.py          ← Full processing pipeline
```
