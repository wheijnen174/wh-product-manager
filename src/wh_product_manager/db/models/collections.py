from typing import Optional

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.base_model import Base


class Collections(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    breadcrumbs: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    shopify_category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    collection_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    handle: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    level: Mapped[int] = mapped_column(BigInteger, nullable=False)
