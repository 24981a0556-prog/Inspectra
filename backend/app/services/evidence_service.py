"""
EvidenceService — stub for future evidence extraction from AI agent output.

TODO: Implement after AI agents (label_agent, quantity_agent, declaration_agent) are built.
      This service will:
      1. Accept AI agent output (bounding boxes + OCR text)
      2. Persist Evidence records to the DB
      3. Link Evidence records to ComplianceChecks
"""
from sqlalchemy.orm import Session


class EvidenceService:
    def __init__(self, db: Session):
        self.db = db

    def extract_from_ai_result(self, ai_result_id: int):
        """
        TODO: Parse AIResult.result_json and create Evidence records.
        """
        raise NotImplementedError("EvidenceService is not yet implemented.")
