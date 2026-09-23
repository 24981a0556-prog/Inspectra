"""
DeclarationAgent — extracts mandatory package declarations from label agent observations.

Architecture note:
  This agent EXTRACTS and STRUCTURES only.
  It does NOT determine legal compliance.
  Compliance is determined downstream by the DeclarationEngine rule engine.

Reference: Legal Metrology (Packaged Commodities) Rules, 2011
  - Rule 6: Mandatory declarations on every package
  - Rule 18: MRP declaration requirements
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Extraction patterns for each mandatory declaration field
# ─────────────────────────────────────────────────────────────────────────────

_PATTERNS: dict[str, list[re.Pattern]] = {
    "product_identity": [
        re.compile(r'^([A-Z][A-Z\s]{2,30}(?:SALT|SUGAR|FLOUR|TEA|COFFEE|RICE|OIL|SPICE|POWDER|PASTE|SAUCE|JUICE|MILK|GHEE|BUTTER|BISCUIT|COOKIE|CHIP|NOODLE|PASTA|PICKLE|JAM|HONEY|CHOCOLATE|SNACK|CHIPS))', re.IGNORECASE | re.MULTILINE),
    ],
    "manufacturer": [
        re.compile(r'(?:manufactured\s+by|packed\s+by|marketed\s+by|manufactured\s+and\s+packed\s+by)[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
    ],
    "address": [
        re.compile(r'(?:address|regd\.?\s+office|registered\s+office|manufactured\s+at|factory)[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'(?:plot|unit|survey|khasra|door|flat|building|tower|block)[\s.#\-]+.+?(?:\d{6})', re.IGNORECASE),
    ],
    "net_quantity": [
        re.compile(r'net\s+(?:quantity|qty|weight|wt|content)[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'(\d+(?:\.\d+)?\s*(?:kg|g|gram|ml|l|litre|liter)(?:\s*\(\d+\s*(?:g|ml)\))?)', re.IGNORECASE),
    ],
    "mrp": [
        re.compile(r'(?:mrp|maximum\s+retail\s+price|m\.r\.p\.?)\s*(?:\(incl\.?\s+of\s+all\s+taxes?\))?\s*[:\-]?\s*(?:rs\.?|₹|inr)\s*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
        re.compile(r'₹\s*(\d+(?:[.,]\d+)?)', re.IGNORECASE),
    ],
    "manufacture_date": [
        re.compile(r'(?:manufactured|mfg|manufacturing|packed|best\s+before|use\s+by|expiry)\s*(?:date|dt\.?|month|yr|year)?[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'(?:see\s+(?:top|bottom|cap|lid|pack|packet|seal)\s+of\s+pack)', re.IGNORECASE),
    ],
    "consumer_care": [
        re.compile(r'(?:consumer\s+care|helpline|toll\s+free|customer\s+care|contact|call\s+us)[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'(?:\d{4}[-\s]\d{2,4}[-\s]\d{4})', re.IGNORECASE),
    ],
    "country_of_origin": [
        re.compile(r'country\s+of\s+origin[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'made\s+in[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
        re.compile(r'product\s+of[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
    ],
    "fssai_license": [
        re.compile(r'(?:fssai|fpo|agmark|lic\.?\s+no\.?|license\s+no\.?)[\s:]+(.+?)(?:\n|$)', re.IGNORECASE),
    ],
}

_FIELD_DISPLAY = {
    "product_identity":  "Product Identity/Name",
    "manufacturer":      "Manufacturer / Packer",
    "address":           "Address",
    "net_quantity":      "Net Quantity",
    "mrp":               "MRP",
    "manufacture_date":  "Manufacture/Best Before Date",
    "consumer_care":     "Consumer Care Information",
    "country_of_origin": "Country of Origin",
    "fssai_license":     "FSSAI License No.",
}


class DeclarationAgent:
    """
    Extracts applicable mandatory package declarations from label agent output.

    Output schema (result_json):
    {
      "declarations": [
        {
          "field": "mrp",
          "display_name": "MRP",
          "value": "₹28.00",
          "confidence": 0.97,
          "source_image_id": 5,
          "source_obs_id": "OBS-004"
        }
      ],
      "fields_detected": ["product_identity", "manufacturer", "mrp", ...],
      "fields_not_detected": ["country_of_origin"],
      "agent": "declaration-agent-v1",
      "version": "1.0.0"
    }
    """

    MODEL_NAME = "declaration-agent-v1"
    MODEL_VERSION = "1.0.0"

    def run(
        self,
        inspection_id: int,
        label_agent_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract declarations from label observations.

        Args:
            inspection_id: For logging
            label_agent_result: Output from LabelAgent.run()

        Returns:
            Structured declaration agent output
        """
        logger.info("[DeclarationAgent] inspection_id=%s — extracting declarations", inspection_id)

        observations = label_agent_result.get("observations", [])
        raw_text_combined = label_agent_result.get("raw_text_combined", "")

        # Build a lookup of obs by id for provenance
        obs_by_id = {obs["obs_id"]: obs for obs in observations}

        declarations = []
        fields_detected = set()

        for field_key, patterns in _PATTERNS.items():
            best_match = None
            best_confidence = 0.0
            best_obs_id = None
            best_image_id = None

            # Try each observation text
            for obs in observations:
                text = obs.get("text", "")
                obs_conf = obs.get("confidence", 0.85)
                obs_id = obs.get("obs_id")
                image_id = obs.get("image_id")

                for pattern in patterns:
                    m = pattern.search(text)
                    if m:
                        try:
                            value = m.group(1).strip() if m.lastindex else m.group(0).strip()
                        except IndexError:
                            value = m.group(0).strip()

                        value = re.sub(r'\s+', ' ', value).strip()
                        if not value or len(value) < 2:
                            continue

                        confidence = round(obs_conf * 0.95, 4)
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = value
                            best_obs_id = obs_id
                            best_image_id = image_id
                        break

            # Also try searching the combined raw text if not found in obs
            if not best_match and raw_text_combined:
                for pattern in patterns:
                    m = pattern.search(raw_text_combined)
                    if m:
                        try:
                            value = m.group(1).strip() if m.lastindex else m.group(0).strip()
                        except IndexError:
                            value = m.group(0).strip()
                        value = re.sub(r'\s+', ' ', value).strip()
                        if value and len(value) >= 2:
                            best_match = value
                            best_confidence = 0.80
                            break

            if best_match:
                declarations.append({
                    "field": field_key,
                    "display_name": _FIELD_DISPLAY.get(field_key, field_key),
                    "value": best_match,
                    "confidence": best_confidence,
                    "source_image_id": best_image_id,
                    "source_obs_id": best_obs_id,
                })
                fields_detected.add(field_key)

        fields_not_detected = [f for f in _PATTERNS if f not in fields_detected]

        result = {
            "declarations": declarations,
            "fields_detected": list(fields_detected),
            "fields_not_detected": fields_not_detected,
            "total_fields_checked": len(_PATTERNS),
            "agent": self.MODEL_NAME,
            "version": self.MODEL_VERSION,
        }

        logger.info(
            "[DeclarationAgent] inspection_id=%s — %d/%d fields detected",
            inspection_id, len(fields_detected), len(_PATTERNS)
        )
        return result
