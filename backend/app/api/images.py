"""
Images API — upload images to an inspection with a view type label.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.inspection import Inspection
from app.models.inspection_image import InspectionImage, ViewType
from app.schemas.inspection import InspectionImageOut
from app.services.storage_service import get_storage_service

router = APIRouter()


@router.post("/{inspection_id}/images", response_model=InspectionImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    inspection_id: int,
    view_type: ViewType = Form(ViewType.OTHER),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    if current_user.role == UserRole.INSPECTOR and inspection.inspector_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, WebP, TIFF.",
        )

    storage = get_storage_service()
    file_bytes = await file.read()

    # store() returns a URL or path that the client can use
    stored_url, file_hash = storage.store(
        file_bytes=file_bytes,
        filename=file.filename,
        inspection_id=inspection_id,
        content_type=file.content_type,
    )

    image = InspectionImage(
        inspection_id=inspection_id,
        image_url=stored_url,
        view_type=view_type,
        file_hash=file_hash,
        original_filename=file.filename,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.get("/{inspection_id}/images", response_model=List[InspectionImageOut])
def list_images(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return db.query(InspectionImage).filter(InspectionImage.inspection_id == inspection_id).all()
