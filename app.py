"""
KOHLER AI Bathroom Designer & Planner -- Streamlit prototype.

BLOCK 6 note: this is a presentation-layer rewrite only. Every call below
still goes through the same, unmodified deterministic functions in src/ --
nothing about feasibility, pricing, scoring, water math, or numeric
grounding changed here. What changed:

  - A dark, restrained "premium studio" visual theme (CSS only).
  - A staged journey (welcome -> space -> style -> reveal -> design ->
    products) via st.session_state, instead of one long scrolling form.
  - When src.optimization.optimizer.generate_alternatives() returns no
    feasible bundle (an extremely small room, or a very tight budget), the
    UI now falls back to generate_best_effort_alternative() -- a wholly
    separate, additive ranking pass added in Block 6 -- instead of showing
    a dead end. The result is always clearly labeled ("Compact Space Edit"
    / "Best-Fit Design") and its real remaining violations are still shown.
    The strict feasibility engine itself is untouched; this file never
    pretends a best-effort result is fully feasible.
  - The old 2D "Conceptual Layout Study" floor plan is no longer the
    primary visual. render_isometric_view() (added to
    src/visualization/floorplan.py in Block 6) renders a stylized pseudo-3D
    "AI CONCEPT VISUALIZATION" from the SAME validated zone/geometry data;
    render_floorplan() itself is untouched and still covered by its own
    tests, it's just not used on the main path any more.
  - Product cards now carry a small inline-SVG silhouette (CSS/SVG only,
    no downloaded images, nothing claimed to be a real KOHLER photo).
  - "View details" shows only clean, human-readable fields -- no JSON, no
    Python objects, no internal identifiers.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import streamlit as st

from src.ai.explanation import generate_explanation
from src.data.catalog import load_catalog
from src.data.schemas import AestheticStyle, BathroomDimensions, ProductCategory, RequirementSpec
from src.optimization.optimizer import generate_alternatives, generate_best_effort_alternative
from src.sustainability.water_calculator import UsageAssumptions, estimate_water_use
from src.utils.config import openai_key_status
from src.visualization.floorplan import ISO_VIEW_PRESETS, render_isometric_view

st.set_page_config(
    page_title="KOHLER AI Bathroom Designer", page_icon="\U0001F6C1", layout="wide"
)

# ---------------------------------------------------------------------------
# Display-only label maps -- purely cosmetic, never fed back into the
# constraint engine, optimizer, or catalog.
# ---------------------------------------------------------------------------

# Real, catalog-backed styles only (matches src/data/schemas.py::AestheticStyle
# exactly -- four values, all four already present and scored by the
# optimizer's style_match component).
FUNCTIONAL_STYLES = [
    (AestheticStyle.MINIMALIST_MODERN, "Minimalist Modern", "Clean geometry. Quiet surfaces."),
    (AestheticStyle.CLASSIC_LUXURY, "Classic Luxury", "Timeless forms. Rich detailing."),
    (AestheticStyle.JAPANESE_ZEN, "Japanese Zen", "Natural calm. Simplicity and balance."),
    (AestheticStyle.CONTEMPORARY, "Contemporary", "Confident lines. Understated warmth."),
]
STYLE_DISPLAY_NAME = {s.value: label for s, label, _ in FUNCTIONAL_STYLES}

# Cosmetic-only "mood" tags (Block 6, item 5). None of these exist as real
# product/style tags in the catalog, so they are never written into
# RequirementSpec.style or used by the optimizer's scoring. They are stored
# in RequirementSpec.priorities -- a genuine, already-existing free-text
# field that the schema defines for exactly this purpose -- purely so the
# written "why this design" note can reflect the mood the person asked for.
MOOD_TAGS = [
    "Warm Minimal", "Modern Luxe", "Natural", "Monochrome",
    "Spa Inspired", "Elegant Neutral",
]

# Real catalog categories -> the functional "Essentials" toggles.
ESSENTIAL_CATEGORY_LABELS = {
    ProductCategory.SMART_TOILET: "Smart Toilet",
    ProductCategory.VANITY: "Wash Basin / Vanity",
    ProductCategory.FAUCET: "Faucet",
    ProductCategory.THERMOSTATIC_SHOWER: "Thermostatic Shower",
}
# Visually present, but NOT wired to required_categories -- there is no
# backing catalog category for these yet. Shown as an honest "coming soon"
# row rather than invented/fabricated product data.
INERT_ESSENTIALS = ["Mirror", "Storage", "Lighting", "Accessories"]

CATEGORY_DISPLAY = {c.value: label for c, label in ESSENTIAL_CATEGORY_LABELS.items()}

DATA_STATUS_SHORT = {
    "synthetic_demo": "Demo catalogue · synthetic specification",
    "prototype_assumed": "Demo catalogue · prototype assumption",
    "verified_public": "Verified · public KOHLER listing",
}

PACKAGE_TAGLINES = {
    "essential": "Essential functionality",
    "balanced": "Balanced comfort + design",
    "premium": "Complete luxury concept",
}


def package_tagline(label: str) -> str:
    lowered = label.lower()
    for key, tagline in PACKAGE_TAGLINES.items():
        if key in lowered:
            return tagline
    return "A best-fit design concept"


def fmt_ft(value: float) -> str:
    return f"{value:g}"


def is_best_effort(alt) -> bool:
    return hasattr(alt, "compromise_notes")


def shorten(text: str, max_sentences: int = 4) -> str:
    """Keep the AI-written explanation feature, but cap it at a handful of
    short sentences for the reveal/design screens (Block 6, item 15) --
    never regenerated shorter by the model itself, just trimmed for
    display, so the numeric-grounding-verified text is unchanged."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [p for p in parts if p][:max_sentences]
    return " ".join(kept)


