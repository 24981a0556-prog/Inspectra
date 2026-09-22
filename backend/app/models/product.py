"""
Product model — represents a packaged commodity under inspection.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id           = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(100), unique=True, index=True, nullable=False)
    product_name = Column(String(255), nullable=False)
    category     = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
