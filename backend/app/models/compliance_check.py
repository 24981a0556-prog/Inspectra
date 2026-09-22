"""
ComplianceCheck model — stores the result of a rule evaluation for a given inspection.
NOTE: This table is a stub. No rule engines are implemented yet.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class ComplianceStatus(str, enum.Enum):
    NOT_CHECKED       = "NOT_CHECKED"
    PROCESSING        = "PROCESSING"
    PASS              = "PASS"
    FAIL              = "FAIL"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    NOT_APPLICABLE    = "NOT_APPLICABLE"


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id                   = Column(Integer, primary_key=True, index=True)
    inspection_id        = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    rule_id              = Column(String(100), nullable=False)
    rule_version         = Column(String(20), nullable=True)
    status               = Column(Enum(ComplianceStatus), nullable=False, default=ComplianceStatus.NOT_CHECKED)
    message              = Column(String(2000), nullable=True)
    confidence           = Column(Float, nullable=True)
    evidence_id          = Column(Integer, ForeignKey("evidences.id"), nullable=True)
    requires_human_review = Column(Boolean, default=False)
    created_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    inspection           = relationship("Inspection", back_populates="compliance_checks")
