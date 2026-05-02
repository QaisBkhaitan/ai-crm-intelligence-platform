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

    # Revenue value
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

    # Buying activity
    score += min(total_orders * 8, 25)

    # Customer interaction activity
    score += min(total_signals * 4, 18)

    # Positive signals improve confidence
    score += min(positive_signals * 5, 12)

    # Pending actions show there is work to do, but too many urgent actions hurt health
    if pending_actions > 0:
        score += min(pending_actions * 2, 8)

    # Risk penalties
    score -= min(high_risk_signals * 12, 35)
    score -= min(complaints * 10, 30)
    score -= min(high_priority_actions * 6, 18)

    score = max(0, min(score, 100))

    if high_risk_signals > 0 or complaints > 0 or high_priority_actions > 0:
        status = "cold"
    elif score >= 70:
        status = "hot"
    elif score >= 40:
        status = "warm"
    else:
        status = "cold"

    return score, status


def get_customer_profile(customer: Customer, db: Session):
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

    latest_order_at = (
        db.query(func.max(Order.created_at))
        .filter(Order.customer_id == customer.id)
        .scalar()
    )

    latest_signal_at = (
        db.query(func.max(SocialSignal.created_at))
        .filter(SocialSignal.customer_id == customer.id)
        .scalar()
    )

    latest_action_at = (
        db.query(func.max(Action.created_at))
        .filter(Action.customer_id == customer.id)
        .scalar()
    )

    last_activity_at = max(
        [value for value in [customer.updated_at, latest_order_at, latest_signal_at, latest_action_at] if value],
        default=customer.created_at,
    )

    health_score, status = calculate_customer_health(
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
        risk_level = "high"
    elif inquiries > 0 or upsell_actions > 0:
        relationship_status = "active_opportunity"
        risk_level = "medium"
    elif total_orders > 0 or total_signals > 0:
        relationship_status = "engaged"
        risk_level = "low"
    else:
        relationship_status = "quiet"
        risk_level = "low"

    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "company": customer.company,
        "email": customer.email,
        "phone": customer.phone,
        "source": customer.source,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "last_activity_at": last_activity_at,
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
        "health_score": health_score,
        "status": status,
        "relationship_status": relationship_status,
        "risk_level": risk_level,
    }


def build_priority_reason(profile: dict):
    reasons = []

    if profile["total_sales"] >= 1000:
        reasons.append("high account value")

    if profile["pending_actions"] > 0:
        reasons.append("pending execution work")

    if profile["inquiries"] > 0:
        reasons.append("recent buying or interest signals")

    if profile["total_orders"] >= 2:
        reasons.append("repeat purchase activity")

    if not reasons:
        reasons.append("strong CRM activity pattern")

    return "Priority account due to " + ", ".join(reasons) + "."


def build_risk_reason(profile: dict):
    reasons = []

    if profile["high_risk_signals"] > 0:
        reasons.append(f"{profile['high_risk_signals']} high-risk signal(s)")

    if profile["complaints"] > 0:
        reasons.append(f"{profile['complaints']} complaint signal(s)")

    if profile["retention_actions"] > 0:
        reasons.append(f"{profile['retention_actions']} open retention action(s)")

    if profile["high_priority_actions"] > 0:
        reasons.append(f"{profile['high_priority_actions']} high-priority pending action(s)")

    if profile["total_orders"] == 0:
        reasons.append("no recorded orders")

    if not reasons:
        reasons.append("low activity and weak engagement")

    return "Account risk detected because of " + ", ".join(reasons) + "."


def build_growth_reason(profile: dict):
    reasons = []

    if profile["total_sales"] >= 700:
        reasons.append("meaningful revenue history")

    if profile["praise"] > 0:
        reasons.append("positive customer praise")

    if profile["positive_signals"] > 0:
        reasons.append("positive sentiment signals")

    if profile["inquiries"] > 0:
        reasons.append("active interest or buying intent")

    if profile["upsell_actions"] > 0:
        reasons.append("existing upsell action")

    if not reasons:
        reasons.append("growth-ready engagement pattern")

    return "Growth opportunity based on " + ", ".join(reasons) + "."


