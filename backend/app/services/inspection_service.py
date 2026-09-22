"""
InspectionService — business logic for inspection creation and numbering.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.inspection import Inspection


def generate_inspection_number(db: Session) -> str:
    """
    Generate a sequential inspection number in the format INS-YYYY-NNNNN.
    Example: INS-2026-00001

    Uses the current year and the total count of inspections to determine sequence.
    Thread-safety note: For high concurrency, use a DB sequence instead.
    """
    year = datetime.utcnow().year
    count = db.query(Inspection).count()
    sequence = count + 1
    return f"INS-{year}-{sequence:05d}"
