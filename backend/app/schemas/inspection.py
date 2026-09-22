"""
Inspection Pydantic schemas.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.inspection import InspectionStatus
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

    model_config = {"from_attributes": True}


class InspectionDetail(BaseModel):
    id: int
    inspection_number: str
    status: InspectionStatus
    notes: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    product: ProductOut
    inspector: UserOut
    images: List[InspectionImageOut] = []

    model_config = {"from_attributes": True}
