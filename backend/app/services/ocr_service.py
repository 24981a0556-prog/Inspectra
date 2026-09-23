"""
OCRService — Abstract interface for OCR/Vision providers.

Architecture:
  The application calls OCRService.extract_text(image_bytes).
  The concrete provider is swapped by configuration (OCR_PROVIDER env var).

Providers implemented:
  - DemoOCRProvider  : Deterministic, realistic output. No API key needed. Used for prototyping.
  - GeminiOCRProvider: Calls Google Gemini Vision. Requires GEMINI_API_KEY.

AI extracts and detects. It does NOT determine legal compliance.
Compliance is determined by deterministic rule engines after extraction.
"""
from __future__ import annotations

import abc
import base64
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class OCRService(abc.ABC):
    """Abstract base class for all OCR/Vision providers."""

    @abc.abstractmethod
    def extract_text(self, image_bytes: bytes, image_id: int | None = None) -> dict[str, Any]:
        """
        Extract structured text and observations from an image.

        Returns a dict with keys:
          raw_text      : Full raw text extracted from image
          text_blocks   : List of {text, confidence, position_hint}
          provider      : Name of the provider used
          image_id      : Echo of input image_id
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Demo Provider — deterministic, realistic, no API required
# ─────────────────────────────────────────────────────────────────────────────

# DEMO PACKAGE: Tata Salt 1kg
# This dataset represents a realistic Indian packaged commodity label.
# It is used exclusively for demonstration and testing purposes.
# Results are deterministic and repeatable.
_DEMO_LABEL_TEXT = """TATA SALT
IODISED SALT
Net Quantity: 1 kg (1000 g)
MRP (Incl. of all taxes): ₹28.00
Best Before: 24 months from date of manufacture
Manufactured by: Tata Consumer Products Limited
Address: Tata Consumer Products Ltd., Regd. Office: 1, Bishop Lefroy Road, Kolkata - 700 020
Country of Origin: India
Consumer Care: 1800-11-8765 (Toll Free)
FSSAI Lic. No. 10013032001010
Manufactured at: Unit No. 8, Plot No. 67-77, APMC Yard, Turbhe Navi Mumbai - 400 703
Month & Year of Manufacture: See top of pack
"""

_DEMO_TEXT_BLOCKS = [
    {"text": "TATA SALT", "confidence": 0.99, "position_hint": "top-center"},
    {"text": "IODISED SALT", "confidence": 0.98, "position_hint": "top-center"},
    {"text": "Net Quantity: 1 kg (1000 g)", "confidence": 0.97, "position_hint": "center-left"},
    {"text": "MRP (Incl. of all taxes): ₹28.00", "confidence": 0.98, "position_hint": "center-right"},
    {"text": "Best Before: 24 months from date of manufacture", "confidence": 0.95, "position_hint": "bottom-left"},
    {"text": "Manufactured by: Tata Consumer Products Limited", "confidence": 0.96, "position_hint": "bottom-left"},
    {"text": "Address: Tata Consumer Products Ltd., Regd. Office: 1, Bishop Lefroy Road, Kolkata - 700 020", "confidence": 0.92, "position_hint": "bottom-left"},
    {"text": "Country of Origin: India", "confidence": 0.99, "position_hint": "bottom-right"},
    {"text": "Consumer Care: 1800-11-8765 (Toll Free)", "confidence": 0.94, "position_hint": "bottom-right"},
    {"text": "FSSAI Lic. No. 10013032001010", "confidence": 0.93, "position_hint": "bottom-center"},
    {"text": "Manufactured at: Unit No. 8, Plot No. 67-77, APMC Yard, Turbhe Navi Mumbai - 400 703", "confidence": 0.88, "position_hint": "bottom-left"},
    {"text": "Month & Year of Manufacture: See top of pack", "confidence": 0.91, "position_hint": "bottom-left"},
]


class DemoOCRProvider(OCRService):
    """
    DEMO OCR Provider — for prototyping and presentation.

    Produces realistic, deterministic structured output representing a standard
    Indian packaged commodity (Tata Salt 1kg).

    This provider is clearly identified in all output as 'demo'.
    It does NOT represent the output of a real OCR system.
    It is used only when no real API key is configured.
    """

    PROVIDER_NAME = "demo"

    def extract_text(self, image_bytes: bytes, image_id: int | None = None) -> dict[str, Any]:
        logger.info("[DEMO OCR] Processing image_id=%s — using Demo OCR Provider", image_id)
        return {
            "raw_text": _DEMO_LABEL_TEXT,
            "text_blocks": _DEMO_TEXT_BLOCKS,
            "provider": self.PROVIDER_NAME,
            "image_id": image_id,
            "note": "DEMO: Output is deterministic demo data, not from real OCR processing.",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Gemini Provider — uses Google Gemini Vision API
# ─────────────────────────────────────────────────────────────────────────────

class GeminiOCRProvider(OCRService):
    """
    Gemini Vision OCR Provider.
    Requires GEMINI_API_KEY in environment.
    Falls back to DemoOCRProvider if the API call fails.
    """

    PROVIDER_NAME = "gemini"
    MODEL = "gemini-1.5-flash"

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._client = genai.GenerativeModel(self.MODEL)
            except ImportError:
                logger.warning("google-generativeai not installed, falling back to demo provider.")
                return None
        return self._client

    def extract_text(self, image_bytes: bytes, image_id: int | None = None) -> dict[str, Any]:
        client = self._get_client()
        if client is None:
            logger.warning("[Gemini OCR] Client unavailable, falling back to Demo provider.")
            return DemoOCRProvider().extract_text(image_bytes, image_id)

        try:
            import google.generativeai as genai
            image_part = {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}
            prompt = (
                "You are an OCR assistant for a legal metrology inspection system. "
                "Extract ALL text visible on this product packaging label. "
                "Return a JSON object with two keys:\n"
                "1. 'raw_text': complete extracted text as a single string\n"
                "2. 'text_blocks': array of objects, each with 'text' (string), 'confidence' (0-1 float), 'position_hint' (string describing location)\n"
                "Extract everything visible. Do not interpret or assess compliance."
            )
            response = client.generate_content([prompt, image_part])
            text = response.text.strip()
            # Try to parse JSON from response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                data["provider"] = self.PROVIDER_NAME
                data["image_id"] = image_id
                return data
            # If not JSON, wrap as raw_text
            return {
                "raw_text": text,
                "text_blocks": [{"text": text, "confidence": 0.85, "position_hint": "unknown"}],
                "provider": self.PROVIDER_NAME,
                "image_id": image_id,
            }
        except Exception as exc:
            logger.error("[Gemini OCR] API call failed: %s. Falling back to demo provider.", exc)
            result = DemoOCRProvider().extract_text(image_bytes, image_id)
            result["provider"] = f"gemini-fallback-to-demo"
            return result


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def get_ocr_service() -> OCRService:
    """
    Factory: returns the appropriate OCR service based on app configuration.
    Always falls back safely to the Demo provider.
    """
    from app.core.config import settings
    provider = settings.effective_ocr_provider
    if provider == "gemini" and settings.GEMINI_API_KEY:
        logger.info("OCR Provider: Gemini Vision")
        return GeminiOCRProvider(api_key=settings.GEMINI_API_KEY)
    logger.info("OCR Provider: Demo (no real API configured)")
    return DemoOCRProvider()
