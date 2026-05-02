from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from groq import Groq
from dotenv import load_dotenv
import os
import json

from app.services.action_generation_service import generate_all_ai_actions
from app.database import get_db

from app.models.customer import Customer
from app.models.note import Note
from app.models.order import Order
from app.models.import_log import ImportLog
from app.models.action import Action
from app.models.social_signal import SocialSignal

from app.services.business_brain_service import get_business_brain
from app.services.customer_service import query_customers
from app.services.executive_brief_service import generate_executive_brief
from app.services.dashboard_service import get_dashboard_overview
from app.services.recommendation_service import get_actionable_recommendations
from app.services.rag_service import (
    rebuild_crm_knowledge_index,
    search_crm_knowledge,
)

load_dotenv()

router = APIRouter(prefix="/ai", tags=["AI"])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -------------------------
# Serialization Helpers
# -------------------------

def serialize_order(order: Order):
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "product_name": order.product_name,
        "amount": order.amount,
        "source": order.source,
        "created_at": order.created_at,
    }


def serialize_signal(signal: SocialSignal):
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


# -------------------------
# Customer Context + Intelligence
# -------------------------

def find_customer_by_name(name: str, db: Session):
    if not name:
        return None

    return (
        db.query(Customer)
        .filter(Customer.name.ilike(f"%{name.strip()}%"))
        .first()
    )


def get_customer_orders(customer_id: int, db: Session):
    return (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .all()
    )


def get_customer_signals(customer_id: int, db: Session):
    return (
        db.query(SocialSignal)
        .filter(SocialSignal.customer_id == customer_id)
        .order_by(SocialSignal.created_at.desc(), SocialSignal.id.desc())
        .all()
    )


def get_customer_actions(customer_id: int, db: Session):
    return (
        db.query(Action)
        .filter(Action.customer_id == customer_id)
        .order_by(Action.created_at.desc(), Action.id.desc())
        .all()
    )


def build_suggested_follow_up_message(
    customer: Customer,
    intelligence: dict,
    latest_signal=None,
):
    name = customer.name
    company = customer.company

    relationship_status = intelligence.get("relationship_status")
    total_sales = intelligence.get("total_sales", 0)
    high_risk_signals = intelligence.get("high_risk_signals", 0)
    inquiries = intelligence.get("inquiries", 0)
    praise = intelligence.get("praise", 0)

    if latest_signal and hasattr(latest_signal, "suggested_reply") and latest_signal.suggested_reply:
        return latest_signal.suggested_reply

    if relationship_status == "needs_attention":
        return (
            f"Hi {name}, I wanted to personally follow up regarding your recent experience with {company}. "
            f"We noticed there may be an issue that needs attention, and I’d like to help resolve it as quickly as possible."
        )

    if inquiries > 0:
        return (
            f"Hi {name}, thanks for your recent interest in {company}. "
            f"I’d be happy to help you explore the best option and answer any questions you have."
        )

    if praise > 0:
        return (
            f"Hi {name}, thank you for the positive feedback about {company}. "
            f"We appreciate it and would be happy to support your next step whenever you are ready."
        )

    if total_sales >= 1000:
        return (
            f"Hi {name}, I wanted to check in and see how things are going with {company}. "
            f"Based on your previous activity, there may be a good opportunity to explore a higher-value option or next step."
        )

    if high_risk_signals > 0:
        return (
            f"Hi {name}, I wanted to follow up and make sure your recent concern is being handled properly. "
            f"Please let us know how we can help."
        )

    return (
        f"Hi {name}, I wanted to follow up and see if there is anything {company} can help you with right now."
    )


