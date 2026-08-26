from dataclasses import dataclass
from typing import Any

from wh_product_manager.db.models.properties.definition import allowed_created_by
from wh_product_manager.db.models.properties.value import PropertyValueORM


@dataclass
class UnifiedPropertyValue:
    """Standard property value structure across all suppliers"""

    normalized_value: str
    display_value: str
    created_by: str

    def __post_init__(self):
        if self.created_by not in allowed_created_by:
            raise ValueError(
                f"Invalid created_by: {self.created_by}. Must be one of {allowed_created_by}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "normalized_value": self.normalized_value,
            "display_value": self.display_value,
            "created_by": self.created_by,
        }

    def to_orm(self) -> PropertyValueORM:
        """Convert to ORM object"""
        value = PropertyValueORM(
            normalized_value=self.normalized_value,
            display_value=self.display_value,
            created_by=self.created_by,
        )

        return value
