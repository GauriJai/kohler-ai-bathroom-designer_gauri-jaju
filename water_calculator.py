"""
Sustainability / water-consumption calculator.

Pure arithmetic on values already present in the validated Product catalog
(see the data policy in data/data_sources.md) plus explicit, user-visible
usage assumptions. No LLM involvement, no hidden formulas, no certification
claims -- every number here can be recomputed by hand from the inputs shown.

This module deliberately does NOT decide anything about feasibility; it is
informational output attached to an already-optimizer-selected bundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.data.schemas import Product, ProductCategory

DAYS_PER_YEAR = 365

# Baseline "typical / non-water-saving fixture" values, used only to express
# a potential-savings comparison. These are prototype assumptions for
# illustration, NOT certified or sourced figures -- kept identical to the
# baselines already used for the optimizer's water_efficiency score so the
# two numbers in the UI never contradict each other.
BASELINE_FLUSH_LITRES = 6.0        # litres per flush, older non-dual-flush toilet
BASELINE_SHOWER_LPM = 10.0         # litres per minute, standard shower head
BASELINE_FAUCET_LPM = 8.0          # litres per minute, standard faucet


class UsageAssumptions(BaseModel):
    """
    Every field here is a user-editable, clearly-labeled assumption -- the
    calculator's output is only as good as these, and the UI must show them
    alongside any number they produce.
    """

    num_users: int = Field(4, ge=1, le=20)
    flushes_per_person_per_day: float = Field(5.0, ge=0, le=20)
    showers_per_person_per_week: float = Field(7.0, ge=0, le=21)
    shower_duration_minutes: float = Field(8.0, ge=0, le=60)
    faucet_uses_per_person_per_day: float = Field(6.0, ge=0, le=30)
    faucet_use_duration_minutes: float = Field(1.0, ge=0, le=10)


@dataclass
class WaterEstimateItem:
    category: str
    product_id: str
    product_name: str
    daily_litres: float
    status: str  # "assumed" or "verified", copied from the product record
    formula: str  # human-readable, so the number is auditable in the UI


@dataclass
class WaterEstimateResult:
    assumptions: UsageAssumptions
    items: List[WaterEstimateItem]
    daily_total_litres: float
    annual_total_litres: float
    baseline_annual_litres: float
    estimated_annual_savings_litres: float
    estimated_savings_percent: float
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "assumptions": self.assumptions.model_dump(),
            "items": [vars(i) for i in self.items],
            "daily_total_litres": round(self.daily_total_litres, 1),
            "annual_total_litres": round(self.annual_total_litres, 0),
            "baseline_annual_litres": round(self.baseline_annual_litres, 0),
            "estimated_annual_savings_litres": round(self.estimated_annual_savings_litres, 0),
            "estimated_savings_percent": round(self.estimated_savings_percent, 1),
            "warnings": self.warnings,
        }


def estimate_water_use(
    bundle: Dict[ProductCategory, Product],
    assumptions: Optional[UsageAssumptions] = None,
) -> WaterEstimateResult:
    assumptions = assumptions or UsageAssumptions()
    items: List[WaterEstimateItem] = []
    warnings: List[str] = [
        "These figures are estimates based on the usage assumptions shown, "
        "not measured data. Product water-consumption values are prototype "
        "figures (see data_status on each product) unless marked 'verified'."
    ]

    daily_total = 0.0
    baseline_daily = 0.0

    toilet = bundle.get(ProductCategory.SMART_TOILET)
    if toilet and toilet.water_consumption:
        flush_value = toilet.water_consumption.value
        daily = assumptions.num_users * assumptions.flushes_per_person_per_day * flush_value
        daily_total += daily
        baseline_daily += assumptions.num_users * assumptions.flushes_per_person_per_day * BASELINE_FLUSH_LITRES
        items.append(WaterEstimateItem(
            category="smart_toilet", product_id=toilet.product_id, product_name=toilet.product_name,
            daily_litres=round(daily, 2), status=toilet.water_consumption.status.value,
            formula=(f"{assumptions.num_users} users x {assumptions.flushes_per_person_per_day} "
                     f"flushes/day x {flush_value} L/flush"),
        ))
    else:
        warnings.append("No smart toilet with a water_consumption value in this bundle; excluded from the estimate.")

    shower = bundle.get(ProductCategory.THERMOSTATIC_SHOWER)
    if shower and shower.water_consumption:
        flow = shower.water_consumption.value
        weekly_minutes = assumptions.num_users * assumptions.showers_per_person_per_week * assumptions.shower_duration_minutes
        daily = (weekly_minutes * flow) / 7.0
        daily_total += daily
        baseline_weekly_minutes = weekly_minutes
        baseline_daily += (baseline_weekly_minutes * BASELINE_SHOWER_LPM) / 7.0
        items.append(WaterEstimateItem(
            category="thermostatic_shower", product_id=shower.product_id, product_name=shower.product_name,
            daily_litres=round(daily, 2), status=shower.water_consumption.status.value,
            formula=(f"{assumptions.num_users} users x {assumptions.showers_per_person_per_week} showers/week x "
                     f"{assumptions.shower_duration_minutes} min x {flow} L/min, averaged per day"),
        ))
    else:
        warnings.append("No thermostatic shower with a water_consumption value in this bundle; excluded from the estimate.")

    faucet = bundle.get(ProductCategory.FAUCET)
    if faucet and faucet.water_consumption:
        flow = faucet.water_consumption.value
        daily = (assumptions.num_users * assumptions.faucet_uses_per_person_per_day
                  * assumptions.faucet_use_duration_minutes * flow)
        daily_total += daily
        baseline_daily += (assumptions.num_users * assumptions.faucet_uses_per_person_per_day
                            * assumptions.faucet_use_duration_minutes * BASELINE_FAUCET_LPM)
        items.append(WaterEstimateItem(
            category="faucet", product_id=faucet.product_id, product_name=faucet.product_name,
            daily_litres=round(daily, 2), status=faucet.water_consumption.status.value,
            formula=(f"{assumptions.num_users} users x {assumptions.faucet_uses_per_person_per_day} uses/day x "
                     f"{assumptions.faucet_use_duration_minutes} min x {flow} L/min"),
        ))
    else:
        warnings.append("No faucet with a water_consumption value in this bundle; excluded from the estimate.")

    annual_total = daily_total * DAYS_PER_YEAR
    baseline_annual = baseline_daily * DAYS_PER_YEAR
    savings = baseline_annual - annual_total
    savings_pct = (savings / baseline_annual * 100.0) if baseline_annual > 0 else 0.0

    return WaterEstimateResult(
        assumptions=assumptions,
        items=items,
        daily_total_litres=daily_total,
        annual_total_litres=annual_total,
        baseline_annual_litres=baseline_annual,
        estimated_annual_savings_litres=savings,
        estimated_savings_percent=savings_pct,
        warnings=warnings,
    )
