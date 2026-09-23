"""
Evidence model — stores structured evidence produced by AI agents for a given inspection.
Each evidence record is linked to a source image and a specific agent.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Evidence(Base):
    __tablename__ = "evidences"

    id               = Column(Integer, primary_key=True, index=True)
    inspection_id    = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    image_id         = Column(Integer, ForeignKey("inspection_images.id"), nullable=True)
    # Human-readable ref: "EV-001", "EV-002" — used in rule results
    evidence_ref_id  = Column(String(20), nullable=True, index=True)
    # Which agent produced this evidence
    agent_type       = Column(String(50), nullable=True)   # "label_agent" | "quantity_agent" | "declaration_agent"
    # Type/category of evidence
    evidence_type    = Column(String(100), nullable=True)  # e.g. "MRP_TEXT", "NET_WEIGHT", "MANUFACTURER"
    field_name       = Column(String(100), nullable=True)  # e.g. "mrp", "net_quantity", "manufacturer"
    extracted_value  = Column(String(1000), nullable=True) # The actual extracted text/value
    # Bounding box (nullable — not all agents produce bbox)
    bbox_x           = Column(Float, nullable=True)
    bbox_y           = Column(Float, nullable=True)
    bbox_width       = Column(Float, nullable=True)
    bbox_height      = Column(Float, nullable=True)
    ocr_text         = Column(String(1000), nullable=True)
    confidence       = Column(Float, nullable=True)
    extra_data       = Column(JSON, nullable=True)         # Additional structured data
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    inspection       = relationship("Inspection", back_populates="evidences")
    image            = relationship("InspectionImage")
