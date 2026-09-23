"""
HumanReview model — stores the overall human inspector review record for an inspection.
Individual finding reviews are stored inline on ComplianceCheck records for MVP simplicity.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.compliance_check import ComplianceStatus


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id                   = Column(Integer, primary_key=True, index=True)
    inspection_id        = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    compliance_check_id  = Column(Integer, ForeignKey("compliance_checks.id"), nullable=True)
    reviewer_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_status      = Column(Enum(ComplianceStatus), nullable=True)
    final_status         = Column(Enum(ComplianceStatus), nullable=False)
    comment              = Column(String(2000), nullable=True)
    reviewed_at          = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    inspection           = relationship("Inspection", back_populates="human_reviews")
    reviewer             = relationship("User", foreign_keys=[reviewer_id])
