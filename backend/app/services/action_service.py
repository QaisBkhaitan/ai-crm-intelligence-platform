from datetime import datetime
from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.customer import Customer


ALLOWED_ACTION_TYPES = {
    "follow_up",
    "upsell",
    "retention",
    "data_cleanup",
    "review",
}

ALLOWED_PRIORITIES = {
    "high",
    "medium",
    "low",
}

ALLOWED_STATUSES = {
    "pending",
    "completed",
    "cancelled",
}

ALLOWED_SOURCES = {
    "ai",
    "manual",
}


def serialize_action(action: Action):
    return {
        "id": action.id,
        "customer_id": action.customer_id,
        "signal_id": action.signal_id,
        "action_type": action.action_type,
        "title": action.title,
        "description": action.description,
        "reason": action.reason,
        "suggested_reply": action.suggested_reply,
        "ai_confidence": action.ai_confidence,
        "priority": action.priority,
        "status": action.status,
        "source": action.source,
        "created_at": action.created_at,
        "completed_at": action.completed_at,
    }


def validate_action_type(action_type: str):
    return action_type in ALLOWED_ACTION_TYPES


def validate_priority(priority: str):
    return priority in ALLOWED_PRIORITIES


def validate_status(status: str):
    return status in ALLOWED_STATUSES


def validate_source(source: str):
    return source in ALLOWED_SOURCES


def create_action(
    db: Session,
    customer_id: int,
    action_type: str,
    title: str,
    description: str,
    priority: str = "medium",
    source: str = "ai",
    signal_id: int | None = None,
    reason: str | None = None,
    suggested_reply: str | None = None,
    ai_confidence: float | None = None,
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        return {"error": "Customer not found"}

    if not validate_action_type(action_type):
        return {"error": f"Invalid action_type. Allowed: {sorted(ALLOWED_ACTION_TYPES)}"}

    if not validate_priority(priority):
        return {"error": f"Invalid priority. Allowed: {sorted(ALLOWED_PRIORITIES)}"}

    if not validate_source(source):
        return {"error": f"Invalid source. Allowed: {sorted(ALLOWED_SOURCES)}"}

    if not title.strip():
        return {"error": "Title is required"}

    if not description.strip():
        return {"error": "Description is required"}

    action = Action(
        customer_id=customer_id,
        signal_id=signal_id,
        action_type=action_type.strip(),
        title=title.strip(),
        description=description.strip(),
        reason=reason,
        suggested_reply=suggested_reply,
        ai_confidence=ai_confidence,
        priority=priority.strip(),
        status="pending",
        source=source.strip(),
    )

    db.add(action)
    db.commit()
    db.refresh(action)

    return serialize_action(action)


def get_all_actions(db: Session):
    actions = db.query(Action).order_by(Action.created_at.desc(), Action.id.desc()).all()
    return [serialize_action(action) for action in actions]


def get_actions_by_customer(customer_id: int, db: Session):
    actions = (
        db.query(Action)
        .filter(Action.customer_id == customer_id)
        .order_by(Action.created_at.desc(), Action.id.desc())
        .all()
    )

    return [serialize_action(action) for action in actions]


def get_actions_by_status(status: str, db: Session):
    if not validate_status(status):
        return {"error": f"Invalid status. Allowed: {sorted(ALLOWED_STATUSES)}"}

    actions = (
        db.query(Action)
        .filter(Action.status == status.strip())
        .order_by(Action.created_at.desc(), Action.id.desc())
        .all()
    )

    return [serialize_action(action) for action in actions]


def get_action_by_id(action_id: int, db: Session):
    action = db.query(Action).filter(Action.id == action_id).first()

    if not action:
        return None

    return serialize_action(action)


def mark_action_completed(action_id: int, db: Session):
    action = db.query(Action).filter(Action.id == action_id).first()

    if not action:
        return {"error": "Action not found"}

    if action.status == "completed":
        return {"error": "Action is already completed"}

    action.status = "completed"
    action.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(action)

    return serialize_action(action)


def cancel_action(action_id: int, db: Session):
    action = db.query(Action).filter(Action.id == action_id).first()

    if not action:
        return {"error": "Action not found"}

    if action.status == "completed":
        return {"error": "Completed action cannot be cancelled"}

    if action.status == "cancelled":
        return {"error": "Action is already cancelled"}

    action.status = "cancelled"
    action.completed_at = None

    db.commit()
    db.refresh(action)

    return serialize_action(action)


def get_action_summary(db: Session):
    actions = db.query(Action).all()

    pending_count = len([a for a in actions if a.status == "pending"])
    completed_count = len([a for a in actions if a.status == "completed"])
    cancelled_count = len([a for a in actions if a.status == "cancelled"])

    high_priority_count = len([a for a in actions if a.priority == "high"])
    medium_priority_count = len([a for a in actions if a.priority == "medium"])
    low_priority_count = len([a for a in actions if a.priority == "low"])

    return {
        "total_actions": len(actions),
        "pending_count": pending_count,
        "completed_count": completed_count,
        "cancelled_count": cancelled_count,
        "high_priority_count": high_priority_count,
        "medium_priority_count": medium_priority_count,
        "low_priority_count": low_priority_count,
    }