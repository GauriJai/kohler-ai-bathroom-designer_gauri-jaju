# KOHLER AI Bathroom Designer & Planner

*"From bathroom constraints to a personalized, space-aware bathroom design."*

A student prototype built for the KOHLER–MIT-WPU AI Research Lab Program
(Track 1: AI Bathroom Designer & Planner).

## Problem

Choosing a bathroom product bundle means juggling physical space, budget,
style, and product compatibility at once — something most shopping tools
don't do together.

## Solution

An AI-assisted design workflow that turns a customer's natural-language (or
form-based) requirements into a product bundle that has been *validated*
against real space and budget constraints, with a conceptual 2D layout, a
water-use estimate, and a plain-language explanation.

## Key innovation

> **Generative AI proposes. Deterministic constraint optimization validates.**

The LLM is only ever allowed to (a) turn natural language into a structured
requirement object, and (b) narrate a bundle that a separate Python engine
already selected and scored. It never invents a price, a dimension, a
water-consumption figure, or a feasibility verdict — and an automatic
numeric-grounding guard rejects any AI-generated explanation that states a
number not traceable to that engine's output (see `docs/architecture.md`).

## Architecture at a glance

```
User input (form or free text)
    -> Requirement extraction (LLM, Pydantic-validated; rule-based fallback)
    -> Product catalog (data/products.json)
    -> Deterministic constraint engine (budget, category, space, clearance)
    -> Exhaustive-search bundle optimizer (transparent weighted scoring)
    -> Sustainability calculator (water-use estimate)
    -> 2D floor-plan renderer
    -> AI explanation generator (grounded, numeric-guard verified)
    -> Streamlit UI
```

Full diagram and rationale: [`docs/architecture.md`](docs/architecture.md).

### AI components
- `src/ai/requirement_parser.py` — OpenAI structured-output extraction of
  the customer's free-text request into a `RequirementSpec`.
- `src/ai/explanation.py` — narrates an already-validated bundle; every
  number in its output is checked against the input data before being shown.
- Both have a fully offline fallback (see "Offline mode" below).

### Deterministic components (the source of truth)
- `src/data/schemas.py` / `src/data/catalog.py` — product data and retrieval.
- `src/optimization/constraints.py` — budget, category-coverage, room-area,
  and simplified 4-zone spatial/clearance checks.
- `src/optimization/optimizer.py` — exhaustive search over every feasible
  category combination, scored by a transparent, configurable weighted
  formula (weights and full logic documented in `docs/methodology.md`).
- `src/sustainability/water_calculator.py` — plain arithmetic water-use
  estimate from user-editable usage assumptions.
- `src/visualization/floorplan.py` — Matplotlib 2D layout, using the exact
  same zone geometry the constraint engine validated against.

### Technology stack
Python 3.11+, Streamlit, Pydantic v2, Matplotlib, OpenAI API (optional),
python-dotenv, pytest.

## Repository structure

```
kohler-ai-bathroom-designer/
|-- app.py                     Streamlit application (entry point)
|-- requirements.txt
|-- .env.example
|-- data/
|   |-- products.json          24-product prototype catalog (synthetic_demo)
|   |-- data_sources.md        Data policy / provenance
|-- src/
|   |-- ai/                    LLM requirement parsing + explanation + prompts
|   |-- data/                  Pydantic schemas + catalog loader
|   |-- optimization/          Constraint engine + optimizer
|   |-- sustainability/        Water-use calculator
|   |-- visualization/         2D floor-plan renderer
|   |-- utils/                 Config / env loading
|-- scripts/generate_catalog.py  One-off catalog generator (not run by the app)
|-- tests/                     pytest suite (see "How to run tests")
|-- docs/                      architecture / methodology / assumptions / limitations
|-- prompts/                   Prompt documentation + PDF
|-- presentation/               4-slide presentation PDF
|-- demo/                      Demo script
```

## Setup instructions

These commands work the same way on Windows, macOS, and Linux — use
`python` (Windows) or `python3` (macOS/Linux) consistently for your platform.

### 1. Create and activate a virtual environment

Windows (PowerShell or cmd):
```
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:
```
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure environment variables (optional)
```
copy .env.example .env        (Windows)
cp .env.example .env          (macOS/Linux)
```
Open `.env` and, **optionally**, set:
```
OPENAI_API_KEY=your-key-here
```
Leave it blank to run entirely in offline mode (see below) — the app never
requires a key to function.

### 4. Run the test suite
```
python -m pytest -q
```
All tests run with no API key and no network access.

### 5. Launch the application
```
python -m streamlit run app.py
```
Streamlit will print a local URL (typically `http://localhost:8501`) — open
it in a browser.

## Demo scenario

The app's default form values are the program's own example:

- Bathroom: 8 ft x 6 ft
- Budget: ₹2,50,000
- Style: Japanese Zen
- Required categories: smart toilet, faucet, thermostatic shower, vanity

Click **"Generate / Regenerate Design"** with these defaults (or paste the
equivalent sentence into the free-text box: *"I have an 8 by 6 feet
bathroom. My budget is ₹2.5 lakh. I want a Japanese Zen style with a smart
toilet, shower, vanity, and a minimalist faucet."*) to see the full workflow.

## Expected workflow

1. **Structured requirement** — shown with a badge indicating whether it
   came from the LLM, the offline rule-based parser, or the manual form.
2. **Three bundle alternatives** (Essential / Balanced / Premium) as tabs,
   each showing: selected products, feasibility result, score breakdown,
   2D floor plan, water-use estimate, and an AI explanation.
3. **Compare bundles** table across all three alternatives.
4. A JSON download of any bundle's full design summary.

If no bundle is feasible (budget too low, room too small, etc.), the app
says so explicitly rather than showing something misleading.

## Offline mode

With no `OPENAI_API_KEY` set (or if any OpenAI call fails for any reason —
missing key, invalid key, rate limit, timeout, network error, or malformed
output), the app automatically falls back to:
- a regex/keyword rule-based requirement parser, and
- a deterministic template explanation generator.

Nothing else in the pipeline (catalog, constraints, optimizer,
sustainability, floor plan) ever depends on an API key. This fallback path
is unit-tested directly (see `tests/test_requirement_parser.py`,
`tests/test_explanation.py`, `tests/test_edge_cases.py`) and is also what
the Streamlit smoke test (`tests/test_app_smoke.py`) exercises.

## Data policy

KOHLER/MIT-WPU did not provide an official product catalogue for this
program. Every product record in `data/products.json` is currently
`data_status: synthetic_demo` — plausible but fabricated data created only
to exercise this prototype's pipeline. **None of it should be read as real
KOHLER pricing or specifications.** Full policy: `data/data_sources.md`.
The schema (`src/data/schemas.py`) enforces this policy structurally: a
record cannot claim `verified_public` status without a `source_url`.

## Limitations

See `docs/limitations.md` for the full list. In short: simplified 4-zone
layout (not free placement), no plumbing/electrical/structural validation,
synthetic catalog, sustainability figures are estimates from user-set
assumptions, and no layout here is construction-ready.

## Future scope

Official KOHLER catalogue integration, real-time pricing/availability,
image/floor-plan understanding, 3D visualization, plumbing-aware layout
validation, and installation/service integration.
