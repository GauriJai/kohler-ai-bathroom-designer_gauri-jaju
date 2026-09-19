"""
AI design-explanation generator.

CRITICAL DESIGN RULE (see prompts/system_prompt for the enforced version):
the LLM here is a narrator, never a decision-maker. It receives the
already-validated, already-scored bundle as JSON and may only explain it in
words. To make that rule enforceable rather than just requested, every
number the LLM's output contains is checked against the set of numbers that
were actually in its input (`_extract_numbers` + `_verify_numbers_grounded`).
If the model states a number that isn't traceable to the input, its output
is REJECTED and the deterministic template explanation is used instead --
the same fallback path used when there's no API key at all.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from src.ai.prompts import EXPLANATION_SYSTEM_PROMPT

DEFAULT_MODEL = os.environ.get("OPENAI_EXPLANATION_MODEL", "gpt-4o-mini")


@dataclass
class ExplanationResult:
    text: str
    method: Literal["llm", "template_fallback"]
    notes: List[str] = field(default_factory=list)


def _get_openai_client():
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Numeric grounding guard
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _collect_allowed_numbers(bundle_payload: dict) -> set:
    """
    Walks the bundle/validation/water-estimate JSON and gathers every number
    that legitimately appears in it, plus common rounded/derived forms
    (nearest lakh, nearest thousand, percentages already given) so an LLM
    that rounds "₹237,500" to "about ₹2.4 lakh" isn't falsely flagged.
    """
    raw_numbers: set = set()

    def walk(value):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            raw_numbers.add(float(value))
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(bundle_payload)

    allowed: set = set()
    for n in raw_numbers:
        allowed.add(round(n, 2))
        allowed.add(round(n))
        allowed.add(round(n / 1000))          # thousands, e.g. "72 thousand"
        allowed.add(round(n / 100000, 2))     # lakhs, e.g. "2.4 lakh"
        allowed.add(round(n / 100000))
        allowed.add(round(n * 100, 2))        # a 0-1 score expressed as a percentage
        allowed.add(round(n * 100))
    # small integers that show up as counts/labels are harmless either way
    allowed.update({0, 1, 2, 3, 4, 5})
    return allowed


def _verify_numbers_grounded(text: str, allowed_numbers: set, tolerance: float = 0.03) -> List[str]:
    """Returns a list of numeric substrings in `text` that could not be matched
    to anything in `allowed_numbers` (within a small relative tolerance)."""
    unmatched = []
    for match in _NUMBER_RE.findall(text):
        cleaned = match.replace(",", "")
        try:
            value = float(cleaned)
        except ValueError:
            continue
        if any(abs(value - a) <= max(1.0, tolerance * max(value, a)) for a in allowed_numbers):
            continue
        unmatched.append(match)
    return unmatched


# ---------------------------------------------------------------------------
# Template fallback (also the offline/mock path)
# ---------------------------------------------------------------------------

def generate_template_explanation(bundle_payload: dict) -> str:
    products = bundle_payload.get("products", {})
    label = bundle_payload.get("label", "This bundle")
    total = bundle_payload.get("total_cost_inr", 0)
    remaining = bundle_payload.get("remaining_budget_inr", 0)
    scores = bundle_payload.get("scores", {})
    validation = bundle_payload.get("validation", {})

    product_lines = ", ".join(
        f"{cat.replace('_', ' ')} ({p.get('product_name', 'unknown')})"
        for cat, p in products.items()
    )
    style_pct = round(scores.get("style_match", 0) * 100)
    water_pct = round(scores.get("water_efficiency", 0) * 100)

    parts = [
        f"{label} combines {product_lines} for a total of ₹{total:,.0f}, "
        f"leaving ₹{remaining:,.0f} of your stated budget unused."
    ]
    parts.append(
        f"About {style_pct}% of the selected products are tagged for your requested "
        f"style, and the products score {water_pct}% on the prototype's water-efficiency scale."
    )
    if validation.get("violations"):
        parts.append(
            "Note: this combination did not pass all feasibility checks -- "
            + "; ".join(validation["violations"])
        )
    else:
        parts.append(
            "This combination passed the prototype's budget, category, and simplified "
            "space checks, but is not a construction-ready plan."
        )
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def generate_explanation(
    bundle_payload: dict, client=None, prefer_llm: bool = True, model: str = DEFAULT_MODEL
) -> ExplanationResult:
    notes: List[str] = []

    if prefer_llm:
        try:
            client = client or _get_openai_client()
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
                    {"role": "user", "content": str(bundle_payload)},
                ],
                temperature=0.4,
            )
            text = completion.choices[0].message.content
            if not text:
                raise ValueError("LLM returned empty explanation")

            allowed = _collect_allowed_numbers(bundle_payload)
            unmatched = _verify_numbers_grounded(text, allowed)
            if unmatched:
                notes.append(
                    f"LLM explanation rejected by the numeric-grounding guard "
                    f"(unverifiable numbers: {unmatched}); used the template explanation instead."
                )
            else:
                return ExplanationResult(text=text, method="llm", notes=notes)
        except Exception as exc:  # noqa: BLE001 -- any LLM failure falls back
            notes.append(
                f"LLM explanation unavailable ({type(exc).__name__}: {exc}); "
                "used the template explanation instead."
            )

    return ExplanationResult(
        text=generate_template_explanation(bundle_payload), method="template_fallback", notes=notes
    )
