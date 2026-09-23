"""
EvidenceService — creates structured Evidence DB records from agent output.

Every observation produced by an AI agent that has compliance relevance
is persisted as an Evidence record with a human-readable ref ID (EV-001, EV-002…).
Evidence records provide traceability from compliance checks back to source images.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.evidence import Evidence

logger = logging.getLogger(__name__)


class EvidenceService:
    def __init__(self, db: Session):
        self.db = db

    def create_evidence_from_agents(
        self,
        inspection_id: int,
        declaration_result: dict[str, Any],
        quantity_result: dict[str, Any],
        label_result: dict[str, Any],
    ) -> dict[str, str]:
        """
        Create Evidence DB records from all agent outputs.

        Returns:
            evidence_map: {field_key → evidence_ref_id}  e.g. {"mrp": "EV-003"}
        """
        logger.info("[EvidenceService] inspection_id=%s — creating evidence records", inspection_id)

        counter = self._get_next_counter(inspection_id)
        evidence_map: dict[str, str] = {}

        # ── Declaration agent evidence ────────────────────────────────────────
        for decl in declaration_result.get("declarations", []):
            ref_id = f"EV-{counter:03d}"
            ev = Evidence(
                inspection_id=inspection_id,
                image_id=decl.get("source_image_id"),
                evidence_ref_id=ref_id,
                agent_type="declaration_agent",
                evidence_type=decl.get("field", "").upper(),
                field_name=decl.get("field"),
                extracted_value=decl.get("value"),
                confidence=decl.get("confidence"),
                ocr_text=decl.get("value"),
                extra_data={
                    "display_name": decl.get("display_name"),
                    "source_obs_id": decl.get("source_obs_id"),
                },
            )
            self.db.add(ev)
            evidence_map[decl["field"]] = ref_id
            counter += 1

        # ── Quantity agent evidence ───────────────────────────────────────────
        primary_qty = quantity_result.get("primary_quantity")
        if primary_qty:
            ref_id = f"EV-{counter:03d}"
            ev = Evidence(
                inspection_id=inspection_id,
                image_id=primary_qty.get("source_image_id"),
                evidence_ref_id=ref_id,
                agent_type="quantity_agent",
                evidence_type="NET_QUANTITY",
                field_name="net_quantity",
                extracted_value=primary_qty.get("raw_value"),
                confidence=primary_qty.get("confidence"),
                ocr_text=primary_qty.get("raw_value"),
                extra_data={
                    "numeric_value": primary_qty.get("numeric_value"),
                    "unit": primary_qty.get("unit"),
                    "normalized_value": primary_qty.get("normalized_value"),
                    "normalized_unit": primary_qty.get("normalized_unit"),
                    "source_obs_id": primary_qty.get("source_obs_id"),
                },
            )
            self.db.add(ev)
            # quantity evidence maps to both net_quantity and qty_unit keys
            if "net_quantity" not in evidence_map:
                evidence_map["net_quantity"] = ref_id
            evidence_map["quantity_primary"] = ref_id
            counter += 1

        # ── Label agent placement/readability observations ───────────────────
        for obs in label_result.get("placement_observations", []) + label_result.get("readability_observations", []):
            ref_id = f"EV-{counter:03d}"
            ev = Evidence(
                inspection_id=inspection_id,
                image_id=None,
                evidence_ref_id=ref_id,
                agent_type="label_agent",
                evidence_type="OBSERVATION",
                field_name="label_observation",
                extracted_value=obs.get("observation"),
                confidence=obs.get("confidence"),
                ocr_text=None,
                extra_data={"obs_id": obs.get("obs_id")},
            )
            self.db.add(ev)
            counter += 1

        self.db.commit()

        logger.info(
            "[EvidenceService] inspection_id=%s — created %d evidence records",
            inspection_id, counter - 1
        )
        return evidence_map

    def _get_next_counter(self, inspection_id: int) -> int:
        """Get next available evidence counter for this inspection."""
        existing = (
            self.db.query(Evidence)
            .filter(Evidence.inspection_id == inspection_id)
            .count()
        )
        return existing + 1

    def get_all_for_inspection(self, inspection_id: int) -> list[Evidence]:
        return (
            self.db.query(Evidence)
            .filter(Evidence.inspection_id == inspection_id)
            .order_by(Evidence.id)
            .all()
        )