# ---------------------------------------------------------------------------
# Tiny CSS-only product silhouettes -- line-art only, no downloaded images,
# nothing presented as an actual KOHLER product photo (Block 6, item 10).
# ---------------------------------------------------------------------------
PRODUCT_ICON_PATHS = {
    "smart_toilet": """
        <rect x="20" y="9" width="24" height="15" rx="3"/>
        <rect x="24" y="24" width="16" height="6"/>
        <ellipse cx="32" cy="44" rx="17" ry="11"/>
        <path d="M17 40 Q32 31 47 40" fill="none"/>
    """,
    "vanity": """
        <rect x="7" y="17" width="50" height="6" rx="1"/>
        <ellipse cx="32" cy="29" rx="13" ry="6.5"/>
        <rect x="9" y="38" width="46" height="18"/>
        <line x1="32" y1="38" x2="32" y2="56"/>
    """,
    "faucet": """
        <rect x="25" y="45" width="14" height="7" rx="1.5"/>
        <path d="M32 45 V27 Q32 19 44 19 Q51 19 51 27" fill="none"/>
        <circle cx="25" cy="39" r="3.4"/>
    """,
    "thermostatic_shower": """
        <rect x="27" y="7" width="7" height="42" rx="2.5"/>
        <path d="M27 12 Q12 12 12 23 Q12 30 18 30" fill="none"/>
        <circle cx="12" cy="34" r="1.6"/>
        <circle cx="17" cy="38" r="1.6"/>
        <circle cx="22" cy="41" r="1.6"/>
        <circle cx="30.5" cy="41" r="4.2"/>
    """,
}


def render_icon(category_value: str) -> str:
    paths = PRODUCT_ICON_PATHS.get(category_value, "")
    return (
        '<svg viewBox="0 0 64 64" width="52" height="52" class="kad-icon-svg" '
        'fill="none" stroke="currentColor" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round">' + paths + "</svg>"
    )


# ---------------------------------------------------------------------------
# Dark, restrained theme -- deep black / charcoal / graphite surfaces, warm
# ivory text, soft grey secondary text, one restrained brass/champagne
# accent used sparingly for hairlines and emphasis only. No blue, no
# purple, no glow, no gradients-as-decoration, no emoji, no bright cards.
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
:root {
    --void:#0B0A08;
    --charcoal:#141210;
    --graphite:#1B1815;
    --surface:#201D18;
    --surface-2:#262219;
    --hairline:#332E26;
    --hairline-soft:#241F19;
    --ivory:#EFE8D8;
    --grey:#A79C89;
    --grey-2:#948B78;
    --taupe:#6E6555;
    --brass:#B08D51;
    --brass-deep:#96723F;
    --brass-soft:rgba(176,141,81,0.14);
    --font-serif: Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', serif;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
}

html, body, .stApp { background-color: var(--void) !important; }
.stApp, .stApp p, .stApp span, .stApp label, .stApp div { color: var(--ivory); }
.stApp { font-family: var(--font-sans); }

#MainMenu, div[data-testid="stToolbar"], div[data-testid="stDecoration"],
header[data-testid="stHeader"] { visibility: hidden; height: 0; }
footer { visibility: hidden; }

.block-container { padding-top: 0.9rem !important; padding-bottom: 2.4rem !important; max-width: 1080px; }

hr.kad-hairline { border: none; border-top: 1px solid var(--hairline); margin: 30px 0; }

/* ---------- Top nav + progress ---------- */
.kad-nav {
    display: flex; align-items: baseline; justify-content: space-between;
    padding: 8px 2px 16px 2px; border-bottom: 1px solid var(--hairline); margin-bottom: 8px;
    flex-wrap: wrap; gap: 10px;
}
.kad-wordmark { font-family: var(--font-serif); font-size: 1.05rem; letter-spacing: 0.06em; color: var(--ivory); }
.kad-navlinks { display: flex; gap: 26px; align-items:center; }
.kad-navlinks .kad-navlink {
    font-family: var(--font-sans); font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--grey-2);
}
.kad-navlinks .kad-navlink.active { color: var(--brass); }
.kad-progress {
    font-family: var(--font-sans); font-size: 0.64rem; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--taupe); padding: 10px 2px 22px 2px;
}
.kad-progress .step.active { color: var(--brass); }

/* Buttons rendered inline in the nav row (Streamlit buttons dropped into
   narrow columns) -- strip them down to plain uppercase text links. */
.st-key-nav_design button, .st-key-nav_products button {
    background: transparent !important; border: none !important; padding: 0 !important;
    font-family: var(--font-sans) !important; font-size: 0.72rem !important; letter-spacing: 0.16em !important;
    text-transform: uppercase; color: var(--grey-2) !important; box-shadow: none !important;
}
.st-key-nav_design button:hover, .st-key-nav_products button:hover { color: var(--brass) !important; }
.st-key-nav_design button:disabled, .st-key-nav_products button:disabled { color: var(--hairline) !important; }

/* ---------- Welcome screen ---------- */
.kad-welcome {
    min-height: 62vh; display: flex; flex-direction: column; align-items: center;
    justify-content: center; text-align: center; padding: 8vh 0 0 0;
}
.kad-welcome-mark {
    font-family: var(--font-serif); font-size: 2.5rem; letter-spacing: 0.05em; color: var(--ivory);
    margin-bottom: 18px; line-height: 1.15;
}
.kad-welcome-tag {
    font-family: var(--font-serif); font-style: italic; color: var(--grey-2); font-size: 1.15rem;
    margin-bottom: 46px;
}
.st-key-begin_design { display:flex !important; justify-content:center; margin-top: -4vh; width: 100% !important; }
.st-key-begin_design .stButton { width: auto !important; flex: 0 0 auto !important; }
.st-key-begin_design button {
    background: transparent !important; border: 1px solid var(--brass) !important; color: var(--ivory) !important;
    font-family: var(--font-sans) !important; letter-spacing: 0.22em !important; font-size: 0.82rem !important;
    text-transform: uppercase; padding: 0.9rem 2.6rem !important; border-radius: 0 !important;
    width: auto !important; flex: 0 0 auto !important;
}
.st-key-begin_design button:hover { background: var(--brass-soft) !important; }

