"""
ReportService — stub for PDF/Excel report generation.

TODO: Implement after compliance checks are produced by the rule engine.
      This service will:
      1. Aggregate all ComplianceCheck records for an Inspection
      2. Pull Evidence records and image URLs
      3. Render a PDF report (suggested: reportlab or weasyprint)
      4. Save the PDF via StorageService
      5. Return the download URL
"""
from sqlalchemy.orm import Session


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def generate_pdf(self, inspection_id: int) -> str:
        """
        TODO: Generate a compliance report PDF and return its download URL.
        """
        raise NotImplementedError("ReportService is not yet implemented.")
