"""
InspectionImage model — stores metadata for each image uploaded to an inspection.
The actual file bytes are handled by the StorageService abstraction.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class ViewType(str, enum.Enum):
    FRONT  = "FRONT"
    BACK   = "BACK"
    LEFT   = "LEFT"
    RIGHT  = "RIGHT"
    TOP    = "TOP"
    BOTTOM = "BOTTOM"
    OTHER  = "OTHER"


class InspectionImage(Base):
    __tablename__ = "inspection_images"

    id            = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    # image_url stores the storage path/key — resolved to a URL by StorageService
    image_url     = Column(String(1024), nullable=False)
    view_type     = Column(Enum(ViewType), nullable=False, default=ViewType.OTHER)
    file_hash     = Column(String(64), nullable=True)   # SHA-256 for integrity
    original_filename = Column(String(512), nullable=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    inspection    = relationship("Inspection", back_populates="images")
