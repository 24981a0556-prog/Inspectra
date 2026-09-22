"""
User model — stores inspector, supervisor, and admin accounts.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Enum, DateTime
from app.core.database import Base


class UserRole(str, enum.Enum):
    INSPECTOR = "INSPECTOR"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(255), nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole), nullable=False, default=UserRole.INSPECTOR)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
