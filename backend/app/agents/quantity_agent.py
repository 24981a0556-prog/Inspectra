"""
QuantityAgent — AI agent for verifying net quantity declarations on package labels.

STATUS: NOT IMPLEMENTED — Stub only.

When implemented, this agent will:
1. Accept InspectionImage records
2. Detect and read net quantity declaration (e.g., "500g", "1L", "250ml")
3. Optionally compare against a reference measurement if a scale/measurement image is provided
4. Return structured result with detected quantity, unit, and confidence

Reference: Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(b) net quantity declaration
"""


class QuantityAgent:
    def __init__(self, model_name: str = "gemini-2.0-flash", model_version: str = "latest"):
        self.model_name = model_name
        self.model_version = model_version

    def run(self, inspection_id: int, image_ids: list[int]) -> dict:
        """
        TODO: Implement quantity detection and verification.
        Returns: dict with detected quantity, unit, position, and confidence.
        """
        raise NotImplementedError("QuantityAgent is not yet implemented.")
