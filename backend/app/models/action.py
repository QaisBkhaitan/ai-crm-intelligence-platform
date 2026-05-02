from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.sql import func

from app.database import Base


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)

    # Link action back to the customer signal that created it
    signal_id = Column(Integer, ForeignKey("social_signals.id"), nullable=True, index=True)

    action_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    # AI decision metadata
    reason = Column(Text, nullable=True)
    suggested_reply = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)

    priority = Column(String, nullable=False, default="medium")
    status = Column(String, nullable=False, default="pending")
    source = Column(String, nullable=False, default="ai")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)