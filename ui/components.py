"""
GeoClean UI — HTML Component Generators

Branded HTML components rendered via st.markdown(unsafe_allow_html=True).
"""


def render_header() -> str:
    """Generate the PTV branded header HTML.

    Returns HTML string with:
    - Geometric gradient background (orange → red → magenta → purple)
    - PTV Logistics logo (white text on dark left section)
    - App title "GeoClean" in white
    - Tagline "Clean Data. Smart Locations. Optimized Deliveries." in white
    - 12px rounded corners
    """
    return """
<div class="ptv-header">
    <div class="ptv-header-logo">PTV | LOGISTICS</div>
    <div>
        <div class="ptv-header-title">GeoClean</div>
        <div class="ptv-header-tagline">Clean Data. Smart Locations. Optimized Deliveries.</div>
    </div>
</div>
"""


def render_card(content: str, title: str = "", accent_color: str = "#E31E24") -> str:
    """Wrap content in a PTV-styled card container.

    Args:
        content: HTML content to place inside the card
        title: Optional card title with section divider
        accent_color: Bottom border accent color (default PTV red)

    Returns HTML with:
    - Light gray (#f2f2f2) background
    - 12px rounded corners
    - 4px colored bottom border accent
    - Optional title with red-to-purple gradient divider line
    """
    title_html = ""
    if title:
        title_html = f"""
        <div class="ptv-card-title">{title}</div>
        <div class="ptv-card-divider"></div>
"""

    return f"""
<div class="ptv-card" style="border-bottom-color: {accent_color};">
    {title_html}
    {content}
</div>
"""


def render_metric_card(label: str, value: int, color: str, icon: str = "") -> str:
    """Generate a single metric card for the results summary.

    Args:
        label: Metric label (e.g., "High Confidence")
        value: Count value
        color: Top border accent color
        icon: Optional emoji icon

    Returns HTML with:
    - White background
    - 4px colored top border
    - Centered text
    - Large value number, smaller label below
    """
    icon_html = f'<div class="ptv-metric-icon">{icon}</div>' if icon else ""

    return f"""
<div class="ptv-metric-card" style="border-top-color: {color};">
    {icon_html}
    <div class="ptv-metric-value" style="color: {color};">{value}</div>
    <div class="ptv-metric-label">{label}</div>
</div>
"""


def render_section_divider() -> str:
    """Generate the PTV red-to-purple gradient divider line.

    Returns a short (80px wide, 3px tall) gradient line used under section headings.
    """
    return '<div class="ptv-divider"></div>'


def get_confidence_color(level: str) -> str:
    """Map confidence level to PTV brand color.

    Args:
        level: "High", "Medium", or "Low"

    Returns:
        Color hex string: High → #4CAF50, Medium → #F26522, Low → #E31E24
    """
    colors = {
        "High": "#4CAF50",
        "Medium": "#F26522",
        "Low": "#E31E24",
    }
    return colors.get(level, "#E31E24")
