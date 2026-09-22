"""
Evidence model — stores bounding box and OCR data extracted by AI agents.
NOTE: This table is a stub. No evidence extraction is implemented yet.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from app.core.database import Base


class Evidence(Base):
    __tablename__ = "evidences"

    id            = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    image_id      = Column(Integer, ForeignKey("inspection_images.id"), nullable=True)
    evidence_type = Column(String(100), nullable=True)  # e.g. "MRP_TEXT", "NET_WEIGHT"
    bbox_x        = Column(Float, nullable=True)
    bbox_y        = Column(Float, nullable=True)
    bbox_width    = Column(Float, nullable=True)
    bbox_height   = Column(Float, nullable=True)
    ocr_text      = Column(String(1000), nullable=True)
    confidence    = Column(Float, nullable=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