def get_customer_intelligence(customer_id: int, db: Session):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        return None

    total_orders = (
        db.query(func.count(Order.id))
        .filter(Order.customer_id == customer_id)
        .scalar()
        or 0
    )

    total_sales = (
        db.query(func.sum(Order.amount))
        .filter(Order.customer_id == customer_id)
        .scalar()
        or 0
    )

    total_signals = (
        db.query(func.count(SocialSignal.id))
        .filter(SocialSignal.customer_id == customer_id)
        .scalar()
        or 0
    )

    high_risk_signals = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer_id,
            SocialSignal.risk_level == "high",
        )
        .scalar()
        or 0
    )

    complaints = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer_id,
            SocialSignal.intent == "complaint",
        )
        .scalar()
        or 0
    )

    inquiries = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer_id,
            SocialSignal.intent == "inquiry",
        )
        .scalar()
        or 0
    )

    praise = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer_id,
            SocialSignal.intent == "praise",
        )
        .scalar()
        or 0
    )

    positive_signals = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer_id,
            SocialSignal.sentiment == "positive",
        )
        .scalar()
        or 0
    )

    negative_signals = (
        db.query(func.count(SocialSignal.id))
        .filter(
            SocialSignal.customer_id == customer_id,
            SocialSignal.sentiment == "negative",
        )
        .scalar()
        or 0
    )

    total_actions = (
        db.query(func.count(Action.id))
        .filter(Action.customer_id == customer_id)
        .scalar()
        or 0
    )

    pending_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer_id,
            Action.status == "pending",
        )
        .scalar()
        or 0
    )

    completed_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer_id,
            Action.status == "completed",
        )
        .scalar()
        or 0
    )

    high_priority_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer_id,
            Action.status == "pending",
            Action.priority == "high",
        )
        .scalar()
        or 0
    )

    retention_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer_id,
            Action.status == "pending",
            Action.action_type == "retention",
        )
        .scalar()
        or 0
    )

    upsell_actions = (
        db.query(func.count(Action.id))
        .filter(
            Action.customer_id == customer_id,
            Action.status == "pending",
            Action.action_type == "upsell",
        )
        .scalar()
        or 0
    )

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

    # Customer engagement
    score += min(total_signals * 4, 18)
    score += min(positive_signals * 5, 12)
    score += min(inquiries * 3, 9)
    score += min(praise * 5, 12)

    # Active execution
    if pending_actions > 0:
        score += min(pending_actions * 2, 8)

    # Risk penalties
    score -= min(high_risk_signals * 12, 35)
    score -= min(complaints * 10, 30)
    score -= min(high_priority_actions * 6, 18)
    score -= min(negative_signals * 6, 18)

    score = max(0, min(score, 100))

    if high_risk_signals > 0 or complaints > 0 or retention_actions > 0 or high_priority_actions > 0:
        status = "cold"
        relationship_status = "needs_attention"
        risk_level = "high"
        next_best_action = "Review high-risk signals and complete urgent retention or follow-up actions."
        risk_reason = (
            "This account has risk indicators such as complaints, high-risk signals, "
            "retention actions, or urgent pending work."
        )
        opportunity_reason = "Growth should wait until the risk is handled."
    elif total_sales >= 1000 or praise > 0 or positive_signals > 0:
        status = "hot"
        relationship_status = "engaged"
        risk_level = "low"
        next_best_action = "Use the positive account momentum to propose an upsell, renewal, or high-value follow-up."
        risk_reason = "No major risk pattern detected."
        opportunity_reason = "This account has strong revenue, positive sentiment, or praise signals."
    elif inquiries > 0 or upsell_actions > 0 or pending_actions > 0:
        status = "warm"
        relationship_status = "active_opportunity"
        risk_level = "medium"
        next_best_action = "Follow up while the customer is showing active interest or while pending actions are open."
        risk_reason = "No urgent risk, but the account needs timely follow-up."
        opportunity_reason = "This account has inquiry signals, open work, or an upsell opportunity."
    elif total_orders > 0 or total_signals > 0:
        status = "warm"
        relationship_status = "engaged"
        risk_level = "low"
        next_best_action = "Maintain engagement and monitor for the next sales or support signal."
        risk_reason = "No urgent risk detected."
        opportunity_reason = "This account has some activity and can be nurtured."
    else:
        status = "cold"
        relationship_status = "quiet"
        risk_level = "low"
        next_best_action = "Re-engage this customer or enrich the account with orders, signals, or actions."
        risk_reason = "The account has limited activity data."
        opportunity_reason = "More data is needed before identifying a strong opportunity."

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
        "risk_level": risk_level,

        # Kept for frontend/API compatibility.
        "total_notes": 0,

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
        "recommended_action": next_best_action,
        "next_best_action": next_best_action,
        "risk_reason": risk_reason,
        "opportunity_reason": opportunity_reason,
    }


