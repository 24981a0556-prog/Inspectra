"""
ComplianceCheck model — stores the result of a deterministic rule evaluation for a given inspection.
AI agents provide structured evidence. This model records the rule engine's deterministic verdict.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Enum, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class ComplianceStatus(str, enum.Enum):
    NOT_CHECKED        = "NOT_CHECKED"
    PROCESSING         = "PROCESSING"
    PASS               = "PASS"
    FAIL               = "FAIL"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
    NOT_APPLICABLE     = "NOT_APPLICABLE"


class ComplianceSeverity(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id                    = Column(Integer, primary_key=True, index=True)
    inspection_id         = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    rule_id               = Column(String(100), nullable=False)
    rule_version          = Column(String(20), nullable=True)
    rule_name             = Column(String(255), nullable=True)
    engine_type           = Column(String(50), nullable=True)    # "declaration" | "measurement"
    status                = Column(Enum(ComplianceStatus), nullable=False, default=ComplianceStatus.NOT_CHECKED)
    severity              = Column(Enum(ComplianceSeverity), nullable=True)
    message               = Column(String(2000), nullable=True)
    confidence            = Column(Float, nullable=True)
    evidence_ref_ids      = Column(JSON, nullable=True)          # List of "EV-001", "EV-002"
    evidence_id           = Column(Integer, ForeignKey("evidences.id"), nullable=True)
    requires_human_review = Column(Boolean, default=False)
    # Human review override
    human_reviewed        = Column(Boolean, default=False)
    human_action          = Column(String(50), nullable=True)    # "CONFIRM" | "REJECT" | "NEEDS_VERIFICATION"
    human_comment         = Column(String(2000), nullable=True)
    human_reviewer_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    human_reviewed_at     = Column(DateTime(timezone=True), nullable=True)
    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    inspection            = relationship("Inspection", back_populates="compliance_checks")
    human_reviewer        = relationship("User", foreign_keys=[human_reviewer_id])
