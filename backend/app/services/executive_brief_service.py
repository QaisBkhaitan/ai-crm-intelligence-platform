from sqlalchemy.orm import Session

from app.services.business_brain_service import get_business_brain


def generate_executive_brief(db: Session):
    brain = get_business_brain(db)

    executive_summary = brain.get("executive_summary", {})
    top_priorities = brain.get("top_priorities", [])
    biggest_risks = brain.get("biggest_risks", [])
    growth_opportunities = brain.get("growth_opportunities", [])
    operational_warnings = brain.get("operational_warnings", [])
    action_plan = brain.get("action_plan", [])

    priority_lines = [
        (
            f"{item.get('customer_name', 'Customer')} "
            f"({item.get('company', 'Unknown company')}): "
            f"{item.get('recommended_action', 'Review this account.')}"
        )
        for item in top_priorities[:3]
    ]

    risk_lines = [
        (
            f"{item.get('customer_name', 'Customer')} "
            f"({item.get('company', 'Unknown company')}): "
            f"{item.get('recommended_action', 'Review this risk.')}"
        )
        for item in biggest_risks[:3]
    ]

    growth_lines = [
        (
            f"{item.get('customer_name', 'Customer')} "
            f"({item.get('company', 'Unknown company')}): "
            f"{item.get('recommended_action', 'Review this opportunity.')}"
        )
        for item in growth_opportunities[:3]
    ]

    warning_lines = [
        warning.get("message", "Operational warning needs review.")
        for warning in operational_warnings[:5]
    ]

    summary_text = executive_summary.get(
        "summary_text",
        "No executive summary available yet. Import customer, order, and signal data to activate business intelligence.",
    )

    total_customers = executive_summary.get("total_customers", 0)
    total_orders = executive_summary.get("total_orders", 0)
    total_sales = executive_summary.get("total_sales", 0)
    total_signals = executive_summary.get("total_signals", 0)
    pending_actions = executive_summary.get("pending_actions", 0)
    high_risk_signals = executive_summary.get("high_risk_signals", 0)
    unmatched_signals = executive_summary.get("unmatched_signals", 0)

    if biggest_risks:
        executive_focus = "Retention and risk response"
        focus_reason = "There are customer accounts with high-risk signals, complaints, or urgent pending actions."
    elif growth_opportunities:
        executive_focus = "Revenue growth"
        focus_reason = "There are accounts showing upsell, inquiry, positive sentiment, or strong revenue patterns."
    elif top_priorities:
        executive_focus = "Execution follow-up"
        focus_reason = "There are priority accounts with pending work or meaningful account value."
    elif unmatched_signals > 0:
        executive_focus = "Pipeline cleanup"
        focus_reason = "There are unmatched customer signals that may represent leads or missing customer links."
    else:
        executive_focus = "Monitoring"
        focus_reason = "No urgent risk or growth pattern is currently dominant."

    if total_customers == 0:
        health_assessment = "No CRM data yet"
    elif high_risk_signals > 0 or pending_actions > 10:
        health_assessment = "Needs attention"
    elif growth_opportunities or top_priorities:
        health_assessment = "Active"
    else:
        health_assessment = "Stable"

    closing_note = (
        "This executive brief is generated from live CRM data, including customers, "
        "orders, customer signals, AI-generated actions, import health, and account-level risk/opportunity indicators."
    )

    return {
        "headline": "Executive CRM Brief",
        "summary_text": summary_text,
        "health_assessment": health_assessment,
        "executive_focus": executive_focus,
        "focus_reason": focus_reason,
        "key_metrics": {
            "total_customers": total_customers,
            "total_orders": total_orders,
            "total_sales": total_sales,
            "total_signals": total_signals,
            "total_actions": executive_summary.get("total_actions", 0),
            "pending_actions": pending_actions,
            "high_priority_actions": executive_summary.get("high_priority_actions", 0),
            "high_risk_signals": high_risk_signals,
            "unmatched_signals": unmatched_signals,
            "hot_customers": executive_summary.get("hot_customers", 0),
            "warm_customers": executive_summary.get("warm_customers", 0),
            "cold_customers": executive_summary.get("cold_customers", 0),
            "priority_count": executive_summary.get("priority_count", 0),
            "risk_count": executive_summary.get("risk_count", 0),
            "growth_count": executive_summary.get("growth_count", 0),
            "warning_count": executive_summary.get("warning_count", 0),
        },
        "top_priorities": priority_lines,
        "biggest_risks": risk_lines,
        "growth_opportunities": growth_lines,
        "operational_warnings": warning_lines,
        "action_plan": action_plan,
        "raw_sections": {
            "top_priorities": top_priorities,
            "biggest_risks": biggest_risks,
            "growth_opportunities": growth_opportunities,
            "operational_warnings": operational_warnings,
        },
        "closing_note": closing_note,
    }