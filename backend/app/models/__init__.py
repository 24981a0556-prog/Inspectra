"""
INSPECTRA Models — re-export all models so `import app.models` populates Base.metadata.
"""
from app.models.user import User  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.inspection import Inspection  # noqa: F401
from app.models.inspection_image import InspectionImage  # noqa: F401
from app.models.ai_result import AIResult  # noqa: F401
from app.models.compliance_check import ComplianceCheck  # noqa: F401
from app.models.evidence import Evidence  # noqa: F401
from app.models.human_review import HumanReview  # noqa: F401