def get_customer_ai_insights(customer_id: int, db: Session):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        return None

    orders = get_customer_orders(customer_id, db)
    signals = get_customer_signals(customer_id, db)
    actions = get_customer_actions(customer_id, db)

    total_orders = len(orders)
    total_sales = sum(order.amount for order in orders)
    total_signals = len(signals)

    high_risk_signals = len(
        [signal for signal in signals if signal.risk_level == "high"]
    )

    complaints = len(
        [signal for signal in signals if signal.intent == "complaint"]
    )

    inquiries = len(
        [signal for signal in signals if signal.intent == "inquiry"]
    )

    praise = len(
        [signal for signal in signals if signal.intent == "praise"]
    )

    pending_actions = len(
        [action for action in actions if action.status == "pending"]
    )

    completed_actions = len(
        [action for action in actions if action.status == "completed"]
    )

    high_priority_actions = len(
        [
            action for action in actions
            if action.status == "pending" and action.priority == "high"
        ]
    )

    intelligence = get_customer_intelligence(customer_id, db)

    if not intelligence:
        return None

    status = intelligence["status"]
    relationship_status = intelligence["relationship_status"]
    health_score = intelligence["health_score"]

    if relationship_status == "needs_attention":
        account_summary = (
            f"{customer.name} from {customer.company} needs attention. "
            f"The account has {high_risk_signals} high-risk signal(s), "
            f"{complaints} complaint(s), and {high_priority_actions} high-priority pending action(s)."
        )
        risk_assessment = intelligence["risk_reason"]
        opportunity_assessment = "Opportunity exists only after resolving the current risk signals."
        opportunity_flag = "Retention risk"
    elif relationship_status == "active_opportunity":
        account_summary = (
            f"{customer.name} from {customer.company} is an active opportunity. "
            f"The account has {inquiries} inquiry signal(s), {pending_actions} pending action(s), "
            f"and ${total_sales} in tracked revenue."
        )
        risk_assessment = intelligence["risk_reason"]
        opportunity_assessment = intelligence["opportunity_reason"]
        opportunity_flag = "Active opportunity"
    elif status == "hot":
        account_summary = (
            f"{customer.name} from {customer.company} is a strong account with "
            f"${total_sales} in tracked revenue, {total_orders} order(s), and {praise} praise signal(s)."
        )
        risk_assessment = "No major risk pattern detected."
        opportunity_assessment = intelligence["opportunity_reason"]
        opportunity_flag = "High growth potential"
    elif status == "warm":
        account_summary = (
            f"{customer.name} from {customer.company} has moderate activity with "
            f"{total_orders} order(s), {total_signals} signal(s), and {pending_actions} pending action(s)."
        )
        risk_assessment = intelligence["risk_reason"]
        opportunity_assessment = intelligence["opportunity_reason"]
        opportunity_flag = "Moderate growth opportunity"
    else:
        account_summary = (
            f"{customer.name} from {customer.company} has limited activity data. "
            f"The account may need re-engagement or more CRM activity."
        )
        risk_assessment = intelligence["risk_reason"]
        opportunity_assessment = intelligence["opportunity_reason"]
        opportunity_flag = "Needs re-engagement"

    suggested_follow_up_message = build_suggested_follow_up_message(
        customer=customer,
        intelligence=intelligence,
        latest_signal=signals[0] if signals else None,
    )

    latest_signal_preview = (
        signals[0].content if signals else "No recent customer signals available."
    )

    latest_order_preview = (
        f"{orders[0].product_name} (${orders[0].amount})"
        if orders
        else "No recent orders available."
    )

    latest_action_preview = (
        f"{actions[0].title} ({actions[0].priority} priority, {actions[0].status})"
        if actions
        else "No recent actions available."
    )

    return {
        "customer": serialize_customer(customer),
        "insight_summary": {
            "health_score": health_score,
            "status": status,
            "relationship_status": relationship_status,
            "risk_level": intelligence["risk_level"],

            # Kept for frontend/API compatibility.
            "total_notes": 0,

            "total_orders": total_orders,
            "total_sales": total_sales,
            "total_signals": total_signals,
            "high_risk_signals": high_risk_signals,
            "complaints": complaints,
            "inquiries": inquiries,
            "praise": praise,
            "total_actions": len(actions),
            "pending_actions": pending_actions,
            "completed_actions": completed_actions,
            "high_priority_actions": high_priority_actions,
        },
        "ai_recommendation": {
            "account_summary": account_summary,
            "risk_assessment": risk_assessment,
            "opportunity_assessment": opportunity_assessment,
            "next_best_action": intelligence["next_best_action"],
            "reason": (
                intelligence["risk_reason"]
                if relationship_status == "needs_attention"
                else intelligence["opportunity_reason"]
            ),
            "opportunity_flag": opportunity_flag,
            "suggested_follow_up_message": suggested_follow_up_message,
        },
        "context_preview": {
            "latest_note": (
                "Notes are not the current intelligence source. "
                "This CRM now prioritizes signals, orders, and actions."
            ),
            "latest_order": latest_order_preview,
            "latest_signal": latest_signal_preview,
            "latest_action": latest_action_preview,
        },
        "recent_orders": [
            serialize_order(order)
            for order in orders[:5]
        ],
        "recent_signals": [
            serialize_signal(signal)
            for signal in signals[:5]
        ],
        "recent_actions": [
            serialize_action(action)
            for action in actions[:5]
        ],
    }


