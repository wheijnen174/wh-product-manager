"""
Unified supplier data schemas
Standard format for all supplier data
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class UnifiedVariant:
    """Standard variant structure across all suppliers"""

    sku: str
    stock: int
    price: float
    cost: float
    barcode: str | None = None
    size_title: str | None = None
    weight: int | None = None
    country_of_origin: str | None = None
    hscode: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sku": self.sku,
            "stock": self.stock,
            "price": self.price,
            "cost": self.cost,
            "barcode": self.barcode,
            "size_title": self.size_title,
            "weight": self.weight,
            "country_of_origin": self.country_of_origin,
            "hscode": self.hscode,
        }


@dataclass
class UnifiedProperty:
    """Standard product property structure across all suppliers"""

    single_or_multi: str  # "single" or "multi"
    field_type: str  # "metaobject" or "metafield"
    values: list[str] | str

    def __post_init__(self) -> None:
        """Validate the property after initialization"""
        # Validate single_or_multi
        if self.single_or_multi not in ("single", "multi"):
            raise ValueError(
                f"single_or_multi must be 'single' or 'multi', "
                f"got '{self.single_or_multi}'"
            )

        # Validate field_type
        if self.field_type not in ("metaobject", "metafield"):
            raise ValueError(
                f"field_type must be 'metaobject' or 'metafield', "
                f"got '{self.field_type}'"
            )

        # Validate values based on single_or_multi
        if self.single_or_multi == "multi":
            if isinstance(self.values, str):
                # If it's a string, convert it to a list
                self.values = [self.values]
            elif not isinstance(self.values, list):  # type: ignore
                raise ValueError(
                    f"When single_or_multi='multi', values must be a list, "
                    f"got {type(self.values).__name__}"
                )
            if not all(isinstance(v, str) for v in self.values):  # type: ignore
                raise ValueError("All values in the list must be strings")
        else:  # single_or_multi == "single"
            if not isinstance(self.values, str):
                raise ValueError(
                    f"When single_or_multi='single', values must be a string, "
                    f"got {type(self.values).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "single_or_multi": self.single_or_multi,
            "field_type": self.field_type,
            "values": self.values,
        }


@dataclass
class UnifiedProduct:
    """Standard product structure across all suppliers"""

    supplier_product_id: int
    title: str
    images: list[str]
    category: str
    variants: list[UnifiedVariant]
    description: str | None = None
    properties: dict[str, UnifiedProperty] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "supplier_product_id": self.supplier_product_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "images": self.images,
            "variants": [v.to_dict() for v in self.variants],
            "properties": {k: v.to_dict() for k, v in (self.properties or {}).items()},
        }


@dataclass
class SupplierDataResult:
    """Result of fetching and transforming supplier data"""

    supplier_name: str
    status: str  # "success" or "failed"
    item_count: int = 0
    error: str | None = None
    products: dict[str, UnifiedProduct] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "supplier_name": self.supplier_name,
            "status": self.status,
            "item_count": self.item_count,
            "error": self.error,
            "products": {k: v.to_dict() for k, v in (self.products or {}).items()},
        }
