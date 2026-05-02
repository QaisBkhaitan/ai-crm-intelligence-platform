from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.customer_service import (
    get_all_customers,
    get_customer_by_id,
    create_customer,
    delete_customer,
    query_customers,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    company: str


@router.get("/")
def get_customers(db: Session = Depends(get_db)):
    return get_all_customers(db)


@router.get("/query")
def get_customers_query(
    search: str = Query(default=""),
    company: str = Query(default=""),
    source: str = Query(default=""),
    created_after: str = Query(default=""),
    created_before: str = Query(default=""),
    sort_by: str = Query(default="id"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return query_customers(
        db=db,
        search=search,
        company=company,
        source=source,
        created_after=created_after,
        created_before=created_before,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit,
    )


@router.get("/{customer_id}")
def get_single_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = get_customer_by_id(customer_id, db)

    if not customer:
        return {"error": "Customer not found"}

    return customer


@router.post("/")
def add_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    return create_customer(customer, db)


@router.delete("/{customer_id}")
def remove_customer(customer_id: int, db: Session = Depends(get_db)):
    result = delete_customer(customer_id, db)

    if not result:
        return {"error": "Customer not found"}

    return result