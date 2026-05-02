from math import ceil
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.customer import Customer
from app.models.order import Order
from app.models.action import Action
from app.models.social_signal import SocialSignal
from app.services.rag_service import safe_rebuild_crm_knowledge_index


ALLOWED_SORT_FIELDS = {
    "id": Customer.id,
    "name": Customer.name,
    "email": Customer.email,
    "company": Customer.company,
    "created_at": Customer.created_at,
    "updated_at": Customer.updated_at,
}


def parse_date_value(value: str):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def serialize_customer(customer: Customer):
    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "company": customer.company,
        "source": customer.source,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
    }


def format_last_activity(*values):
    valid_values = [value for value in values if value is not None]

    if not valid_values:
        return None

    return max(valid_values)


def calculate_customer_health(
    total_orders: int,
    total_sales: int,
    total_signals: int,
    high_risk_signals: int,
    pending_actions: int,
    high_priority_actions: int,
):
    score = 0

    # Revenue strength
    if total_sales >= 3000:
        score += 35
    elif total_sales >= 1500:
        score += 28
    elif total_sales >= 700:
        score += 22
    elif total_sales >= 250:
        score += 14
    elif total_sales > 0:
        score += 8

    # Commercial activity
    score += min(total_orders * 8, 25)

    # Engagement/activity signals
    score += min(total_signals * 4, 20)

    # Open work means this account needs attention
    if pending_actions > 0:
        score += min(pending_actions * 4, 12)

    # Risk reduces health
    score -= min(high_risk_signals * 10, 30)
    score -= min(high_priority_actions * 5, 15)

    score = max(0, min(score, 100))

    if high_risk_signals > 0 or high_priority_actions > 0:
        health_status = "cold"
        relationship_status = "needs_attention"
        priority_label = "Risk"
        next_best_action = "Review high-risk signals and resolve urgent pending actions."
    elif total_sales >= 1000 and pending_actions > 0:
        health_status = "hot"
        relationship_status = "active_opportunity"
        priority_label = "Opportunity"
        next_best_action = "Follow up with this high-value account and move the pending action forward."
    elif total_sales >= 1000:
        health_status = "hot"
        relationship_status = "engaged"
        priority_label = "Growth"
        next_best_action = "Explore upsell or retention opportunities with this strong account."
    elif total_orders > 0 or total_signals > 0:
        health_status = "warm"
        relationship_status = "engaged"
        priority_label = "Engaged"
        next_best_action = "Maintain engagement and watch for a follow-up opportunity."
    else:
        health_status = "cold"
        relationship_status = "quiet"
        priority_label = "Quiet"
        next_best_action = "Re-engage this customer or enrich their profile with more activity data."

    return {
        "health_score": score,
        "health_status": health_status,
        "relationship_status": relationship_status,
        "priority_label": priority_label,
        "next_best_action": next_best_action,
    }


