"""
GeoClean Configuration
Load API keys and settings from environment or .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Azure Maps
AZURE_MAPS_KEY = os.getenv("AZURE_MAPS_KEY", "")
AZURE_MAPS_BASE_URL = "https://atlas.microsoft.com"

# PTV Developer
PTV_DEVELOPER_API_KEY = os.getenv("PTV_DEVELOPER_API_KEY", "")

# Geocoding defaults
DEFAULT_RESULT_LIMIT = 3
REQUEST_TIMEOUT_SECONDS = 10
