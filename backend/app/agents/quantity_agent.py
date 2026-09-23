"""
QuantityAgent — identifies and normalizes net quantity declarations from package labels.

Architecture note:
  This agent EXTRACTS and NORMALIZES only.
  It does NOT determine legal compliance.
  Compliance is determined downstream by the MeasurementEngine rule engine.

Reference: Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(b)
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Supported unit normalization map
# All weights → grams, all volumes → millilitres
_UNIT_NORMALIZE = {
    "g": ("g", 1.0),
    "gram": ("g", 1.0),
    "grams": ("g", 1.0),
    "gm": ("g", 1.0),
    "kg": ("g", 1000.0),
    "kilogram": ("g", 1000.0),
    "kilograms": ("g", 1000.0),
    "ml": ("ml", 1.0),
    "millilitre": ("ml", 1.0),
    "millilitres": ("ml", 1.0),
    "milliliter": ("ml", 1.0),
    "milliliters": ("ml", 1.0),
    "l": ("ml", 1000.0),
    "litre": ("ml", 1000.0),
    "litres": ("ml", 1000.0),
    "liter": ("ml", 1000.0),
    "liters": ("ml", 1000.0),
}

# Supported units for display (must be in this set to pass the unit validation rule)
SUPPORTED_UNITS = {"g", "kg", "ml", "l", "litre", "liter"}

# Regex pattern to match quantity declarations
_QTY_PATTERN = re.compile(
    r'\b(\d+(?:[.,]\d+)?)\s*'
    r'(kg|kilogram|kilograms|g|gram|grams|gm|'
    r'l|litre|litres|liter|liters|ml|millilitre|millilitres|milliliter|milliliters)\b',
    re.IGNORECASE
)

# Pattern to find Net Quantity declarations specifically
_NET_QTY_PATTERN = re.compile(
    r'(?:net\s+(?:quantity|qty|weight|wt|content|contents?)?[\s:]*)?'
    r'\b(\d+(?:[.,]\d+)?)\s*'
    r'(kg|kilogram|kilograms|g|gram|grams|gm|'
    r'l|litre|litres|liter|liters|ml|millilitre|millilitres|milliliter|milliliters)\b',
    re.IGNORECASE
)


class QuantityAgent:
    """
    Identifies and normalizes net quantity declarations from label agent output.

    Output schema (result_json):
    {
      "detected": true,
      "quantities": [
        {
          "raw_value": "1 kg (1000 g)",
          "numeric_value": 1.0,
          "unit": "kg",
          "normalized_value": 1000.0,
          "normalized_unit": "g",
          "confidence": 0.97,
          "source_image_id": 5,
          "source_obs_id": "OBS-003",
          "is_primary": true
        }
      ],
      "primary_quantity": {...},
      "agent": "quantity-agent-v1",
      "version": "1.0.0"
    }
    """

    MODEL_NAME = "quantity-agent-v1"
    MODEL_VERSION = "1.0.0"

    def run(
        self,
        inspection_id: int,
        label_agent_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract quantity from label agent observations.

        Args:
            inspection_id: For logging
            label_agent_result: Output from LabelAgent.run()

        Returns:
            Structured quantity agent output
        """
        logger.info("[QuantityAgent] inspection_id=%s — parsing quantity from label observations", inspection_id)

        observations = label_agent_result.get("observations", [])
        detected_quantities = []

        for obs in observations:
            text = obs.get("text", "")
            image_id = obs.get("image_id")
            obs_id = obs.get("obs_id")
            base_confidence = obs.get("confidence", 0.85)

            # Look for Net Quantity pattern first
            for match in _NET_QTY_PATTERN.finditer(text):
                qty = self._parse_match(match, image_id, obs_id, base_confidence, text)
                if qty:
                    # Boost confidence if explicitly labelled as "Net Quantity"
                    if re.search(r'net\s+(quantity|qty|weight|wt)', text, re.IGNORECASE):
                        qty["confidence"] = min(qty["confidence"] + 0.05, 1.0)
                        qty["is_net_declared"] = True
                    detected_quantities.append(qty)

        # Deduplicate by (numeric_value, unit)
        seen = set()
        unique_quantities = []
        for q in detected_quantities:
            key = (q["normalized_value"], q["normalized_unit"])
            if key not in seen:
                seen.add(key)
                unique_quantities.append(q)

        # Mark primary (highest confidence)
        if unique_quantities:
            unique_quantities.sort(key=lambda x: x["confidence"], reverse=True)
            unique_quantities[0]["is_primary"] = True
            for q in unique_quantities[1:]:
                q["is_primary"] = False

        primary = unique_quantities[0] if unique_quantities else None

        result = {
            "detected": bool(unique_quantities),
            "quantities": unique_quantities,
            "primary_quantity": primary,
            "agent": self.MODEL_NAME,
            "version": self.MODEL_VERSION,
        }

        logger.info(
            "[QuantityAgent] inspection_id=%s — detected=%s, primary=%s",
            inspection_id,
            result["detected"],
            primary.get("raw_value") if primary else "None"
        )
        return result

    def _parse_match(
        self,
        match: re.Match,
        image_id: int | None,
        obs_id: str | None,
        base_confidence: float,
        source_text: str,
    ) -> dict[str, Any] | None:
        try:
            raw_num_str = match.group(1).replace(",", ".")
            raw_unit = match.group(2).lower()
            numeric_value = float(raw_num_str)

            if raw_unit not in _UNIT_NORMALIZE:
                return None

            norm_unit, factor = _UNIT_NORMALIZE[raw_unit]
            normalized_value = numeric_value * factor

            # Skip implausible values (e.g. year numbers, phone numbers)
            if normalized_value > 100_000 or normalized_value < 0.01:
                return None

            raw_value = f"{raw_num_str} {raw_unit}"

            return {
                "raw_value": raw_value,
                "numeric_value": numeric_value,
                "unit": raw_unit,
                "normalized_value": normalized_value,
                "normalized_unit": norm_unit,
                "confidence": round(base_confidence * 0.97, 4),
                "source_image_id": image_id,
                "source_obs_id": obs_id,
                "is_primary": False,
                "is_net_declared": False,
            }
        except (ValueError, IndexError):
            return None
