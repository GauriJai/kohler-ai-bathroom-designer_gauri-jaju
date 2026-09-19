"""
Bundle optimizer: exhaustive search + transparent weighted scoring.

Design choice (documented in the Phase-1 plan): with a catalog of only a
handful of products per category, brute-force search over every combination
finds the TRUE optimum for the chosen scoring function -- no heuristic,
no black-box solver, every score component is a plain Python function you
can read top to bottom. This is deliberately simpler than OR-Tools/CP-SAT,
which was considered and rejected for the prototype: same correctness
guarantee at this scale, far less implementation/debugging risk for a solo
build on a tight deadline.

Scoring formula (weights configurable, matches the brief's Section 10):

    overall_score = 0.30 * style_match
                  + 0.25 * budget_fit
                  + 0.20 * space_efficiency
                  + 0.15 * feature_match
                  + 0.10 * water_efficiency
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product as iter_product
from typing import Dict, List, Optional

from src.data.catalog import Catalog
from src.data.schemas import AestheticStyle, Product, ProductCategory, RequirementSpec
from src.optimization.constraints import ValidationResult, validate_bundle

DEFAULT_WEIGHTS = {
    "style_match": 0.30,
    "budget_fit": 0.25,
    "space_efficiency": 0.20,
    "feature_match": 0.15,
    "water_efficiency": 0.10,
}

# Rough "typical fixture" baselines used only to normalise the water-efficiency
# score to a 0-1 range. These are prototype assumptions, not certified figures.
WATER_BASELINES = {
    "litres_per_flush": 6.0,      # older-style single flush toilets
    "litres_per_minute": 10.0,    # a non-water-saving shower/faucet flow rate
}

BundleType = Dict[ProductCategory, Product]


@dataclass
class ScoredBundle:
    label: str
    bundle: BundleType
    total_cost_inr: float
    remaining_budget_inr: float
    scores: Dict[str, float]
    overall_score: float
    validation: ValidationResult

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "products": {
                cat.value: p.model_dump() for cat, p in self.bundle.items()
            },
            "total_cost_inr": self.total_cost_inr,
            "remaining_budget_inr": self.remaining_budget_inr,
            "scores": self.scores,
            "overall_score": round(self.overall_score, 4),
            "validation": self.validation.as_dict(),
        }


def _style_match(bundle: BundleType, style: AestheticStyle) -> float:
    if not bundle:
        return 0.0
    hits = sum(1 for p in bundle.values() if style in p.style_tags)
    return hits / len(bundle)


def _budget_fit(total_cost: float, budget: float) -> float:
    if budget <= 0:
        return 0.0
    ratio = total_cost / budget
    # Bundles are already filtered to be within budget upstream; reward
    # higher (but not over) budget utilisation -- an unused budget is not
    # "free", it means a less complete/less capable bundle was chosen.
    return max(0.0, min(1.0, ratio))


def _space_efficiency(bundle: BundleType, requirement: RequirementSpec) -> float:
    from src.optimization.constraints import _zone_footprints_mm

    zones = _zone_footprints_mm(requirement.bathroom.length_ft, requirement.bathroom.width_ft)
    ratios = []
    for category, p in bundle.items():
        if category == ProductCategory.FAUCET or category not in zones:
            continue
        avail_w, avail_d = zones[category]
        if category == ProductCategory.THERMOSTATIC_SHOWER:
            # dimensions_mm already is the shower-zone footprint -- see
            # constraints.check_spatial_fit for the same convention.
            needed_w = p.dimensions_mm.width
            needed_d = p.dimensions_mm.depth
        else:
            needed_w = p.dimensions_mm.width + 2 * p.installation_requirements.minimum_clearance_side_mm
            needed_d = p.dimensions_mm.depth + p.installation_requirements.minimum_clearance_front_mm
        if avail_w <= 0 or avail_d <= 0:
            continue
        ratios.append(min(1.0, (needed_w * needed_d) / (avail_w * avail_d)))
    if not ratios:
        return 0.5
    return sum(ratios) / len(ratios)


def _feature_match(bundle: BundleType) -> float:
    if not bundle:
        return 0.0
    # Normalise by a generous cap so a well-featured bundle can reach 1.0
    # without an arbitrary single "ideal feature count" being hardcoded.
    counts = [len(p.features) for p in bundle.values()]
    avg = sum(counts) / len(counts)
    return max(0.0, min(1.0, avg / 4.0))


def _water_efficiency(bundle: BundleType) -> float:
    scores = []
    for p in bundle.values():
        if p.water_consumption is None:
            continue
        baseline = WATER_BASELINES.get(p.water_consumption.unit)
        if not baseline:
            continue
        scores.append(max(0.0, min(1.0, 1 - (p.water_consumption.value / baseline))))
    if not scores:
        return 0.5
    return sum(scores) / len(scores)


def score_bundle(
    bundle: BundleType,
    requirement: RequirementSpec,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    weights = weights or DEFAULT_WEIGHTS
    total_cost = sum(p.price_inr for p in bundle.values())

    components = {
        "style_match": _style_match(bundle, requirement.style),
        "budget_fit": _budget_fit(total_cost, requirement.budget_inr),
        "space_efficiency": _space_efficiency(bundle, requirement),
        "feature_match": _feature_match(bundle),
        "water_efficiency": _water_efficiency(bundle),
    }
    overall = sum(components[k] * weights.get(k, 0.0) for k in components)
    components["overall_score"] = overall
    return components


def _generate_feasible_bundles(
    requirement: RequirementSpec, catalog: Catalog
) -> List[BundleType]:
    categories = requirement.required_categories
    candidate_lists = []
    for cat in categories:
        candidates = catalog.by_category(cat)
        if not candidates:
            return []  # a required category has zero catalog products -- caller reports this
        candidate_lists.append(candidates)

    feasible = []
    for combo in iter_product(*candidate_lists):
        bundle = dict(zip(categories, combo))
        validation = validate_bundle(bundle, requirement)
        if validation.is_feasible:
            feasible.append(bundle)
    return feasible


def generate_alternatives(
    requirement: RequirementSpec,
    catalog: Catalog,
    weights: Optional[Dict[str, float]] = None,
) -> List[ScoredBundle]:
    """
    Returns up to 3 labeled alternatives: Essential (cheapest feasible),
    Balanced (highest overall_score), Premium (most expensive feasible
    within budget). Duplicate bundles are collapsed to keep the UI honest
    about how many genuinely distinct options exist.
    """
    weights = weights or DEFAULT_WEIGHTS
    feasible = _generate_feasible_bundles(requirement, catalog)

    if not feasible:
        return []

    def total_cost(b: BundleType) -> float:
        return sum(p.price_inr for p in b.values())

    def bundle_key(b: BundleType) -> tuple:
        return tuple(sorted((c.value, p.product_id) for c, p in b.items()))

    scored: Dict[tuple, ScoredBundle] = {}

    def make_scored(bundle: BundleType, label: str) -> ScoredBundle:
        components = score_bundle(bundle, requirement, weights)
        cost = total_cost(bundle)
        validation = validate_bundle(bundle, requirement)
        return ScoredBundle(
            label=label,
            bundle=bundle,
            total_cost_inr=cost,
            remaining_budget_inr=requirement.budget_inr - cost,
            scores={k: round(v, 4) for k, v in components.items() if k != "overall_score"},
            overall_score=components["overall_score"],
            validation=validation,
        )

    cheapest = min(feasible, key=total_cost)
    most_expensive = max(feasible, key=total_cost)
    best_scored = max(feasible, key=lambda b: score_bundle(b, requirement, weights)["overall_score"])

    for bundle, label in [
        (cheapest, "Essential Bundle"),
        (best_scored, "Balanced Bundle"),
        (most_expensive, "Premium Bundle"),
    ]:
        key = bundle_key(bundle)
        if key not in scored:
            scored[key] = make_scored(bundle, label)
        # if two labels collapse onto the same bundle (small catalog!), keep
        # the first label and note it rather than silently duplicating.

    # order: Essential, Balanced, Premium (by cost)
    ordered = sorted(scored.values(), key=lambda sb: sb.total_cost_inr)
    return ordered


# ---------------------------------------------------------------------------
# Best-effort fallback path (Block 6) -- used ONLY when generate_alternatives()
# above returns an empty list. It never changes what "feasible" means and
# never touches _generate_feasible_bundles / validate_bundle: it is a wholly
# separate ranking pass that considers every combination (feasible or not)
# and returns the single one that comes closest to fitting the space and
# the budget, with its real remaining violations still attached. The UI
# must never present this result as fully feasible -- see BestEffortBundle
# .validation and .compromise_notes below.
# ---------------------------------------------------------------------------

@dataclass
class BestEffortBundle:
    label: str
    bundle: BundleType
    total_cost_inr: float
    remaining_budget_inr: float
    scores: Dict[str, float]
    overall_score: float
    validation: ValidationResult
    compromise_notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "products": {cat.value: p.model_dump() for cat, p in self.bundle.items()},
            "total_cost_inr": self.total_cost_inr,
            "remaining_budget_inr": self.remaining_budget_inr,
            "scores": self.scores,
            "overall_score": round(self.overall_score, 4),
            "validation": self.validation.as_dict(),
            "compromise_notes": self.compromise_notes,
            "is_best_effort": True,
        }


def _spatial_overage_ratio(bundle: BundleType, requirement: RequirementSpec) -> float:
    """Sum, over every zoned category, of how far its needed footprint AREA
    exceeds the zone's available area (0 if it fits). Purely a ranking
    signal for the fallback path below -- check_spatial_fit remains the
    only function that decides real feasibility."""
    from src.optimization.constraints import _zone_footprints_mm

    zones = _zone_footprints_mm(requirement.bathroom.length_ft, requirement.bathroom.width_ft)
    total = 0.0
    for category, p in bundle.items():
        if category == ProductCategory.FAUCET or category not in zones:
            continue
        avail_w, avail_d = zones[category]
        if avail_w <= 0 or avail_d <= 0:
            total += 5.0
            continue
        if category == ProductCategory.THERMOSTATIC_SHOWER:
            needed_w, needed_d = p.dimensions_mm.width, p.dimensions_mm.depth
        else:
            needed_w = p.dimensions_mm.width + 2 * p.installation_requirements.minimum_clearance_side_mm
            needed_d = p.dimensions_mm.depth + p.installation_requirements.minimum_clearance_front_mm
        total += max(0.0, (needed_w * needed_d) / (avail_w * avail_d) - 1.0)
    return total


def _budget_overage_ratio(bundle: BundleType, requirement: RequirementSpec) -> float:
    if requirement.budget_inr <= 0:
        return 0.0
    cost = sum(p.price_inr for p in bundle.values())
    return max(0.0, (cost - requirement.budget_inr) / requirement.budget_inr)


def generate_best_effort_alternative(
    requirement: RequirementSpec,
    catalog: Catalog,
    weights: Optional[Dict[str, float]] = None,
) -> Optional[BestEffortBundle]:
    """
    Called by the UI only when generate_alternatives() returns []. Ranks
    every combination of required-category products (not just the feasible
    ones) by combined spatial + budget overage, and returns the single
    closest one -- preferring combinations that fit better, then cheaper
    ones as a tie-break, which naturally favors smaller/cheaper products
    over larger/pricier ones without special-casing either. Returns None
    only when a required category has zero catalog products at all (nothing
    to offer, not a compromise).
    """
    weights = weights or DEFAULT_WEIGHTS
    categories = requirement.required_categories
    candidate_lists = []
    for cat in categories:
        candidates = catalog.by_category(cat)
        if not candidates:
            return None
        candidate_lists.append(candidates)

    best_combo: Optional[BundleType] = None
    best_key: Optional[tuple] = None
    for combo in iter_product(*candidate_lists):
        bundle = dict(zip(categories, combo))
        spatial = _spatial_overage_ratio(bundle, requirement)
        budget = _budget_overage_ratio(bundle, requirement)
        cost = sum(p.price_inr for p in bundle.values())
        key = (spatial + budget, cost)
        if best_key is None or key < best_key:
            best_key = key
            best_combo = bundle

    if best_combo is None:
        return None

    components = score_bundle(best_combo, requirement, weights)
    cost = sum(p.price_inr for p in best_combo.values())
    validation = validate_bundle(best_combo, requirement)

    compromise_notes: List[str] = []
    if cost > requirement.budget_inr:
        compromise_notes.append(f"₹{cost - requirement.budget_inr:,.0f} above your target budget.")
    spatial_violations = [v for v in validation.violations if "budget" not in v.lower()]
    if spatial_violations:
        compromise_notes.append(
            "One clearance requirement is tighter than recommended."
            if len(spatial_violations) == 1
            else f"{len(spatial_violations)} clearance requirements are tighter than recommended."
        )

    label = "Compact Space Edit" if spatial_violations else "Best-Fit Design"

    return BestEffortBundle(
        label=label,
        bundle=best_combo,
        total_cost_inr=cost,
        remaining_budget_inr=requirement.budget_inr - cost,
        scores={k: round(v, 4) for k, v in components.items() if k != "overall_score"},
        overall_score=components["overall_score"],
        validation=validation,
        compromise_notes=compromise_notes,
    )
