"""
INSPECTRA — Database Engine & Session Factory
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # reconnect if connection dropped
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All SQLAlchemy models inherit from this base."""
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables on startup (safe — skips existing tables).
    In production, prefer Alembic migrations over this.
    """
    # Import all models so SQLAlchemy's metadata is populated before create_all
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
