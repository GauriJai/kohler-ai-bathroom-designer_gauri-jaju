"""
Generates prompts/prompts_documentation.pdf from the prompt documentation
already written in prompts/*.md and src/ai/prompts.py. Not part of the
runtime app -- run manually:

    python scripts/generate_prompts_pdf.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "prompts" / "prompts_documentation.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("TitlePage", parent=styles["Title"], fontSize=26, leading=32, spaceAfter=8))
styles.add(ParagraphStyle("SubtitlePage", parent=styles["Normal"], fontSize=14, alignment=TA_CENTER,
                          textColor=colors.HexColor("#3A6EA5"), spaceAfter=6))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#1F3864"),
                          spaceBefore=18, spaceAfter=8))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, textColor=colors.HexColor("#3A6EA5"),
                          spaceBefore=12, spaceAfter=6))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14.5, spaceAfter=8))
styles.add(ParagraphStyle("BulletItem", parent=styles["Normal"], fontSize=10, leading=14.5, spaceAfter=4,
                          leftIndent=14, bulletIndent=4))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8.5, textColor=colors.grey,
                          spaceAfter=10))
code_style = ParagraphStyle("Code", fontName="Courier", fontSize=8.3, leading=11,
                             backColor=colors.HexColor("#F4F6F8"), borderPadding=6)
cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8.5, leading=11)
header_cell_style = ParagraphStyle("HeaderCell", parent=cell_style, textColor=colors.white,
                                    fontName="Helvetica-Bold")


def cell(text, header=False):
    return Paragraph(text, header_cell_style if header else cell_style)


def wrapped_table(rows, col_widths, style):
    wrapped_rows = [
        [cell(value, header=(row_idx == 0)) for value in row]
        for row_idx, row in enumerate(rows)
    ]
    return Table(wrapped_rows, colWidths=col_widths, style=style)

DISCLAIMER = (
    "This document describes a student prototype built for the KOHLER–MIT-WPU AI "
    "Research Lab Program. It does not claim access to any official KOHLER internal "
    "system, database, or documentation. All product data referenced in examples is "
    "synthetic/demo data created for this prototype -- see data/data_sources.md."
)


def code_block(text: str):
    return Preformatted(text, code_style)


def h1(text):
    return Paragraph(text, styles["H1"])


def h2(text):
    return Paragraph(text, styles["H2"])


def body(text):
    return Paragraph(text, styles["Body"])


def bullets(items):
    return [Paragraph(f"• {i}", styles["BulletItem"]) for i in items]


story = []

# ---------------------------------------------------------------------------
# Title page
# ---------------------------------------------------------------------------
story.append(Spacer(1, 1.6 * inch))
story.append(Paragraph("KOHLER AI Bathroom Designer &amp; Planner", styles["TitlePage"]))
story.append(Paragraph("Prompts Documentation", styles["SubtitlePage"]))
story.append(Spacer(1, 0.25 * inch))
story.append(Paragraph('"From bathroom constraints to a personalized, space-aware bathroom design."',
                        ParagraphStyle("tag", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10.5,
                                       textColor=colors.grey)))
story.append(Spacer(1, 1.0 * inch))
story.append(HRFlowable(width="80%", thickness=0.6, color=colors.HexColor("#BBBBBB"), hAlign="CENTER"))
story.append(Spacer(1, 0.2 * inch))
story.append(Paragraph(DISCLAIMER, ParagraphStyle("disclaimer", parent=styles["Normal"], fontSize=9,
                                                    alignment=TA_CENTER, textColor=colors.HexColor("#444444"))))
story.append(Spacer(1, 0.6 * inch))
story.append(Paragraph("KOHLER–MIT-WPU AI Research Lab Program — Track 1", styles["Caption"]))
story.append(PageBreak())

# ---------------------------------------------------------------------------
# 1. AI architecture
# ---------------------------------------------------------------------------
story.append(h1("1. AI Architecture"))
story.append(body(
    "Core principle: <b>Generative AI proposes. Deterministic constraint optimization "
    "validates.</b> The application uses exactly two LLM calls, each scoped to one job, "
    "and a deterministic Python engine (constraint checks, optimizer, sustainability "
    "calculator, floor-plan renderer) that is the sole source of truth for prices, "
    "dimensions, feasibility, and scores."
))
story.append(wrapped_table(
    [["Stage", "Driven by"],
     ["Requirement extraction", "AI (LLM), with a rule-based fallback"],
     ["Product retrieval", "Deterministic (catalog filters)"],
     ["Constraint validation", "Deterministic (budget / category / space / clearance)"],
     ["Bundle optimization", "Deterministic (exhaustive search + weighted scoring)"],
     ["Sustainability analysis", "Deterministic (arithmetic on user-set assumptions)"],
     ["2D layout generation", "Deterministic (same zone geometry as validation)"],
     ["Explanation generation", "AI (LLM), grounded by a numeric-verification guard, with a template fallback"]],
    [2.3 * inch, 3.7 * inch],
    TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]),
))
story.append(Spacer(1, 8))
story.append(body(
    "The LLM cannot override the deterministic engine: its requirement-extraction "
    "output is re-validated by the same Pydantic schema the manual form uses, and its "
    "explanation output only ever narrates a bundle that has already been scored and "
    "validated -- there is no code path where LLM output feeds back into price, "
    "dimension, or feasibility logic. Full detail: docs/architecture.md."
))

# ---------------------------------------------------------------------------
# 2. System instructions
# ---------------------------------------------------------------------------
story.append(h1("2. System Instructions"))
story.append(body(
    "There are exactly two system prompts in this application, each narrowly scoped to "
    "one job, defined in <font face='Courier'>src/ai/prompts.py</font>. There is no "
    "general-purpose “master” system prompt -- see prompts/system_prompt.md for the "
    "rationale (smaller blast radius, mismatched grounding needs, different output types)."
))
story.extend(bullets([
    "<b>REQUIREMENT_EXTRACTION_SYSTEM_PROMPT</b> — used by src/ai/requirement_parser.py",
    "<b>EXPLANATION_SYSTEM_PROMPT</b> — used by src/ai/explanation.py",
]))

# ---------------------------------------------------------------------------
# 3. Requirement extraction prompt
# ---------------------------------------------------------------------------
story.append(h1("3. Requirement Extraction Prompt"))
story.append(h2("Purpose"))
story.append(body("Converts the customer's free-text bathroom description into structured fields, "
                   "without designing, selecting products, or judging feasibility."))
story.append(h2("Full text"))
story.append(code_block(
"""You are a requirement-extraction assistant for a bathroom-design prototype.