def get_business_brain(db: Session):
    customers = db.query(Customer).all()

    profiles = [get_customer_profile(customer, db) for customer in customers]

    total_customers = len(profiles)
    total_orders = db.query(Order).count()
    total_sales = db.query(func.sum(Order.amount)).scalar() or 0
    total_signals = db.query(SocialSignal).count()
    total_actions = db.query(Action).count()

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

    high_risk_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.risk_level == "high")
        .count()
    )

    unmatched_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.customer_id.is_(None))
        .count()
    )

    failed_imports = (
        db.query(ImportLog)
        .filter(ImportLog.status == "failed")
        .count()
    )

    customers_without_orders = len(
        [profile for profile in profiles if profile["total_orders"] == 0]
    )

    customers_without_signals = len(
        [profile for profile in profiles if profile["total_signals"] == 0]
    )

    customers_without_actions = len(
        [profile for profile in profiles if profile["total_actions"] == 0]
    )

    hot_customers = [profile for profile in profiles if profile["status"] == "hot"]
    warm_customers = [profile for profile in profiles if profile["status"] == "warm"]
    cold_customers = [profile for profile in profiles if profile["status"] == "cold"]

    priority_candidates = sorted(
        [
            profile for profile in profiles
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
    )

    risk_candidates = sorted(
        [
            profile for profile in profiles
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
    )

    growth_candidates = sorted(
        [
            profile for profile in profiles
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
    )

    top_priorities = []
    for profile in priority_candidates[:5]:
        top_priorities.append(
            {
                "customer_id": profile["customer_id"],
                "customer_name": profile["customer_name"],
                "company": profile["company"],
                "status": profile["status"],
                "health_score": profile["health_score"],
                "total_sales": profile["total_sales"],
                "pending_actions": profile["pending_actions"],
                "reason": build_priority_reason(profile),
                "recommended_action": "Review the account context and complete the most important pending follow-up.",
            }
        )

    biggest_risks = []
    for profile in risk_candidates[:5]:
        biggest_risks.append(
            {
                "customer_id": profile["customer_id"],
                "customer_name": profile["customer_name"],
                "company": profile["company"],
                "status": profile["status"],
                "health_score": profile["health_score"],
                "total_sales": profile["total_sales"],
                "high_risk_signals": profile["high_risk_signals"],
                "complaints": profile["complaints"],
                "pending_actions": profile["pending_actions"],
                "reason": build_risk_reason(profile),
                "recommended_action": "Prioritize retention outreach and resolve the highest-risk customer signal or pending action.",
            }
        )

    growth_opportunities = []
    for profile in growth_candidates[:5]:
        growth_opportunities.append(
            {
                "customer_id": profile["customer_id"],
                "customer_name": profile["customer_name"],
                "company": profile["company"],
                "status": profile["status"],
                "health_score": profile["health_score"],
                "total_sales": profile["total_sales"],
                "inquiries": profile["inquiries"],
                "praise": profile["praise"],
                "reason": build_growth_reason(profile),
                "recommended_action": "Create a personalized upsell or follow-up offer based on recent account activity.",
            }
        )

    operational_warnings = []

    if failed_imports > 0:
        operational_warnings.append(
            {
                "type": "failed_imports",
                "count": failed_imports,
                "message": f"{failed_imports} failed import operation(s) need review.",
            }
        )

    if unmatched_signals > 0:
        operational_warnings.append(
            {
                "type": "unmatched_signals",
                "count": unmatched_signals,
                "message": f"{unmatched_signals} customer signal(s) are not linked to CRM customers.",
            }
        )

    if high_risk_signals > 0:
        operational_warnings.append(
            {
                "type": "high_risk_signals",
                "count": high_risk_signals,
                "message": f"{high_risk_signals} high-risk signal(s) require attention.",
            }
        )

    if high_priority_actions > 0:
        operational_warnings.append(
            {
                "type": "high_priority_actions",
                "count": high_priority_actions,
                "message": f"{high_priority_actions} high-priority pending action(s) are still open.",
            }
        )

    if customers_without_orders > 0:
        operational_warnings.append(
            {
                "type": "customers_without_orders",
                "count": customers_without_orders,
                "message": f"{customers_without_orders} customer(s) have no order history.",
            }
        )

    if customers_without_signals > 0:
        operational_warnings.append(
            {
                "type": "customers_without_signals",
                "count": customers_without_signals,
                "message": f"{customers_without_signals} customer(s) have no linked customer signals.",
            }
        )

    if customers_without_actions > 0:
        operational_warnings.append(
            {
                "type": "customers_without_actions",
                "count": customers_without_actions,
                "message": f"{customers_without_actions} customer(s) have no AI or manual actions yet.",
            }
        )

    action_plan = []

    if biggest_risks:
        action_plan.append(
            f"Start with retention: review {biggest_risks[0]['customer_name']} from {biggest_risks[0]['company']} because this account has the strongest risk indicators."
        )

    if top_priorities:
        action_plan.append(
            f"Move priority work forward: complete the most important follow-up for {top_priorities[0]['customer_name']} from {top_priorities[0]['company']}."
        )

    if growth_opportunities:
        action_plan.append(
            f"Create a revenue opportunity: prepare an upsell or personalized offer for {growth_opportunities[0]['customer_name']} from {growth_opportunities[0]['company']}."
        )

    if unmatched_signals > 0:
        action_plan.append(
            "Clean the signal pipeline by linking unmatched customer signals to existing customers or converting them into new leads."
        )

    if failed_imports > 0:
        action_plan.append(
            "Review failed imports so the CRM intelligence layer is working with complete data."
        )

    if not action_plan:
        action_plan.append(
            "No urgent operational issues found. Continue monitoring new signals, orders, and pending actions."
        )

    executive_summary = {
        "total_customers": total_customers,
        "total_orders": total_orders,
        "total_sales": total_sales,
        "total_signals": total_signals,
        "total_actions": total_actions,
        "pending_actions": pending_actions,
        "high_priority_actions": high_priority_actions,
        "high_risk_signals": high_risk_signals,
        "unmatched_signals": unmatched_signals,
        "hot_customers": len(hot_customers),
        "warm_customers": len(warm_customers),
        "cold_customers": len(cold_customers),
        "priority_count": len(top_priorities),
        "risk_count": len(biggest_risks),
        "growth_count": len(growth_opportunities),
        "warning_count": len(operational_warnings),
        "summary_text": (
            f"The CRM contains {total_customers} customer account(s), "
            f"{total_orders} order(s), ${total_sales} in tracked revenue, "
            f"{total_signals} customer signal(s), and {pending_actions} pending action(s). "
            f"There are {len(biggest_risks)} risk account(s), "
            f"{len(growth_opportunities)} growth opportunit(ies), "
            f"and {unmatched_signals} unmatched signal(s) that may represent leads or data cleanup work."
        ),
    }

    return {
        "executive_summary": executive_summary,
        "customer_profiles": profiles,
        "top_priorities": top_priorities,
        "biggest_risks": biggest_risks,
        "growth_opportunities": growth_opportunities,
        "operational_warnings": operational_warnings,
        "action_plan": action_plan,
    }