/* ---------- Headings / rhythm ---------- */
.kad-eyebrow {
    font-family: var(--font-sans); font-size: 0.7rem; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--brass); font-weight: 600; margin-bottom: 8px;
}
.kad-h1 {
    font-family: var(--font-serif); font-weight: 400; color: var(--ivory);
    font-size: 2.1rem; line-height: 1.15; margin: 0 0 8px 0;
}
.kad-h2 {
    font-family: var(--font-serif); font-weight: 400; color: var(--ivory);
    font-size: 1.5rem; line-height: 1.2; margin: 0 0 6px 0;
}
.kad-sub { font-family: var(--font-serif); font-style: italic; color: var(--grey-2); font-size: 0.98rem; margin: 0 0 22px 0; }

/* ---------- Form groups / containers ---------- */
.kad-group-label {
    font-family: var(--font-sans); font-size: 0.7rem; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--brass); font-weight: 600; margin: 0 0 12px 0;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface) !important; border: 1px solid var(--hairline) !important;
    border-radius: 2px !important; box-shadow: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 2px 2px; }

div[data-testid="stNumberInput"] input, div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input {
    background: var(--graphite) !important; border: 1px solid var(--hairline) !important;
    border-radius: 2px !important; color: var(--ivory) !important; font-family: var(--font-sans);
}
div[data-testid="stNumberInput"] button { border-color: var(--hairline) !important; background: var(--graphite) !important; }
div[data-testid="stWidgetLabel"] label p {
    font-family: var(--font-sans) !important; font-size: 0.74rem !important; letter-spacing: 0.06em;
    color: var(--grey-2) !important; text-transform: uppercase;
}

/* Slider -- remove Streamlit's default red/coral accent entirely */
div[data-testid="stSlider"] [role="slider"] { background-color: var(--brass) !important; border-color: var(--brass) !important; box-shadow: none !important;}
div[data-testid="stSlider"] div[data-baseweb="slider"] > div > div { background: var(--brass) !important; }
div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child { background: var(--hairline) !important; }
div[data-testid="stTickBar"] { display: none; }

/* Checkbox */
div[data-testid="stCheckbox"] label p { color: var(--ivory) !important; text-transform: none !important; font-size: 0.88rem !important; }
div[data-testid="stCheckbox"] span[data-baseweb="checkbox"] > div { border-color: var(--taupe) !important; background: var(--graphite) !important; }
div[data-testid="stCheckbox"] input:checked + div { background: var(--brass) !important; border-color: var(--brass) !important; }

/* Multiselect / pills tags */
div[data-testid="stMultiSelectTagsContainer"] span[data-tag] { background-color: var(--surface-2) !important; border: 1px solid var(--brass) !important; border-radius: 2px !important; }
div[data-testid="stMultiSelectTagsContainer"] span[data-tag] * { color: var(--ivory) !important; fill: var(--ivory) !important; stroke: var(--ivory) !important; }
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div { border-radius: 2px !important; border-color: var(--hairline) !important; background: var(--graphite) !important; }

/* Pills / segmented control */
div[data-testid="stButtonGroup"] button {
    border-radius: 2px !important; border-color: var(--hairline) !important;
    background: var(--graphite) !important; color: var(--grey-2) !important; font-family: var(--font-sans) !important;
    letter-spacing: 0.04em;
}
div[data-testid="stButtonGroup"] button[aria-checked="true"] { background: var(--brass) !important; color: var(--void) !important; border-color: var(--brass) !important; }
div[data-testid="stButtonGroup"] button[aria-checked="true"] * { color: var(--void) !important; }

/* Buttons */
div.stButton button[kind="primary"] {
    background: var(--brass) !important; border: 1px solid var(--brass) !important;
    color: var(--void) !important; border-radius: 2px !important; letter-spacing: 0.14em;
    text-transform: uppercase; font-size: 0.82rem !important; padding: 0.75rem 1.8rem !important;
    font-family: var(--font-sans) !important;
}
div.stButton button[kind="primary"] * { color: var(--void) !important; }
div.stButton button[kind="primary"]:hover { background: var(--ivory) !important; border-color: var(--ivory) !important; }
div.stButton button[kind="secondary"] {
    border-radius: 2px !important; border-color: var(--hairline) !important; color: var(--grey-2) !important;
    font-family: var(--font-sans) !important; letter-spacing: 0.1em; background: transparent !important;
    text-transform: uppercase; font-size: 0.74rem !important;
}
div.stButton button[kind="secondary"]:hover { border-color: var(--brass) !important; color: var(--brass) !important; }

/* Expander */
div[data-testid="stExpander"] { border: 1px solid var(--hairline) !important; border-radius: 2px !important; background: var(--surface) !important; }
div[data-testid="stExpander"] summary div[data-testid="stMarkdownContainer"] p { font-family: var(--font-sans) !important; color: var(--grey-2) !important; font-size: 0.82rem !important; }

