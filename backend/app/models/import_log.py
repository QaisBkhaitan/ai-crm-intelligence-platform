from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class ImportLog(Base):
    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)      # customers / orders / notes
    file_name = Column(String, nullable=False)
    inserted_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="success")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)