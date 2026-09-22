"""
Dashboard API — aggregated statistics from real database data.
No hardcoded values. All counts come from the DB.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.inspection import Inspection, InspectionStatus
from app.schemas.inspection import InspectionOut
from pydantic import BaseModel
from typing import Dict

router = APIRouter()


class DashboardStats(BaseModel):
    total_inspections: int
    by_status: Dict[str, int]
    total_products: int
    total_inspectors: int


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.product import Product

    base_query = db.query(Inspection)
    if current_user.role == UserRole.INSPECTOR:
        base_query = base_query.filter(Inspection.inspector_id == current_user.id)

    total = base_query.count()

    # Count per status
    status_counts = (
        base_query
        .with_entities(Inspection.status, func.count(Inspection.id))
        .group_by(Inspection.status)
        .all()
    )
    by_status = {s.value: 0 for s in InspectionStatus}
    for status, count in status_counts:
        by_status[status.value] = count

    total_products = db.query(Product).count()
    total_inspectors = db.query(User).filter(User.role == UserRole.INSPECTOR).count()

    return DashboardStats(
        total_inspections=total,
        by_status=by_status,
        total_products=total_products,
        total_inspectors=total_inspectors,
    )


@router.get("/recent-inspections", response_model=List[InspectionOut])
def get_recent_inspections(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Inspection)
    if current_user.role == UserRole.INSPECTOR:
        query = query.filter(Inspection.inspector_id == current_user.id)
    return query.order_by(Inspection.created_at.desc()).limit(limit).all()
