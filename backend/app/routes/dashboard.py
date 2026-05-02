from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order
from app.services.dashboard_service import get_dashboard_overview

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_customers = db.query(Customer).count()
    total_orders = db.query(Order).count()
    total_sales = db.query(func.sum(Order.amount)).scalar() or 0

    return {
        "total_customers": total_customers,
        "total_orders": total_orders,
        "total_sales": total_sales,
    }


@router.get("/overview")
def dashboard_overview(db: Session = Depends(get_db)):
    return get_dashboard_overview(db)