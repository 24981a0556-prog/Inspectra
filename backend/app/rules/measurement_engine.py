"""
MeasurementEngine — deterministic rule engine for net quantity and presentation validation.

Architecture:
  This engine validates structured evidence produced by the QuantityAgent and LabelAgent.
  It applies measurement and presentation rules deterministically (pure logic, no ML).
  It produces PASS / FAIL / NEEDS_VERIFICATION results.

Reference: Legal Metrology (Packaged Commodities) Rules, 2011
  - Rule 6(1)(b): Net quantity declaration in standard units
  - Schedule II: Standard weights and measures
"""
from __future__ import annotations

import logging
from typing import Any

from app.rules.rule_loader import get_rule_loader

logger = logging.getLogger(__name__)

# Units recognised as standard under LM(PC) Rules 2011
_STANDARD_UNITS = {
    "g", "gram", "grams", "gm",
    "kg", "kilogram", "kilograms",
    "ml", "millilitre", "millilitres", "milliliter", "milliliters",
    "l", "litre", "litres", "liter", "liters",
}


class MeasurementEngine:
    """
    Deterministic rule engine for net quantity and presentation validation.

    Input: Structured output from QuantityAgent + LabelAgent
    Output: List of compliance check results
    """

    ENGINE_NAME = "measurement"

    def evaluate(
        self,
        inspection_id: int,
        quantity_result: dict[str, Any],
        label_result: dict[str, Any],
        evidence_map: dict[str, str],   # field_key → evidence_ref_id
    ) -> list[dict[str, Any]]:
        """
        Apply all measurement rules to agent output.

        Args:
            inspection_id: For logging
            quantity_result: Output from QuantityAgent.run()
            label_result: Output from LabelAgent.run() (for readability)
            evidence_map: Maps field_key to evidence_ref_id

        Returns:
            List of compliance check dicts
        """
        logger.info("[MeasurementEngine] inspection_id=%s — evaluating measurement rules", inspection_id)

        loader = get_rule_loader()
        rules = loader.get_measurement_rules()
        rule_version = loader.version

        results = []

        for rule in rules:
            rule_id = rule["id"]
            rule_name = rule.get("name", rule_id)
            rule_ref = rule.get("rule_ref", "")
            severity = rule.get("severity", "MEDIUM")
            vtype = rule.get("validation_type", "")

            result = self._apply_rule(
                rule=rule,
                rule_version=rule_version,
                quantity_result=quantity_result,
                label_result=label_result,
                evidence_map=evidence_map,
            )
            results.append(result)

        passes = sum(1 for r in results if r["status"] == "PASS")
        fails = sum(1 for r in results if r["status"] == "FAIL")
        needs_v = sum(1 for r in results if r["status"] == "NEEDS_VERIFICATION")

        logger.info(
            "[MeasurementEngine] inspection_id=%s — %d rules: %d PASS, %d FAIL, %d NEEDS_VERIFICATION",
            inspection_id, len(results), passes, fails, needs_v
        )
        return results

    def _apply_rule(
        self,
        rule: dict[str, Any],
        rule_version: str,
        quantity_result: dict[str, Any],
        label_result: dict[str, Any],
        evidence_map: dict[str, str],
    ) -> dict[str, Any]:
        rule_id = rule["id"]
        rule_name = rule.get("name", rule_id)
        rule_ref = rule.get("rule_ref", "")
        severity = rule.get("severity", "MEDIUM")
        vtype = rule.get("validation_type", "")
        mandatory = rule.get("mandatory", True)

        qty_detected = quantity_result.get("detected", False)
        primary_qty = quantity_result.get("primary_quantity")
        evidence_ref = evidence_map.get("net_quantity")
        evidence_refs = [evidence_ref] if evidence_ref else []

        if vtype == "quantity_presence":
            if qty_detected and primary_qty:
                status = "PASS"
                reason = f"Net quantity declaration detected: '{primary_qty.get('raw_value', '')}' (confidence: {primary_qty.get('confidence', 0):.0%})"
                confidence = primary_qty.get("confidence")
            else:
                status = "FAIL"
                reason = "Net quantity declaration could not be detected in the submitted package images. This may indicate non-compliance with " + rule_ref + "."
                confidence = None

        elif vtype == "unit_validity":
            if not qty_detected or not primary_qty:
                status = "NEEDS_VERIFICATION"
                reason = "Unit validation skipped — no quantity detected."
                confidence = None
            else:
                unit = primary_qty.get("unit", "").lower().strip()
                if unit in _STANDARD_UNITS:
                    status = "PASS"
                    reason = f"Net quantity expressed in standard unit '{unit}' as required by {rule_ref}."
                    confidence = primary_qty.get("confidence")
                else:
                    status = "FAIL"
                    reason = f"Unit '{unit}' is not a recognised standard unit under {rule_ref}. Standard units: g, kg, ml, L."
                    confidence = primary_qty.get("confidence")

        elif vtype == "value_range":
            if not qty_detected or not primary_qty:
                status = "NEEDS_VERIFICATION"
                reason = "Value range validation skipped — no quantity detected."
                confidence = None
            else:
                norm_val = primary_qty.get("normalized_value", 0)
                min_val = rule.get("min_normalized", 0.01)
                max_val = rule.get("max_normalized", 50000)
                if min_val <= norm_val <= max_val:
                    status = "PASS"
                    reason = f"Declared quantity value {primary_qty.get('raw_value', '')} is within plausible range."
                    confidence = primary_qty.get("confidence")
                else:
                    status = "FAIL"
                    reason = f"Declared quantity value {norm_val} {primary_qty.get('normalized_unit', '')} is outside plausible range."
                    confidence = primary_qty.get("confidence")

        elif vtype == "readability_check":
            observations = label_result.get("observations", [])
            if not observations:
                status = "NEEDS_VERIFICATION"
                reason = "No text regions detected — readability cannot be assessed. Human verification required."
                confidence = None
                evidence_refs = []
            else:
                avg_conf = sum(o.get("confidence", 0) for o in observations) / len(observations)
                threshold = rule.get("confidence_threshold", 0.80)
                if avg_conf >= threshold:
                    status = "PASS"
                    reason = f"Label text appears legible — average extraction confidence {avg_conf:.0%} meets threshold ({threshold:.0%})."
                    confidence = avg_conf
                else:
                    status = "NEEDS_VERIFICATION"
                    reason = f"Label text readability may be insufficient — average confidence {avg_conf:.0%} is below threshold ({threshold:.0%}). Human verification recommended."
                    confidence = avg_conf
                evidence_refs = []

        else:
            status = "NEEDS_VERIFICATION"
            reason = f"Rule validation type '{vtype}' is not yet implemented. Human verification required."
            confidence = None

        return {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "rule_ref": rule_ref,
            "field": vtype,
            "status": status,
            "severity": severity,
            "reason": reason,
            "confidence": confidence,
            "evidence_refs": evidence_refs,
            "engine": self.ENGINE_NAME,
            "rule_version": rule_version,
            "requires_human_review": status in ("FAIL", "NEEDS_VERIFICATION"),
        }
