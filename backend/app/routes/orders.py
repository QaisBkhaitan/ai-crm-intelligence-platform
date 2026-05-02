from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import Order
from app.services.rag_service import safe_rebuild_crm_knowledge_index
router = APIRouter(prefix="/orders", tags=["Orders"])


class OrderCreate(BaseModel):
    product_name: str
    amount: int


@router.get("/{customer_id}")
def get_orders(customer_id: int, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.customer_id == customer_id).all()

    return [
        {
            "id": order.id,
            "customer_id": order.customer_id,
            "product_name": order.product_name,
            "amount": order.amount,
            "source": order.source,
            "created_at": order.created_at,
        }
        for order in orders
    ]


@router.post("/{customer_id}")
def add_order(customer_id: int, order: OrderCreate, db: Session = Depends(get_db)):
    new_order = Order(
        customer_id=customer_id,
        product_name=order.product_name,
        amount=order.amount,
        source="manual",
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    safe_rebuild_crm_knowledge_index(db)
    return {
        "id": new_order.id,
        "customer_id": new_order.customer_id,
        "product_name": new_order.product_name,
        "amount": new_order.amount,
        "source": new_order.source,
        "created_at": new_order.created_at,
    }