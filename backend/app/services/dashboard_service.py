from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.customer import Customer
from app.models.order import Order
from app.models.action import Action
from app.models.social_signal import SocialSignal
from app.models.import_log import ImportLog


def calculate_customer_intelligence(
    customer,
    orders_count: int,
    total_sales: int,
    signals_count: int,
    high_risk_signals: int,
    complaints: int,
    inquiries: int,
    praise: int,
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

    # Buying activity
    score += min(orders_count * 8, 25)

    # Customer engagement through signals
    score += min(signals_count * 4, 18)

    # Positive intent improves account confidence
    score += min(praise * 5, 12)
    score += min(inquiries * 3, 9)

    # Pending work means there is active CRM motion
    if pending_actions > 0:
        score += min(pending_actions * 2, 8)

    # Risk penalties
    score -= min(high_risk_signals * 12, 35)
    score -= min(complaints * 10, 30)
    score -= min(high_priority_actions * 6, 18)

    score = max(0, min(score, 100))

    if high_risk_signals > 0 or complaints > 0 or high_priority_actions > 0:
        status = "cold"
        relationship_status = "needs_attention"
        recommended_action = "Resolve high-risk signals and urgent pending actions before focusing on growth."
    elif total_sales >= 1000 or praise > 0:
        status = "hot"
        relationship_status = "engaged"
        recommended_action = "Prioritize this account for upsell, retention, or a high-value follow-up."
    elif inquiries > 0 or pending_actions > 0:
        status = "warm"
        relationship_status = "active_opportunity"
        recommended_action = "Follow up while the customer is showing active interest or open work exists."
    elif orders_count > 0 or signals_count > 0:
        status = "warm"
        relationship_status = "engaged"
        recommended_action = "Maintain engagement and continue monitoring account activity."
    else:
        status = "cold"
        relationship_status = "quiet"
        recommended_action = "Re-engage this account or enrich it with more data."

    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "company": customer.company,
        "email": customer.email,
        "phone": customer.phone,
        "source": customer.source,
        "health_score": score,
        "status": status,
        "relationship_status": relationship_status,
        "total_orders": orders_count,
        "total_sales": total_sales,
        "total_signals": signals_count,
        "high_risk_signals": high_risk_signals,
        "complaints": complaints,
        "inquiries": inquiries,
        "praise": praise,
        "pending_actions": pending_actions,
        "high_priority_actions": high_priority_actions,
        "recommended_action": recommended_action,
    }


