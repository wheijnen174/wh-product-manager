import json
from typing import Any, cast

from sqlalchemy import JSON, BigInteger, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.base_model import Base


class ShopifyStoreAuthentication(Base):
    __tablename__ = "shopify_authorized_stores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    store_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )

    access_token: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    token_encryption_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )

    api_version: Mapped[str] = mapped_column(String(10))
    api_batch_delay: Mapped[float] = mapped_column(Float)

    extra_data: Mapped[JSON] = mapped_column(JSON, server_default="{}", nullable=False)

    def get_extra_data(
        self,
    ) -> dict[str, Any]:
        extra_data_raw: Any = self.extra_data
        if extra_data_raw is None:
            extra_data: dict[str, Any] = {}
        elif isinstance(extra_data_raw, str):
            try:
                parsed = json.loads(extra_data_raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in store.extra_data for store={self.id}"
                ) from exc

            if not isinstance(parsed, dict):
                raise ValueError(
                    f"Expected JSON object in store.extra_data for store={self.id}, got {type(parsed).__name__}"
                )
            parsed_dict = cast(dict[str, Any], parsed)
            extra_data = parsed_dict
        elif isinstance(extra_data_raw, dict):
            extra_data = cast(dict[str, Any], extra_data_raw)
        else:
            raise ValueError(
                f"Unsupported extra_data type for store={self.id}: {type(extra_data_raw).__name__}"
            )

        return extra_data
