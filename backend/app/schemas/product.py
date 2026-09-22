"""
Product Pydantic schemas.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProductCreate(BaseModel):
    product_code: str
    product_name: str
    category: Optional[str] = None
    manufacturer: Optional[str] = None


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    manufacturer: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    product_code: str
    product_name: str
    category: Optional[str]
    manufacturer: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
