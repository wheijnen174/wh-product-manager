from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from wh_product_manager.db.models.base import Base


class ShopifyCategoryTaxonomies(Base):
    __tablename__ = "shopify_category_taxonomies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
