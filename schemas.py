"""
Pydantic data models for the KOHLER AI Bathroom Designer & Planner prototype.

IMPORTANT DATA POLICY (see data/data_sources.md):
This project uses NO official KOHLER catalogue, pricing, or internal
specifications. Every product record carries a `data_status` field that
tells you exactly how trustworthy each value is:

- "verified_public"   -> taken from a publicly listed product page (source_url set)
- "prototype_assumed" -> a reasonable engineering assumption, not sourced
- "synthetic_demo"    -> fabricated purely to populate the prototype catalog

Nothing in this file, or in data/products.json, should ever be presented
to a user as official KOHLER data.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

class ProductCategory(str, Enum):
    SMART_TOILET = "smart_toilet"
    FAUCET = "faucet"
    THERMOSTATIC_SHOWER = "thermostatic_shower"
    VANITY = "vanity"


class DataStatus(str, Enum):
    VERIFIED_PUBLIC = "verified_public"
    PROTOTYPE_ASSUMED = "prototype_assumed"
    SYNTHETIC_DEMO = "synthetic_demo"


class WaterValueStatus(str, Enum):
    VERIFIED = "verified"
    ASSUMED = "assumed"


class AestheticStyle(str, Enum):
    MINIMALIST_MODERN = "minimalist_modern"
    CLASSIC_LUXURY = "classic_luxury"
    JAPANESE_ZEN = "japanese_zen"
    CONTEMPORARY = "contemporary"


# ---------------------------------------------------------------------------
# Product sub-structures
# ---------------------------------------------------------------------------

class DimensionsMM(BaseModel):
    """All fixture dimensions are stored in millimetres for consistency."""

    width: float = Field(..., gt=0, description="Left-right footprint, mm")
    depth: float = Field(..., gt=0, description="Front-back footprint, mm")
    height: float = Field(..., gt=0, description="Vertical height, mm")


class WaterConsumption(BaseModel):
    value: float = Field(..., ge=0)
    unit: str = Field(..., description="e.g. 'litres_per_flush', 'litres_per_minute'")
    status: WaterValueStatus = WaterValueStatus.ASSUMED


class InstallationRequirements(BaseModel):
    minimum_clearance_front_mm: float = Field(0, ge=0)
    minimum_clearance_side_mm: float = Field(0, ge=0)
    minimum_clearance_back_mm: float = Field(0, ge=0)


# ---------------------------------------------------------------------------
# Product model
# ---------------------------------------------------------------------------

class Product(BaseModel):
    product_id: str
    brand: str
    product_name: str
    category: ProductCategory
    data_status: DataStatus
    source_url: Optional[str] = None

    price_inr: float = Field(..., gt=0)
    dimensions_mm: DimensionsMM

    style_tags: List[AestheticStyle] = Field(default_factory=list)
    finish: str = "unspecified"
    features: List[str] = Field(default_factory=list)

    water_consumption: Optional[WaterConsumption] = None
    installation_requirements: InstallationRequirements = Field(
        default_factory=InstallationRequirements
    )
    compatibility_tags: List[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def _check_source_consistency(self) -> "Product":
        # Enforce the data policy at the schema level, not just by convention:
        # a record cannot claim to be verified_public without a source_url.
        if self.data_status == DataStatus.VERIFIED_PUBLIC and not self.source_url:
            raise ValueError(
                f"{self.product_id}: data_status is 'verified_public' but "
                "source_url is missing."
            )
        return self


# ---------------------------------------------------------------------------
# Structured requirement extraction target (Section 3, Step 3 of the brief)
# ---------------------------------------------------------------------------

class BathroomDimensions(BaseModel):
    length_ft: float = Field(..., gt=0, le=100)
    width_ft: float = Field(..., gt=0, le=100)
    ceiling_height_ft: Optional[float] = Field(None, gt=0, le=20)

    @property
    def area_sqft(self) -> float:
        return self.length_ft * self.width_ft


class RequirementSpec(BaseModel):
    """
    The single structured object the whole downstream pipeline consumes.
    Produced either by the LLM extractor (validated against this schema)
    or directly by the Streamlit form. The LLM is never allowed to skip
    this validation step.
    """

    bathroom: BathroomDimensions
    budget_inr: float = Field(..., gt=0)
    style: AestheticStyle
    required_categories: List[ProductCategory] = Field(
        default_factory=lambda: [
            ProductCategory.SMART_TOILET,
            ProductCategory.FAUCET,
            ProductCategory.THERMOSTATIC_SHOWER,
            ProductCategory.VANITY,
        ]
    )
    priorities: List[str] = Field(default_factory=list)
    water_saving_preference: bool = False
    accessibility_preference: bool = False

    @field_validator("required_categories")
    @classmethod
    def _dedupe_categories(cls, v: List[ProductCategory]) -> List[ProductCategory]:
        seen = []
        for c in v:
            if c not in seen:
                seen.append(c)
        if not seen:
            raise ValueError("required_categories must not be empty")
        return seen
