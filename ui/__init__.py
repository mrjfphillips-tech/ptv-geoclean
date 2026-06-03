"""
GeoClean UI Package

Encapsulates all presentation logic: CSS generation, HTML components, and map visualization.
"""

from ui.styles import get_brand_css
from ui.components import (
    render_header,
    render_card,
    render_metric_card,
    render_section_divider,
    get_confidence_color,
)

# map_view is imported separately since it has additional dependencies (folium)
try:
    from ui.map_view import build_results_map
except ImportError:
    build_results_map = None  # type: ignore

__all__ = [
    "get_brand_css",
    "render_header",
    "render_card",
    "render_metric_card",
    "render_section_divider",
    "get_confidence_color",
    "build_results_map",
]
