"""
GeoClean UI — Brand CSS Styles

Generates the complete CSS block for PTV Logistics brand styling.
Injected once at the top of app.py via st.markdown().
"""


def get_brand_css() -> str:
    """Return the complete CSS string for PTV brand styling.

    Includes:
    - Base typography (font family, sizes, weights, colors)
    - Card component styles (.ptv-card)
    - Header bar styles (.ptv-header)
    - Button overrides (primary red, secondary outlined)
    - Metric card styles (.ptv-metric-card)
    - Confidence color classes (.confidence-high, .confidence-medium, .confidence-low)
    - File upload drop zone styles
    - Sidebar overrides
    - Responsive breakpoints (@media max-width: 768px)
    - Section divider gradient line (.ptv-divider)
    """
    return """
/* ─── Base Typography ─────────────────────────────────────────────────── */

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 1rem;
    line-height: 1.5;
    color: #333333;
}

h1 {
    font-weight: 700;
    color: #1a1a1a;
}

h2 {
    font-weight: 600;
    color: #1a1a1a;
}

h3 {
    font-weight: 500;
    color: #1a1a1a;
}

p, li {
    font-size: 1rem;
    line-height: 1.5;
    color: #333333;
}

.text-secondary {
    color: #666666;
}

/* ─── Card Styles ─────────────────────────────────────────────────────── */

.ptv-card {
    background-color: #f2f2f2;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border-bottom: 4px solid #E31E24;
}

.ptv-card-title {
    font-weight: 600;
    font-size: 1.1rem;
    color: #1a1a1a;
    margin-bottom: 0.5rem;
}

.ptv-card-divider {
    width: 80px;
    height: 3px;
    background: linear-gradient(90deg, #E31E24, #7B1FA2);
    border: none;
    margin-bottom: 1rem;
}

/* ─── Header Bar Styles ───────────────────────────────────────────────── */

.ptv-header {
    background: linear-gradient(135deg, #F26522 0%, #E31E24 35%, #C2185B 65%, #7B1FA2 100%);
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.ptv-header-logo {
    background-color: #1a1a1a;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.9rem;
    white-space: nowrap;
    color: #ffffff;
}

.ptv-header-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
}

.ptv-header-tagline {
    font-size: 1rem;
    color: #ffffff;
    opacity: 0.9;
    margin: 0;
}

/* ─── Primary Button Overrides ────────────────────────────────────────── */

.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background-color: #E31E24 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px;
    font-weight: 600;
    transition: background-color 0.2s ease;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    background-color: #C4161C !important;
    color: #ffffff !important;
}

/* ─── Secondary Button Styles ─────────────────────────────────────────── */

.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {
    background-color: #ffffff !important;
    color: #E31E24 !important;
    border: 2px solid #E31E24 !important;
    border-radius: 6px;
    font-weight: 600;
    transition: background-color 0.2s ease;
}

.stButton > button[kind="secondary"]:hover,
.stButton > button[data-testid="baseButton-secondary"]:hover {
    background-color: #fef2f2 !important;
}

/* ─── Metric Card Styles ──────────────────────────────────────────────── */

.ptv-metric-card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    text-align: center;
    border-top: 4px solid #E31E24;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.ptv-metric-value {
    font-size: 2rem;
    font-weight: 700;
    margin: 0.25rem 0;
}

.ptv-metric-label {
    font-size: 0.85rem;
    color: #666666;
    font-weight: 500;
}

.ptv-metric-icon {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}

/* ─── Confidence Color Classes ────────────────────────────────────────── */

.confidence-high {
    color: #4CAF50;
}

.confidence-medium {
    color: #F26522;
}

.confidence-low {
    color: #E31E24;
}

/* ─── File Upload Drop Zone ───────────────────────────────────────────── */

[data-testid="stFileUploader"] section {
    background-color: #fafafa !important;
    border: 2px dashed #ccc !important;
    border-radius: 12px;
    padding: 1rem;
    transition: border-color 0.2s ease;
}

[data-testid="stFileUploader"] section:hover {
    border-color: #4CAF50 !important;
}

/* ─── Sidebar Overrides ───────────────────────────────────────────────── */

[data-testid="stSidebar"] {
    background-color: #f2f2f2 !important;
}

[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #ffffff !important;
    border: 1px solid #e0e0e0 !important;
}

[data-testid="stSidebar"] label {
    color: #333333 !important;
    font-weight: 500;
}

/* ─── Section Divider ─────────────────────────────────────────────────── */

.ptv-divider {
    width: 80px;
    height: 3px;
    background: linear-gradient(90deg, #E31E24, #7B1FA2);
    border: none;
    margin: 0.75rem 0;
}

/* ─── Responsive Breakpoints ──────────────────────────────────────────── */

@media (max-width: 768px) {
    .ptv-header {
        flex-direction: column;
        text-align: center;
        padding: 1rem;
    }

    .ptv-card {
        padding: 1rem;
    }

    [data-testid="column"] {
        flex-direction: column !important;
    }

    .ptv-metric-card {
        margin-bottom: 0.5rem;
    }
}
"""
