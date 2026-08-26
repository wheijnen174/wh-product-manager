from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from wh_product_manager.db.models.products.variant import VariantORM


@dataclass
class UnifiedVariant:
    """Standard variant structure across all suppliers"""

    sku: str
    size_title: Optional[str]
    stock: int
    price: float
    cost: float
    rrp: Optional[float]
    barcode: Optional[str]
    weight: Optional[int]
    country_of_origin: Optional[str]
    hscode: Optional[int]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sku": self.sku,
            "size_title": self.size_title,
            "stock": self.stock,
            "price": self.price,
            "cost": self.cost,
            "rrp": self.rrp,
            "barcode": self.barcode,
            "weight": self.weight,
            "country_of_origin": self.country_of_origin,
            "hscode": self.hscode,
        }

    def to_orm(
        self,
        *,
        supplier_name: str,
        seen_at: Optional[datetime],
    ) -> VariantORM:
        update_time = seen_at or datetime.now(timezone.utc)

        variant = VariantORM(
            supplier_name=supplier_name,
            sku=self.sku,
            size_title=self.size_title,
            stock=self.stock,
            price=self.price,
            cost=self.cost,
            rrp=self.rrp,
            barcode=self.barcode,
            weight=self.weight,
            country_of_origin=self.country_of_origin,
            hscode=self.hscode,
            last_seen_at=update_time,
            missing_since=None,
            is_missing=False,
        )

        return variant
