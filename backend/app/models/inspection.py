"""
Inspection model — represents a single inspection workflow for a packaged product.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class InspectionStatus(str, enum.Enum):
    DRAFT           = "DRAFT"
    IN_PROGRESS     = "IN_PROGRESS"
    ANALYZING       = "ANALYZING"          # Pipeline is running
    COMPLETED       = "COMPLETED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    CLOSED          = "CLOSED"


class FinalDecision(str, enum.Enum):
    COMPLIANT               = "COMPLIANT"
    NON_COMPLIANT           = "NON_COMPLIANT"
    REQUIRES_FURTHER_REVIEW = "REQUIRES_FURTHER_REVIEW"


class Inspection(Base):
    __tablename__ = "inspections"

    id                      = Column(Integer, primary_key=True, index=True)
    inspection_number       = Column(String(30), unique=True, index=True, nullable=False)
    product_id              = Column(Integer, ForeignKey("products.id"), nullable=False)
    inspector_id            = Column(Integer, ForeignKey("users.id"), nullable=False)
    status                  = Column(Enum(InspectionStatus), nullable=False, default=InspectionStatus.DRAFT)
    notes                   = Column(String(2000), nullable=True)
    started_at              = Column(DateTime(timezone=True), nullable=True)
    completed_at            = Column(DateTime(timezone=True), nullable=True)
    created_at              = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Analysis pipeline state
    analysis_error          = Column(String(2000), nullable=True)
    is_demo                 = Column(Boolean, default=False)
    # Human verification fields
    final_decision          = Column(Enum(FinalDecision), nullable=True)
    final_decision_comment  = Column(String(2000), nullable=True)
    finalized_at            = Column(DateTime(timezone=True), nullable=True)
    finalized_by_id         = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    product           = relationship("Product", backref="inspections")
    inspector         = relationship("User", foreign_keys=[inspector_id], backref="inspections")
    finalized_by      = relationship("User", foreign_keys=[finalized_by_id])
    images            = relationship("InspectionImage", back_populates="inspection", cascade="all, delete-orphan")
    compliance_checks = relationship("ComplianceCheck", back_populates="inspection", cascade="all, delete-orphan")
    ai_results        = relationship("AIResult", back_populates="inspection", cascade="all, delete-orphan")
    evidences         = relationship("Evidence", back_populates="inspection", cascade="all, delete-orphan")
    human_reviews     = relationship("HumanReview", back_populates="inspection", cascade="all, delete-orphan")

