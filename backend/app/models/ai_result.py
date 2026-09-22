"""
AIResult model — stores the output of an AI agent for a given inspection.
NOTE: This table is a stub. No agents are implemented yet.
      When agents are built, they will write records here.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from app.core.database import Base


class AIResult(Base):
    __tablename__ = "ai_results"

    id             = Column(Integer, primary_key=True, index=True)
    inspection_id  = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    # agent_type: "label_agent" | "quantity_agent" | "declaration_agent"
    agent_type     = Column(String(100), nullable=False)
    input_image_id = Column(Integer, ForeignKey("inspection_images.id"), nullable=True)
    result_json    = Column(JSON, nullable=True)    # raw agent output
    confidence     = Column(Float, nullable=True)
    model_name     = Column(String(100), nullable=True)
    model_version  = Column(String(50), nullable=True)
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