def build_customer_context(customer_id: int, db: Session):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        return None

    orders = get_customer_orders(customer_id, db)[:5]
    signals = get_customer_signals(customer_id, db)[:5]
    actions = get_customer_actions(customer_id, db)[:5]

    intelligence = get_customer_intelligence(customer_id, db)

    if not intelligence:
        return None

    orders_text = (
        "\n".join(
            [
                f"- {order.product_name}: ${order.amount} | Source: {order.source} | Created: {order.created_at}"
                for order in orders
            ]
        )
        if orders
        else "No recent orders."
    )

    signals_text = (
        "\n".join(
            [
                (
                    f"- Source: {signal.source} | Sentiment: {signal.sentiment} | "
                    f"Intent: {signal.intent} | Risk: {signal.risk_level} | "
                    f"Content: {signal.content}"
                )
                for signal in signals
            ]
        )
        if signals
        else "No linked customer signals."
    )

    actions_text = (
        "\n".join(
            [
                (
                    f"- Type: {action.action_type} | Priority: {action.priority} | "
                    f"Status: {action.status} | Title: {action.title} | "
                    f"Reason: {action.reason or 'N/A'}"
                )
                for action in actions
            ]
        )
        if actions
        else "No recent actions."
    )

    context = f"""
Customer Info:
Name: {customer.name}
Company: {customer.company}
Email: {customer.email}
Phone: {customer.phone}
Source: {customer.source}
Created At: {customer.created_at}
Updated At: {customer.updated_at}

Account Metrics:
Total Orders: {intelligence.get("total_orders")}
Total Sales: ${intelligence.get("total_sales")}
Total Signals: {intelligence.get("total_signals")}
High Risk Signals: {intelligence.get("high_risk_signals")}
Complaints: {intelligence.get("complaints")}
Inquiries: {intelligence.get("inquiries")}
Praise Signals: {intelligence.get("praise")}
Pending Actions: {intelligence.get("pending_actions")}
High Priority Actions: {intelligence.get("high_priority_actions")}

AI Customer Intelligence:
Health Score: {intelligence.get("health_score")}
Status: {intelligence.get("status")}
Relationship Status: {intelligence.get("relationship_status")}
Risk Level: {intelligence.get("risk_level")}
Risk Reason: {intelligence.get("risk_reason")}
Opportunity Reason: {intelligence.get("opportunity_reason")}
Next Best Action: {intelligence.get("next_best_action")}

Recent Orders:
{orders_text}

Recent Customer Signals:
{signals_text}

Recent Actions:
{actions_text}
"""

    return context


