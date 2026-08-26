from dataclasses import dataclass
from typing import Any, Optional

from wh_product_manager.db.models.properties.definition import (
    PropertyDefinitionORM,
    allowed_created_by,
    allowed_input_kind,
    allowed_storage_kind,
    allowed_value_type,
)
from wh_product_manager.properties.schemas.value import UnifiedPropertyValue


@dataclass
class UnifiedPropertyDefinition:
    """Standard property definition structure across all suppliers"""

    key: str
    label: str

    input_kind: str
    storage_kind: str
    value_type: str

    values: list[UnifiedPropertyValue]

    created_by: str
    created_by_supplier_name: Optional[str] = None

    allow_supplier_create: bool = True
    allow_ai_assign: bool = True
    allow_ai_create_values: bool = True

    def __post_init__(self):

        if self.input_kind not in allowed_input_kind:
            raise ValueError(
                f"Invalid input_kind: {self.input_kind}. Must be one of {allowed_input_kind}"
            )
        if self.storage_kind not in allowed_storage_kind:
            raise ValueError(
                f"Invalid storage_kind: {self.storage_kind}. Must be one of {allowed_storage_kind}"
            )
        if self.value_type not in allowed_value_type:
            raise ValueError(
                f"Invalid value_type: {self.value_type}. Must be one of {allowed_value_type}"
            )
        if self.created_by not in allowed_created_by:
            raise ValueError(
                f"Invalid created_by: {self.created_by}. Must be one of {allowed_created_by}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "key": self.key,
            "label": self.label,
            "input_kind": self.input_kind,
            "storage_kind": self.storage_kind,
            "value_type": self.value_type,
            "allow_supplier_create": self.allow_supplier_create,
            "allow_ai_assign": self.allow_ai_assign,
            "allow_ai_create_values": self.allow_ai_create_values,
            "created_by": self.created_by,
            "created_by_supplier_name": self.created_by_supplier_name,
            "values": [value.to_dict() for value in self.values],
        }

    def to_orm(self) -> PropertyDefinitionORM:
        """Convert to ORM object"""
        definition = PropertyDefinitionORM(
            key=self.key,
            label=self.label,
            input_kind=self.input_kind,
            storage_kind=self.storage_kind,
            value_type=self.value_type,
            allow_supplier_create=self.allow_supplier_create,
            allow_ai_assign=self.allow_ai_assign,
            allow_ai_create_values=self.allow_ai_create_values,
            created_by=self.created_by,
            created_by_supplier_name=self.created_by_supplier_name,
            values=[value.to_orm() for value in self.values],
        )

        return definition
