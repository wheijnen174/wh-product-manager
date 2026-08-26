from dataclasses import dataclass
from typing import Any, Optional

from wh_product_manager.db.models.products.media import MediaORM

content_type_mapping = {
    "image": "IMAGE",
    "video": "VIDEO",
    "model": "MODEL_3D",
}


@dataclass
class UnifiedMedia:
    """Standard product media structure across all suppliers"""

    source_url: str
    filename: Optional[str] = None
    alt_text: Optional[str] = None
    content_type: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "source_url": self.source_url,
            "filename": self.filename,
            "alt_text": self.alt_text,
            "content_type": self.content_type,
        }

    def to_orm(self) -> MediaORM:
        """Convert to MediaORM"""
        return MediaORM(
            source_url=self.source_url,
            filename=self.filename,
            alt_text=self.alt_text,
            content_type=self.content_type,
        )