/* Alerts -- neutral, restrained */
div[data-testid="stAlertContainer"], div[data-testid="stAlert"] {
    border-radius: 2px !important; border: 1px solid var(--hairline) !important;
    background: var(--surface) !important; color: var(--ivory) !important;
}
div[data-testid="stAlertContainer"] *, div[data-testid="stAlert"] * { color: var(--ivory) !important; }
div[data-testid="stAlertContentError"], div[data-testid="stNotificationContentError"] { border-left: 3px solid #7A4A3A !important; }

div[data-testid="stStatusWidget"] { border-radius: 2px !important; border: 1px solid var(--hairline) !important; background: var(--surface) !important; }
div[data-testid="stStatusWidget"] p, div[data-testid="stStatusWidget"] span { color: var(--grey-2) !important; }

/* ---------- Style / package cards ---------- */
.kad-swatch { height: 58px; border: 1px solid var(--hairline); margin-bottom: 10px; }
.kad-swatch.minimalist_modern { background: linear-gradient(135deg, #232019, #34302A); }
.kad-swatch.classic_luxury { background: linear-gradient(135deg, #2E2118, #50331C); }
.kad-swatch.japanese_zen { background: linear-gradient(135deg, #23241E, #3A3A2D); }
.kad-swatch.contemporary { background: linear-gradient(135deg, #1A1A1A, #38383A); }
.kad-style-name { font-family: var(--font-serif); font-size: 1.02rem; color: var(--ivory); margin-bottom: 2px; }
.kad-style-desc { font-size: 0.78rem; color: var(--grey-2); margin-bottom: 10px; min-height: 34px; }
.kad-style-card { border: 1px solid var(--hairline); padding: 14px; background: var(--surface); margin-bottom: 8px; }
.kad-style-card.selected { border-color: var(--brass); }

.kad-inert-row { display:flex; gap:8px; flex-wrap:wrap; margin-top: 10px; }
.kad-chip {
    font-family: var(--font-sans); font-size: 0.68rem; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--taupe); border: 1px dashed var(--hairline); padding: 5px 11px; border-radius: 999px;
}

/* ---------- Reveal ---------- */
.kad-hero-frame { border: 1px solid var(--hairline); background: var(--charcoal); padding: 0; }
.kad-package-name { font-family: var(--font-serif); font-size: 1.9rem; color: var(--ivory); margin: 4px 0 0 0; }
.kad-package-tagline { font-family: var(--font-serif); font-style: italic; color: var(--grey-2); font-size: 1rem; margin: 2px 0 14px 0; }
.kad-package-price { font-family: var(--font-serif); font-size: 1.5rem; color: var(--brass); }
.kad-package-meta {
    font-family: var(--font-sans); font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--grey-2); margin: 6px 0 20px 0;
}
.kad-supporting { font-size: 0.94rem; color: var(--grey-2); margin-bottom: 26px; }

.kad-compromise {
    border: 1px solid var(--brass-deep); border-left: 3px solid var(--brass);
    background: var(--brass-soft); padding: 12px 16px; font-size: 0.86rem; color: var(--ivory);
    margin: 6px 0 20px 0;
}
.kad-compromise .kad-compromise-label {
    font-family: var(--font-sans); font-size: 0.68rem; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--brass); margin-bottom: 4px; font-weight: 600;
}

/* ---------- Package picker ---------- */
.kad-pkg-card { border: 1px solid var(--hairline); padding: 18px; background: var(--surface); height: 100%; }
.kad-pkg-card.selected { border-color: var(--brass); background: var(--surface-2); }
.kad-pkg-card .kad-pkg-name { font-family: var(--font-serif); font-size: 1.15rem; color: var(--ivory); margin-bottom: 2px; }
.kad-pkg-card .kad-pkg-tag { font-size: 0.78rem; color: var(--grey-2); margin-bottom: 10px; font-style: italic; }
.kad-pkg-card .kad-pkg-price { font-family: var(--font-serif); font-size: 1.3rem; color: var(--brass); }

/* ---------- Stats / water-at-a-glance ---------- */
.kad-stat-label { font-family: var(--font-sans); font-size: 0.66rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--grey-2); margin-bottom: 2px; }
.kad-stat-value { font-family: var(--font-serif); font-size: 1.5rem; color: var(--ivory); line-height: 1.1; }
.kad-stat-value.small { font-size: 1.15rem; }
.kad-stat-block { margin-bottom: 16px; }
.kad-stat-accent .kad-stat-value { color: var(--brass); }

.kad-explanation { font-family: var(--font-serif); font-size: 1.02rem; line-height: 1.6; color: var(--ivory); border-left: 2px solid var(--brass); padding-left: 16px; margin: 8px 0 6px 0; }

/* ---------- Product cards ---------- */
.kad-icon-card {
    border: 1px solid var(--hairline); background: var(--surface); padding: 20px 16px;
    display:flex; flex-direction:column; align-items:center; text-align:center; height: 100%;
}
.kad-icon-svg { color: var(--brass); margin-bottom: 10px; }
.kad-product-cat { font-family: var(--font-sans); font-size: 0.64rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--grey-2); }
.kad-product-name { font-family: var(--font-serif); font-size: 1.0rem; color: var(--ivory); margin: 4px 0; }
.kad-product-price { font-family: var(--font-sans); font-size: 0.92rem; color: var(--brass); font-weight: 600; }
.kad-product-status { font-family: var(--font-sans); font-size: 0.66rem; color: var(--taupe); margin-top: 8px; }

.kad-detail-row { display:flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid var(--hairline-soft); font-size: 0.86rem; }
.kad-detail-row span:first-child { color: var(--grey-2); }
.kad-detail-row span:last-child { color: var(--ivory); text-align: right; }
.kad-detail-features { font-size: 0.86rem; color: var(--ivory); line-height: 1.6; margin: 6px 0; }
.kad-detail-footnote { font-size: 0.72rem; color: var(--taupe); margin-top: 10px; font-style: italic; }

/* ---------- Footer ---------- */
.kad-footer { border-top: 1px solid var(--hairline); padding-top: 20px; margin-top: 40px; }
.kad-footer-line { font-size: 0.72rem; color: var(--taupe); line-height: 1.7; max-width: 640px; }
.kad-credit { margin-top: 22px; font-family: var(--font-serif); font-style: italic; color: var(--grey-2); font-size: 0.86rem; line-height: 1.5; }

@media (max-width: 900px) {
    .kad-h1 { font-size: 1.7rem; }
    .kad-welcome-mark { font-size: 1.9rem; }
    .kad-nav { flex-direction: column; align-items: flex-start; }
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource
def get_catalog():
    return load_catalog()


CATALOG = get_catalog()
KEY_STATUS = openai_key_status()

# ---------------------------------------------------------------------------
# Stage machine
# ---------------------------------------------------------------------------
if "stage" not in st.session_state:
    st.session_state["stage"] = "welcome"


def goto(stage: str) -> None:
    st.session_state["stage"] = stage
    st.rerun()


STAGE_PROGRESS = ["space", "style", "design", "products"]
PROGRESS_LABELS = {"space": "01 SPACE", "style": "02 STYLE", "design": "03 DESIGN", "products": "04 PRODUCTS"}
# "reveal" belongs visually under the same progress step as "design".
PROGRESS_ALIAS = {"reveal": "design"}


def render_nav() -> None:
    has_design = "alternatives" in st.session_state
    current = st.session_state["stage"]
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([2.6, 1.1, 1.5, 3.8])
    with nav_col1:
        st.markdown('<div class="kad-wordmark">KOHLER AI</div>', unsafe_allow_html=True)
    with nav_col2:
        if st.button("DESIGN", key="nav_design", disabled=not has_design, use_container_width=True):
            goto("design")
    with nav_col3:
        if st.button("PRODUCTS", key="nav_products", disabled=not has_design, use_container_width=True):
            goto("products")

    progress_key = PROGRESS_ALIAS.get(current, current)
    if progress_key in STAGE_PROGRESS:
        bits = []
        for step in STAGE_PROGRESS:
            cls = "step active" if step == progress_key else "step"
            bits.append(f'<span class="{cls}">{PROGRESS_LABELS[step]}</span>')
        st.markdown('<div class="kad-progress">' + " &middot; ".join(bits) + "</div>", unsafe_allow_html=True)
    else:
        st.markdown('<div style="margin-bottom:22px;"></div>', unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(
        """
        <div class="kad-footer">
            <div class="kad-footer-line">Prototype visualization &middot; Demonstration data. This
            interface uses a synthetic demonstration catalogue and is not an official KOHLER product
            catalogue or pricing source.</div>
            <div class="kad-footer-line" style="margin-top:6px;">Conceptual design only &mdash; final
            plumbing, electrical, structural and installation decisions require qualified professionals.</div>
            <div class="kad-credit">Created by<br/>GAURI GIRISH JAJU</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Pipeline -- unchanged deterministic building blocks, just invoked from the
# staged UI instead of one long form.
# ---------------------------------------------------------------------------
def run_pipeline() -> None:
    requirement = RequirementSpec(
        bathroom=BathroomDimensions(
            length_ft=st.session_state["length_ft"], width_ft=st.session_state["width_ft"]
        ),
        budget_inr=st.session_state["budget_inr"],
        style=st.session_state["style_value"],
        required_categories=st.session_state["category_values"],
        priorities=st.session_state.get("mood_tags", []) + (
            [st.session_state["vision_note"]] if st.session_state.get("vision_note") else []
        ),
    )

    usage_assumptions = UsageAssumptions(
        num_users=st.session_state.get("num_users", 4),
        flushes_per_person_per_day=st.session_state.get("flushes", 5.0),
        showers_per_person_per_week=st.session_state.get("showers_per_week", 7.0),
        shower_duration_minutes=st.session_state.get("shower_minutes", 8.0),
        faucet_uses_per_person_per_day=st.session_state.get("faucet_uses", 6.0),
        faucet_use_duration_minutes=st.session_state.get("faucet_minutes", 1.0),
    )

    with st.spinner("Designing your bathroom…"):
        alternatives = generate_alternatives(requirement, CATALOG)
        best_effort_mode = False
        if not alternatives:
            be = generate_best_effort_alternative(requirement, CATALOG)
            if be is not None:
                alternatives = [be]
                best_effort_mode = True

        water_results = {alt.label: estimate_water_use(alt.bundle, usage_assumptions) for alt in alternatives}
        explanations = {
            alt.label: generate_explanation(alt.as_dict(), prefer_llm=(KEY_STATUS == "configured"))
            for alt in alternatives
        }

    st.session_state["requirement"] = requirement
    st.session_state["usage_assumptions"] = usage_assumptions
    st.session_state["alternatives"] = alternatives
    st.session_state["best_effort_mode"] = best_effort_mode
    st.session_state["explanations"] = explanations
    st.session_state["water_results"] = water_results
    default_label = next((a.label for a in alternatives if "balanced" in a.label.lower()), alternatives[0].label)
    st.session_state["selected_label"] = default_label


def get_isometric_image(alt, requirement, view: str = "Isometric") -> str:
    """Cache key MUST include bathroom dimensions, not just product IDs +
    view. The optimizer can (and does, e.g. for the Essential and Premium
    tiers -- see Block 6.2 build-log entry) pick the exact same set of
    products for two different room sizes, since price/feasibility for
    those tiers doesn't depend on the room. Without the dimensions in the
    key, a regenerate after only changing the room size would silently
    reuse the previous room's already-rendered PNG (same product IDs =
    same filename) instead of re-rendering the new room's geometry --
    a stale-visualization bug, not a pricing/feasibility one."""
    tmp_dir = Path(tempfile.gettempdir())
    key = "_".join(p.product_id for p in alt.bundle.values())
    dims_key = f"{requirement.bathroom.length_ft:g}x{requirement.bathroom.width_ft:g}"
    out_path = tmp_dir / f"kad_iso_{key}_{dims_key}_{view.lower()}.png"
    if not out_path.exists():
        render_isometric_view(alt.bundle, requirement, output_path=out_path, view=view)
    return str(out_path)


def render_view_switcher(state_key: str) -> str:
    """Small pills row letting the person orbit the isometric hero visual
    (up/top, down/front, left, right) instead of only ever seeing the
    fixed default angle -- purely a display choice, the underlying
    geometry and fixtures never change."""
    current = st.session_state.get(state_key, "Isometric")
    view = st.pills(
        "View", options=list(ISO_VIEW_PRESETS.keys()), default=current,
        selection_mode="single", label_visibility="collapsed", key=f"{state_key}_pills",
    )
    view = view or current
    st.session_state[state_key] = view
    return view


# ===========================================================================
# WELCOME -- item 2: only wordmark, tagline, one CTA. Nothing else.
# ===========================================================================
def render_welcome() -> None:
    st.markdown(
        """
        <div class="kad-welcome">
            <div class="kad-welcome-mark">KOHLER AI<br/>BATHROOM DESIGNER</div>
            <div class="kad-welcome-tag">Your space. Reimagined.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("[ BEGIN DESIGN ]", key="begin_design"):
        goto("space")


# ===========================================================================
# SPACE -- length x width, budget.
# ===========================================================================
def render_space() -> None:
    render_nav()
    st.markdown('<div class="kad-eyebrow">Step 01</div>', unsafe_allow_html=True)
    st.markdown('<div class="kad-h1">YOUR SPACE</div>', unsafe_allow_html=True)
    st.markdown('<div class="kad-sub">Every design begins with the room itself.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.markdown('<div class="kad-group-label">Dimensions</div>', unsafe_allow_html=True)
            length_ft = st.slider(
                "Length (ft)", min_value=3.0, max_value=20.0,
                value=st.session_state.get("length_ft", 8.0), step=0.5, key="length_ft_slider",
            )
            width_ft = st.slider(
                "Width (ft)", min_value=3.0, max_value=20.0,
                value=st.session_state.get("width_ft", 6.0), step=0.5, key="width_ft_slider",
            )
            st.markdown(
                f'<div class="kad-stat-label" style="margin-top:6px;">Room area</div>'
                f'<div class="kad-stat-value small">{length_ft * width_ft:g} sq ft</div>',
                unsafe_allow_html=True,
            )
    with col2:
        with st.container(border=True):
            st.markdown('<div class="kad-group-label">Investment</div>', unsafe_allow_html=True)
            budget_inr = st.slider(
                "Budget (INR)", min_value=10_000.0, max_value=1_000_000.0,
                value=st.session_state.get("budget_inr", 250_000.0), step=5_000.0, key="budget_inr_slider",
            )
            st.markdown(
                f'<div class="kad-stat-label" style="margin-top:6px;">Your budget</div>'
                f'<div class="kad-stat-value small">₹{budget_inr:,.0f}</div>',
                unsafe_allow_html=True,
            )

    st.session_state["length_ft"] = length_ft
    st.session_state["width_ft"] = width_ft
    st.session_state["budget_inr"] = budget_inr

    st.write("")
    b1, b2 = st.columns([1, 5])
    with b1:
        if st.button("← Start over", key="space_back", type="secondary"):
            goto("welcome")
    with b2:
        _, cta = st.columns([3, 1.4])
        with cta:
            if st.button("NEXT →", key="space_next", type="primary", use_container_width=True):
                goto("style")
    render_footer()


# ===========================================================================
# STYLE -- style cards, mood tags, essentials, optional note.
# ===========================================================================
def render_style() -> None:
    render_nav()
    st.markdown('<div class="kad-eyebrow">Step 02</div>', unsafe_allow_html=True)
    st.markdown('<div class="kad-h1">STYLE &amp; PREFERENCES</div>', unsafe_allow_html=True)
    st.markdown('<div class="kad-sub">Choose the mood your bathroom should carry.</div>', unsafe_allow_html=True)

    st.markdown('<div class="kad-group-label">Style</div>', unsafe_allow_html=True)
    current_style = st.session_state.get("style_value", AestheticStyle.JAPANESE_ZEN.value)
    st.session_state["style_value"] = current_style
    style_cols = st.columns(4)
    for scol, (enum_val, label, desc) in zip(style_cols, FUNCTIONAL_STYLES):
        with scol:
            selected = enum_val.value == current_style
            st.markdown(
                f'<div class="kad-style-card {"selected" if selected else ""}">'
                f'<div class="kad-swatch {enum_val.value}"></div>'
                f'<div class="kad-style-name">{label}</div>'
                f'<div class="kad-style-desc">{desc}</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Selected ✓" if selected else "Choose", key=f"style_{enum_val.value}",
                         type="primary" if selected else "secondary", use_container_width=True):
                st.session_state["style_value"] = enum_val.value
                st.rerun()

    st.write("")
    with st.container(border=True):
        st.markdown('<div class="kad-group-label">Mood (optional)</div>', unsafe_allow_html=True)
        mood_tags = st.multiselect(
            "Additional mood", MOOD_TAGS, default=st.session_state.get("mood_tags", []),
            label_visibility="collapsed",
        )
        st.caption("Sets the tone of your design notes only — every product shown still comes from the same validated catalogue.")
    st.session_state["mood_tags"] = mood_tags

    st.write("")
    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.markdown('<div class="kad-group-label">Essentials</div>', unsafe_allow_html=True)
            category_values = []
            for cat, label in ESSENTIAL_CATEGORY_LABELS.items():
                default_checked = cat.value in st.session_state.get(
                    "category_values", [c.value for c in ESSENTIAL_CATEGORY_LABELS]
                )
                if st.checkbox(label, value=default_checked, key=f"ess_{cat.value}"):
                    category_values.append(cat.value)
            st.markdown(
                '<div class="kad-inert-row">' + "".join(
                    f'<span class="kad-chip">{name} · soon</span>' for name in INERT_ESSENTIALS
                ) + "</div>",
                unsafe_allow_html=True,
            )
    with col2:
        with st.container(border=True):
            st.markdown('<div class="kad-group-label">Anything else?</div>', unsafe_allow_html=True)
            vision_note = st.text_input(
                "Notes for your designer (optional)",
                value=st.session_state.get("vision_note", ""),
                placeholder="e.g. I'd like everything to feel very quiet and uncluttered.",
                label_visibility="collapsed",
            )
            st.write("")
            with st.expander("Water-usage assumptions"):
                st.session_state["num_users"] = st.slider("Number of users", 1, 10, st.session_state.get("num_users", 4))
                st.session_state["flushes"] = st.slider("Flushes / person / day", 1.0, 10.0, st.session_state.get("flushes", 5.0))
                st.session_state["showers_per_week"] = st.slider("Showers / person / week", 1.0, 14.0, st.session_state.get("showers_per_week", 7.0))
                st.session_state["shower_minutes"] = st.slider("Shower duration (min)", 2.0, 20.0, st.session_state.get("shower_minutes", 8.0))
                st.session_state["faucet_uses"] = st.slider("Faucet uses / person / day", 1.0, 15.0, st.session_state.get("faucet_uses", 6.0))
                st.session_state["faucet_minutes"] = st.slider("Faucet use duration (min)", 0.2, 5.0, st.session_state.get("faucet_minutes", 1.0))

    st.session_state["category_values"] = category_values
    st.session_state["vision_note"] = vision_note

    st.write("")
    if not category_values:
        st.error("Choose at least one essential to continue.")

    b1, b2 = st.columns([1, 5])
    with b1:
        if st.button("← Back", key="style_back", type="secondary"):
            goto("space")
    with b2:
        _, cta = st.columns([2.6, 1.6])
        with cta:
            if st.button("[ DESIGN MY BATHROOM ]", key="generate_button", type="primary",
                         use_container_width=True, disabled=not category_values):
                run_pipeline()
                goto("reveal")
    render_footer()


# ===========================================================================
# REVEAL -- the "wow" moment. Visual first, minimal text.
# ===========================================================================
def render_reveal() -> None:
    render_nav()
    requirement: RequirementSpec = st.session_state["requirement"]
    alternatives = st.session_state["alternatives"]
    best_effort = st.session_state["best_effort_mode"]
    alt = next(a for a in alternatives if a.label == st.session_state["selected_label"])

    st.markdown('<div class="kad-eyebrow">Your bathroom</div>', unsafe_allow_html=True)
    st.markdown('<div class="kad-h1">YOUR BATHROOM</div>', unsafe_allow_html=True)

    st.markdown('<div class="kad-hero-frame">', unsafe_allow_html=True)
    st.image(get_isometric_image(alt, requirement), width='stretch')
    st.markdown("</div>", unsafe_allow_html=True)

    piece_count = len(alt.bundle)
    st.markdown(
        f'<div class="kad-package-name">{alt.label.replace("Bundle", "").strip() if not is_best_effort(alt) else alt.label}</div>'
        f'<div class="kad-package-tagline">{package_tagline(alt.label)}</div>'
        f'<div class="kad-package-price">₹{alt.total_cost_inr:,.0f}</div>'
        f'<div class="kad-package-meta">{piece_count} PIECE COLLECTION</div>',
        unsafe_allow_html=True,
    )

    if best_effort:
        notes = " ".join(getattr(alt, "compromise_notes", []))
        st.markdown(
            f'<div class="kad-compromise"><div class="kad-compromise-label">{alt.label}</div>'
            f'Designed around your available space with compact fixture selections. {notes}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="kad-supporting">Designed around your space and preferences.</div>',
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("[ VIEW DESIGN ]", key="reveal_view_design", type="primary", use_container_width=True):
            goto("design")
    with c2:
        if st.button("[ EXPLORE PRODUCTS ]", key="reveal_explore_products", type="secondary", use_container_width=True):
            goto("products")
    render_footer()


# ===========================================================================
# DESIGN -- the fuller "3D / Visual Design" screen: package picker, why
# this design, water at a glance.
# ===========================================================================
def render_design() -> None:
    render_nav()
    requirement: RequirementSpec = st.session_state["requirement"]
    alternatives = st.session_state["alternatives"]
    best_effort = st.session_state["best_effort_mode"]
    explanations = st.session_state["explanations"]
    water_results = st.session_state["water_results"]

    st.markdown('<div class="kad-eyebrow">Step 03</div>', unsafe_allow_html=True)
    st.markdown('<div class="kad-h1">YOUR DESIGN</div>', unsafe_allow_html=True)

    if not best_effort and len(alternatives) > 1:
        st.markdown('<div class="kad-sub">Choose the concept that feels right — there is no single "best."</div>', unsafe_allow_html=True)
        pkg_cols = st.columns(len(alternatives))
        for pcol, a in zip(pkg_cols, alternatives):
            with pcol:
                selected = a.label == st.session_state["selected_label"]
                st.markdown(
                    f'<div class="kad-pkg-card {"selected" if selected else ""}">'
                    f'<div class="kad-pkg-name">{a.label.replace("Bundle", "").strip()}</div>'
                    f'<div class="kad-pkg-tag">{package_tagline(a.label)}</div>'
                    f'<div class="kad-pkg-price">₹{a.total_cost_inr:,.0f}</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("View this concept" if not selected else "Selected ✓", key=f"pick_{a.label}",
                             type="primary" if selected else "secondary", use_container_width=True):
                    st.session_state["selected_label"] = a.label
                    st.rerun()
        st.write("")

    alt = next(a for a in alternatives if a.label == st.session_state["selected_label"])
    explanation = explanations[alt.label]
    water_result = water_results[alt.label]

    current_view = render_view_switcher("design_view")
    st.markdown('<div class="kad-hero-frame">', unsafe_allow_html=True)
    st.image(get_isometric_image(alt, requirement, current_view), width='stretch')
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption("AI concept visualization — stylized, not construction-ready. Numbered markers match the legend under the image.")

    if best_effort:
        notes = " ".join(getattr(alt, "compromise_notes", []))
        st.markdown(
            f'<div class="kad-compromise"><div class="kad-compromise-label">{alt.label}</div>'
            f'Designed around your available space with compact fixture selections. {notes}</div>',
            unsafe_allow_html=True,
        )
    elif alt.validation.warnings:
        for w in alt.validation.warnings[:1]:
            st.caption(f"Note: {w}")

    st.write("")
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.markdown(f'<div class="kad-stat-label">Total</div><div class="kad-stat-value small kad-stat-accent">₹{alt.total_cost_inr:,.0f}</div>', unsafe_allow_html=True)
    with stat_cols[1]:
        st.markdown(f'<div class="kad-stat-label">Remaining</div><div class="kad-stat-value small">₹{alt.remaining_budget_inr:,.0f}</div>', unsafe_allow_html=True)
    with stat_cols[2]:
        st.markdown(f'<div class="kad-stat-label">Room</div><div class="kad-stat-value small">{fmt_ft(requirement.bathroom.length_ft)} × {fmt_ft(requirement.bathroom.width_ft)} ft</div>', unsafe_allow_html=True)
    with stat_cols[3]:
        st.markdown(f'<div class="kad-stat-label">Style</div><div class="kad-stat-value small">{STYLE_DISPLAY_NAME.get(requirement.style.value, requirement.style.value)}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="kad-hairline"/>', unsafe_allow_html=True)
    st.markdown('<div class="kad-h2">WHY THIS DESIGN</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kad-explanation">{shorten(explanation.text, 4)}</div>', unsafe_allow_html=True)

    with st.expander("See how this was scored"):
        st.bar_chart({k.replace("_", " ").title(): v for k, v in alt.scores.items()})
        st.caption("Each bar is one component of the internal design-match score (0–1). Weights: src/optimization/optimizer.py.")

    st.markdown('<div class="kad-h2" style="margin-top:26px;">WATER AT A GLANCE</div>', unsafe_allow_html=True)
    wcols = st.columns(3)
    with wcols[0]:
        st.markdown(f'<div class="kad-stat-label">Daily</div><div class="kad-stat-value small">{water_result.daily_total_litres:,.0f} L</div>', unsafe_allow_html=True)
    with wcols[1]:
        st.markdown(f'<div class="kad-stat-label">Annual</div><div class="kad-stat-value small">{water_result.annual_total_litres:,.0f} L</div>', unsafe_allow_html=True)
    with wcols[2]:
        st.markdown(f'<div class="kad-stat-label">Potential saving</div><div class="kad-stat-value small">{water_result.estimated_savings_percent:.1f}%</div>', unsafe_allow_html=True)
    st.caption("Estimated from assumed usage patterns and prototype specifications.")

    st.write("")
    if st.button("[ EXPLORE PRODUCTS ]", key="design_explore_products", type="primary"):
        goto("products")
    render_footer()


# ===========================================================================
# PRODUCTS -- visual cards + clean, code-free "View details".
# ===========================================================================
def render_products() -> None:
    render_nav()
    requirement: RequirementSpec = st.session_state["requirement"]
    alternatives = st.session_state["alternatives"]
    alt = next(a for a in alternatives if a.label == st.session_state["selected_label"])

    st.markdown('<div class="kad-eyebrow">Step 04</div>', unsafe_allow_html=True)
    st.markdown('<div class="kad-h1">SELECTED PRODUCTS</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kad-sub">From your {alt.label.replace("Bundle", "").strip()} design.</div>', unsafe_allow_html=True)

    cols = st.columns(len(alt.bundle))
    for pcol, (category, product) in zip(cols, alt.bundle.items()):
        with pcol:
            status_key = product.data_status.value
            st.markdown(
                f"""
                <div class="kad-icon-card">
                    {render_icon(category.value)}
                    <div class="kad-product-cat">{CATEGORY_DISPLAY.get(category.value, category.value)}</div>
                    <div class="kad-product-name">{product.product_name}</div>
                    <div class="kad-product-price">₹{product.price_inr:,.0f}</div>
                    <div class="kad-product-status">{DATA_STATUS_SHORT.get(status_key, status_key)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("View details"):
                d = product.dimensions_mm
                st.markdown(
                    f"""
                    <div class="kad-detail-row"><span>Name</span><span>{product.product_name}</span></div>
                    <div class="kad-detail-row"><span>Price</span><span>₹{product.price_inr:,.0f}</span></div>
                    <div class="kad-detail-row"><span>Dimensions</span><span>{d.width:.0f} × {d.depth:.0f} × {d.height:.0f} mm</span></div>
                    <div class="kad-detail-row"><span>Style</span><span>{", ".join(STYLE_DISPLAY_NAME.get(s.value, s.value) for s in product.style_tags) or "—"}</span></div>
                    <div class="kad-detail-row"><span>Finish</span><span>{product.finish.replace("_", " ").title()}</span></div>
                    """,
                    unsafe_allow_html=True,
                )
                if product.features:
                    pretty_features = [f.replace("_", " ").strip().capitalize() for f in product.features]
                    st.markdown(
                        '<div class="kad-detail-features">' + "<br/>".join(f"— {f}" for f in pretty_features) + "</div>",
                        unsafe_allow_html=True,
                    )
                if product.water_consumption:
                    wc = product.water_consumption
                    st.markdown(
                        f'<div class="kad-detail-row"><span>Water use</span>'
                        f'<span>{wc.value:g} {wc.unit.replace("_", " ")}</span></div>',
                        unsafe_allow_html=True,
                    )
                ir = product.installation_requirements
                st.markdown(
                    f'<div class="kad-detail-row"><span>Clearance (mm)</span>'
                    f'<span>F {ir.minimum_clearance_front_mm:.0f} · S {ir.minimum_clearance_side_mm:.0f} · '
                    f'B {ir.minimum_clearance_back_mm:.0f}</span></div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="kad-detail-footnote">*Estimated/prototype specification for demonstration.</div>', unsafe_allow_html=True)

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back to design", key="products_back_design", type="secondary", use_container_width=True):
            goto("design")
    with c2:
        if st.button("Start a new design", key="products_restart", type="secondary", use_container_width=True):
            for k in ["alternatives", "requirement", "explanations", "water_results", "best_effort_mode", "selected_label", "usage_assumptions"]:
                st.session_state.pop(k, None)
            goto("welcome")
    render_footer()


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
STAGE_RENDERERS = {
    "welcome": render_welcome,
    "space": render_space,
    "style": render_style,
    "reveal": render_reveal,
    "design": render_design,
    "products": render_products,
}
STAGE_RENDERERS.get(st.session_state["stage"], render_welcome)()
