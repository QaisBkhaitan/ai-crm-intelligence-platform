from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.database import Base


class SocialSignal(Base):
    __tablename__ = "social_signals"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(Integer, nullable=True)

    source = Column(String, nullable=False)  # facebook / instagram / website

    author_name = Column(String, nullable=True)
    author_handle = Column(String, nullable=True)

    content = Column(Text, nullable=False)

    sentiment = Column(String, default="unknown")  # positive / negative / neutral
    intent = Column(String, default="unknown")  # complaint / inquiry / praise
    risk_level = Column(String, default="low")  # low / medium / high

    external_post_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)