# -------------------------
# Smart Tools
# -------------------------

def query_customers_tool(action_input: dict, db: Session):
    return query_customers(
        db=db,
        search=action_input.get("search", ""),
        company=action_input.get("company", ""),
        source=action_input.get("source", ""),
        created_after=action_input.get("created_after", ""),
        created_before=action_input.get("created_before", ""),
        sort_by=action_input.get("sort_by", "id"),
        sort_order=action_input.get("sort_order", "desc"),
        page=action_input.get("page", 1),
        limit=action_input.get("limit", 5),
    )


def get_business_brain_tool(db: Session):
    return get_business_brain(db)


def get_executive_brief_tool(db: Session):
    return generate_executive_brief(db)


def get_customer_workspace_tool(customer_name: str, db: Session):
    customer = find_customer_by_name(customer_name, db)

    if not customer:
        return {"error": "Customer not found"}

    orders = get_customer_orders(customer.id, db)
    signals = get_customer_signals(customer.id, db)
    actions = get_customer_actions(customer.id, db)

    total_orders = len(orders)
    total_sales = sum(order.amount for order in orders)

    total_signals = len(signals)
    high_risk_signals = len([signal for signal in signals if signal.risk_level == "high"])
    complaints = len([signal for signal in signals if signal.intent == "complaint"])
    inquiries = len([signal for signal in signals if signal.intent == "inquiry"])
    praise = len([signal for signal in signals if signal.intent == "praise"])

    pending_actions = len([action for action in actions if action.status == "pending"])
    completed_actions = len([action for action in actions if action.status == "completed"])
    high_priority_actions = len(
        [
            action for action in actions
            if action.status == "pending" and action.priority == "high"
        ]
    )

    intelligence = get_customer_intelligence(customer.id, db)
    insights = get_customer_ai_insights(customer.id, db)

    return {
        "customer": serialize_customer(customer),
        "metrics": {
            "total_orders": total_orders,
            "total_sales": total_sales,

            # Kept for compatibility with old frontend/agent wording.
            "total_notes": 0,

            "total_signals": total_signals,
            "high_risk_signals": high_risk_signals,
            "complaints": complaints,
            "inquiries": inquiries,
            "praise": praise,
            "total_actions": len(actions),
            "pending_actions": pending_actions,
            "completed_actions": completed_actions,
            "high_priority_actions": high_priority_actions,
        },
        "intelligence": intelligence,
        "insights": insights,
        "recent_notes": [],
        "recent_orders": [
            serialize_order(order)
            for order in orders[:5]
        ],
        "recent_signals": [
            serialize_signal(signal)
            for signal in signals[:5]
        ],
        "recent_actions": [
            serialize_action(action)
            for action in actions[:5]
        ],
    }


def get_business_overview_tool(db: Session):
    return get_dashboard_overview(db)


def get_import_history_tool(action_input: dict, db: Session):
    limit = action_input.get("limit", 10)
    entity_type = action_input.get("entity_type", "").strip()

    query = db.query(ImportLog)

    if entity_type:
        query = query.filter(ImportLog.entity_type == entity_type)

    logs = query.order_by(ImportLog.created_at.desc()).limit(limit).all()

    return {
        "items": [
            {
                "id": log.id,
                "entity_type": log.entity_type,
                "file_name": log.file_name,
                "inserted_count": log.inserted_count,
                "skipped_count": log.skipped_count,
                "error_count": log.error_count,
                "status": log.status,
                "created_at": log.created_at,
            }
            for log in logs
        ]
    }


def get_actionable_recommendations_tool(db: Session):
    return get_actionable_recommendations(db)


def search_crm_knowledge_tool(action_input: dict):
    return search_crm_knowledge(
        query_text=action_input.get("query", ""),
        n_results=action_input.get("n_results", 5),
        entity_type=action_input.get("entity_type", ""),
    )


