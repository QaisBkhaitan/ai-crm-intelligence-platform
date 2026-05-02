from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.customer import Customer
from app.models.order import Order
from app.models.import_log import ImportLog
from app.models.action import Action
from app.models.social_signal import SocialSignal


def calculate_customer_health(
    total_orders: int,
    total_sales: int,
    total_signals: int,
    high_risk_signals: int,
    complaints: int,
    pending_actions: int,
    high_priority_actions: int,
    positive_signals: int,
):
    score = 0

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

    score += min(total_orders * 8, 25)
    score += min(total_signals * 4, 18)
    score += min(positive_signals * 5, 12)

    if pending_actions > 0:
        score += min(pending_actions * 2, 8)

    score -= min(high_risk_signals * 12, 35)
    score -= min(complaints * 10, 30)
    score -= min(high_priority_actions * 6, 18)

    score = max(0, min(score, 100))

    if high_risk_signals > 0 or complaints > 0 or high_priority_actions > 0:
        status = "cold"
        recommended_action = "Resolve customer risk signals and complete urgent retention actions."
    elif score >= 70:
        status = "hot"
        recommended_action = "Prioritize follow-up and explore upsell or expansion opportunities."
    elif score >= 40:
        status = "warm"
        recommended_action = "Maintain engagement and move the customer toward the next action."
    else:
        status = "cold"
        recommended_action = "Re-engage this customer or enrich the account with more activity data."

    return score, status, recommended_action


def build_customer_profile(customer: Customer, db: Session):
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

    complaints = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer.id,
            SocialSignal.intent == "complaint",
        )
        .scalar()
        or 0
    )

    inquiries = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer.id,
            SocialSignal.intent == "inquiry",
        )
        .scalar()
        or 0
    )

    praise = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer.id,
            SocialSignal.intent == "praise",
        )
        .scalar()
        or 0
    )

    positive_signals = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer.id,
            SocialSignal.sentiment == "positive",
        )
        .scalar()
        or 0
    )

    negative_signals = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer.id,
            SocialSignal.sentiment == "negative",
        )
        .scalar()
        or 0
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

    retention_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer.id,
            Action.action_type == "retention",
            Action.status == "pending",
        )
        .scalar()
        or 0
    )

    upsell_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer.id,
            Action.action_type == "upsell",
            Action.status == "pending",
        )
        .scalar()
        or 0
    )

    score, status, recommended_action = calculate_customer_health(
        total_orders=total_orders,
        total_sales=total_sales,
        total_signals=total_signals,
        high_risk_signals=high_risk_signals,
        complaints=complaints,
        pending_actions=pending_actions,
        high_priority_actions=high_priority_actions,
        positive_signals=positive_signals,
    )

    if high_risk_signals > 0 or complaints > 0 or retention_actions > 0:
        relationship_status = "needs_attention"
    elif inquiries > 0 or upsell_actions > 0:
        relationship_status = "active_opportunity"
    elif total_orders > 0 or total_signals > 0:
        relationship_status = "engaged"
    else:
        relationship_status = "quiet"

    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "company": customer.company,
        "email": customer.email,
        "phone": customer.phone,
        "source": customer.source,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "total_orders": total_orders,
        "total_sales": total_sales,
        "total_signals": total_signals,
        "high_risk_signals": high_risk_signals,
        "complaints": complaints,
        "inquiries": inquiries,
        "praise": praise,
        "positive_signals": positive_signals,
        "negative_signals": negative_signals,
        "total_actions": total_actions,
        "pending_actions": pending_actions,
        "completed_actions": completed_actions,
        "high_priority_actions": high_priority_actions,
        "retention_actions": retention_actions,
        "upsell_actions": upsell_actions,
        "health_score": score,
        "status": status,
        "relationship_status": relationship_status,
        "recommended_action": recommended_action,
    }