def get_customer_dashboard_profile(customer: Customer, db: Session):
    orders_count = (
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

    signals_count = (
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

    pending_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer.id,
            Action.status == "pending",
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

    return calculate_customer_intelligence(
        customer=customer,
        orders_count=orders_count,
        total_sales=total_sales,
        signals_count=signals_count,
        high_risk_signals=high_risk_signals,
        complaints=complaints,
        inquiries=inquiries,
        praise=praise,
        pending_actions=pending_actions,
        high_priority_actions=high_priority_actions,
    )


def serialize_latest_signal(signal: SocialSignal):
    return {
        "id": signal.id,
        "customer_id": signal.customer_id,
        "source": signal.source,
        "author_name": signal.author_name,
        "author_handle": signal.author_handle,
        "content": signal.content,
        "sentiment": signal.sentiment,
        "intent": signal.intent,
        "risk_level": signal.risk_level,
        "external_post_url": signal.external_post_url,
        "created_at": signal.created_at,
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


def get_distribution(db: Session, model, field):
    rows = (
        db.query(field, func.count(model.id))
        .group_by(field)
        .all()
    )

    return [
        {
            "label": row[0] or "unknown",
            "count": row[1] or 0,
        }
        for row in rows
    ]


def get_dashboard_overview(db: Session):
    total_customers = db.query(Customer).count()
    total_orders = db.query(Order).count()
    total_sales = db.query(func.sum(Order.amount)).scalar() or 0

    total_signals = db.query(SocialSignal).count()

    high_risk_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.risk_level == "high")
        .count()
    )

    medium_risk_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.risk_level == "medium")
        .count()
    )

    low_risk_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.risk_level == "low")
        .count()
    )

    complaints = (
        db.query(SocialSignal)
        .filter(SocialSignal.intent == "complaint")
        .count()
    )

    inquiries = (
        db.query(SocialSignal)
        .filter(SocialSignal.intent == "inquiry")
        .count()
    )

    praise = (
        db.query(SocialSignal)
        .filter(SocialSignal.intent == "praise")
        .count()
    )

    other_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.intent == "other")
        .count()
    )

    matched_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.customer_id.isnot(None))
        .count()
    )

    unmatched_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.customer_id.is_(None))
        .count()
    )

    total_actions = db.query(Action).count()

    pending_actions = (
        db.query(Action)
        .filter(Action.status == "pending")
        .count()
    )

    completed_actions = (
        db.query(Action)
        .filter(Action.status == "completed")
        .count()
    )

    cancelled_actions = (
        db.query(Action)
        .filter(Action.status == "cancelled")
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

    signal_actions = (
        db.query(Action)
        .filter(Action.signal_id.isnot(None))
        .count()
    )

    pending_signal_actions = (
        db.query(Action)
        .filter(
            Action.signal_id.isnot(None),
            Action.status == "pending",
        )
        .count()
    )

    high_priority_signal_actions = (
        db.query(Action)
        .filter(
            Action.signal_id.isnot(None),
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

    partial_imports = (
        db.query(ImportLog)
        .filter(ImportLog.status == "partial_success")
        .count()
    )

    successful_imports = (
        db.query(ImportLog)
        .filter(ImportLog.status == "success")
        .count()
    )

    customers = db.query(Customer).all()

    intelligence_list = [
        get_customer_dashboard_profile(customer, db)
        for customer in customers
    ]

    top_customers = sorted(
        [
            customer
            for customer in intelligence_list
            if customer["status"] == "hot"
        ],
        key=lambda item: (
            item["health_score"],
            item["total_sales"],
            item["total_orders"],
        ),
        reverse=True,
    )[:5]

    at_risk_customers = sorted(
        [
            customer
            for customer in intelligence_list
            if (
                customer["relationship_status"] == "needs_attention"
                or customer["high_risk_signals"] > 0
                or customer["complaints"] > 0
                or customer["high_priority_actions"] > 0
            )
        ],
        key=lambda item: (
            item["high_risk_signals"],
            item["complaints"],
            item["high_priority_actions"],
            item["total_sales"],
        ),
        reverse=True,
    )[:5]

    opportunity_customers = sorted(
        [
            customer
            for customer in intelligence_list
            if (
                customer["relationship_status"] == "active_opportunity"
                or customer["inquiries"] > 0
                or customer["praise"] > 0
                or customer["total_sales"] >= 700
            )
            and customer["relationship_status"] != "needs_attention"
        ],
        key=lambda item: (
            item["total_sales"],
            item["inquiries"],
            item["praise"],
            item["health_score"],
        ),
        reverse=True,
    )[:5]

    latest_signals = (
        db.query(SocialSignal)
        .order_by(SocialSignal.created_at.desc(), SocialSignal.id.desc())
        .limit(5)
        .all()
    )

    top_risk_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.risk_level == "high")
        .order_by(SocialSignal.created_at.desc(), SocialSignal.id.desc())
        .limit(5)
        .all()
    )

    priority_actions = (
        db.query(Action)
        .filter(Action.status == "pending")
        .order_by(
            Action.priority.desc(),
            Action.created_at.desc(),
            Action.id.desc(),
        )
        .limit(5)
        .all()
    )

    conversion_rate = round((signal_actions / total_signals) * 100, 2) if total_signals else 0
    match_rate = round((matched_signals / total_signals) * 100, 2) if total_signals else 0
    action_completion_rate = round((completed_actions / total_actions) * 100, 2) if total_actions else 0

    strong_customers_count = len(
        [customer for customer in intelligence_list if customer["status"] == "hot"]
    )

    warm_customers_count = len(
        [customer for customer in intelligence_list if customer["status"] == "warm"]
    )

    at_risk_customers_count = len(
        [
            customer
            for customer in intelligence_list
            if customer["relationship_status"] == "needs_attention"
        ]
    )

    quiet_customers_count = len(
        [
            customer
            for customer in intelligence_list
            if customer["relationship_status"] == "quiet"
        ]
    )

    pipeline_health = "stable"

    if high_risk_signals > 0 or high_priority_actions > 0:
        pipeline_health = "needs_attention"
    elif inquiries > 0 or opportunity_customers:
        pipeline_health = "active_opportunity"
    elif total_signals == 0:
        pipeline_health = "inactive"

    if total_signals > 0:
        executive_message = (
            f"Your CRM processed {total_signals} customer signal(s), "
            f"created {signal_actions} signal-driven action(s), and currently has "
            f"{pending_actions} pending execution item(s). "
            f"{high_risk_signals} signal(s) are high risk and {unmatched_signals} signal(s) are still unmatched."
        )
    else:
        executive_message = (
            "No customer signals have been processed yet. Import signals to activate the AI decision pipeline."
        )

    if high_risk_signals > 0 or high_priority_actions > 0:
        recommendation = "Start with high-risk signals and high-priority pending actions."
    elif opportunity_customers:
        recommendation = "Focus on active opportunities and accounts showing buying intent."
    elif unmatched_signals > 0:
        recommendation = "Link unmatched signals to existing customers or convert them into new leads."
    elif total_customers == 0:
        recommendation = "Import customer and order data to activate dashboard intelligence."
    else:
        recommendation = "Continue monitoring orders, customer signals, and pending actions."

    business_summary = {
        "strong_customers_count": strong_customers_count,
        "warm_customers_count": warm_customers_count,
        "at_risk_customers_count": at_risk_customers_count,
        "quiet_customers_count": quiet_customers_count,
        "pipeline_health": pipeline_health,
        "message": executive_message,
        "recommendation": recommendation,
    }

    return {
        "metrics": {
            "total_customers": total_customers,
            "total_orders": total_orders,
            "total_sales": total_sales,
            "total_signals": total_signals,
            "total_actions": total_actions,
            "pending_actions": pending_actions,
            "completed_actions": completed_actions,
            "cancelled_actions": cancelled_actions,
            "high_priority_actions": high_priority_actions,
        },
        "signal_summary": {
            "total_signals": total_signals,
            "high_risk_signals": high_risk_signals,
            "medium_risk_signals": medium_risk_signals,
            "low_risk_signals": low_risk_signals,
            "complaints": complaints,
            "inquiries": inquiries,
            "praise": praise,
            "other": other_signals,
            "matched_signals": matched_signals,
            "unmatched_signals": unmatched_signals,
            "signal_actions": signal_actions,
            "pending_signal_actions": pending_signal_actions,
            "high_priority_signal_actions": high_priority_signal_actions,
            "conversion_rate": conversion_rate,
            "match_rate": match_rate,
        },
        "action_summary": {
            "total_actions": total_actions,
            "pending_actions": pending_actions,
            "completed_actions": completed_actions,
            "cancelled_actions": cancelled_actions,
            "high_priority_actions": high_priority_actions,
            "signal_actions": signal_actions,
            "pending_signal_actions": pending_signal_actions,
            "completion_rate": action_completion_rate,
        },
        "import_summary": {
            "successful_imports": successful_imports,
            "partial_imports": partial_imports,
            "failed_imports": failed_imports,
        },
        "top_customers": top_customers,
        "at_risk_customers": at_risk_customers,
        "opportunity_customers": opportunity_customers,
        "latest_signals": [
            serialize_latest_signal(signal)
            for signal in latest_signals
        ],
        "top_risk_signals": [
            serialize_latest_signal(signal)
            for signal in top_risk_signals
        ],
        "priority_actions": [
            serialize_action(action)
            for action in priority_actions
        ],
        "distributions": {
            "signals_by_source": [
                {
                    "source": item["label"],
                    "count": item["count"],
                }
                for item in get_distribution(db, SocialSignal, SocialSignal.source)
            ],
            "signals_by_intent": [
                {
                    "intent": item["label"],
                    "count": item["count"],
                }
                for item in get_distribution(db, SocialSignal, SocialSignal.intent)
            ],
            "signals_by_risk": [
                {
                    "risk_level": item["label"],
                    "count": item["count"],
                }
                for item in get_distribution(db, SocialSignal, SocialSignal.risk_level)
            ],
            "actions_by_status": [
                {
                    "status": item["label"],
                    "count": item["count"],
                }
                for item in get_distribution(db, Action, Action.status)
            ],
            "actions_by_type": [
                {
                    "action_type": item["label"],
                    "count": item["count"],
                }
                for item in get_distribution(db, Action, Action.action_type)
            ],
        },
        "business_summary": business_summary,
    }