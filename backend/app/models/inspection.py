"""
Inspection model — represents a single inspection workflow for a packaged product.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class InspectionStatus(str, enum.Enum):
    DRAFT      = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED  = "COMPLETED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    CLOSED     = "CLOSED"


class Inspection(Base):
    __tablename__ = "inspections"

    id                = Column(Integer, primary_key=True, index=True)
    inspection_number = Column(String(30), unique=True, index=True, nullable=False)
    product_id        = Column(Integer, ForeignKey("products.id"), nullable=False)
    inspector_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    status            = Column(Enum(InspectionStatus), nullable=False, default=InspectionStatus.DRAFT)
    notes             = Column(String(2000), nullable=True)
    started_at        = Column(DateTime(timezone=True), nullable=True)
    completed_at      = Column(DateTime(timezone=True), nullable=True)
    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    product           = relationship("Product", backref="inspections")
    inspector         = relationship("User", backref="inspections")
    images            = relationship("InspectionImage", back_populates="inspection", cascade="all, delete-orphan")
    compliance_checks = relationship("ComplianceCheck", back_populates="inspection", cascade="all, delete-orphan")
