from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.action_service import (
    create_action,
    get_all_actions,
    get_actions_by_customer,
    get_actions_by_status,
    get_action_by_id,
    mark_action_completed,
    cancel_action,
    get_action_summary,
)

router = APIRouter(prefix="/actions", tags=["Actions"])


class ActionCreate(BaseModel):
    customer_id: int
    action_type: str
    title: str
    description: str
    priority: str = "medium"
    source: str = "ai"


@router.get("/")
def list_actions(db: Session = Depends(get_db)):
    return get_all_actions(db)


@router.get("/summary")
def actions_summary(db: Session = Depends(get_db)):
    return get_action_summary(db)


@router.get("/by-status")
def actions_by_status(
    status: str = Query(...),
    db: Session = Depends(get_db),
):
    return get_actions_by_status(status, db)


@router.get("/customer/{customer_id}")
def actions_for_customer(customer_id: int, db: Session = Depends(get_db)):
    return get_actions_by_customer(customer_id, db)


@router.get("/{action_id}")
def single_action(action_id: int, db: Session = Depends(get_db)):
    action = get_action_by_id(action_id, db)

    if not action:
        return {"error": "Action not found"}

    return action


@router.post("/")
def add_action(action: ActionCreate, db: Session = Depends(get_db)):
    return create_action(
        db=db,
        customer_id=action.customer_id,
        action_type=action.action_type,
        title=action.title,
        description=action.description,
        priority=action.priority,
        source=action.source,
    )


@router.put("/{action_id}/complete")
def complete_action(action_id: int, db: Session = Depends(get_db)):
    return mark_action_completed(action_id, db)


@router.put("/{action_id}/cancel")
def cancel_existing_action(action_id: int, db: Session = Depends(get_db)):
    return cancel_action(action_id, db)