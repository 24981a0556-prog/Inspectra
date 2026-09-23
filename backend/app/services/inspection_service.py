"""
InspectionService — business logic for inspection creation, numbering, and analysis orchestration.

InspectionOrchestrator coordinates the complete analysis pipeline:
  1. Retrieve images from DB
  2. OCR/Vision (via OCRService)
  3. LabelAgent
  4. QuantityAgent
  5. DeclarationAgent
  6. EvidenceService (persist evidence)
  7. DeclarationEngine (deterministic rule validation)
  8. MeasurementEngine (deterministic rule validation)
  9. Persist AIResult, ComplianceCheck records
 10. Update inspection status

Architecture note:
  AI agents extract and detect. Rule engines validate deterministically. Humans decide.
  The orchestrator never asks AI to determine compliance.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.inspection import Inspection, InspectionStatus
from app.models.ai_result import AIResult
from app.models.compliance_check import ComplianceCheck, ComplianceStatus, ComplianceSeverity
from app.models.inspection_image import InspectionImage

logger = logging.getLogger(__name__)


def generate_inspection_number(db: Session) -> str:
    """
    Generate a sequential inspection number in the format INS-YYYY-NNNNN.
    Example: INS-2026-00001
    """
    year = datetime.utcnow().year
    count = db.query(Inspection).count()
    sequence = count + 1
    return f"INS-{year}-{sequence:05d}"


class InspectionOrchestrator:
    """
    Orchestrates the complete INSPECTRA analysis pipeline for one inspection.

    Usage:
        orchestrator = InspectionOrchestrator(db)
        orchestrator.run(inspection_id)
    """

    def __init__(self, db: Session):
        self.db = db

    def run(self, inspection_id: int) -> dict[str, Any]:
        """
        Execute the full pipeline. Updates DB throughout. Returns summary.
        Raises on unrecoverable errors, but stores error message on inspection.
        """
        logger.info("[Orchestrator] Starting pipeline for inspection_id=%s", inspection_id)

        inspection = self.db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            raise ValueError(f"Inspection {inspection_id} not found")

        # Mark as analyzing
        inspection.status = InspectionStatus.ANALYZING
        inspection.started_at = datetime.now(timezone.utc)
        inspection.analysis_error = None
        self.db.commit()

        try:
            result = self._execute_pipeline(inspection)
            inspection.status = InspectionStatus.REQUIRES_REVIEW
            self.db.commit()
            logger.info("[Orchestrator] Pipeline complete for inspection_id=%s", inspection_id)
            return result
        except Exception as exc:
            logger.error("[Orchestrator] Pipeline failed for inspection_id=%s: %s", inspection_id, exc, exc_info=True)
            inspection.status = InspectionStatus.IN_PROGRESS
            inspection.analysis_error = str(exc)[:1999]
            self.db.commit()
            raise

    def _execute_pipeline(self, inspection: Inspection) -> dict[str, Any]:
        from app.services.ocr_service import get_ocr_service
        from app.agents.label_agent import LabelAgent
        from app.agents.quantity_agent import QuantityAgent
        from app.agents.declaration_agent import DeclarationAgent
        from app.services.evidence_service import EvidenceService
        from app.rules.declaration_engine import DeclarationEngine
        from app.rules.measurement_engine import MeasurementEngine

        inspection_id = inspection.id

        # ── Step 1: Load images ───────────────────────────────────────────────
        logger.info("[Orchestrator] Step 1: Loading images")
        db_images = (
            self.db.query(InspectionImage)
            .filter(InspectionImage.inspection_id == inspection_id)
            .all()
        )
        if not db_images:
            raise ValueError("No images uploaded for this inspection. Please upload package images first.")

        image_dicts = []
        for img in db_images:
            img_bytes = self._load_image_bytes(img.image_url)
            image_dicts.append({
                "id": img.id,
                "bytes": img_bytes,
                "view_type": img.view_type.value if hasattr(img.view_type, 'value') else str(img.view_type),
            })

        # ── Step 2: OCR via LabelAgent ────────────────────────────────────────
        logger.info("[Orchestrator] Step 2-3: Running LabelAgent (OCR + observations)")
        label_agent = LabelAgent()
        label_result = label_agent.run(inspection_id, image_dicts)

        # Persist AIResult for label agent
        label_ai = AIResult(
            inspection_id=inspection_id,
            agent_type="label_agent",
            result_json=label_result,
            confidence=self._avg_confidence(label_result.get("observations", [])),
            model_name=label_result.get("agent", "label-agent-v1"),
            model_version=label_result.get("version", "1.0.0"),
            provider=label_result.get("provider", "demo"),
        )
        self.db.add(label_ai)
        self.db.flush()

        # ── Step 3: QuantityAgent ─────────────────────────────────────────────
        logger.info("[Orchestrator] Step 4: Running QuantityAgent")
        qty_agent = QuantityAgent()
        quantity_result = qty_agent.run(inspection_id, label_result)

        qty_ai = AIResult(
            inspection_id=inspection_id,
            agent_type="quantity_agent",
            result_json=quantity_result,
            confidence=quantity_result.get("primary_quantity", {}).get("confidence") if quantity_result.get("primary_quantity") else None,
            model_name=quantity_result.get("agent", "quantity-agent-v1"),
            model_version=quantity_result.get("version", "1.0.0"),
            provider=label_result.get("provider", "demo"),
        )
        self.db.add(qty_ai)
        self.db.flush()

        # ── Step 4: DeclarationAgent ──────────────────────────────────────────
        logger.info("[Orchestrator] Step 5: Running DeclarationAgent")
        decl_agent = DeclarationAgent()
        declaration_result = decl_agent.run(inspection_id, label_result)

        decl_ai = AIResult(
            inspection_id=inspection_id,
            agent_type="declaration_agent",
            result_json=declaration_result,
            confidence=self._avg_confidence(declaration_result.get("declarations", [])),
            model_name=declaration_result.get("agent", "declaration-agent-v1"),
            model_version=declaration_result.get("version", "1.0.0"),
            provider=label_result.get("provider", "demo"),
        )
        self.db.add(decl_ai)
        self.db.flush()

        # ── Step 5: Create Evidence records ───────────────────────────────────
        logger.info("[Orchestrator] Step 6: Generating evidence records")
        ev_service = EvidenceService(self.db)
        evidence_map = ev_service.create_evidence_from_agents(
            inspection_id, declaration_result, quantity_result, label_result
        )

        # ── Step 6: Declaration Rule Engine ───────────────────────────────────
        logger.info("[Orchestrator] Step 7: Running DeclarationEngine")
        decl_engine = DeclarationEngine()
        decl_checks = decl_engine.evaluate(inspection_id, declaration_result, evidence_map)
        self._persist_compliance_checks(inspection_id, decl_checks)

        # ── Step 7: Measurement Rule Engine ───────────────────────────────────
        logger.info("[Orchestrator] Step 8: Running MeasurementEngine")
        meas_engine = MeasurementEngine()
        meas_checks = meas_engine.evaluate(inspection_id, quantity_result, label_result, evidence_map)
        self._persist_compliance_checks(inspection_id, meas_checks)

        self.db.commit()

        all_checks = decl_checks + meas_checks
        return {
            "inspection_id": inspection_id,
            "label_result": label_result,
            "quantity_result": quantity_result,
            "declaration_result": declaration_result,
            "evidence_map": evidence_map,
            "declaration_checks": decl_checks,
            "measurement_checks": meas_checks,
            "summary": {
                "total_checks": len(all_checks),
                "pass": sum(1 for c in all_checks if c["status"] == "PASS"),
                "fail": sum(1 for c in all_checks if c["status"] == "FAIL"),
                "needs_verification": sum(1 for c in all_checks if c["status"] == "NEEDS_VERIFICATION"),
            }
        }

    def _load_image_bytes(self, image_url: str) -> bytes:
        """Load image bytes from local storage or URL."""
        from app.core.config import settings

        if settings.STORAGE_BACKEND == "local":
            # image_url is like "/uploads/123/filename.jpg"
            # Remove leading slash and prepend the upload dir
            rel_path = image_url.lstrip("/")
            # Try both with and without the 'uploads' prefix
            paths_to_try = [
                os.path.join(settings.LOCAL_UPLOAD_DIR, rel_path.removeprefix("uploads/").lstrip("/")),
                rel_path,
                os.path.join(settings.LOCAL_UPLOAD_DIR, rel_path),
            ]
            for path in paths_to_try:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        return f.read()
            # If not found, return placeholder bytes (1px transparent PNG)
            logger.warning("[Orchestrator] Image file not found: %s — using placeholder", image_url)
            return self._placeholder_image_bytes()
        else:
            import httpx
            resp = httpx.get(image_url, timeout=30)
            resp.raise_for_status()
            return resp.content

    @staticmethod
    def _placeholder_image_bytes() -> bytes:
        """Return a 1x1 white PNG as placeholder when image file is missing."""
        import base64
        # 1x1 white PNG
        b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
            "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
        )
        return base64.b64decode(b64)

    def _avg_confidence(self, items: list[dict]) -> float | None:
        if not items:
            return None
        confs = [i.get("confidence") for i in items if i.get("confidence") is not None]
        return round(sum(confs) / len(confs), 4) if confs else None

    def _persist_compliance_checks(self, inspection_id: int, checks: list[dict]):
        """Persist a list of compliance check dicts to the DB."""
        _severity_map = {
            "LOW": ComplianceSeverity.LOW,
            "MEDIUM": ComplianceSeverity.MEDIUM,
            "HIGH": ComplianceSeverity.HIGH,
            "CRITICAL": ComplianceSeverity.CRITICAL,
        }
        _status_map = {
            "PASS": ComplianceStatus.PASS,
            "FAIL": ComplianceStatus.FAIL,
            "NEEDS_VERIFICATION": ComplianceStatus.NEEDS_VERIFICATION,
        }

        for check in checks:
            cc = ComplianceCheck(
                inspection_id=inspection_id,
                rule_id=check["rule_id"],
                rule_version=check.get("rule_version"),
                rule_name=check.get("rule_name"),
                engine_type=check.get("engine"),
                status=_status_map.get(check["status"], ComplianceStatus.NEEDS_VERIFICATION),
                severity=_severity_map.get(check.get("severity", "MEDIUM"), ComplianceSeverity.MEDIUM),
                message=check.get("reason"),
                confidence=check.get("confidence"),
                evidence_ref_ids=check.get("evidence_refs", []),
                requires_human_review=check.get("requires_human_review", False),
            )
            self.db.add(cc)
        self.db.flush()
