"""
LabelAgent — AI agent for extracting label text and declarations from package images.

STATUS: NOT IMPLEMENTED — Stub only.

When implemented, this agent will:
1. Accept a list of InspectionImage records (primarily FRONT/BACK views)
2. Run an OCR + vision model to extract all text from the label
3. Identify declared fields: product name, net quantity, MRP, date of mfg, best before,
   manufacturer name & address, importer name (if applicable), customer care info
4. Return a structured JSON result that gets saved to AIResult.result_json
5. Pass results to the DeclarationEngine for rule evaluation

Reference: Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6 mandatory declarations
"""


class LabelAgent:
    def __init__(self, model_name: str = "gemini-2.0-flash", model_version: str = "latest"):
        self.model_name = model_name
        self.model_version = model_version

    def run(self, inspection_id: int, image_ids: list[int]) -> dict:
        """
        TODO: Implement label extraction.
        Returns: dict with extracted fields and bounding boxes.
        """
        raise NotImplementedError("LabelAgent is not yet implemented.")
