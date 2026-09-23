"""
Inspection Pydantic schemas.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.inspection import InspectionStatus, FinalDecision
from app.models.inspection_image import ViewType
from app.schemas.product import ProductOut
from app.schemas.user import UserOut


class InspectionCreate(BaseModel):
    product_id: int
    notes: Optional[str] = None


class InspectionStatusUpdate(BaseModel):
    status: InspectionStatus


class InspectionImageOut(BaseModel):
    id: int
    inspection_id: int
    image_url: str
    view_type: ViewType
    original_filename: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectionOut(BaseModel):
    id: int
    inspection_number: str
    product_id: int
    inspector_id: int
    status: InspectionStatus
    notes: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    is_demo: Optional[bool] = False
    final_decision: Optional[FinalDecision] = None
    finalized_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InspectionDetail(BaseModel):
    id: int
    inspection_number: str
    status: InspectionStatus
    notes: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    is_demo: Optional[bool] = False
    final_decision: Optional[FinalDecision] = None
    final_decision_comment: Optional[str] = None
    finalized_at: Optional[datetime] = None
    analysis_error: Optional[str] = None
    product: ProductOut
    inspector: UserOut
    images: List[InspectionImageOut] = []

    model_config = {"from_attributes": True}