Your ONLY job is to convert the user's natural-language description of their
desired bathroom into the structured fields you were given a schema for.
You are NOT designing the bathroom, NOT selecting products, and NOT deciding
whether anything is feasible -- a separate deterministic system does that.

Rules:
- Extract only what the user actually said or clearly implied. Do not invent
  a budget, dimensions, or style the user did not mention.
- If the user gives dimensions in a different unit (e.g. meters), convert to
  feet. If they give budget in lakhs (1 lakh = 100,000) or crores, convert
  to plain INR.
- required_categories must only contain: smart_toilet, faucet,
  thermostatic_shower, vanity. Map synonyms sensibly, but only include a
  category the user actually asked for or is clearly required by context.
- style must be exactly one of: minimalist_modern, classic_luxury,
  japanese_zen, contemporary. Pick the closest match; default to
  contemporary if truly unclear.
- Never invent product names, prices, or specifications -- you have no
  access to the product catalog and must not reference specific products."""
))
story.append(h2("Inputs / Outputs"))
story.append(body("<b>Input:</b> the system prompt (fixed) + the customer's raw free-text description. "
                   "<b>Output:</b> a Pydantic <font face='Courier'>_ExtractedRequirement</font> object, "
                   "produced via OpenAI's structured-output feature "
                   "(<font face='Courier'>client.chat.completions.parse(response_format=_ExtractedRequirement)</font>), "
                   "then re-validated into the application's real <font face='Courier'>RequirementSpec</font>."))

# ---------------------------------------------------------------------------
# 4. Explanation-generation prompt
# ---------------------------------------------------------------------------
story.append(h1("4. Explanation-Generation Prompt"))
story.append(h2("Purpose"))
story.append(body("Narrates an already-selected, already-scored, already-validated product bundle "
                   "in plain, customer-facing language -- it never decides anything, only explains."))
story.append(h2("Full text"))
story.append(code_block(
"""You are a design-explanation assistant for a bathroom-design prototype.

