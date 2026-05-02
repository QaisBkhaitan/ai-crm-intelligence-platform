from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_name = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)

    source = Column(String, nullable=False, default="manual")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)