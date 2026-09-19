"""
2D bathroom floor-plan renderer.

Draws the same simplified 4-zone layout the constraint engine validates
against (src.optimization.constraints.zone_layout_mm is the single source
of truth for the geometry -- this module only draws it, it does not decide
anything). Output is a PNG that always carries the "not construction-ready"
disclaimer as a visible caption, per the brief's rule that a generated
layout must never be presented as final.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")  # headless-safe backend, required for Streamlit/server use
import matplotlib.patches as patches
import matplotlib.pyplot as plt

from src.data.schemas import Product, ProductCategory, RequirementSpec
from src.optimization.constraints import zone_layout_mm

MM_PER_FT = 304.8

FLOORPLAN_ROOM_COLOR = "#2B2621"      # charcoal outline
FLOORPLAN_ZONE_EDGE = "#847A6A"       # taupe dashed zone edges
FLOORPLAN_ZONE_LABEL = "#6E6455"      # muted label text
FLOORPLAN_CLEARANCE_EDGE = "#A9834B"  # restrained brass, replaces bright orange
FLOORPLAN_CAPTION_COLOR = "#6E6455"   # muted taupe, replaces bright firebrick
FLOORPLAN_BACKGROUND = "#FBF8F2"      # warm ivory, matches the app background

# Zone fills: muted, neutral tones (stone/ivory family) instead of saturated
# blue/orange/green -- purely a color-palette change, the zone geometry
# itself still comes only from zone_layout_mm().
ZONE_COLORS = {
    ProductCategory.THERMOSTATIC_SHOWER: "#E7EBEA",
    ProductCategory.SMART_TOILET: "#EFE8D9",
    ProductCategory.VANITY: "#E6E7DC",
}

FIXTURE_COLOR = "#2B2621"
DISCLAIMER = (
    "Simplified prototype layout for feasibility illustration only -- NOT a "
    "construction-ready plan. Verify with a qualified designer/plumber."
)


def render_floorplan(
    bundle: Dict[ProductCategory, Product],
    requirement: RequirementSpec,
    output_path: Optional[Path] = None,
    title: str = "Prototype 2D Bathroom Layout",
) -> Path:
    """
    Renders the bathroom outline, the 4 fixed zones, and each selected
    fixture's footprint (centered in its zone) to a PNG file and returns
    the path written.
    """
    length_mm = requirement.bathroom.length_ft * MM_PER_FT
    width_mm = requirement.bathroom.width_ft * MM_PER_FT
    zones = zone_layout_mm(requirement.bathroom.length_ft, requirement.bathroom.width_ft)

    fig, ax = plt.subplots(figsize=(7, 7 * (length_mm / width_mm) if width_mm else 7))
    fig.patch.set_facecolor(FLOORPLAN_BACKGROUND)
    ax.set_facecolor(FLOORPLAN_BACKGROUND)
    for spine in ax.spines.values():
        spine.set_color(FLOORPLAN_ZONE_EDGE)

    # Bathroom outline (x = room width, y = room length, both in mm)
    ax.add_patch(patches.Rectangle((0, 0), width_mm, length_mm, fill=False,
                                    edgecolor=FLOORPLAN_ROOM_COLOR, linewidth=1.6))

    # Zones (skip faucet -- it shares the vanity zone visually)
    drawn_zone_categories = [c for c in zones if c != ProductCategory.FAUCET]
    for category in drawn_zone_categories:
        x, y, w, d = zones[category]
        ax.add_patch(patches.Rectangle(
            (x, y), w, d, facecolor=ZONE_COLORS.get(category, "#EEEEEE"),
            edgecolor=FLOORPLAN_ZONE_EDGE, linestyle="--", linewidth=1, alpha=0.9,
        ))
        ax.text(x + w / 2, y + 12, category.value.replace("_", " ").title(),
                ha="center", va="top", fontsize=8, color=FLOORPLAN_ZONE_LABEL)

    # Fixtures, centered within their zone
    for category, product in bundle.items():
        if category == ProductCategory.FAUCET or category not in zones:
            continue
        zx, zy, zw, zd = zones[category]

        if category == ProductCategory.THERMOSTATIC_SHOWER:
            fw, fd = product.dimensions_mm.width, product.dimensions_mm.depth
        else:
            side = product.installation_requirements.minimum_clearance_side_mm
            fw = product.dimensions_mm.width
            fd = product.dimensions_mm.depth
            # draw the clearance zone lightly behind the fixture
            front = product.installation_requirements.minimum_clearance_front_mm
            cx = zx + (zw - fw) / 2
            cy = zy + (zd - fd - front) / 2
            ax.add_patch(patches.Rectangle(
                (cx - side, cy), fw + 2 * side, fd + front,
                facecolor="none", edgecolor=FLOORPLAN_CLEARANCE_EDGE, linestyle=":", linewidth=1,
            ))

        fx = zx + (zw - fw) / 2
        fy = zy + (zd - fd) / 2
        ax.add_patch(patches.Rectangle((fx, fy), fw, fd, facecolor=FIXTURE_COLOR, alpha=0.88,
                                        edgecolor=FLOORPLAN_ROOM_COLOR, linewidth=1))
        ax.text(fx + fw / 2, fy + fd / 2, product.product_name,
                ha="center", va="center", fontsize=6.5, color="white", wrap=True)

    ax.set_xlim(-100, width_mm + 100)
    ax.set_ylim(-100, length_mm + 100)
    ax.set_aspect("equal")
    ax.invert_yaxis()  # y=0 (shower/near wall) at top, matches a plan-view reading order
    ax.set_xlabel("Width (mm)", color=FLOORPLAN_ZONE_LABEL, fontsize=8.5)
    ax.set_ylabel("Length (mm)", color=FLOORPLAN_ZONE_LABEL, fontsize=8.5)
    ax.tick_params(colors=FLOORPLAN_ZONE_LABEL, labelsize=7.5)
    ax.set_title(
        f"{title}\n{requirement.bathroom.length_ft:.1f} ft x {requirement.bathroom.width_ft:.1f} ft "
        f"({requirement.bathroom.area_sqft:.0f} sq ft)",
        color=FLOORPLAN_ROOM_COLOR, fontsize=10.5,
    )
    fig.text(0.5, 0.01, DISCLAIMER, ha="center", va="bottom", fontsize=7.5,
              color=FLOORPLAN_CAPTION_COLOR, wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 1))

    output_path = output_path or Path("floorplan_output.png")
    fig.savefig(output_path, dpi=150, facecolor=FLOORPLAN_BACKGROUND)
    plt.close(fig)
    return output_path


# ===========================================================================
# Block 6 -- pseudo-3D isometric concept visualization
#
# This is the "AI CONCEPT VISUALIZATION" shown in the design reveal. It is
# a second, independent renderer -- it does not replace render_floorplan()
# above (kept intact for its own tests) and it does not decide anything: it
# reads the SAME zone_layout_mm() geometry and the SAME validated Product
# records (dimensions_mm.height included -- a real catalog field, not an
# invented one) and projects them with a standard 30-degree isometric
# transform. No 3D library, no new dependency -- matplotlib polygons only.
# Explicitly NOT construction-ready and never claimed to be photorealistic.
# ===========================================================================

ISO_BACKGROUND = "#171310"      # near-black, deeper than the app's own charcoal
ISO_FLOOR = "#332D24"           # dark graphite floor, lifted for readability against the background
ISO_WALL_LEFT = "#3A342A"
ISO_WALL_BACK = "#423A2E"
ISO_EDGE = "#A9834B"            # brass, used only for thin outlines
ISO_LABEL = "#B9AE96"           # muted warm grey for category labels

# Fixture block faces, lightest (top) to darkest (front) -- a simple 3-tone
# shading trick that reads as "sculptural product form in a dark showroom"
# rather than an engineering diagram. Purely decorative constants.
ISO_FIXTURE_TOP = "#EDE7D8"
ISO_FIXTURE_RIGHT = "#CFC6AF"
ISO_FIXTURE_FRONT = "#B4AA90"

# Decorative-only scale applied to each product's real dimensions_mm.height
# so a floor-to-ceiling shower enclosure (~2.1-2.3m) doesn't visually dwarf
# a toilet (~0.4m) inside a compact illustration. Does not touch the stored
# height value or any spatial-fit calculation -- display only.
ISO_HEIGHT_VISUAL_SCALE = 0.5
ISO_MAX_FIXTURE_HEIGHT_MM = 950.0  # decorative cap so a floor-to-ceiling shower
# enclosure doesn't visually dwarf the other fixtures or collide with their
# labels -- display only, never used by any spatial-fit calculation.
ISO_WALL_HEIGHT_MM = 2400.0

ISO_DISCLAIMER_TITLE = "AI CONCEPT VISUALIZATION"
ISO_DISCLAIMER_SUB = (
    "Stylized pseudo-3D layout for illustration only -- not a photorealistic "
    "or construction-ready render."
)

ISO_MARKER_FILL = "#171310"
ISO_MARKER_TEXT = "#EFE8D8"

# Fixed number for each real category, independent of draw order, so the
# small numbered marker on each fixture and the caption legend below the
# image always agree -- this is what lets a viewer tell "which shape is
# the washbasin vs. the shower" without floating text labels colliding
# with taller neighbors (see the view presets below for why floating
# labels don't work well once the camera angle can change).
CATEGORY_NUMBER = {
    ProductCategory.SMART_TOILET: 1,
    ProductCategory.VANITY: 2,
    ProductCategory.THERMOSTATIC_SHOWER: 3,
    ProductCategory.FAUCET: 4,
}
CATEGORY_LEGEND_NAME = {
    ProductCategory.SMART_TOILET: "Smart Toilet",
    ProductCategory.VANITY: "Wash Basin / Vanity",
    ProductCategory.THERMOSTATIC_SHOWER: "Thermostatic Shower",
    ProductCategory.FAUCET: "Faucet",
}

# ---------------------------------------------------------------------------
# Camera: azimuth (rotation around the vertical axis -- "left/right") and
# elevation (tilt above the floor -- "up/down") as a standard orthographic
# rotate-then-tilt projection, not a fixed 30-degree isometric constant.
# Still plain trigonometry/matplotlib polygons, no 3D library. Presets are
# kept within a range where the viewer stays in front of the two drawn
# walls (roughly azimuth 10-80 degrees) so the room never flips inside-out.
# ---------------------------------------------------------------------------
ISO_VIEW_PRESETS = {
    "Isometric": {"azimuth": 45.0, "elevation": 35.0},
    "Top": {"azimuth": 45.0, "elevation": 80.0},
    "Left": {"azimuth": 75.0, "elevation": 28.0},
    "Right": {"azimuth": 15.0, "elevation": 28.0},
    "Front": {"azimuth": 45.0, "elevation": 16.0},
}
DEFAULT_ISO_VIEW = "Isometric"


def _make_projector(azimuth_deg: float, elevation_deg: float):
    """Returns a project(x, y, z) -> (sx, sy) function for this camera
    angle. Rotating azimuth swings the view left/right around the room;
    raising elevation tilts it from eye-level ("Front") toward directly
    overhead ("Top")."""
    a = math.radians(azimuth_deg)
    e = math.radians(elevation_deg)
    cos_a, sin_a = math.cos(a), math.sin(a)
    sin_e, cos_e = math.sin(e), math.cos(e)

    def project(x: float, y: float, z: float) -> tuple:
        xr = x * cos_a - y * sin_a
        yr = x * sin_a + y * cos_a
        sx = xr
        sy = yr * sin_e + z * cos_e
        return sx, sy

    return project


def _iso_poly(ax, project, corners_3d, facecolor, edgecolor=ISO_EDGE, lw=0.6, alpha=1.0, zorder=1):
    pts = [project(*c) for c in corners_3d]
    ax.add_patch(patches.Polygon(pts, closed=True, facecolor=facecolor, edgecolor=edgecolor,
                                  linewidth=lw, alpha=alpha, zorder=zorder))


def _iso_box(ax, project, x, y, w, d, h, zorder_base, z0: float = 0.0,
             top=ISO_FIXTURE_TOP, right=ISO_FIXTURE_RIGHT, front=ISO_FIXTURE_FRONT):
    """Draws one solid as a shaded isometric box: top, right (x=x+w plane),
    and front (y=y+d plane) faces, each a plain filled polygon. z0 lets a
    box start above the floor (e.g. a shower head mounted on a column) --
    still just matplotlib polygons, no 3D mesh library."""
    z1 = z0 + h
    _iso_poly(
        ax, project,
        [(x, y, z1), (x + w, y, z1), (x + w, y + d, z1), (x, y + d, z1)],
        top, lw=0.7, zorder=zorder_base + 2,
    )
    _iso_poly(
        ax, project,
        [(x + w, y, z0), (x + w, y + d, z0), (x + w, y + d, z1), (x + w, y, z1)],
        right, lw=0.7, zorder=zorder_base + 1,
    )
    _iso_poly(
        ax, project,
        [(x, y + d, z0), (x + w, y + d, z0), (x + w, y + d, z1), (x, y + d, z1)],
        front, lw=0.7, zorder=zorder_base + 1,
    )


def _iso_toilet(ax, project, x, y, w, d, h, zorder_base):
    """A toilet reads as two stacked forms, not one box: a low, wide bowl
    to the front and a taller, narrower cistern/tank set against the back
    of its own footprint. Still pure isometric boxes -- just two of them,
    composited -- but the stepped silhouette is recognizable as a toilet
    rather than a plain cuboid."""
    bowl_w, bowl_d, bowl_h = w * 0.86, d * 0.78, h * 0.46
    bowl_x, bowl_y = x + (w - bowl_w) / 2, y
    _iso_box(ax, project, bowl_x, bowl_y, bowl_w, bowl_d, bowl_h, zorder_base)

    tank_w, tank_d, tank_h = w * 0.62, d * 0.34, h
    tank_x, tank_y = x + (w - tank_w) / 2, y + d - tank_d
    _iso_box(ax, project, tank_x, tank_y, tank_w, tank_d, tank_h, zorder_base + 4)


def _iso_shower(ax, project, x, y, w, d, h, zorder_base):
    """A shower reads as a low base tray, a slim control column in the back
    corner, and a small head unit floating partway up that column -- again
    three plain isometric boxes composited, no new geometry primitives."""
    tray_h = min(h * 0.06, 70.0)
    _iso_box(ax, project, x, y, w, d, tray_h, zorder_base,
             top=ISO_FIXTURE_RIGHT, right=ISO_FIXTURE_FRONT, front=ISO_FIXTURE_FRONT)

    col_w, col_d, col_h = w * 0.22, d * 0.22, h
    col_x, col_y = x + w - col_w, y + d - col_d
    _iso_box(ax, project, col_x, col_y, col_w, col_d, col_h, zorder_base + 4)

    head_w, head_d, head_h = w * 0.34, d * 0.24, h * 0.07
    head_x, head_y = col_x - head_w * 0.4, col_y - head_d * 0.2
    head_z0 = h * 0.82
    _iso_box(ax, project, head_x, head_y, head_w, head_d, head_h, zorder_base + 8, z0=head_z0)


def _iso_vanity(ax, project, x, y, w, d, h, zorder_base):
    """A wash basin / vanity reads as a wall-mounted counter with a basin
    set into its top, floating above a slim wall bracket -- not a solid
    floor-standing box. This matches the catalogue's own "Floating Vanity"
    products and makes it visually distinct from the toilet and shower
    forms next to it. Still composited plain isometric boxes."""
    counter_h = h * 0.16
    counter_z0 = h * 0.5
    _iso_box(ax, project, x, y, w, d, counter_h, zorder_base, z0=counter_z0)

    basin_w, basin_d, basin_h = w * 0.6, d * 0.55, h * 0.22
    basin_x, basin_y = x + (w - basin_w) / 2, y + d * 0.12
    basin_z0 = counter_z0 + counter_h
    _iso_box(ax, project, basin_x, basin_y, basin_w, basin_d, basin_h, zorder_base + 4, z0=basin_z0)

    bracket_w, bracket_d = w * 0.16, d * 0.16
    bracket_x, bracket_y = x + (w - bracket_w) / 2, y + d - bracket_d
    _iso_box(ax, project, bracket_x, bracket_y, bracket_w, bracket_d, counter_z0, zorder_base - 1)


def _iso_marker(ax, project, x, y, z, number: int, room_scale_mm: float, zorder: int):
    """A small numbered disc at a fixture's floor centroid, keyed to the
    caption legend below the image. Anchored at floor level (not the top
    of the fixture) so its screen position tracks the fixture's spread-out
    x/y position rather than its height -- unlike inline text labels, this
    stays legible from every camera angle, including a near-top-down view
    where floor position is all there is."""
    sx, sy = project(x, y, z)
    radius = room_scale_mm * 0.028
    ax.add_patch(patches.Circle((sx, sy), radius, facecolor=ISO_MARKER_FILL,
                                 edgecolor=ISO_EDGE, linewidth=1.0, zorder=zorder))
    ax.text(sx, sy, str(number), ha="center", va="center", fontsize=9,
             color=ISO_MARKER_TEXT, weight="bold", family="sans-serif", zorder=zorder + 1)


def render_isometric_view(
    bundle: Dict[ProductCategory, Product],
    requirement: RequirementSpec,
    output_path: Optional[Path] = None,
    title: str = "",
    view: str = DEFAULT_ISO_VIEW,
) -> Path:
    """
    Renders a pseudo-3D isometric concept view of the room + selected
    fixtures, using the identical zone_layout_mm() geometry the constraint
    engine validates against. Works for ANY positive dimensions, including
    the best-effort/compact-space scenarios where fixtures may overlap
    their zone -- the picture is illustrative either way, and the app is
    responsible for surfacing the real feasibility warnings alongside it.

    `view` selects the camera angle from ISO_VIEW_PRESETS ("Isometric"
    (default), "Top", "Left", "Right", "Front") -- an unrecognized name
    falls back to the default rather than raising, since this only ever
    changes how the same validated geometry is drawn.
    """
    length_mm = requirement.bathroom.length_ft * MM_PER_FT
    width_mm = requirement.bathroom.width_ft * MM_PER_FT
    zones = zone_layout_mm(requirement.bathroom.length_ft, requirement.bathroom.width_ft)
    room_scale_mm = max(width_mm, length_mm)

    preset = ISO_VIEW_PRESETS.get(view, ISO_VIEW_PRESETS[DEFAULT_ISO_VIEW])
    project = _make_projector(preset["azimuth"], preset["elevation"])

    fig, ax = plt.subplots(figsize=(9, 6.2))
    fig.patch.set_facecolor(ISO_BACKGROUND)
    ax.set_facecolor(ISO_BACKGROUND)

    # Floor
    _iso_poly(ax, project, [(0, 0, 0), (width_mm, 0, 0), (width_mm, length_mm, 0), (0, length_mm, 0)],
              ISO_FLOOR, edgecolor=ISO_EDGE, lw=0.8, zorder=1)

    # Two back walls meeting at the far-left corner -- just enough to read
    # as "a room", left deliberately open on the near/right side so the
    # fixtures inside are never hidden. The view presets are kept within
    # an azimuth range that keeps these walls behind the camera's subject.
    _iso_poly(ax, project, [(0, 0, 0), (0, length_mm, 0), (0, length_mm, ISO_WALL_HEIGHT_MM), (0, 0, ISO_WALL_HEIGHT_MM)],
              ISO_WALL_LEFT, edgecolor=ISO_EDGE, lw=0.5, alpha=0.9, zorder=0)
    _iso_poly(ax, project, [(0, length_mm, 0), (width_mm, length_mm, 0), (width_mm, length_mm, ISO_WALL_HEIGHT_MM), (0, length_mm, ISO_WALL_HEIGHT_MM)],
              ISO_WALL_BACK, edgecolor=ISO_EDGE, lw=0.5, alpha=0.9, zorder=0)

    # Fixtures, back-to-front (largest x+y first) so nearer pieces draw on top.
    drawable = [
        (category, product) for category, product in bundle.items()
        if category != ProductCategory.FAUCET and category in zones
    ]
    drawable.sort(key=lambda item: sum(zones[item[0]][:2]), reverse=True)

    legend_entries = []
    for i, (category, product) in enumerate(drawable):
        zx, zy, zw, zd = zones[category]
        fw, fd = product.dimensions_mm.width, product.dimensions_mm.depth
        fh = min(product.dimensions_mm.height * ISO_HEIGHT_VISUAL_SCALE, ISO_MAX_FIXTURE_HEIGHT_MM)
        fx = zx + (zw - fw) / 2
        fy = zy + (zd - fd) / 2
        zbase = 10 + i * 12

        # Toilet, shower, and vanity each get a composited, more
        # recognizable silhouette (still plain matplotlib polygons -- no
        # mesh/3D library) instead of one plain cuboid.
        if category == ProductCategory.SMART_TOILET:
            _iso_toilet(ax, project, fx, fy, fw, fd, fh, zorder_base=zbase)
        elif category == ProductCategory.THERMOSTATIC_SHOWER:
            _iso_shower(ax, project, fx, fy, fw, fd, fh, zorder_base=zbase)
        elif category == ProductCategory.VANITY:
            _iso_vanity(ax, project, fx, fy, fw, fd, fh, zorder_base=zbase)
        else:
            _iso_box(ax, project, fx, fy, fw, fd, fh, zorder_base=zbase)

        number = CATEGORY_NUMBER.get(category)
        if number is not None:
            _iso_marker(ax, project, fx + fw / 2, fy + fd / 2, 0, number, room_scale_mm,
                        zorder=zbase + 20)
            legend_entries.append((number, CATEGORY_LEGEND_NAME.get(category, category.value)))

    ax.set_aspect("equal")
    ax.axis("off")

    all_corners = [
        project(x, y, z)
        for x in (0, width_mm) for y in (0, length_mm) for z in (0, ISO_WALL_HEIGHT_MM)
    ]
    xs = [p[0] for p in all_corners]
    ys = [p[1] for p in all_corners]
    pad_x = (max(xs) - min(xs)) * 0.08 or width_mm * 0.1
    pad_y = (max(ys) - min(ys)) * 0.10 or length_mm * 0.1
    ax.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax.set_ylim(min(ys) - pad_y, max(ys) + pad_y)

    fig.text(0.5, 0.06, ISO_DISCLAIMER_TITLE, ha="center", va="bottom",
              fontsize=9, color=ISO_EDGE, weight="bold", family="sans-serif")
    fig.text(0.5, 0.03, ISO_DISCLAIMER_SUB, ha="center", va="bottom",
              fontsize=7.5, color=ISO_LABEL, family="sans-serif")
    if legend_entries:
        legend_entries.sort(key=lambda e: e[0])
        legend_text = "    ".join(f"({n}) {name}" for n, name in legend_entries)
        fig.text(0.5, 0.005, legend_text, ha="center", va="bottom",
                  fontsize=7.5, color=ISO_EDGE, family="sans-serif")
    fig.tight_layout(rect=(0, 0.1, 1, 1))

    output_path = output_path or Path("isometric_output.png")
    fig.savefig(output_path, dpi=160, facecolor=ISO_BACKGROUND)
    plt.close(fig)
    return output_path