def get_actionable_recommendations(db: Session):
    customers = db.query(Customer).all()

    customer_profiles = [
        build_customer_profile(customer, db)
        for customer in customers
    ]

    priority_customers = sorted(
        [
            profile for profile in customer_profiles
            if (
                profile["total_sales"] >= 700
                or profile["pending_actions"] > 0
                or profile["inquiries"] > 0
            )
            and profile["high_risk_signals"] == 0
            and profile["complaints"] == 0
        ],
        key=lambda item: (
            item["pending_actions"],
            item["total_sales"],
            item["inquiries"],
            item["health_score"],
        ),
        reverse=True,
    )[:5]

    at_risk_customers = sorted(
        [
            profile for profile in customer_profiles
            if (
                profile["high_risk_signals"] > 0
                or profile["complaints"] > 0
                or profile["retention_actions"] > 0
                or profile["high_priority_actions"] > 0
                or profile["relationship_status"] == "needs_attention"
            )
        ],
        key=lambda item: (
            item["high_risk_signals"],
            item["complaints"],
            item["high_priority_actions"],
            item["retention_actions"],
            item["total_sales"],
        ),
        reverse=True,
    )[:5]

    upsell_opportunities = sorted(
        [
            profile for profile in customer_profiles
            if (
                profile["total_sales"] >= 500
                or profile["praise"] > 0
                or profile["positive_signals"] > 0
                or profile["upsell_actions"] > 0
                or profile["inquiries"] > 0
            )
            and profile["high_risk_signals"] == 0
            and profile["complaints"] == 0
        ],
        key=lambda item: (
            item["total_sales"],
            item["praise"],
            item["positive_signals"],
            item["inquiries"],
            item["upsell_actions"],
        ),
        reverse=True,
    )[:5]

    customers_without_orders = [
        profile for profile in customer_profiles
        if profile["total_orders"] == 0
    ]

    customers_without_signals = [
        profile for profile in customer_profiles
        if profile["total_signals"] == 0
    ]

    customers_without_actions = [
        profile for profile in customer_profiles
        if profile["total_actions"] == 0
    ]

    unmatched_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.customer_id.is_(None))
        .count()
    )

    high_risk_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.risk_level == "high")
        .count()
    )

    pending_actions = (
        db.query(Action)
        .filter(Action.status == "pending")
        .count()
    )

    high_priority_actions = (
        db.query(Action)
        .filter(
            Action.status == "pending",
            Action.priority == "high",
        )
        .count()
    )

    failed_imports = (
        db.query(ImportLog)
        .filter(ImportLog.status == "failed")
        .count()
    )

    data_warnings = []

    if customers_without_orders:
        data_warnings.append(
            {
                "type": "customers_without_orders",
                "count": len(customers_without_orders),
                "message": f"{len(customers_without_orders)} customer(s) have no orders yet.",
            }
        )

    if customers_without_signals:
        data_warnings.append(
            {
                "type": "customers_without_signals",
                "count": len(customers_without_signals),
                "message": f"{len(customers_without_signals)} customer(s) have no linked customer signals yet.",
            }
        )

    if customers_without_actions:
        data_warnings.append(
            {
                "type": "customers_without_actions",
                "count": len(customers_without_actions),
                "message": f"{len(customers_without_actions)} customer(s) have no generated or manual actions yet.",
            }
        )

    if unmatched_signals > 0:
        data_warnings.append(
            {
                "type": "unmatched_signals",
                "count": unmatched_signals,
                "message": f"{unmatched_signals} signal(s) are not linked to CRM customers.",
            }
        )

    if high_risk_signals > 0:
        data_warnings.append(
            {
                "type": "high_risk_signals",
                "count": high_risk_signals,
                "message": f"{high_risk_signals} high-risk signal(s) need review.",
            }
        )

    if high_priority_actions > 0:
        data_warnings.append(
            {
                "type": "high_priority_actions",
                "count": high_priority_actions,
                "message": f"{high_priority_actions} high-priority pending action(s) are still open.",
            }
        )

    if failed_imports > 0:
        data_warnings.append(
            {
                "type": "failed_imports",
                "count": failed_imports,
                "message": f"{failed_imports} import operation(s) failed and may need review.",
            }
        )

    recommended_actions = []

    if at_risk_customers:
        customer = at_risk_customers[0]
        recommended_actions.append(
            f"Handle retention risk first: review {customer['customer_name']} from {customer['company']} and resolve their highest-risk signal or pending action."
        )

    if priority_customers:
        customer = priority_customers[0]
        recommended_actions.append(
            f"Move priority work forward: follow up with {customer['customer_name']} from {customer['company']}."
        )

    if upsell_opportunities:
        customer = upsell_opportunities[0]
        recommended_actions.append(
            f"Explore upsell opportunity with {customer['customer_name']} from {customer['company']} based on revenue, positive signals, or inquiry activity."
        )

    if unmatched_signals > 0:
        recommended_actions.append(
            "Link unmatched signals to existing customers or convert them into new leads."
        )

    if pending_actions > 0:
        recommended_actions.append(
            f"Review the execution queue and complete the most important pending actions. Current pending actions: {pending_actions}."
        )

    if failed_imports > 0:
        recommended_actions.append(
            "Review failed imports to keep CRM data complete and reliable."
        )

    if not recommended_actions:
        recommended_actions.append(
            "No urgent recommendations right now. Continue monitoring new orders, signals, and actions."
        )

    summary = {
        "total_customers": len(customer_profiles),
        "priority_count": len(priority_customers),
        "at_risk_count": len(at_risk_customers),
        "upsell_count": len(upsell_opportunities),
        "warning_count": len(data_warnings),
        "pending_actions": pending_actions,
        "high_priority_actions": high_priority_actions,
        "unmatched_signals": unmatched_signals,
        "high_risk_signals": high_risk_signals,
    }

    return {
        "summary": summary,
        "customer_profiles": customer_profiles,
        "priority_customers": priority_customers,
        "at_risk_customers": at_risk_customers,
        "upsell_opportunities": upsell_opportunities,
        "data_warnings": data_warnings,
        "recommended_actions": recommended_actions,
    }