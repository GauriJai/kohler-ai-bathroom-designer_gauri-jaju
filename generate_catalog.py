"""
One-off generator for the prototype product catalog (data/products.json).

Not part of the runtime app — run this manually when you want to regenerate
or hand-edit the catalog's structure. All records are data_status =
"synthetic_demo": plausible values invented for this prototype, NOT sourced
from an official KOHLER catalogue. See data/data_sources.md for the policy.

Run:
    python scripts/generate_catalog.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data.schemas import Product  # noqa: E402

PRODUCTS = []

# ---------------------------------------------------------------------------
# SMART TOILETS (6)
# ---------------------------------------------------------------------------
PRODUCTS += [
    dict(
        product_id="KT-101", brand="KOHLER", product_name="Prototype Essential Comfort Toilet",
        category="smart_toilet", data_status="synthetic_demo", source_url=None,
        price_inr=22000, dimensions_mm=dict(width=380, depth=680, height=400),
        style_tags=["contemporary", "minimalist_modern"], finish="white",
        features=["dual_flush", "soft_close_seat"],
        water_consumption=dict(value=4.8, unit="litres_per_flush", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=600, minimum_clearance_side_mm=150),
        compatibility_tags=["budget_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KT-102", brand="KOHLER", product_name="Prototype Compact Zen Toilet",
        category="smart_toilet", data_status="synthetic_demo", source_url=None,
        price_inr=48000, dimensions_mm=dict(width=370, depth=650, height=390),
        style_tags=["japanese_zen", "minimalist_modern"], finish="matte_white",
        features=["dual_flush", "slow_close_lid", "water_saving_flush"],
        water_consumption=dict(value=4.0, unit="litres_per_flush", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=600, minimum_clearance_side_mm=150),
        compatibility_tags=["compact_bathroom", "water_saving"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KT-103", brand="KOHLER", product_name="Prototype Smart Comfort Toilet with Bidet",
        category="smart_toilet", data_status="synthetic_demo", source_url=None,
        price_inr=65000, dimensions_mm=dict(width=400, depth=700, height=420),
        style_tags=["japanese_zen", "contemporary"], finish="white",
        features=["integrated_bidet", "heated_seat", "auto_flush", "night_light"],
        water_consumption=dict(value=4.0, unit="litres_per_flush", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=650, minimum_clearance_side_mm=180),
        compatibility_tags=["smart_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KT-104", brand="KOHLER", product_name="Prototype Heritage Luxury Toilet",
        category="smart_toilet", data_status="synthetic_demo", source_url=None,
        price_inr=78000, dimensions_mm=dict(width=410, depth=720, height=430),
        style_tags=["classic_luxury"], finish="ivory",
        features=["dual_flush", "decorative_trim", "soft_close_seat"],
        water_consumption=dict(value=5.0, unit="litres_per_flush", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=650, minimum_clearance_side_mm=180),
        compatibility_tags=["luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KT-105", brand="KOHLER", product_name="Prototype Smart Suite Toilet",
        category="smart_toilet", data_status="synthetic_demo", source_url=None,
        price_inr=118000, dimensions_mm=dict(width=420, depth=730, height=450),
        style_tags=["contemporary", "classic_luxury"], finish="white",
        features=["integrated_bidet", "heated_seat", "auto_flush", "remote_control", "night_light"],
        water_consumption=dict(value=4.5, unit="litres_per_flush", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=700, minimum_clearance_side_mm=200),
        compatibility_tags=["smart_bathroom", "luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KT-106", brand="KOHLER", product_name="Prototype Signature Smart Toilet",
        category="smart_toilet", data_status="synthetic_demo", source_url=None,
        price_inr=152000, dimensions_mm=dict(width=430, depth=740, height=460),
        style_tags=["classic_luxury", "contemporary"], finish="black_matte",
        features=["integrated_bidet", "heated_seat", "auto_flush", "remote_control",
                   "night_light", "auto_deodorizer"],
        water_consumption=dict(value=4.2, unit="litres_per_flush", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=700, minimum_clearance_side_mm=200),
        compatibility_tags=["smart_bathroom", "luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
]

# ---------------------------------------------------------------------------
# FAUCETS (6)
# ---------------------------------------------------------------------------
PRODUCTS += [
    dict(
        product_id="KF-201", brand="KOHLER", product_name="Prototype Essential Single-Lever Faucet",
        category="faucet", data_status="synthetic_demo", source_url=None,
        price_inr=4200, dimensions_mm=dict(width=50, depth=180, height=200),
        style_tags=["contemporary", "minimalist_modern"], finish="chrome",
        features=["single_lever", "water_saving_aerator"],
        water_consumption=dict(value=6.0, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=0, minimum_clearance_side_mm=50),
        compatibility_tags=["budget_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KF-202", brand="KOHLER", product_name="Prototype Zen Minimal Faucet",
        category="faucet", data_status="synthetic_demo", source_url=None,
        price_inr=8500, dimensions_mm=dict(width=40, depth=160, height=180),
        style_tags=["japanese_zen", "minimalist_modern"], finish="matte_black",
        features=["single_lever", "low_flow_aerator"],
        water_consumption=dict(value=4.5, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=0, minimum_clearance_side_mm=50),
        compatibility_tags=["water_saving"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KF-203", brand="KOHLER", product_name="Prototype Touchless Sensor Faucet",
        category="faucet", data_status="synthetic_demo", source_url=None,
        price_inr=15500, dimensions_mm=dict(width=55, depth=190, height=210),
        style_tags=["contemporary"], finish="chrome",
        features=["touchless_sensor", "water_saving_aerator"],
        water_consumption=dict(value=5.0, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=0, minimum_clearance_side_mm=50),
        compatibility_tags=["smart_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KF-204", brand="KOHLER", product_name="Prototype Heritage Cross-Handle Faucet",
        category="faucet", data_status="synthetic_demo", source_url=None,
        price_inr=13800, dimensions_mm=dict(width=60, depth=200, height=230),
        style_tags=["classic_luxury"], finish="brushed_gold",
        features=["dual_handle", "brass_body"],
        water_consumption=dict(value=7.5, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=0, minimum_clearance_side_mm=60),
        compatibility_tags=["luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KF-205", brand="KOHLER", product_name="Prototype Pull-Down Spray Faucet",
        category="faucet", data_status="synthetic_demo", source_url=None,
        price_inr=21000, dimensions_mm=dict(width=65, depth=220, height=320),
        style_tags=["contemporary", "classic_luxury"], finish="brushed_nickel",
        features=["pull_down_spray", "single_lever"],
        water_consumption=dict(value=6.5, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=0, minimum_clearance_side_mm=60),
        compatibility_tags=["luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KF-206", brand="KOHLER", product_name="Prototype Signature Gold Faucet",
        category="faucet", data_status="synthetic_demo", source_url=None,
        price_inr=42000, dimensions_mm=dict(width=60, depth=210, height=260),
        style_tags=["classic_luxury"], finish="polished_gold",
        features=["single_lever", "brass_body", "ceramic_disc_valve"],
        water_consumption=dict(value=6.0, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=0, minimum_clearance_side_mm=60),
        compatibility_tags=["luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
]

# ---------------------------------------------------------------------------
# THERMOSTATIC SHOWERS (6)
# dimensions_mm here represent the minimum shower-zone footprint the system
# needs (enclosure + panel), not just the control unit -- documented in notes.
# ---------------------------------------------------------------------------
PRODUCTS += [
    dict(
        product_id="KS-301", brand="KOHLER", product_name="Prototype Essential Thermostatic Shower",
        category="thermostatic_shower", data_status="synthetic_demo", source_url=None,
        price_inr=32000, dimensions_mm=dict(width=800, depth=800, height=2100),
        style_tags=["contemporary", "minimalist_modern"], finish="chrome",
        features=["thermostatic_mixing", "handheld_spray"],
        water_consumption=dict(value=9.0, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=700, minimum_clearance_side_mm=100),
        compatibility_tags=["budget_bathroom"],
        notes=("Dimensions represent minimum shower-zone footprint (enclosure), "
               "not the physical size of the mixing valve. Prototype data; not "
               "an official KOHLER specification."),
    ),
    dict(
        product_id="KS-302", brand="KOHLER", product_name="Prototype Zen Rain Shower System",
        category="thermostatic_shower", data_status="synthetic_demo", source_url=None,
        price_inr=55000, dimensions_mm=dict(width=850, depth=850, height=2150),
        style_tags=["japanese_zen", "minimalist_modern"], finish="matte_black",
        features=["thermostatic_mixing", "rain_shower_head", "low_flow_nozzle"],
        water_consumption=dict(value=7.0, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=750, minimum_clearance_side_mm=100),
        compatibility_tags=["water_saving"],
        notes=("Dimensions represent minimum shower-zone footprint (enclosure), "
               "not the physical size of the mixing valve. Prototype data; not "
               "an official KOHLER specification."),
    ),
    dict(
        product_id="KS-303", brand="KOHLER", product_name="Prototype Digital Thermostatic Shower",
        category="thermostatic_shower", data_status="synthetic_demo", source_url=None,
        price_inr=78000, dimensions_mm=dict(width=900, depth=900, height=2150),
        style_tags=["contemporary"], finish="chrome",
        features=["thermostatic_mixing", "digital_display", "multiple_outlets", "handheld_spray"],
        water_consumption=dict(value=9.5, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=800, minimum_clearance_side_mm=120),
        compatibility_tags=["smart_bathroom"],
        notes=("Dimensions represent minimum shower-zone footprint (enclosure), "
               "not the physical size of the mixing valve. Prototype data; not "
               "an official KOHLER specification."),
    ),
    dict(
        product_id="KS-304", brand="KOHLER", product_name="Prototype Heritage Shower System",
        category="thermostatic_shower", data_status="synthetic_demo", source_url=None,
        price_inr=95000, dimensions_mm=dict(width=900, depth=900, height=2200),
        style_tags=["classic_luxury"], finish="brushed_gold",
        features=["thermostatic_mixing", "rain_shower_head", "handheld_spray", "decorative_trim"],
        water_consumption=dict(value=10.0, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=800, minimum_clearance_side_mm=120),
        compatibility_tags=["luxury_bathroom"],
        notes=("Dimensions represent minimum shower-zone footprint (enclosure), "
               "not the physical size of the mixing valve. Prototype data; not "
               "an official KOHLER specification."),
    ),
    dict(
        product_id="KS-305", brand="KOHLER", product_name="Prototype Premium Rain Shower Suite",
        category="thermostatic_shower", data_status="synthetic_demo", source_url=None,
        price_inr=132000, dimensions_mm=dict(width=950, depth=950, height=2200),
        style_tags=["contemporary", "classic_luxury"], finish="brushed_nickel",
        features=["thermostatic_mixing", "rain_shower_head", "digital_display",
                   "multiple_outlets", "handheld_spray"],
        water_consumption=dict(value=9.0, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=850, minimum_clearance_side_mm=130),
        compatibility_tags=["luxury_bathroom", "smart_bathroom"],
        notes=("Dimensions represent minimum shower-zone footprint (enclosure), "
               "not the physical size of the mixing valve. Prototype data; not "
               "an official KOHLER specification."),
    ),
    dict(
        product_id="KS-306", brand="KOHLER", product_name="Prototype Signature Zen Shower Suite",
        category="thermostatic_shower", data_status="synthetic_demo", source_url=None,
        price_inr=168000, dimensions_mm=dict(width=1000, depth=1000, height=2250),
        style_tags=["japanese_zen", "classic_luxury"], finish="matte_black",
        features=["thermostatic_mixing", "rain_shower_head", "low_flow_nozzle",
                   "handheld_spray", "digital_display"],
        water_consumption=dict(value=6.5, unit="litres_per_minute", status="assumed"),
        installation_requirements=dict(minimum_clearance_front_mm=850, minimum_clearance_side_mm=130),
        compatibility_tags=["luxury_bathroom", "water_saving"],
        notes=("Dimensions represent minimum shower-zone footprint (enclosure), "
               "not the physical size of the mixing valve. Prototype data; not "
               "an official KOHLER specification."),
    ),
]

# ---------------------------------------------------------------------------
# VANITIES (6)
# water_consumption is null -- the vanity itself does not consume water
# (its faucet does, and is scored separately).
# ---------------------------------------------------------------------------
PRODUCTS += [
    dict(
        product_id="KV-401", brand="KOHLER", product_name="Prototype Essential Wall-Mounted Vanity",
        category="vanity", data_status="synthetic_demo", source_url=None,
        price_inr=14000, dimensions_mm=dict(width=600, depth=460, height=820),
        style_tags=["minimalist_modern", "contemporary"], finish="white",
        features=["single_basin", "wall_mounted"],
        water_consumption=None,
        installation_requirements=dict(minimum_clearance_front_mm=600, minimum_clearance_side_mm=100),
        compatibility_tags=["compact_bathroom", "budget_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KV-402", brand="KOHLER", product_name="Prototype Zen Floating Vanity",
        category="vanity", data_status="synthetic_demo", source_url=None,
        price_inr=32000, dimensions_mm=dict(width=750, depth=460, height=820),
        style_tags=["japanese_zen", "minimalist_modern"], finish="natural_wood",
        features=["single_basin", "wall_mounted", "storage_drawers"],
        water_consumption=None,
        installation_requirements=dict(minimum_clearance_front_mm=600, minimum_clearance_side_mm=100),
        compatibility_tags=["compact_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KV-403", brand="KOHLER", product_name="Prototype Contemporary Storage Vanity",
        category="vanity", data_status="synthetic_demo", source_url=None,
        price_inr=48000, dimensions_mm=dict(width=900, depth=480, height=830),
        style_tags=["contemporary"], finish="grey_matte",
        features=["single_basin", "storage_drawers", "led_mirror_compatible"],
        water_consumption=None,
        installation_requirements=dict(minimum_clearance_front_mm=650, minimum_clearance_side_mm=100),
        compatibility_tags=["smart_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KV-404", brand="KOHLER", product_name="Prototype Heritage Freestanding Vanity",
        category="vanity", data_status="synthetic_demo", source_url=None,
        price_inr=68000, dimensions_mm=dict(width=1050, depth=500, height=850),
        style_tags=["classic_luxury"], finish="dark_walnut",
        features=["single_basin", "freestanding", "decorative_trim", "storage_drawers"],
        water_consumption=None,
        installation_requirements=dict(minimum_clearance_front_mm=700, minimum_clearance_side_mm=120),
        compatibility_tags=["luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KV-405", brand="KOHLER", product_name="Prototype Double Basin Luxury Vanity",
        category="vanity", data_status="synthetic_demo", source_url=None,
        price_inr=95000, dimensions_mm=dict(width=1400, depth=520, height=850),
        style_tags=["classic_luxury", "contemporary"], finish="marble_white",
        features=["double_basin", "freestanding", "storage_drawers", "led_mirror_compatible"],
        water_consumption=None,
        installation_requirements=dict(minimum_clearance_front_mm=750, minimum_clearance_side_mm=150),
        compatibility_tags=["luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
    dict(
        product_id="KV-406", brand="KOHLER", product_name="Prototype Signature Zen Double Vanity",
        category="vanity", data_status="synthetic_demo", source_url=None,
        price_inr=118000, dimensions_mm=dict(width=1500, depth=520, height=850),
        style_tags=["japanese_zen", "classic_luxury"], finish="natural_wood",
        features=["double_basin", "wall_mounted", "storage_drawers", "led_mirror_compatible"],
        water_consumption=None,
        installation_requirements=dict(minimum_clearance_front_mm=750, minimum_clearance_side_mm=150),
        compatibility_tags=["luxury_bathroom"],
        notes="Prototype data; not an official KOHLER specification.",
    ),
]

def main():
    validated = []
    for raw in PRODUCTS:
        product = Product(**raw)  # raises if any record violates the schema/policy
        validated.append(json.loads(product.model_dump_json()))

    out_path = ROOT / "data" / "products.json"
    out_path.write_text(json.dumps(validated, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(validated)} validated products to {out_path}")

    counts = {}
    for p in validated:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    print("Category counts:", counts)


if __name__ == "__main__":
    main()