You will be given a JSON object describing a bundle of products that has
ALREADY been selected and validated by a separate deterministic system: the
prices, dimensions, feasibility result, and scores are all final and
correct. Your ONLY job is to explain, in plain and encouraging language,
why this bundle suits the customer's stated requirements.

Hard rules -- violating any of these makes your output unusable:
1. Do not state any price, dimension, water-consumption value, or score
   that is not already present in the JSON you were given. Round for
   readability only, never invent or adjust a figure.
2. Do not claim the layout is construction-ready or that measurements are
   exact -- always defer final verification to a qualified professional.
3. Do not claim any certification, official KOHLER endorsement, or
   sustainability certification not stated in the input data.
4. If the bundle has validation violations or warnings, mention them.
5. Keep it concise: 3-5 short sentences, warm and professional in tone."""
))
story.append(h2("Inputs / Outputs"))
story.append(body("<b>Input:</b> the system prompt (fixed) + the bundle's scored JSON payload "
                   "(<font face='Courier'>ScoredBundle.as_dict()</font>). <b>Output:</b> 3–5 sentences "
                   "of prose via a plain <font face='Courier'>chat.completions.create()</font> call "
                   "(no structured-output schema, since the target is text, not data)."))

# ---------------------------------------------------------------------------
# 5. Structured output schema
# ---------------------------------------------------------------------------
story.append(h1("5. Structured Output Schema"))
story.append(body("Used only by the requirement-extraction call. Deliberately a separate model from "
                   "the domain <font face='Courier'>RequirementSpec</font> (plain Literals instead of "
                   "Enums) for maximum compatibility with OpenAI's structured-output feature:"))
story.append(code_block(
"""class _ExtractedBathroom(BaseModel):
    length_ft: float
    width_ft: float
    ceiling_height_ft: Optional[float] = None

