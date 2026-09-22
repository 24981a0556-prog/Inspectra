"""
HumanReview model — allows supervisors to override AI compliance decisions.
NOTE: This table is a stub. No human review UI is wired yet.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from app.core.database import Base
from app.models.compliance_check import ComplianceStatus


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id                 = Column(Integer, primary_key=True, index=True)
    inspection_id      = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    compliance_check_id = Column(Integer, ForeignKey("compliance_checks.id"), nullable=True)
    reviewer_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_status    = Column(Enum(ComplianceStatus), nullable=True)
    final_status       = Column(Enum(ComplianceStatus), nullable=False)
    comment            = Column(String(2000), nullable=True)
    reviewed_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
