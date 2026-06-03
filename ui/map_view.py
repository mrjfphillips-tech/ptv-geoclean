"""
GeoClean UI — Map Visualization Module

Renders geocoded results as an interactive Leaflet map via st.components.v1.html().
Uses PTV Developer Raster Maps API tiles when an API key is available;
falls back to OpenStreetMap tiles otherwise.

No extra Python packages needed — Leaflet is loaded from CDN.
"""

import os
import json
from typing import Dict, List, Optional, Tuple


# ─── Tile Layer ────────────────────────────────────────────────────────────────

def _tile_config() -> Dict:
    """Return the tile layer URL and attribution for the map background."""
    api_key = os.environ.get("PTV_DEVELOPER_API_KEY", "")
    if api_key:
        return {
            "url": f"https://api.myptv.com/rastermaps/v1/image-tiles/{{z}}/{{x}}/{{y}}?size=256&apiKey={api_key}",
            "attribution": "&copy; PTV Group | &copy; HERE",
            "maxZoom": 19,
        }
    return {
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "&copy; OpenStreetMap contributors",
        "maxZoom": 19,
    }


# ─── Marker / Line Data ────────────────────────────────────────────────────────

def _build_map_data(results: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract markers and polylines from geocoding results.

    Returns:
        (markers, lines)
        markers: list of dicts with lat, lon, color, tooltip
        lines:   list of dicts with start (lat, lon), end (lat, lon)
    """
    markers: List[Dict] = []
    lines: List[Dict] = []

    CONFIDENCE_COLOR = {"High": "#4CAF50", "Medium": "#F26522", "Low": "#E31E24"}

    for result in results:
        new_lat = result.get("latitude", 0) or 0
        new_lon = result.get("longitude", 0) or 0
        if new_lat == 0 and new_lon == 0:
            continue

        ex_lat = result.get("existing_lat", 0) or 0
        ex_lon = result.get("existing_lon", 0) or 0

        confidence = result.get("confidence_level", "Medium")
        score = result.get("confidence_score", 0.0)
        address = result.get("original_address", "")
        source = result.get("geocoding_source", "")
        distance = result.get("distance_from_existing", 0) or 0
        vstatus = result.get("verification_status", "")
        conf_color = CONFIDENCE_COLOR.get(confidence, "#999")

        dist_line = (
            f"<br>Moved: {distance:.0f}m"
            if distance > 0 and vstatus in ("verified", "discrepancy", "large_discrepancy")
            else ""
        )
        tooltip = (
            f"<b>{address}</b>"
            f"<br><span style='color:{conf_color}'>&#9679;</span> {confidence} ({score:.0%})"
            f"{dist_line}"
            f"<br>Source: {source}"
        )

        has_existing = (ex_lat != 0 or ex_lon != 0) and (ex_lat != new_lat or ex_lon != new_lon)

        if has_existing:
            markers.append({"lat": ex_lat, "lon": ex_lon, "color": "#2196F3", "tooltip": tooltip})
            markers.append({"lat": new_lat, "lon": new_lon, "color": "#4CAF50", "tooltip": tooltip})
            lines.append({"start": [ex_lat, ex_lon], "end": [new_lat, new_lon]})
        else:
            markers.append({"lat": new_lat, "lon": new_lon, "color": "#4CAF50", "tooltip": tooltip})

    return markers, lines


# ─── HTML Builder ──────────────────────────────────────────────────────────────

def build_results_map_html(results: List[Dict], height: int = 500, max_markers: int = 2000) -> Optional[str]:
    """
    Build a self-contained Leaflet HTML string from geocoding results.

    Args:
        results: List of geocoding result dicts.
        height:  Map height in pixels.
        max_markers: Maximum number of markers to render (for performance).

    Returns:
        HTML string for use with st.components.v1.html(), or None if no
        valid coordinates exist in the results.
    """
    markers, lines = _build_map_data(results)
    if not markers:
        return None

    # Limit markers for browser performance — 52K markers will crash the tab
    total_markers = len(markers)
    if total_markers > max_markers:
        # Sample evenly to keep geographic coverage
        step = total_markers // max_markers
        markers = markers[::step][:max_markers]
        lines = lines[::step][:max_markers] if lines else []

    tile = _tile_config()

    # Compute bounding box for auto-fit
    lats = [m["lat"] for m in markers]
    lons = [m["lon"] for m in markers]
    sw = [min(lats) - 0.01, min(lons) - 0.01]
    ne = [max(lats) + 0.01, max(lons) + 0.01]
    center = [(sw[0] + ne[0]) / 2, (sw[1] + ne[1]) / 2]

    markers_json = json.dumps(markers)
    lines_json = json.dumps(lines)
    bounds_json = json.dumps([sw, ne])
    tile_url = tile["url"]
    tile_attr = tile["attribution"]
    tile_max_zoom = tile["maxZoom"]

    # Show truncation notice if applicable
    truncation_notice = ""
    if total_markers > max_markers:
        truncation_notice = f'<div style="position:absolute;top:8px;left:50px;z-index:1000;background:rgba(255,255,255,0.9);padding:4px 10px;border-radius:4px;font-size:11px;box-shadow:0 1px 3px rgba(0,0,0,.2);">Showing {max_markers:,} of {total_markers:,} points</div>'

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin=""/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV/XN/WLcE="
        crossorigin=""></script>
<style>
  html, body {{ margin:0; padding:0; height:100%; }}
  #map {{ height:{height}px; width:100%; }}
  .legend {{ background:white; padding:8px 12px; border-radius:4px;
             box-shadow:0 1px 4px rgba(0,0,0,.3); font-size:12px; line-height:1.8; }}
  .legend-dot {{ display:inline-block; width:10px; height:10px;
                 border-radius:50%; margin-right:5px; }}
</style>
</head>
<body>
{truncation_notice}
<div id="map"></div>
<script>
var map = L.map('map').setView({json.dumps(center)}, 6);

L.tileLayer('{tile_url}', {{
    attribution: '{tile_attr}',
    maxZoom: {tile_max_zoom}
}}).addTo(map);

// Fallback: if PTV tiles fail, switch to OSM
map.on('tileerror', function() {{
    map.eachLayer(function(layer) {{
        if (layer instanceof L.TileLayer) {{ map.removeLayer(layer); }}
    }});
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
    }}).addTo(map);
}});

var markers = {markers_json};
var lines   = {lines_json};
var bounds  = {bounds_json};

markers.forEach(function(m) {{
    var circle = L.circleMarker([m.lat, m.lon], {{
        radius: 5,
        fillColor: m.color,
        color: '#fff',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.8
    }}).addTo(map);
    circle.bindPopup(m.tooltip, {{maxWidth: 280}});
}});

lines.forEach(function(l) {{
    L.polyline([l.start, l.end], {{
        color: '#E31E24', weight: 1.5, opacity: 0.7, dashArray: '4 4'
    }}).addTo(map);
}});

if (bounds[0][0] !== bounds[1][0] || bounds[0][1] !== bounds[1][1]) {{
    map.fitBounds(bounds, {{padding: [20, 20]}});
}}

var legend = L.control({{position: 'bottomright'}});
legend.onAdd = function() {{
    var div = L.DomUtil.create('div', 'legend');
    div.innerHTML =
        '<b>Coordinates</b><br>' +
        '<span class="legend-dot" style="background:#4CAF50"></span>Geocoded<br>' +
        '<span class="legend-dot" style="background:#2196F3"></span>Original<br>' +
        '<span style="color:#E31E24;font-size:14px;">&#8213;</span> Difference';
    return div;
}};
legend.addTo(map);
</script>
</body>
</html>"""

    return html


# ─── Legacy shim (keeps old import working if anything else references it) ────

def build_results_map(results: List[Dict]):
    """Deprecated — call build_results_map_html() instead."""
    return build_results_map_html(results)
