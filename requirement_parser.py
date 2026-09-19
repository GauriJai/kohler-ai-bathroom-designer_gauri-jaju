"""
Natural-language -> structured RequirementSpec.

Two independent paths, both validated by the SAME Pydantic schema
(src.data.schemas.RequirementSpec) before anything downstream ever sees
the result:

1. LLM path (OpenAI structured output) -- used when an API key is present
   and the call succeeds.
2. Rule-based fallback (regex/keyword) -- used automatically whenever the
   LLM path is unavailable or fails for ANY reason (no key, invalid key,
   rate limit, timeout, network error, malformed response). This keeps the
   application fully functional with zero API key, by design (see the
   Phase-1 plan's "offline/mock mode" requirement).

The LLM is only ever allowed to fill in this schema -- it never sees or
touches the product catalog, prices, or feasibility logic.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import List, Literal, Optional

from pydantic import BaseModel, ValidationError

from src.ai.prompts import REQUIREMENT_EXTRACTION_SYSTEM_PROMPT
from src.data.schemas import AestheticStyle, ProductCategory, RequirementSpec

DEFAULT_MODEL = os.environ.get("OPENAI_REQUIREMENT_MODEL", "gpt-4o-mini")


class RequirementExtractionError(Exception):
    """Raised only by the rule-based fallback when it truly cannot parse the input."""


@dataclass
class ExtractionResult:
    requirement: RequirementSpec
    method: Literal["llm", "rule_based_fallback"]
    notes: List[str]


# ---------------------------------------------------------------------------
# Schema the LLM is asked to fill in. Deliberately separate from
# RequirementSpec (plain str/float/bool instead of Enums) for maximum
# compatibility with the OpenAI structured-output feature; the result is
# re-validated against the real RequirementSpec afterwards.
# ---------------------------------------------------------------------------

class _ExtractedBathroom(BaseModel):
    length_ft: float
    width_ft: float
    ceiling_height_ft: Optional[float] = None


class _ExtractedRequirement(BaseModel):
    bathroom: _ExtractedBathroom
    budget_inr: float
    style: Literal["minimalist_modern", "classic_luxury", "japanese_zen", "contemporary"]
    required_categories: List[Literal["smart_toilet", "faucet", "thermostatic_shower", "vanity"]]
    priorities: List[str] = []
    water_saving_preference: bool = False
    accessibility_preference: bool = False


def _to_requirement_spec(extracted: _ExtractedRequirement) -> RequirementSpec:
    return RequirementSpec(**extracted.model_dump())


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------

def _get_openai_client():
    from openai import OpenAI  # imported lazily so the whole app doesn't hard-depend on it

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def parse_requirement_with_llm(
    user_text: str, client=None, model: str = DEFAULT_MODEL
) -> RequirementSpec:
    """
    Raises on ANY failure (missing key, auth error, rate limit, timeout,
    malformed output). Callers must catch broadly and fall back -- this
    function intentionally does not swallow errors itself, so the caller
    can decide how to report them.
    """
    client = client or _get_openai_client()

    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": REQUIREMENT_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        response_format=_ExtractedRequirement,
    )
    message = completion.choices[0].message
    if getattr(message, "refusal", None):
        raise RequirementExtractionError(f"Model refused: {message.refusal}")
    parsed = message.parsed
    if parsed is None:
        raise RequirementExtractionError("LLM returned no parseable structured output")
    return _to_requirement_spec(parsed)


# ---------------------------------------------------------------------------
# Rule-based fallback (regex/keyword). No network, no dependencies.
# ---------------------------------------------------------------------------

_STYLE_KEYWORDS = {
    "japanese_zen": ["japanese zen", "japanese-zen", "zen", "japanese"],
    "classic_luxury": ["classic luxury", "classic", "luxury", "heritage", "traditional"],
    "minimalist_modern": ["minimalist modern", "minimalist", "minimal"],
    "contemporary": ["contemporary", "modern"],
}

_CATEGORY_KEYWORDS = {
    "smart_toilet": ["smart toilet", "toilet", "wc", "commode"],
    "faucet": ["faucet", "tap"],
    "thermostatic_shower": ["thermostatic shower", "shower"],
    "vanity": ["vanity", "basin", "sink", "washbasin"],
}

_LAKH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*lakh", re.IGNORECASE)
_CRORE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*crore", re.IGNORECASE)
_PLAIN_BUDGET_RE = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)
_BUDGET_KEYWORD_RE = re.compile(
    r"budget\s*(?:of|is|:)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE
)
_DIMENSIONS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:x|by|\*)\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|foot)?", re.IGNORECASE
)


def _extract_budget_inr(text: str) -> Optional[float]:
    m = _LAKH_RE.search(text)
    if m:
        return float(m.group(1)) * 100_000
    m = _CRORE_RE.search(text)
    if m:
        return float(m.group(1)) * 10_000_000
    m = _PLAIN_BUDGET_RE.search(text)
    if m:
        return float(m.group(1).replace(",", ""))
    m = _BUDGET_KEYWORD_RE.search(text)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _extract_dimensions(text: str) -> Optional[tuple]:
    m = _DIMENSIONS_RE.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def _extract_style(text: str) -> str:
    lowered = text.lower()
    for style, keywords in _STYLE_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                return style
    return "contemporary"  # documented default, matches the LLM prompt's fallback rule


def _extract_categories(text: str) -> List[str]:
    lowered = text.lower()
    found = []
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                found.append(category)
                break
    return found


def parse_requirement_rule_based(text: str) -> RequirementSpec:
    """
    Deterministic regex/keyword extraction. Deliberately simple and
    conservative -- it is the safety net that keeps the app usable with
    zero API key, not a replacement for the LLM's language understanding.
    Raises RequirementExtractionError if dimensions or budget can't be found
    at all (the two fields with no safe default).
    """
    dims = _extract_dimensions(text)
    budget = _extract_budget_inr(text)

    if dims is None:
        raise RequirementExtractionError(
            "Could not find bathroom dimensions (expected a pattern like '8 by 6 feet' "
            "or '8x6 ft') in the text. Please use the manual form instead."
        )
    if budget is None:
        raise RequirementExtractionError(
            "Could not find a budget (expected a pattern like '₹2.5 lakh' or '250000') "
            "in the text. Please use the manual form instead."
        )

    categories = _extract_categories(text) or [
        "smart_toilet", "faucet", "thermostatic_shower", "vanity",
    ]

    return RequirementSpec(
        bathroom={"length_ft": dims[0], "width_ft": dims[1]},
        budget_inr=budget,
        style=_extract_style(text),
        required_categories=categories,
    )


# ---------------------------------------------------------------------------
# Orchestrator -- this is what the Streamlit app should call.
# ---------------------------------------------------------------------------

def extract_requirement(user_text: str, client=None, prefer_llm: bool = True) -> ExtractionResult:
    notes: List[str] = []

    if prefer_llm:
        try:
            requirement = parse_requirement_with_llm(user_text, client=client)
            return ExtractionResult(requirement=requirement, method="llm", notes=notes)
        except Exception as exc:  # noqa: BLE001 -- intentionally broad: any LLM failure falls back
            notes.append(
                f"LLM requirement extraction unavailable ({type(exc).__name__}: {exc}); "
                "used the offline rule-based parser instead."
            )

    requirement = parse_requirement_rule_based(user_text)
    return ExtractionResult(requirement=requirement, method="rule_based_fallback", notes=notes)
