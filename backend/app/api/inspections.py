"""
Inspections API — create, list, retrieve, and update inspection status.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.product import Product
from app.models.inspection import Inspection, InspectionStatus
from app.schemas.inspection import InspectionCreate, InspectionOut, InspectionDetail, InspectionStatusUpdate
from app.services.inspection_service import generate_inspection_number

router = APIRouter()


@router.post("/", response_model=InspectionOut, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: InspectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    inspection_number = generate_inspection_number(db)

    inspection = Inspection(
        inspection_number=inspection_number,
        product_id=payload.product_id,
        inspector_id=current_user.id,
        notes=payload.notes,
        status=InspectionStatus.DRAFT,
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.get("/", response_model=List[InspectionOut])
def list_inspections(
    skip: int = 0,
    limit: int = 20,
    status: Optional[InspectionStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Inspection)

    # INSPECTOR only sees their own inspections; SUPERVISOR/ADMIN see all
    from app.models.user import UserRole
    if current_user.role == UserRole.INSPECTOR:
        query = query.filter(Inspection.inspector_id == current_user.id)

    if status:
        query = query.filter(Inspection.status == status)

    return query.order_by(Inspection.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{inspection_id}", response_model=InspectionDetail)
def get_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = (
        db.query(Inspection)
        .options(
            joinedload(Inspection.product),
            joinedload(Inspection.inspector),
            joinedload(Inspection.images),
        )
        .filter(Inspection.id == inspection_id)
        .first()
    )
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    # INSPECTOR can only view their own
    from app.models.user import UserRole
    if current_user.role == UserRole.INSPECTOR and inspection.inspector_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    return inspection


@router.patch("/{inspection_id}/status", response_model=InspectionOut)
def update_inspection_status(
    inspection_id: int,
    payload: InspectionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    from app.models.user import UserRole
    if current_user.role == UserRole.INSPECTOR and inspection.inspector_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    inspection.status = payload.status
    if payload.status == InspectionStatus.IN_PROGRESS and not inspection.started_at:
        from datetime import datetime, timezone
        inspection.started_at = datetime.now(timezone.utc)
    if payload.status == InspectionStatus.COMPLETED:
        from datetime import datetime, timezone
        inspection.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(inspection)
    return inspection
