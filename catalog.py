"""
Product catalog loader and filter functions.

This is the RETRIEVAL layer described in the architecture: everything the
constraint engine and optimizer ever see about a product comes through here,
never invented by an LLM. Swap `data/products.json` for a real catalogue
later without touching any other module -- the `Product` schema is the
contract.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, List, Optional

from src.data.schemas import AestheticStyle, Product, ProductCategory

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "products.json"


class Catalog:
    """In-memory product catalog with simple, explainable filters."""

    def __init__(self, products: List[Product]):
        self._products = products

    # -- loading ------------------------------------------------------
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Catalog":
        path = path or DEFAULT_CATALOG_PATH
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        products = [Product(**item) for item in raw]
        return cls(products)

    # -- basic access ---------------------------------------------------
    @property
    def all(self) -> List[Product]:
        return list(self._products)

    def by_id(self, product_id: str) -> Optional[Product]:
        for p in self._products:
            if p.product_id == product_id:
                return p
        return None

    def by_category(self, category: ProductCategory) -> List[Product]:
        return [p for p in self._products if p.category == category]

    # -- filters ----------------------------------------------------------
    def filter(
        self,
        category: Optional[ProductCategory] = None,
        style: Optional[AestheticStyle] = None,
        max_price_inr: Optional[float] = None,
        max_width_mm: Optional[float] = None,
        max_depth_mm: Optional[float] = None,
        required_features: Optional[Iterable[str]] = None,
        water_saving_only: bool = False,
    ) -> List[Product]:
        """Filter the catalog. Every argument is optional and AND-combined."""
        results = self._products

        if category is not None:
            results = [p for p in results if p.category == category]
        if style is not None:
            results = [p for p in results if style in p.style_tags]
        if max_price_inr is not None:
            results = [p for p in results if p.price_inr <= max_price_inr]
        if max_width_mm is not None:
            results = [p for p in results if p.dimensions_mm.width <= max_width_mm]
        if max_depth_mm is not None:
            results = [p for p in results if p.dimensions_mm.depth <= max_depth_mm]
        if required_features:
            req = set(required_features)
            results = [p for p in results if req.issubset(set(p.features))]
        if water_saving_only:
            results = [p for p in results if "water_saving" in p.compatibility_tags]

        return results

    # -- lightweight semantic re-rank (no vector DB needed at this scale) --
    def style_similarity_rank(
        self, candidates: List[Product], style: AestheticStyle
    ) -> List[Product]:
        """
        Simple explainable 'semantic retrieval' step: rank candidates by how
        many of their style_tags/compatibility_tags relate to the requested
        style, instead of a hard filter. This is deliberately transparent --
        a real embedding-based retriever (FAISS/Chroma) could replace this
        function without changing its interface (list[Product] in, ranked
        list[Product] out).
        """

        def score(p: Product) -> float:
            s = 1.0 if style in p.style_tags else 0.0
            # small bonus for tag overlap breadth (more versatile products
            # surface slightly higher when tied)
            s += 0.05 * len(p.style_tags)
            return s

        return sorted(candidates, key=score, reverse=True)


def load_catalog(path: Optional[Path] = None) -> Catalog:
    return Catalog.load(path)