def build_customer_intelligence(customer: Customer, db: Session):
    total_orders = (
        db.query(func.count(Order.id))
        .filter(Order.customer_id == customer.id)
        .scalar()
        or 0
    )

    total_sales = (
        db.query(func.sum(Order.amount))
        .filter(Order.customer_id == customer.id)
        .scalar()
        or 0
    )

    latest_order_at = (
        db.query(func.max(Order.created_at))
        .filter(Order.customer_id == customer.id)
        .scalar()
    )

    total_signals = (
        db.query(func.count(SocialSignal.id))
        .filter(SocialSignal.customer_id == customer.id)
        .scalar()
        or 0
    )

    high_risk_signals = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer.id,
            SocialSignal.risk_level == "high",
        )
        .scalar()
        or 0
    )

    latest_signal_at = (
        db.query(func.max(SocialSignal.created_at))
        .filter(SocialSignal.customer_id == customer.id)
        .scalar()
    )

    total_actions = (
        db.query(func.count(Action.id))
        .filter(Action.customer_id == customer.id)
        .scalar()
        or 0
    )

    pending_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer.id,
            Action.status == "pending",
        )
        .scalar()
        or 0
    )

    completed_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer.id,
            Action.status == "completed",
        )
        .scalar()
        or 0
    )

    high_priority_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer.id,
            Action.status == "pending",
            Action.priority == "high",
        )
        .scalar()
        or 0
    )

    latest_action_at = (
        db.query(func.max(Action.created_at))
        .filter(Action.customer_id == customer.id)
        .scalar()
    )

    health = calculate_customer_health(
        total_orders=total_orders,
        total_sales=total_sales,
        total_signals=total_signals,
        high_risk_signals=high_risk_signals,
        pending_actions=pending_actions,
        high_priority_actions=high_priority_actions,
    )

    last_activity_at = format_last_activity(
        customer.updated_at,
        latest_order_at,
        latest_signal_at,
        latest_action_at,
    )

    return {
        **serialize_customer(customer),
        "intelligence": {
            "total_orders": total_orders,
            "total_sales": total_sales,
            "total_signals": total_signals,
            "high_risk_signals": high_risk_signals,
            "total_actions": total_actions,
            "pending_actions": pending_actions,
            "completed_actions": completed_actions,
            "high_priority_actions": high_priority_actions,
            "last_activity_at": last_activity_at,
            **health,
        },
    }


def get_all_customers(db: Session):
    customers = db.query(Customer).order_by(Customer.id.desc()).all()
    return [build_customer_intelligence(customer, db) for customer in customers]


def get_customer_by_id(customer_id: int, db: Session):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        return None

    return serialize_customer(customer)


def create_customer(customer_data, db: Session):
    existing_customer = (
        db.query(Customer)
        .filter(Customer.email.ilike(customer_data.email.strip().lower()))
        .first()
    )

    if existing_customer:
        return {"error": "Customer with this email already exists"}

    new_customer = Customer(
        name=customer_data.name.strip(),
        email=customer_data.email.strip().lower(),
        phone=customer_data.phone.strip(),
        company=customer_data.company.strip(),
        source="manual",
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    safe_rebuild_crm_knowledge_index(db)

    return serialize_customer(new_customer)


def delete_customer(customer_id: int, db: Session):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        return None

    db.delete(customer)
    db.commit()

    safe_rebuild_crm_knowledge_index(db)

    return {"message": "Customer deleted successfully"}


def query_customers(
    db: Session,
    search: str = "",
    company: str = "",
    source: str = "",
    created_after: str = "",
    created_before: str = "",
    sort_by: str = "id",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 10,
):
    query = db.query(Customer)

    if search:
        search_value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(search_value),
                Customer.email.ilike(search_value),
                Customer.company.ilike(search_value),
                Customer.phone.ilike(search_value),
            )
        )

    if company:
        query = query.filter(Customer.company.ilike(f"%{company.strip()}%"))

    if source:
        query = query.filter(Customer.source == source.strip())

    parsed_created_after = parse_date_value(created_after)
    parsed_created_before = parse_date_value(created_before)

    if parsed_created_after:
        query = query.filter(Customer.created_at >= parsed_created_after)

    if parsed_created_before:
        next_day = parsed_created_before + timedelta(days=1)
        query = query.filter(Customer.created_at < next_day)

    sort_column = ALLOWED_SORT_FIELDS.get(sort_by, Customer.id)

    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total = query.count()

    page = max(page, 1)
    limit = max(min(limit, 100), 1)

    offset = (page - 1) * limit
    customers = query.offset(offset).limit(limit).all()

    items = [build_customer_intelligence(customer, db) for customer in customers]

    total_pages = ceil(total / limit) if total > 0 else 1

    return {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        },
        "filters": {
            "search": search,
            "company": company,
            "source": source,
            "created_after": created_after,
            "created_before": created_before,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    }