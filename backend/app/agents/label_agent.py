"""
LabelAgent — extracts visible text, label regions, placement, and readability observations
from package images using the OCR/Vision service.

Architecture note:
  This agent EXTRACTS and DETECTS only.
  It does NOT determine legal compliance.
  Compliance is determined downstream by the deterministic rule engines.

Reference: Legal Metrology (Packaged Commodities) Rules, 2011
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.ocr_service import get_ocr_service

logger = logging.getLogger(__name__)


class LabelAgent:
    """
    Extracts all label text and structural observations from inspection images.

    Output schema (result_json):
    {
      "observations": [
        {
          "obs_id": "OBS-001",
          "type": "TEXT_REGION",
          "text": "...",
          "image_id": <int>,
          "confidence": 0.94,
          "position_hint": "top-center"
        }
      ],
      "placement_observations": [
        {
          "obs_id": "PLACE-001",
          "observation": "Label text detected on front face",
          "confidence": 0.90
        }
      ],
      "readability_observations": [
        {
          "obs_id": "READ-001",
          "observation": "Text appears legible — high contrast detected",
          "confidence": 0.88
        }
      ],
      "raw_text_combined": "...",
      "provider": "demo",
      "image_count": 3
    }
    """

    MODEL_NAME = "label-agent-v1"
    MODEL_VERSION = "1.0.0"

    def __init__(self):
        self._ocr = get_ocr_service()

    def run(
        self,
        inspection_id: int,
        images: list[dict[str, Any]],  # list of {"id": int, "bytes": bytes, "view_type": str}
    ) -> dict[str, Any]:
        """
        Run label extraction on all provided images.

        Args:
            inspection_id: DB ID of the parent inspection (for logging)
            images: list of image dicts with id, bytes, view_type

        Returns:
            Structured agent output dict
        """
        logger.info("[LabelAgent] inspection_id=%s — processing %d images", inspection_id, len(images))

        all_observations = []
        all_text_parts = []
        obs_counter = 1

        for img in images:
            img_id = img["id"]
            img_bytes = img["bytes"]
            view_type = img.get("view_type", "OTHER")

            ocr_result = self._ocr.extract_text(img_bytes, image_id=img_id)
            text_blocks = ocr_result.get("text_blocks", [])
            raw_text = ocr_result.get("raw_text", "")

            if raw_text:
                all_text_parts.append(raw_text)

            for block in text_blocks:
                obs = {
                    "obs_id": f"OBS-{obs_counter:03d}",
                    "type": "TEXT_REGION",
                    "text": block.get("text", ""),
                    "image_id": img_id,
                    "view_type": view_type,
                    "confidence": block.get("confidence", 0.85),
                    "position_hint": block.get("position_hint", "unknown"),
                }
                all_observations.append(obs)
                obs_counter += 1

        placement_observations = self._detect_placement(all_observations, images)
        readability_observations = self._assess_readability(all_observations)

        provider = images[0]["ocr_provider"] if images and "ocr_provider" in images[0] else self._ocr.__class__.PROVIDER_NAME

        result = {
            "observations": all_observations,
            "placement_observations": placement_observations,
            "readability_observations": readability_observations,
            "raw_text_combined": "\n\n".join(all_text_parts),
            "provider": provider,
            "image_count": len(images),
            "agent": self.MODEL_NAME,
            "version": self.MODEL_VERSION,
        }

        logger.info("[LabelAgent] inspection_id=%s — extracted %d observations", inspection_id, len(all_observations))
        return result

    def _detect_placement(self, observations: list, images: list) -> list[dict]:
        """Generate placement observations from text extraction results."""
        placements = []
        p_counter = 1

        has_front = any(img.get("view_type") == "FRONT" for img in images)
        has_back = any(img.get("view_type") == "BACK" for img in images)

        if has_front:
            placements.append({
                "obs_id": f"PLACE-{p_counter:03d}",
                "observation": "Front face image provided — label extraction performed",
                "confidence": 0.99,
            })
            p_counter += 1

        if has_back:
            placements.append({
                "obs_id": f"PLACE-{p_counter:03d}",
                "observation": "Back face image provided — declaration text extraction performed",
                "confidence": 0.99,
            })
            p_counter += 1

        if observations:
            placements.append({
                "obs_id": f"PLACE-{p_counter:03d}",
                "observation": f"Text regions detected across {len(images)} submitted image(s)",
                "confidence": 0.95,
            })

        return placements

    def _assess_readability(self, observations: list) -> list[dict]:
        """Generate readability observations based on confidence distribution."""
        if not observations:
            return [{
                "obs_id": "READ-001",
                "observation": "No text regions detected — images may be unclear or packaging may lack visible text",
                "confidence": 0.50,
            }]

        avg_confidence = sum(o.get("confidence", 0) for o in observations) / len(observations)
        low_conf_count = sum(1 for o in observations if o.get("confidence", 1) < 0.80)

        readability = []
        r_counter = 1

        if avg_confidence >= 0.90:
            readability.append({
                "obs_id": f"READ-{r_counter:03d}",
                "observation": f"Label text appears legible — average extraction confidence {avg_confidence:.0%}",
                "confidence": avg_confidence,
            })
        elif avg_confidence >= 0.75:
            readability.append({
                "obs_id": f"READ-{r_counter:03d}",
                "observation": f"Label text mostly legible — some regions have reduced confidence ({avg_confidence:.0%} avg)",
                "confidence": avg_confidence,
            })
            r_counter += 1
        else:
            readability.append({
                "obs_id": f"READ-{r_counter:03d}",
                "observation": f"Label text readability is low — manual verification recommended ({avg_confidence:.0%} avg confidence)",
                "confidence": avg_confidence,
            })
            r_counter += 1

        if low_conf_count > 0:
            readability.append({
                "obs_id": f"READ-{r_counter:03d}",
                "observation": f"{low_conf_count} text region(s) have confidence below 80% — human verification may be needed",
                "confidence": 0.70,
            })

        return readability
