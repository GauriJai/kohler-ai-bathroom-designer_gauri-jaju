"""
Generates presentation/presentation.pdf -- the maximum-4-slide competition
deck. Built directly with reportlab's canvas (not Platypus) for precise,
slide-like layout control. Screenshots embedded on slide 3 are real
captures of the running Streamlit app (see presentation/assets/), taken
with Playwright against a live `streamlit run app.py` instance with no
OpenAI API key set -- i.e. the offline-mode path, proven to work.

Run manually:
    python scripts/generate_prompts_pdf.py   # (prompts PDF, separate script)
    python scripts/generate_presentation_pdf.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "presentation" / "assets"
OUT_PATH = ROOT / "presentation" / "presentation.pdf"

PAGE_W, PAGE_H = landscape(LETTER)  # 792 x 612

NAVY = colors.HexColor("#1F3864")
BLUE = colors.HexColor("#3A6EA5")
LIGHT_BLUE = colors.HexColor("#DDEBF7")
GREEN = colors.HexColor("#5B8C3E")
LIGHT_GREEN = colors.HexColor("#E9F3E3")
GRAY = colors.HexColor("#555555")
LIGHT_GRAY = colors.HexColor("#F4F6F8")
WHITE = colors.white

MARGIN = 34


def para(text, size=11, leading=14.5, color=colors.black, bold=False, align="left"):
    style = ParagraphStyle(
        "p", fontName=("Helvetica-Bold" if bold else "Helvetica"), fontSize=size,
        leading=leading, textColor=color,
        alignment={"left": 0, "center": 1, "right": 2}[align],
    )
    return Paragraph(text, style)


def draw_paragraph(c, text, x, y, w, h, **kwargs):
    """Draws a Paragraph flowable at top-left (x, y-h) .. (x+w, y), returns actual height used."""
    p = para(text, **kwargs)
    _, used_h = p.wrap(w, h)
    p.drawOn(c, x, y - used_h)
    return used_h


def header_band(c, slide_no, title, subtitle=None):
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 78, PAGE_W, 78, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(MARGIN, PAGE_H - 48, title)
    if subtitle:
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.HexColor("#C9D8EA"))
        c.drawString(MARGIN, PAGE_H - 66, subtitle)
    # slide number chip
    c.setFillColor(BLUE)
    c.circle(PAGE_W - 30, PAGE_H - 39, 14, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(PAGE_W - 30, PAGE_H - 43, str(slide_no))


def footer(c, text):
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#999999"))
    c.drawString(MARGIN, 16, text)
    c.drawRightString(PAGE_W - MARGIN, 16, "KOHLER–MIT-WPU AI Research Lab Program — Track 1")


def box(c, x, y, w, h, fill=None, stroke=colors.HexColor("#CCCCCC"), radius=6, line_width=0.7):
    if fill:
        c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(line_width)
    c.roundRect(x, y - h, w, h, radius, stroke=1, fill=1 if fill else 0)


def bullet_block(c, items, x, y, w, size=10.5, leading=14, gap=6, color=colors.black):
    cy = y
    for item in items:
        used = draw_paragraph(c, f"• {item}", x, cy, w, 200, size=size, leading=leading, color=color)
        cy -= used + gap
    return cy


# ===========================================================================
# SLIDE 1 -- Problem + Solution
# ===========================================================================

def slide1(c):
    header_band(c, 1, "KOHLER AI Bathroom Designer & Planner")
    c.setFont("Helvetica-Oblique", 12.5)
    c.setFillColor(GRAY)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 100,
                         '"From bathroom constraints to a personalized, space-aware bathroom design."')

    col_w = (PAGE_W - 2 * MARGIN - 24) / 2
    top_y = PAGE_H - 130
    box_h = 300

    # Problem column
    box(c, MARGIN, top_y, col_w, box_h, fill=colors.HexColor("#FBEFEF"), stroke=colors.HexColor("#E0B4B4"))
    c.setFillColor(colors.HexColor("#8B3A3A"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN + 16, top_y - 26, "The Problem")
    bullet_block(c, [
        "Bathroom product selection is constrained all at once by physical space, "
        "budget, style, and product compatibility.",
        "Customers and sales assistants juggle these manually, with no tool that "
        "validates a bundle against all four together.",
        "Generic AI chat tools can suggest products fluently -- but can't guarantee "
        "the suggestion actually fits the room or the budget.",
    ], MARGIN + 16, top_y - 52, col_w - 32, color=colors.HexColor("#4A2222"))

    # Solution column
    x2 = MARGIN + col_w + 24
    box(c, x2, top_y, col_w, box_h, fill=LIGHT_GREEN, stroke=colors.HexColor("#B8D2A0"))
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x2 + 16, top_y - 26, "The Solution")
    bullet_block(c, [
        "An AI-assisted design workflow that converts natural-language customer "
        "requirements into a validated bathroom product bundle.",
        "Generative AI interprets language and explains results; a deterministic "
        "engine validates space, budget, and feasibility.",
        "Output: a scored product bundle, a conceptual 2D layout, a water-use "
        "estimate, and a plain-language explanation -- grounded, not guessed.",
    ], x2 + 16, top_y - 52, col_w - 32, color=colors.HexColor("#284A1A"))

    # Core principle banner
    by = top_y - box_h - 22
    box(c, MARGIN, by, PAGE_W - 2 * MARGIN, 46, fill=NAVY, stroke=NAVY)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13.5)
    c.drawCentredString(PAGE_W / 2, by - 29,
                         "Generative AI proposes. Deterministic optimization validates.")

    footer(c, "Slide 1 of 4 — Problem & Solution")


# ===========================================================================
# SLIDE 2 -- AI Architecture + Tech Stack
# ===========================================================================

def slide2(c):
    header_band(c, 2, "AI Architecture & Technology Stack")

    top_y = PAGE_H - 100
    left_w = 330
    stages = [
        ("Customer Input", LIGHT_GRAY, colors.HexColor("#999999")),
        ("LLM Requirement Extraction", LIGHT_BLUE, BLUE),
        ("Structured Requirements (Pydantic)", LIGHT_GRAY, colors.HexColor("#999999")),
        ("Product Retrieval", LIGHT_GREEN, GREEN),
        ("Deterministic Constraint Engine", LIGHT_GREEN, GREEN),
        ("Optimization (weighted scoring)", LIGHT_GREEN, GREEN),
        ("Sustainability Analysis", LIGHT_GREEN, GREEN),
        ("2D Layout Generation", LIGHT_GREEN, GREEN),
        ("Grounded AI Explanation", LIGHT_BLUE, BLUE),
    ]
    box_h = 30
    gap = 6
    cy = top_y
    cx = MARGIN
    for i, (label, fill, edge) in enumerate(stages):
        box(c, cx, cy, left_w, box_h, fill=fill, stroke=edge, radius=5)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawCentredString(cx + left_w / 2, cy - box_h / 2 - 3.5, label)
        if i < len(stages) - 1:
            arrow_y = cy - box_h
            c.setFillColor(colors.HexColor("#888888"))
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(cx + left_w / 2, arrow_y - 8, "↓")
        cy -= box_h + gap

    legend_y = cy - 6
    c.setFillColor(BLUE)
    c.rect(MARGIN, legend_y - 10, 10, 10, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8.5)
    c.drawString(MARGIN + 14, legend_y - 9, "AI-driven")
    c.setFillColor(GREEN)
    c.rect(MARGIN + 80, legend_y - 10, 10, 10, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.drawString(MARGIN + 94, legend_y - 9, "Deterministic (source of truth)")

    # Right column
    right_x = MARGIN + left_w + 26
    right_w = PAGE_W - MARGIN - right_x

    box(c, right_x, top_y, right_w, 118, fill=LIGHT_BLUE, stroke=BLUE)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_x + 14, top_y - 22, "AI is responsible for:")
    bullet_block(c, [
        "Understanding natural-language requirements",
        "Extracting structured preferences (Pydantic-validated)",
        "Generating grounded, plain-language explanations",
    ], right_x + 14, top_y - 44, right_w - 28, size=9.7, leading=12.5, gap=4)

    y2 = top_y - 130
    box(c, right_x, y2, right_w, 118, fill=LIGHT_GREEN, stroke=GREEN)
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_x + 14, y2 - 22, "Deterministic engine is responsible for:")
    bullet_block(c, [
        "Prices, dimensions, and physical fit",
        "Budget, category, and clearance constraints",
        "Bundle optimization and sustainability calculations",
    ], right_x + 14, y2 - 44, right_w - 28, size=9.7, leading=12.5, gap=4)

    y3 = y2 - 130
    box(c, right_x, y3, right_w, 128, fill=WHITE, stroke=colors.HexColor("#CCCCCC"))
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_x + 14, y3 - 22, "Tech stack")
    draw_paragraph(
        c,
        "Python · Streamlit · Pydantic · OpenAI API (structured outputs) · "
        "Matplotlib · python-dotenv · pytest · JSON product catalog",
        right_x + 14, y3 - 42, right_w - 28, 90, size=10, leading=14,
    )

    footer(c, "Slide 2 of 4 — AI Architecture & Technology Stack")


# ===========================================================================
# SLIDE 3 -- Demo + Innovation
# ===========================================================================

def slide3(c):
    header_band(c, 3, "Live Prototype: Demo & Innovation")

    top_y = PAGE_H - 98
    left_w = 250

    box(c, MARGIN, top_y, left_w, 150, fill=LIGHT_GRAY, stroke=colors.HexColor("#CCCCCC"))
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN + 14, top_y - 22, "Demo scenario")
    demo_lines = [
        "Bathroom: 8 × 6 ft",
        "Budget: Rs. 2,50,000",
        "Style: Japanese Zen",
        "Required: smart toilet, faucet,",
        "thermostatic shower, vanity",
    ]
    dy = top_y - 44
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    for line in demo_lines:
        c.drawString(MARGIN + 14, dy, line)
        dy -= 15.5

    y2 = top_y - 168
    box(c, MARGIN, y2, left_w, 150, fill=LIGHT_BLUE, stroke=BLUE)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN + 14, y2 - 22, "Innovation")
    draw_paragraph(
        c, "“Generative AI proposes.<br/>Deterministic optimization validates.”",
        MARGIN + 14, y2 - 46, left_w - 28, 60, size=11.5, leading=15, bold=True, color=NAVY,
    )
    draw_paragraph(
        c,
        "The system never lets the LLM invent feasibility, dimensions, or pricing -- "
        "every claim traces back to deterministic Python code.",
        MARGIN + 14, y2 - 92, left_w - 28, 60, size=9, leading=12, color=colors.HexColor("#26456B"),
    )

    # Real screenshots on the right
    img_x = MARGIN + left_w + 20
    img_w = PAGE_W - MARGIN - img_x

    metrics_img = ImageReader(str(ASSETS / "balanced_metrics.png"))
    iw, ih = metrics_img.getSize()
    top_img_h = 210
    # Bug fix: previously the bounding box used for drawImage's height was the
    # image's own width-matched aspect height (img_w * ih / iw, ~269pt) rather
    # than top_img_h (210pt) -- taller than the box actually reserved for it,
    # so the screenshot spilled upward past top_y and into the header band.
    # Passing the same (img_w, top_img_h) box to both rect() and drawImage()
    # lets preserveAspectRatio scale the image to fit entirely within the
    # reserved box (constrained by height here), so it can never overlap the
    # header above it.
    c.saveState()
    c.setStrokeColor(colors.HexColor("#CCCCCC"))
    c.setLineWidth(0.7)
    c.rect(img_x, top_y - top_img_h, img_w, top_img_h, stroke=1, fill=0)
    c.drawImage(metrics_img, img_x, top_y - top_img_h, width=img_w, height=top_img_h,
                preserveAspectRatio=True, anchor='n', mask='auto')
    c.restoreState()
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(GRAY)
    c.drawString(img_x, top_y - top_img_h - 11,
                 "Actual Streamlit output — Balanced Bundle (offline mode, no API key)")

    plan_img = ImageReader(str(ASSETS / "balanced_floorplan.png"))
    piw, pih = plan_img.getSize()
    plan_h = 128
    plan_y = top_y - top_img_h - 22
    c.saveState()
    c.setStrokeColor(colors.HexColor("#CCCCCC"))
    c.rect(img_x, plan_y - plan_h, img_w, plan_h, stroke=1, fill=0)
    c.drawImage(plan_img, img_x, plan_y - plan_h, width=img_w, height=plan_h,
                preserveAspectRatio=True, anchor='n', mask='auto')
    c.restoreState()
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(img_x, plan_y - plan_h - 11, "Real generated 2D floor plan for this bundle")

    footer(c, "Slide 3 of 4 — Demo & Innovation")


# ===========================================================================
# SLIDE 4 -- Impact + Future Scope
# ===========================================================================

def slide4(c):
    header_band(c, 4, "Business Impact, Sustainability & Future Scope")

    top_y = PAGE_H - 100
    col_w = (PAGE_W - 2 * MARGIN - 2 * 20) / 3
    box_h = 300

    cols = [
        ("Business Value", LIGHT_GRAY, colors.HexColor("#555555"), [
            "Personalized customer experience at scale",
            "Faster product discovery for sales teams",
            "Space-aware recommendations, not guesswork",
            "Transparent trade-offs (Essential/Balanced/Premium)",
            "Scalable digital design assistance",
        ]),
        ("Sustainability", LIGHT_GREEN, GREEN, [
            "Estimated annual water-use analysis per bundle",
            "Usage-based comparison vs. a baseline fixture",
            "Water-efficiency is a scored optimization input",
            "Every figure labeled as an estimate, never a claim",
            "Aligned with KOHLER's water-conservation focus",
        ]),
        ("Future Scope", LIGHT_BLUE, BLUE, [
            "Official KOHLER catalogue integration",
            "Real-time product availability & pricing",
            "Image / floor-plan understanding",
            "3D bathroom visualization",
            "Plumbing-aware layout validation",
            "Installation/service integration",
        ]),
    ]

    for i, (title, fill, edge, items) in enumerate(cols):
        x = MARGIN + i * (col_w + 20)
        box(c, x, top_y, col_w, box_h, fill=fill, stroke=edge)
        c.setFillColor(edge)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x + 14, top_y - 24, title)
        bullet_block(c, items, x + 14, top_y - 48, col_w - 28, size=9.3, leading=12.5, gap=5,
                     color=colors.HexColor("#222222"))

    by = top_y - box_h - 22
    box(c, MARGIN, by, PAGE_W - 2 * MARGIN, 50, fill=NAVY, stroke=NAVY)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawCentredString(PAGE_W / 2, by - 22,
                         "“AI doesn't replace bathroom design expertise —")
    c.setFont("Helvetica-Bold", 12.5)
    c.drawCentredString(PAGE_W / 2, by - 38, "it makes personalized design scalable.”")

    footer(c, "Slide 4 of 4 — Impact & Future Scope")


def build():
    c = canvas.Canvas(str(OUT_PATH), pagesize=landscape(LETTER))
    c.setTitle("KOHLER AI Bathroom Designer & Planner - Presentation")

    for slide_fn in (slide1, slide2, slide3, slide4):
        slide_fn(c)
        c.showPage()

    c.save()
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    build()