def run_tool(action: str, action_input: dict, db: Session):
    if action == "query_customers":
        return query_customers_tool(action_input, db)

    if action == "get_customer_workspace":
        return get_customer_workspace_tool(
            action_input.get("customer_name", ""),
            db,
        )

    if action == "get_business_brain":
        return get_business_brain_tool(db)

    if action == "get_executive_brief":
        return get_executive_brief_tool(db)

    if action == "get_business_overview":
        return get_business_overview_tool(db)

    if action == "get_import_history":
        return get_import_history_tool(action_input, db)

    if action == "get_actionable_recommendations":
        return get_actionable_recommendations_tool(db)

    if action == "search_crm_knowledge":
        return search_crm_knowledge_tool(action_input)

    return {"error": f"Unknown action: {action}"}


def run_agent(question: str, db: Session):
    clean_question = question.lower().strip()

    simple_questions = [
        "hi",
        "hello",
        "hey",
        "how are you",
        "good morning",
        "good evening",
    ]

    if clean_question in simple_questions:
        return (
            "Hello! I am your AI CRM assistant. Ask me about customers, "
            "orders, signals, actions, imports, recommendations, or business insights."
        )

    system_prompt = """
You are an AI CRM agent connected to a real CRM backend.

You have access to these tools:

1. query_customers
   Input: {
     "search": "",
     "company": "",
     "source": "",
     "created_after": "",
     "created_before": "",
     "sort_by": "id | name | email | company | created_at | updated_at",
     "sort_order": "asc | desc",
     "page": 1,
     "limit": 5
   }

2. get_customer_workspace
   Input: {
     "customer_name": "name"
   }

3. get_business_overview
   Input: {}

4. get_import_history
   Input: {
     "entity_type": "",
     "limit": 10
   }

5. get_actionable_recommendations
   Input: {}

6. search_crm_knowledge
   Input: {
     "query": "",
     "n_results": 5,
     "entity_type": ""
   }

7. get_business_brain
   Input: {}

8. get_executive_brief
   Input: {}

Tool guidance:
- Use query_customers when the user asks to search, filter, sort, or list customers.
- Use get_customer_workspace when the user asks about one specific customer and needs a full picture.
- Use get_business_overview for dashboard, top customers, risky customers, sales, signal activity, actions, or business summary questions.
- Use get_import_history for CSV imports, upload history, failed imports, or recent imported files.
- Use get_actionable_recommendations when the user asks what to do next, who to prioritize, which customers need attention, upsell opportunities, or operational recommendations.
- Use search_crm_knowledge for broader semantic retrieval across CRM data when the user asks open-ended questions, asks about general patterns, or when no structured tool cleanly fits the question.
- entity_type in search_crm_knowledge can be: customer, note, order, import_log. If signals/actions are not indexed yet, use structured tools instead.
- Use get_business_brain when the user asks for strategic priorities, growth opportunities, business risks, weekly focus, or executive-level CRM recommendations.
- Use get_executive_brief when the user asks for an executive summary, management brief, weekly brief, strategic report, or concise business report.

Current CRM direction:
- Customer intelligence should focus on customers, orders, customer signals, and actions.
- Notes are legacy and should not be treated as the main source of intelligence.
- Signals represent real-world customer interactions.
- Actions represent execution work generated from AI or CRM intelligence.

Rules:
- Think step by step internally.
- Use one tool at a time.
- If the question does not need CRM data, answer directly with FINAL ANSWER.
- After receiving tool results, summarize clearly and briefly.
- Mention useful customer names, companies, counts, risks, opportunities, and observations when relevant.
- If there are no matching records, say that clearly.
- Keep tool inputs valid JSON only.
- Do not invent CRM data.
- Be concise and business-focused.

You must respond in one of these two formats only:

Format 1:
ACTION: tool_name
INPUT: {"key": "value"}

Format 2:
FINAL ANSWER: your answer here
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    for _ in range(7):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.2,
        )

        output = response.choices[0].message.content.strip()

        if output.startswith("FINAL ANSWER:"):
            return output.replace("FINAL ANSWER:", "").strip()

        if "ACTION:" in output and "INPUT:" in output:
            try:
                action_part = output.split("ACTION:")[1].split("INPUT:")[0].strip()
                input_part = output.split("INPUT:")[1].strip()

                action = action_part
                action_input = json.loads(input_part)

                tool_result = run_tool(action, action_input, db)

                messages.append({"role": "assistant", "content": output})
                messages.append(
                    {
                        "role": "user",
                        "content": f"OBSERVATION: {json.dumps(tool_result, default=str)}",
                    }
                )
            except Exception as e:
                return f"Agent error while parsing tool usage: {str(e)}"
        else:
            return output

    fallback_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful CRM assistant. Answer clearly and briefly.",
            },
            {"role": "user", "content": question},
        ],
        temperature=0.3,
    )

    return fallback_response.choices[0].message.content


# -------------------------
# Routes
# -------------------------

@router.get("/customer-intelligence/{customer_id}")
def customer_intelligence(customer_id: int, db: Session = Depends(get_db)):
    intelligence = get_customer_intelligence(customer_id, db)

    if not intelligence:
        return {"error": "Customer not found"}

    return intelligence


@router.get("/customer-insights/{customer_id}")
def customer_ai_insights(customer_id: int, db: Session = Depends(get_db)):
    insights = get_customer_ai_insights(customer_id, db)

    if not insights:
        return {"error": "Customer not found"}

    return insights


@router.get("/recommendations")
def ai_recommendations(db: Session = Depends(get_db)):
    return get_actionable_recommendations(db)


@router.post("/rag/rebuild")
def rebuild_rag_index(db: Session = Depends(get_db)):
    return rebuild_crm_knowledge_index(db)


@router.get("/rag/search")
def rag_search(
    query: str,
    n_results: int = 5,
    entity_type: str = "",
):
    return search_crm_knowledge(
        query_text=query,
        n_results=n_results,
        entity_type=entity_type,
    )


@router.post("/customer-summary/{customer_id}")
def generate_customer_summary(customer_id: int, db: Session = Depends(get_db)):
    context = build_customer_context(customer_id, db)

    if not context:
        return {"error": "Customer not found"}

    prompt = f"""