class _ExtractedRequirement(BaseModel):
    bathroom: _ExtractedBathroom
    budget_inr: float
    style: Literal["minimalist_modern", "classic_luxury",
                   "japanese_zen", "contemporary"]
    required_categories: List[Literal["smart_toilet", "faucet",
                   "thermostatic_shower", "vanity"]]
    priorities: List[str] = []
    water_saving_preference: bool = False
    accessibility_preference: bool = False"""
))

# ---------------------------------------------------------------------------
# 6. Grounding rules
# ---------------------------------------------------------------------------
story.append(h1("6. Grounding Rules"))
story.extend(bullets([
    "<b>Extraction:</b> two independent layers -- (1) the OpenAI structured-output "
    "feature enforces the schema above at the API level; (2) the parsed result is "
    "re-validated by constructing the real RequirementSpec, which applies its own "
    "validators (e.g. required_categories must be non-empty). A schema-valid but "
    "semantically empty result is caught at layer 2.",
    "<b>Explanation:</b> grounded post-hoc by the numeric-verification guard "
    "(section 7) rather than by a schema, since the output is free text.",
    "<b>Both:</b> a model refusal is always treated as a failure, never as a "
    "valid-but-empty result.",
]))

# ---------------------------------------------------------------------------
# 7. Numerical grounding / validation rules
# ---------------------------------------------------------------------------
story.append(h1("7. Numerical Grounding / Validation Rules"))
story.append(body("Implemented in <font face='Courier'>src/ai/explanation.py</font>:"))
story.extend(bullets([
    "<font face='Courier'>_collect_allowed_numbers(payload)</font> walks the entire "
    "input JSON and, for every number, adds it plus derived forms to an “allowed” "
    "set: rounded to 2dp, rounded to an integer, in thousands, in lakhs (raw and 2dp), "
    "and as a percentage (for 0–1 scores).",
    "<font face='Courier'>_verify_numbers_grounded(text, allowed, tolerance=0.03)</font> "
    "extracts every numeric substring from the model's output and checks it against "
    "that set within a small relative tolerance.",
    "If <b>any</b> number in the response can't be matched, the entire response is "
    "discarded (not edited) and the deterministic template is used instead.",
    "Verified directly by tests, including a fabricated-number case that is confirmed "
    "to actually get rejected -- not just designed to be.",
]))

# ---------------------------------------------------------------------------
# 8. Offline fallback
# ---------------------------------------------------------------------------
story.append(h1("8. Offline Fallback"))
story.append(wrapped_table(
    [["Component", "Fallback", "Trigger"],
     ["Requirement extraction", "Regex/keyword rule-based parser", "Any exception: no key, invalid key, rate limit, timeout, network error, malformed/invalid output"],
     ["Explanation", "Deterministic string-template summary", "Any exception, OR a fabricated/unverifiable number caught by the grounding guard"]],
    [1.5 * inch, 1.9 * inch, 2.6 * inch],
    TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]),
))
story.append(Spacer(1, 8))
story.append(body("Both fallbacks run with zero network access and zero API key, and the entire "
                   "Streamlit app is smoke-tested end to end with no OPENAI_API_KEY set -- the "
                   "“must work without a key” requirement is a verified, tested property."))

# ---------------------------------------------------------------------------
# 9. Example input/output
# ---------------------------------------------------------------------------
story.append(h1("9. Example Input / Output"))
story.append(h2("Requirement extraction"))
story.append(body("Input (the brief's own demo sentence):"))
story.append(code_block(
'I have an 8 by 6 feet bathroom. My budget is Rs.2.5 lakh. I want a Japanese\n'
'Zen style with a smart toilet, shower, vanity, and a minimalist faucet.'
))
story.append(body("Output (structured -- verified identical whether produced by the LLM path or the "
                   "rule-based fallback, for this exact sentence):"))
story.append(code_block(
"""{
  "bathroom": {"length_ft": 8, "width_ft": 6, "ceiling_height_ft": null},
  "budget_inr": 250000,
  "style": "japanese_zen",
  "required_categories": ["smart_toilet", "faucet",
                          "thermostatic_shower", "vanity"],
  "priorities": [],
  "water_saving_preference": false,
  "accessibility_preference": false
}"""
))
story.append(h2("Explanation (template fallback, reproduced from an actual test fixture)"))
story.append(code_block(
"""Balanced Bundle combines smart_toilet (Prototype Smart Comfort Toilet with
Bidet), faucet (Prototype Zen Minimal Faucet), thermostatic_shower
(Prototype Premium Rain Shower Suite), vanity (Prototype Zen Floating
Vanity) for a total of Rs.237,500, leaving Rs.12,500 of your stated budget
unused. About 75% of the selected products are tagged for your requested
style, and the products score 33% on the prototype's water-efficiency
scale. This combination passed the prototype's budget, category, and
simplified space checks, but is not a construction-ready plan."""
))

# ---------------------------------------------------------------------------
# 10. Prompt safety and hallucination controls
# ---------------------------------------------------------------------------
story.append(h1("10. Prompt Safety and Hallucination Controls"))
story.extend(bullets([
    "Explicit “you are NOT deciding feasibility / selecting products” framing in the "
    "extraction prompt.",
    "Explicit “never invent a number not in the JSON you were given” rule in the "
    "explanation prompt, enforced in code by the numeric-grounding guard, not just by "
    "instruction.",
    "Two-layer schema validation on extraction output (structured-output schema, then "
    "RequirementSpec's own validators).",
    "A model refusal is treated as a failure and triggers the same fallback as any "
    "other error.",
    "Every fallback path is unit-tested without network access; the app's own "
    "end-to-end smoke test runs with no API key set.",
    "The application never claims access to an official KOHLER internal database, "
    "system, or documentation -- all example data in this document is clearly labeled "
    "synthetic/demo data from this prototype's own catalog.",
]))

story.append(Spacer(1, 14))
story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Source of truth for everything in this document: src/ai/prompts.py, "
    "src/ai/requirement_parser.py, src/ai/explanation.py, and prompts/*.md in the "
    "project repository.", styles["Caption"]
))


def build():
    doc = SimpleDocTemplate(
        str(OUT_PATH), pagesize=LETTER,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        title="KOHLER AI Bathroom Designer & Planner - Prompts Documentation",
    )
    doc.build(story)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    build()
