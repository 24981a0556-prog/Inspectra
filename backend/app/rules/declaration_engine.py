"""
DeclarationEngine — deterministic rule engine for validating label declarations.

Architecture:
  This engine validates structured evidence produced by the DeclarationAgent.
  It applies rules from rules.json deterministically (pure logic, no ML).
  It produces PASS / FAIL / NEEDS_VERIFICATION results.

  AI agents provide evidence. This engine applies rules. Humans make final decisions.

Reference: Legal Metrology (Packaged Commodities) Rules, 2011
"""
from __future__ import annotations

import logging
from typing import Any

from app.rules.rule_loader import get_rule_loader

logger = logging.getLogger(__name__)


class DeclarationEngine:
    """
    Deterministic rule engine for declaration completeness and format validation.

    Input: Structured output from DeclarationAgent
    Output: List of compliance check results

    Each result:
    {
      "rule_id": "DECL-MRP-001",
      "rule_name": "MRP Declaration",
      "rule_ref": "Rule 18",
      "field": "mrp",
      "status": "PASS",           # PASS | FAIL | NEEDS_VERIFICATION
      "severity": "CRITICAL",
      "reason": "MRP declaration detected with high confidence.",
      "confidence": 0.97,
      "evidence_refs": ["EV-003"],   # Evidence record IDs
      "engine": "declaration",
      "rule_version": "1.0.0"
    }
    """

    ENGINE_NAME = "declaration"

    def evaluate(
        self,
        inspection_id: int,
        declaration_result: dict[str, Any],
        evidence_map: dict[str, str],  # field_key → evidence_ref_id ("EV-001")
    ) -> list[dict[str, Any]]:
        """
        Apply all declaration rules to agent output.

        Args:
            inspection_id: For logging
            declaration_result: Output from DeclarationAgent.run()
            evidence_map: Maps field_key to evidence_ref_id for linking

        Returns:
            List of compliance check dicts
        """
        logger.info("[DeclarationEngine] inspection_id=%s — evaluating declaration rules", inspection_id)

        loader = get_rule_loader()
        rules = loader.get_declaration_rules()
        rule_version = loader.version

        # Build a lookup of detected declarations by field_key
        declarations = declaration_result.get("declarations", [])
        decl_by_field: dict[str, dict] = {}
        for decl in declarations:
            field = decl.get("field")
            if field and field not in decl_by_field:
                decl_by_field[field] = decl

        results = []

        for rule in rules:
            rule_id = rule["id"]
            rule_name = rule.get("name", rule_id)
            rule_ref = rule.get("rule_ref", "")
            field_key = rule.get("field_key", "")
            mandatory = rule.get("mandatory", True)
            severity = rule.get("severity", "MEDIUM")

            detected = decl_by_field.get(field_key)
            evidence_ref = evidence_map.get(field_key)
            evidence_refs = [evidence_ref] if evidence_ref else []

            if detected:
                confidence = detected.get("confidence", 0.85)
                value = detected.get("value", "")

                if confidence >= 0.75:
                    status = "PASS"
                    reason = f"{rule_name} detected: '{_truncate(value, 80)}' (confidence: {confidence:.0%})"
                else:
                    # Low confidence — human verification needed
                    status = "NEEDS_VERIFICATION"
                    reason = (
                        f"{rule_name} detected but with low confidence ({confidence:.0%}). "
                        "Human verification recommended."
                    )
            else:
                if mandatory:
                    status = "FAIL"
                    reason = (
                        f"Required declaration '{rule_name}' could not be detected in the submitted package images. "
                        "This may indicate non-compliance with " + rule_ref + "."
                    )
                    confidence = None
                else:
                    status = "NEEDS_VERIFICATION"
                    reason = (
                        f"Optional declaration '{rule_name}' was not detected. "
                        "Inspector should verify whether this declaration is applicable."
                    )
                    confidence = None

            results.append({
                "rule_id": rule_id,
                "rule_name": rule_name,
                "rule_ref": rule_ref,
                "field": field_key,
                "status": status,
                "severity": severity,
                "reason": reason,
                "confidence": confidence,
                "evidence_refs": evidence_refs,
                "engine": self.ENGINE_NAME,
                "rule_version": rule_version,
                "requires_human_review": status in ("FAIL", "NEEDS_VERIFICATION"),
            })

        passes = sum(1 for r in results if r["status"] == "PASS")
        fails = sum(1 for r in results if r["status"] == "FAIL")
        needs_v = sum(1 for r in results if r["status"] == "NEEDS_VERIFICATION")

        logger.info(
            "[DeclarationEngine] inspection_id=%s — %d rules: %d PASS, %d FAIL, %d NEEDS_VERIFICATION",
            inspection_id, len(results), passes, fails, needs_v
        )
        return results


def _truncate(text: str, max_len: int) -> str:
    return text[:max_len] + "…" if len(text) > max_len else text