You are an AI CRM assistant.

Based on the following customer data:

{context}

Return your answer ONLY as JSON in this exact format:

{{
  "summary": "...",
  "status": "hot | warm | cold",
  "relationship_status": "needs_attention | active_opportunity | engaged | quiet",
  "risk_level": "low | medium | high",
  "next_action": "..."
}}

Rules:
- Do NOT write anything outside JSON.
- Keep answers short and practical.
- Base your answer on orders, signals, actions, risk indicators, and revenue.
- Do not use notes as the primary intelligence source.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a strict JSON generator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        raw_text = response.choices[0].message.content

        try:
            parsed = json.loads(raw_text)
            return parsed
        except Exception:
            return {
                "summary": raw_text,
                "status": "unknown",
                "relationship_status": "unknown",
                "risk_level": "unknown",
                "next_action": "N/A",
            }

    except Exception as e:
        intelligence = get_customer_intelligence(customer_id, db)

        if not intelligence:
            return {"error": "Customer not found"}

        return {
            "summary": (
                f"{intelligence['customer_name']} has {intelligence['total_orders']} order(s), "
                f"${intelligence['total_sales']} in tracked revenue, "
                f"{intelligence['total_signals']} linked signal(s), and "
                f"{intelligence['pending_actions']} pending action(s)."
            ),
            "status": intelligence["status"],
            "relationship_status": intelligence["relationship_status"],
            "risk_level": intelligence["risk_level"],
            "next_action": intelligence["next_best_action"],
            "fallback_reason": f"AI summary generation failed: {str(e)}",
        }


@router.get("/business-brain")
def ai_business_brain(db: Session = Depends(get_db)):
    return get_business_brain(db)


@router.get("/executive-brief")
def ai_executive_brief(db: Session = Depends(get_db)):
    return generate_executive_brief(db)


@router.post("/generate-actions")
def ai_generate_actions(db: Session = Depends(get_db)):
    return generate_all_ai_actions(db)


@router.post("/chat")
def ai_chat(db: Session = Depends(get_db), question: str = ""):
    if not question.strip():
        return {"answer": "Please provide a question."}

    answer = run_agent(question, db)
    return {"answer": answer}