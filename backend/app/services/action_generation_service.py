from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.customer import Customer
from app.services.action_service import create_action
from app.services.business_brain_service import get_business_brain
from app.services.recommendation_service import get_actionable_recommendations


def action_exists(
    db: Session,
    customer_id: int,
    action_type: str,
    title: str,
    status: str = "pending",
):
    existing = (
        db.query(Action)
        .filter(
            Action.customer_id == customer_id,
            Action.action_type == action_type,
            Action.title == title,
            Action.status == status,
        )
        .first()
    )

    return existing is not None


def create_action_if_not_exists(
    db: Session,
    customer_id: int,
    action_type: str,
    title: str,
    description: str,
    priority: str = "medium",
    source: str = "ai",
):
    if action_exists(db, customer_id, action_type, title, status="pending"):
        return None

    result = create_action(
        db=db,
        customer_id=customer_id,
        action_type=action_type,
        title=title,
        description=description,
        priority=priority,
        source=source,
    )

    if isinstance(result, dict) and result.get("error"):
        return None

    return result


def generate_actions_from_business_brain(db: Session):
    brain = get_business_brain(db)

    created_actions = []

    top_priorities = brain.get("top_priorities", [])
    biggest_risks = brain.get("biggest_risks", [])
    growth_opportunities = brain.get("growth_opportunities", [])
    operational_warnings = brain.get("operational_warnings", [])

    # 1) Priority accounts -> follow_up actions
    for item in top_priorities:
        customer_id = item.get("customer_id")
        customer_name = item.get("customer_name", "Customer")
        company = item.get("company", "Unknown company")
        reason = item.get("reason", "")
        recommended_action = item.get("recommended_action", "")

        action = create_action_if_not_exists(
            db=db,
            customer_id=customer_id,
            action_type="follow_up",
            title=f"Priority follow-up for {customer_name}",
            description=(
                f"Customer: {customer_name} ({company}). "
                f"Reason: {reason} "
                f"Recommended action: {recommended_action}"
            ),
            priority="high",
            source="ai",
        )

        if action:
            created_actions.append(action)

    # 2) Biggest risks -> retention actions
    for item in biggest_risks:
        customer_id = item.get("customer_id")
        customer_name = item.get("customer_name", "Customer")
        company = item.get("company", "Unknown company")
        reason = item.get("reason", "")
        recommended_action = item.get("recommended_action", "")

        action = create_action_if_not_exists(
            db=db,
            customer_id=customer_id,
            action_type="retention",
            title=f"Retention action for {customer_name}",
            description=(
                f"Customer: {customer_name} ({company}). "
                f"Risk: {reason} "
                f"Recommended action: {recommended_action}"
            ),
            priority="high",
            source="ai",
        )

        if action:
            created_actions.append(action)

    # 3) Growth opportunities -> upsell actions
    for item in growth_opportunities:
        customer_id = item.get("customer_id")
        customer_name = item.get("customer_name", "Customer")
        company = item.get("company", "Unknown company")
        reason = item.get("reason", "")
        recommended_action = item.get("recommended_action", "")

        action = create_action_if_not_exists(
            db=db,
            customer_id=customer_id,
            action_type="upsell",
            title=f"Upsell opportunity for {customer_name}",
            description=(
                f"Customer: {customer_name} ({company}). "
                f"Opportunity: {reason} "
                f"Recommended action: {recommended_action}"
            ),
            priority="medium",
            source="ai",
        )

        if action:
            created_actions.append(action)

    # 4) Operational warnings -> create review/data_cleanup actions
    # These warnings are system-level, not always tied to a customer.
    # We'll map them to existing customers only when possible later.
    # For now we skip direct DB creation because Action requires customer_id.

    return {
        "message": "Actions generated from business brain.",
        "created_count": len(created_actions),
        "created_actions": created_actions,
        "skipped_operational_warnings": len(operational_warnings),
    }


def generate_actions_from_recommendations(db: Session):
    recommendations = get_actionable_recommendations(db)

    created_actions = []

    priority_customers = recommendations.get("priority_customers", [])
    at_risk_customers = recommendations.get("at_risk_customers", [])
    upsell_opportunities = recommendations.get("upsell_opportunities", [])

    for item in priority_customers:
        action = create_action_if_not_exists(
            db=db,
            customer_id=item["customer_id"],
            action_type="follow_up",
            title=f"AI follow-up for {item['customer_name']}",
            description=(
                f"Customer is in priority segment. "
                f"Status: {item['status']}. "
                f"Health score: {item['health_score']}. "
                f"Recommended action: {item['recommended_action']}"
            ),
            priority="high",
            source="ai",
        )
        if action:
            created_actions.append(action)

    for item in at_risk_customers:
        action = create_action_if_not_exists(
            db=db,
            customer_id=item["customer_id"],
            action_type="retention",
            title=f"Retention follow-up for {item['customer_name']}",
            description=(
                f"Customer is at risk. "
                f"Status: {item['status']}. "
                f"Health score: {item['health_score']}. "
                f"Recommended action: {item['recommended_action']}"
            ),
            priority="high",
            source="ai",
        )
        if action:
            created_actions.append(action)

    for item in upsell_opportunities:
        action = create_action_if_not_exists(
            db=db,
            customer_id=item["customer_id"],
            action_type="upsell",
            title=f"Upsell outreach for {item['customer_name']}",
            description=(
                f"Customer has upsell potential. "
                f"Total sales: {item['total_sales']}. "
                f"Status: {item['status']}. "
                f"Recommended action: {item['recommended_action']}"
            ),
            priority="medium",
            source="ai",
        )
        if action:
            created_actions.append(action)

    return {
        "message": "Actions generated from recommendations.",
        "created_count": len(created_actions),
        "created_actions": created_actions,
    }


def generate_all_ai_actions(db: Session):
    business_brain_result = generate_actions_from_business_brain(db)
    recommendations_result = generate_actions_from_recommendations(db)

    total_created = (
        business_brain_result.get("created_count", 0)
        + recommendations_result.get("created_count", 0)
    )

    return {
        "message": "AI action generation completed.",
        "total_created": total_created,
        "business_brain_result": business_brain_result,
        "recommendations_result": recommendations_result,
    }