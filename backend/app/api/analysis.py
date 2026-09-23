"""
Analysis API — triggers and retrieves results from the INSPECTRA analysis pipeline.

Endpoints:
  POST /inspections/{id}/analyze        — trigger analysis pipeline (background)
  GET  /inspections/{id}/analysis       — get AI agent results
  GET  /inspections/{id}/evidence       — get structured evidence records
  GET  /inspections/{id}/compliance     — get compliance check results
  POST /inspections/{id}/review/{cid}   — submit human review for one finding
  POST /inspections/{id}/finalize       — submit final inspection decision
  GET  /inspections/{id}/report         — generate and download PDF report

Architecture note:
  Analysis is triggered in a background thread to avoid blocking the HTTP response.
  The frontend polls /analysis for status updates.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.inspection import Inspection, InspectionStatus, FinalDecision
from app.models.ai_result import AIResult
from app.models.evidence import Evidence
from app.models.compliance_check import ComplianceCheck, ComplianceStatus

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisStatusOut(BaseModel):
    inspection_id: int
    status: str
    analysis_error: Optional[str] = None
    ai_results_count: int
    evidence_count: int
    compliance_checks_count: int


class AIResultOut(BaseModel):
    id: int
    inspection_id: int
    agent_type: str
    result_json: Optional[dict] = None
    confidence: Optional[float] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    provider: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    id: int
    inspection_id: int
    image_id: Optional[int] = None
    evidence_ref_id: Optional[str] = None
    agent_type: Optional[str] = None
    evidence_type: Optional[str] = None
    field_name: Optional[str] = None
    extracted_value: Optional[str] = None
    confidence: Optional[float] = None
    ocr_text: Optional[str] = None
    extra_data: Optional[dict] = None
    created_at: str

    model_config = {"from_attributes": True}


class ComplianceCheckOut(BaseModel):
    id: int
    inspection_id: int
    rule_id: str
    rule_name: Optional[str] = None
    engine_type: Optional[str] = None
    status: str
    severity: Optional[str] = None
    message: Optional[str] = None
    confidence: Optional[float] = None
    evidence_ref_ids: Optional[list] = None
    requires_human_review: bool
    human_reviewed: bool
    human_action: Optional[str] = None
    human_comment: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class ReviewPayload(BaseModel):
    action: str          # "CONFIRM" | "REJECT" | "NEEDS_VERIFICATION"
    comment: Optional[str] = None


class FinalizePayload(BaseModel):
    decision: str        # "COMPLIANT" | "NON_COMPLIANT" | "REQUIRES_FURTHER_REVIEW"
    comment: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_inspection_or_404(inspection_id: int, db: Session) -> Inspection:
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return insp


def _dt_str(dt) -> str:
    return dt.isoformat() if dt else ""


# ─────────────────────────────────────────────────────────────────────────────
# POST /inspections/{id}/analyze
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{inspection_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
def start_analysis(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger the analysis pipeline for an inspection.
    Returns immediately with 202. Pipeline runs in a background thread.
    Poll GET /analysis for status updates.
    """
    inspection = _get_inspection_or_404(inspection_id, db)

    # Guard: don't re-run if already analyzing or completed
    if inspection.status == InspectionStatus.ANALYZING:
        return {"message": "Analysis already in progress.", "inspection_id": inspection_id}

    if not inspection.images:
        raise HTTPException(
            status_code=400,
            detail="No images uploaded. Please upload package images before starting analysis."
        )

    from app.core.config import settings
    provider = settings.effective_ocr_provider

    # Run in background thread using a new DB session (thread-safe)
    def _run_pipeline(insp_id: int):
        from app.core.database import SessionLocal
        from app.services.inspection_service import InspectionOrchestrator
        thread_db = SessionLocal()
        try:
            orch = InspectionOrchestrator(thread_db)
            orch.run(insp_id)
        except Exception as e:
            logger.error("Background pipeline failed for inspection %s: %s", insp_id, e)
        finally:
            thread_db.close()

    t = threading.Thread(target=_run_pipeline, args=(inspection_id,), daemon=True)
    t.start()

    return {
        "message": "Analysis pipeline started.",
        "inspection_id": inspection_id,
        "provider": provider,
        "status": "ANALYZING",
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /inspections/{id}/analysis
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{inspection_id}/analysis", response_model=AnalysisStatusOut)
def get_analysis_status(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analysis pipeline status and result counts."""
    inspection = _get_inspection_or_404(inspection_id, db)

    ai_count = db.query(AIResult).filter(AIResult.inspection_id == inspection_id).count()
    ev_count = db.query(Evidence).filter(Evidence.inspection_id == inspection_id).count()
    cc_count = db.query(ComplianceCheck).filter(ComplianceCheck.inspection_id == inspection_id).count()

    return AnalysisStatusOut(
        inspection_id=inspection_id,
        status=inspection.status.value if hasattr(inspection.status, 'value') else str(inspection.status),
        analysis_error=inspection.analysis_error,
        ai_results_count=ai_count,
        evidence_count=ev_count,
        compliance_checks_count=cc_count,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /inspections/{id}/ai-results
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{inspection_id}/ai-results", response_model=List[AIResultOut])
def get_ai_results(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all AI agent results for this inspection."""
    _get_inspection_or_404(inspection_id, db)
    results = (
        db.query(AIResult)
        .filter(AIResult.inspection_id == inspection_id)
        .order_by(AIResult.created_at)
        .all()
    )
    out = []
    for r in results:
        out.append(AIResultOut(
            id=r.id,
            inspection_id=r.inspection_id,
            agent_type=r.agent_type,
            result_json=r.result_json,
            confidence=r.confidence,
            model_name=r.model_name,
            model_version=r.model_version,
            provider=r.provider,
            created_at=_dt_str(r.created_at),
        ))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# GET /inspections/{id}/evidence
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{inspection_id}/evidence", response_model=List[EvidenceOut])
def get_evidence(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all structured evidence records for this inspection."""
    _get_inspection_or_404(inspection_id, db)
    evidences = (
        db.query(Evidence)
        .filter(Evidence.inspection_id == inspection_id)
        .order_by(Evidence.id)
        .all()
    )
    out = []
    for ev in evidences:
        out.append(EvidenceOut(
            id=ev.id,
            inspection_id=ev.inspection_id,
            image_id=ev.image_id,
            evidence_ref_id=ev.evidence_ref_id,
            agent_type=ev.agent_type,
            evidence_type=ev.evidence_type,
            field_name=ev.field_name,
            extracted_value=ev.extracted_value,
            confidence=ev.confidence,
            ocr_text=ev.ocr_text,
            extra_data=ev.extra_data,
            created_at=_dt_str(ev.created_at),
        ))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# GET /inspections/{id}/compliance
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{inspection_id}/compliance", response_model=List[ComplianceCheckOut])
def get_compliance(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all compliance check results for this inspection."""
    _get_inspection_or_404(inspection_id, db)
    checks = (
        db.query(ComplianceCheck)
        .filter(ComplianceCheck.inspection_id == inspection_id)
        .order_by(ComplianceCheck.id)
        .all()
    )
    out = []
    for c in checks:
        out.append(ComplianceCheckOut(
            id=c.id,
            inspection_id=c.inspection_id,
            rule_id=c.rule_id,
            rule_name=c.rule_name,
            engine_type=c.engine_type,
            status=c.status.value if hasattr(c.status, 'value') else str(c.status),
            severity=c.severity.value if c.severity and hasattr(c.severity, 'value') else None,
            message=c.message,
            confidence=c.confidence,
            evidence_ref_ids=c.evidence_ref_ids or [],
            requires_human_review=c.requires_human_review,
            human_reviewed=c.human_reviewed or False,
            human_action=c.human_action,
            human_comment=c.human_comment,
            created_at=_dt_str(c.created_at),
        ))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# POST /inspections/{id}/review/{compliance_check_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{inspection_id}/review/{compliance_check_id}")
def submit_review(
    inspection_id: int,
    compliance_check_id: int,
    payload: ReviewPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit human review for a specific compliance finding."""
    _get_inspection_or_404(inspection_id, db)

    check = db.query(ComplianceCheck).filter(
        ComplianceCheck.id == compliance_check_id,
        ComplianceCheck.inspection_id == inspection_id,
    ).first()
    if not check:
        raise HTTPException(status_code=404, detail="Compliance check not found.")

    valid_actions = {"CONFIRM", "REJECT", "NEEDS_VERIFICATION"}
    if payload.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")

    check.human_reviewed = True
    check.human_action = payload.action
    check.human_comment = payload.comment
    check.human_reviewer_id = current_user.id
    check.human_reviewed_at = datetime.now(timezone.utc)

    db.commit()
    return {"message": "Review submitted.", "compliance_check_id": compliance_check_id, "action": payload.action}


# ─────────────────────────────────────────────────────────────────────────────
# POST /inspections/{id}/finalize
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{inspection_id}/finalize")
def finalize_inspection(
    inspection_id: int,
    payload: FinalizePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit the final inspection decision (human inspector only)."""
    inspection = _get_inspection_or_404(inspection_id, db)

    valid_decisions = {d.value for d in FinalDecision}
    if payload.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision. Must be one of: {valid_decisions}"
        )

    inspection.final_decision = FinalDecision(payload.decision)
    inspection.final_decision_comment = payload.comment
    inspection.finalized_at = datetime.now(timezone.utc)
    inspection.finalized_by_id = current_user.id
    inspection.status = InspectionStatus.COMPLETED
    inspection.completed_at = datetime.now(timezone.utc)

    db.commit()
    return {
        "message": "Final inspection decision recorded.",
        "inspection_id": inspection_id,
        "decision": payload.decision,
        "finalized_by": current_user.name,
        "finalized_at": inspection.finalized_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /inspections/{id}/report
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{inspection_id}/report")
def download_report(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and return the inspection PDF report as a file download."""
    _get_inspection_or_404(inspection_id, db)

    from app.services.report_service import ReportService
    import os

    try:
        svc = ReportService(db)
        report_url = svc.generate_pdf(inspection_id)
        # report_url is like "/uploads/reports/report_inspection_1_20260923.pdf"
        from app.core.config import settings
        # Convert URL to filesystem path
        rel_path = report_url.lstrip("/")
        file_path = rel_path  # relative to cwd
        if not os.path.exists(file_path):
            # Try with uploads dir prefix
            file_path = os.path.join(settings.LOCAL_UPLOAD_DIR, rel_path.removeprefix("uploads/").lstrip("/"))

        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail=f"Report file not found at {file_path}")

        filename = os.path.basename(file_path)
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")
