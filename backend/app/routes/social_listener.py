from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from groq import Groq
from dotenv import load_dotenv
import os
import json
import re
import csv
import io

from app.database import get_db
from app.models.social_signal import SocialSignal
from app.models.action import Action
from app.models.customer import Customer
from app.models.import_log import ImportLog

load_dotenv()

router = APIRouter(prefix="/social-listener", tags=["Customer Signals"])

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -------------------------
# Request Schemas
# -------------------------

class CustomerSignalCreate(BaseModel):
    source: str
    content: str
    author_name: Optional[str] = None
    author_handle: Optional[str] = None
    external_post_url: Optional[str] = None


class WebsiteFormSignal(BaseModel):
    name: str
    email: Optional[str] = None
    company: Optional[str] = None
    message: str


class ConvertSignalToCustomerRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


# -------------------------
# Constants
# -------------------------

ALLOWED_SOURCES = {
    "facebook",
    "instagram",
    "website",
    "website_form",
    "support_ticket",
    "email",
    "api_webhook",
    "manual_import",
}

ALLOWED_ACTION_TYPES = {
    "follow_up",
    "upsell",
    "retention",
    "review",
}


# -------------------------
# Utility Helpers
# -------------------------

def normalize_source(source: str):
    value = (source or "").strip().lower()

    if not value:
        return "api_webhook"

    if value not in ALLOWED_SOURCES:
        return "api_webhook"

    return value


def looks_like_email(value: Optional[str]):
    if not value:
        return False

    value = value.strip()
    return "@" in value and "." in value


def extract_json_object(raw_text: str):
    if not raw_text:
        return None

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)

    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def map_action_type(intent: str, risk_level: str):
    if intent == "complaint" or risk_level == "high":
        return "retention"

    if intent == "inquiry":
        return "follow_up"

    if intent == "praise":
        return "upsell"

    return "review"


def map_priority(intent: str, risk_level: str):
    if risk_level == "high" or intent == "complaint":
        return "high"

    if risk_level == "medium" or intent == "inquiry":
        return "medium"

    return "low"


def fallback_analysis(content: str):
    text = (content or "").lower()

    negative_words = [
        "late",
        "bad",
        "angry",
        "problem",
        "issue",
        "complaint",
        "delay",
        "not working",
        "upset",
        "frustrated",
        "refund",
        "cancel",
    ]

    positive_words = [
        "great",
        "thanks",
        "good",
        "amazing",
        "love",
        "excellent",
        "helpful",
        "smooth",
    ]

    inquiry_words = [
        "price",
        "pricing",
        "cost",
        "interested",
        "contact",
        "demo",
        "plan",
        "how",
        "book",
        "available",
    ]

    if any(word in text for word in negative_words):
        sentiment = "negative"
        intent = "complaint"
        risk_level = "high"
    elif any(word in text for word in inquiry_words):
        sentiment = "neutral"
        intent = "inquiry"
        risk_level = "medium"
    elif any(word in text for word in positive_words):
        sentiment = "positive"
        intent = "praise"
        risk_level = "low"
    else:
        sentiment = "neutral"
        intent = "other"
        risk_level = "low"

    return {
        "sentiment": sentiment,
        "intent": intent,
        "risk_level": risk_level,
        "urgency": "normal",
        "topic": "general customer message",
        "business_impact": "Needs review",
        "confidence": 0.45,
        "recommended_action_type": map_action_type(intent, risk_level),
        "recommended_priority": map_priority(intent, risk_level),
        "recommended_action_title": "Review customer signal",
        "recommended_action_description": "A customer signal was received and should be reviewed.",
        "suggested_reply": "Thank you for reaching out. Our team will review your message and follow up shortly.",
    }


def normalize_ai_analysis(data: dict, content: str):
    if not isinstance(data, dict):
        return fallback_analysis(content)

    sentiment = data.get("sentiment", "neutral")
    intent = data.get("intent", "other")
    risk_level = data.get("risk_level", "low")

    allowed_sentiments = {"positive", "neutral", "negative"}
    allowed_intents = {"complaint", "inquiry", "praise", "other"}
    allowed_risks = {"low", "medium", "high"}

    if sentiment not in allowed_sentiments:
        sentiment = "neutral"

    if intent not in allowed_intents:
        intent = "other"

    if risk_level not in allowed_risks:
        risk_level = "low"

    action_type = data.get("recommended_action_type") or map_action_type(intent, risk_level)
    priority = data.get("recommended_priority") or map_priority(intent, risk_level)

    if action_type not in ALLOWED_ACTION_TYPES:
        action_type = map_action_type(intent, risk_level)

    if priority not in {"low", "medium", "high"}:
        priority = map_priority(intent, risk_level)

    confidence = data.get("confidence", 0.7)

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.7

    confidence = max(0, min(confidence, 1))

    return {
        "sentiment": sentiment,
        "intent": intent,
        "risk_level": risk_level,
        "urgency": data.get("urgency", "normal"),
        "topic": data.get("topic", "general customer message"),
        "business_impact": data.get("business_impact", "Needs review"),
        "confidence": confidence,
        "recommended_action_type": action_type,
        "recommended_priority": priority,
        "recommended_action_title": data.get("recommended_action_title", "Review customer signal"),
        "recommended_action_description": data.get(
            "recommended_action_description",
            "A customer signal was received and should be reviewed."
        ),
        "suggested_reply": data.get(
            "suggested_reply",
            "Thank you for reaching out. Our team will review your message and follow up shortly."
        ),
    }


def analyze_signal_with_ai(content: str):
    if not os.getenv("GROQ_API_KEY"):
        return fallback_analysis(content)

    prompt = f"""
You are an AI customer intelligence engine for a CRM SaaS platform.

Analyze this incoming customer signal:

\"\"\"{content}\"\"\"

Return ONLY valid JSON in this exact shape:

{{
  "sentiment": "positive | neutral | negative",
  "intent": "complaint | inquiry | praise | other",
  "risk_level": "low | medium | high",
  "urgency": "low | normal | urgent | immediate",
  "topic": "short topic label",
  "business_impact": "short business impact explanation",
  "confidence": 0.0,
  "recommended_action_type": "follow_up | retention | upsell | review",
  "recommended_priority": "low | medium | high",
  "recommended_action_title": "short action title",
  "recommended_action_description": "clear action description for the CRM team",
  "suggested_reply": "short professional reply message"
}}

Rules:
- Do not include markdown.
- Do not explain.
- Return JSON only.
- confidence must be a number between 0 and 1.
""".strip()

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        raw_output = response.choices[0].message.content
        parsed = extract_json_object(raw_output)

        return normalize_ai_analysis(parsed, content)

    except Exception as e:
        print("AI SIGNAL ANALYSIS ERROR:", str(e))
        return fallback_analysis(content)


def find_matching_customer(
    db: Session,
    author_name: Optional[str] = None,
    author_handle: Optional[str] = None,
):
    if author_handle:
        handle_value = author_handle.strip().lower()

        if looks_like_email(handle_value):
            customer = (
                db.query(Customer)
                .filter(Customer.email.ilike(handle_value))
                .first()
            )

            if customer:
                return customer

    if author_name:
        customer = (
            db.query(Customer)
            .filter(Customer.name.ilike(f"%{author_name.strip()}%"))
            .first()
        )

        if customer:
            return customer

    return None


def create_import_log(
    db: Session,
    entity_type: str,
    file_name: str,
    inserted: int,
    skipped: int,
    errors: list[str],
):
    status = "success"

    if inserted > 0 and skipped > 0:
        status = "partial_success"
    elif inserted == 0:
        status = "failed"

    log = ImportLog(
        entity_type=entity_type,
        file_name=file_name,
        inserted_count=inserted,
        skipped_count=skipped,
        error_count=len(errors),
        status=status,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def make_lead_email(signal: SocialSignal):
    if looks_like_email(signal.author_handle):
        return signal.author_handle.strip().lower()

    return f"signal-{signal.id}@lead.local"


def ensure_unique_email(db: Session, email: str):
    base_email = email.strip().lower()

    existing = (
        db.query(Customer)
        .filter(Customer.email.ilike(base_email))
        .first()
    )

    if not existing:
        return base_email

    if "@" not in base_email:
        base_email = f"{base_email}@lead.local"

    local, domain = base_email.split("@", 1)

    counter = 1
    while True:
        candidate = f"{local}+{counter}@{domain}"
        existing = (
            db.query(Customer)
            .filter(Customer.email.ilike(candidate))
            .first()
        )

        if not existing:
            return candidate

        counter += 1


# -------------------------
# Serializers
# -------------------------

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


def serialize_action(action: Optional[Action]):
    if not action:
        return None

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


# -------------------------
# Core Business Logic
# -------------------------

def create_action_from_analysis(
    db: Session,
    signal: SocialSignal,
    analysis: dict,
    matched_customer: Optional[Customer],
):
    action_type = analysis["recommended_action_type"]

    if action_type == "review":
        return None

    customer_label = (
        f"{matched_customer.name} ({matched_customer.company})"
        if matched_customer
        else signal.author_name or signal.author_handle or "Unknown customer"
    )

    description = (
        f"{analysis['recommended_action_description']}\n\n"
        f"Customer/Lead: {customer_label}\n"
        f"Original Signal: {signal.content}\n"
        f"Topic: {analysis['topic']}\n"
        f"Business Impact: {analysis['business_impact']}\n"
        f"AI Confidence: {analysis['confidence']}\n"
        f"Suggested Reply: {analysis['suggested_reply']}"
    )

    action = Action(
        customer_id=matched_customer.id if matched_customer else None,
        signal_id=signal.id,
        action_type=action_type,
        title=analysis["recommended_action_title"],
        description=description,
        reason=analysis["business_impact"],
        suggested_reply=analysis["suggested_reply"],
        ai_confidence=analysis["confidence"],
        priority=analysis["recommended_priority"],
        status="pending",
        source="ai",
    )

    db.add(action)
    return action


def process_customer_signal(payload: CustomerSignalCreate, db: Session):
    source = normalize_source(payload.source)
    content = payload.content.strip()

    if not content:
        raise HTTPException(status_code=400, detail="Signal content is required.")

    analysis = analyze_signal_with_ai(content)

    matched_customer = find_matching_customer(
        db=db,
        author_name=payload.author_name,
        author_handle=payload.author_handle,
    )

    signal = SocialSignal(
        customer_id=matched_customer.id if matched_customer else None,
        source=source,
        author_name=payload.author_name,
        author_handle=payload.author_handle,
        content=content,
        sentiment=analysis["sentiment"],
        intent=analysis["intent"],
        risk_level=analysis["risk_level"],
        external_post_url=payload.external_post_url,
    )

    db.add(signal)
    db.flush()

    action = create_action_from_analysis(
        db=db,
        signal=signal,
        analysis=analysis,
        matched_customer=matched_customer,
    )

    db.commit()
    db.refresh(signal)

    if action:
        db.refresh(action)

    return {
        "message": "Customer signal ingested and analyzed successfully.",
        "signal": serialize_signal(signal),
        "analysis": analysis,
        "matched_customer": serialize_customer(matched_customer) if matched_customer else None,
        "action_created": action is not None,
        "action": serialize_action(action),
    }


def attach_signal_and_actions_to_customer(
    db: Session,
    signal: SocialSignal,
    customer: Customer,
):
    signal.customer_id = customer.id

    related_actions = (
        db.query(Action)
        .filter(Action.signal_id == signal.id)
        .all()
    )

    for action in related_actions:
        action.customer_id = customer.id

    db.commit()
    db.refresh(signal)
    db.refresh(customer)

    return related_actions


# -------------------------
# Ingestion Endpoints
# -------------------------

@router.post("/webhook")
def ingest_webhook_signal(
    payload: CustomerSignalCreate,
    db: Session = Depends(get_db),
):
    return process_customer_signal(payload, db)


@router.post("/website-form")
def ingest_website_form(
    payload: WebsiteFormSignal,
    db: Session = Depends(get_db),
):
    author_name = payload.name.strip()
    enriched_content = payload.message.strip()

    if payload.email:
        enriched_content += f"\n\nEmail: {payload.email}"

    if payload.company:
        enriched_content += f"\nCompany: {payload.company}"

    signal_payload = CustomerSignalCreate(
        source="website_form",
        author_name=author_name,
        author_handle=payload.email,
        content=enriched_content,
    )

    return process_customer_signal(signal_payload, db)


@router.post("/ingest")
def legacy_ingest_signal(
    source: str,
    content: str,
    author_name: Optional[str] = None,
    author_handle: Optional[str] = None,
    external_post_url: Optional[str] = None,
    db: Session = Depends(get_db),
):
    payload = CustomerSignalCreate(
        source=source,
        content=content,
        author_name=author_name,
        author_handle=author_handle,
        external_post_url=external_post_url,
    )

    return process_customer_signal(payload, db)


@router.post("/import-csv")
async def import_customer_signals_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    content = await file.read()

    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(decoded))

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or invalid.")

    required_columns = {"source", "author_name", "content"}
    missing_columns = required_columns - set(reader.fieldnames)

    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {sorted(missing_columns)}",
        )

    inserted = 0
    skipped = 0
    created_actions = 0
    matched_customers = 0
    unmatched_signals = 0
    errors = []

    for row_number, row in enumerate(reader, start=2):
        source = (row.get("source") or "").strip()
        author_name = (row.get("author_name") or "").strip()
        author_handle = (row.get("author_handle") or "").strip()
        content_text = (row.get("content") or "").strip()
        external_post_url = (row.get("external_post_url") or "").strip() or None

        if not source or not author_name or not content_text:
            skipped += 1
            errors.append(
                f"Row {row_number}: missing required fields "
                f"(source, author_name, content)."
            )
            continue

        try:
            payload = CustomerSignalCreate(
                source=source,
                author_name=author_name,
                author_handle=author_handle or None,
                content=content_text,
                external_post_url=external_post_url,
            )

            result = process_customer_signal(payload, db)

            inserted += 1

            if result.get("action_created"):
                created_actions += 1

            if result.get("matched_customer"):
                matched_customers += 1
            else:
                unmatched_signals += 1

        except Exception as e:
            skipped += 1
            errors.append(f"Row {row_number}: {str(e)}")

    log = create_import_log(
        db=db,
        entity_type="customer_signals",
        file_name=file.filename,
        inserted=inserted,
        skipped=skipped,
        errors=errors,
    )

    return {
        "entity": "customer_signals",
        "file_name": file.filename,
        "inserted": inserted,
        "skipped": skipped,
        "created_actions": created_actions,
        "matched_customers": matched_customers,
        "unmatched_signals": unmatched_signals,
        "errors": errors,
        "log_id": log.id,
        "status": log.status,
        "imported_at": log.created_at,
    }


# -------------------------
# Lead / Customer Linking Endpoints
# -------------------------

@router.get("/unmatched")
def get_unmatched_signals(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.customer_id.is_(None))
        .order_by(SocialSignal.created_at.desc(), SocialSignal.id.desc())
        .limit(limit)
        .all()
    )

    return [serialize_signal(signal) for signal in signals]


@router.put("/{signal_id}/link-customer/{customer_id}")
def link_signal_to_existing_customer(
    signal_id: int,
    customer_id: int,
    db: Session = Depends(get_db),
):
    signal = db.query(SocialSignal).filter(SocialSignal.id == signal_id).first()

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found.")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    related_actions = attach_signal_and_actions_to_customer(
        db=db,
        signal=signal,
        customer=customer,
    )

    return {
        "message": "Signal linked to existing customer successfully.",
        "signal": serialize_signal(signal),
        "customer": serialize_customer(customer),
        "updated_actions": [serialize_action(action) for action in related_actions],
        "updated_actions_count": len(related_actions),
    }


@router.post("/{signal_id}/convert-to-customer")
def convert_signal_to_customer(
    signal_id: int,
    payload: Optional[ConvertSignalToCustomerRequest] = None,
    db: Session = Depends(get_db),
):
    signal = db.query(SocialSignal).filter(SocialSignal.id == signal_id).first()

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found.")

    if signal.customer_id:
        existing_customer = (
            db.query(Customer)
            .filter(Customer.id == signal.customer_id)
            .first()
        )

        return {
            "message": "Signal is already linked to a customer.",
            "signal": serialize_signal(signal),
            "customer": serialize_customer(existing_customer) if existing_customer else None,
            "updated_actions": [],
            "updated_actions_count": 0,
        }

    payload = payload or ConvertSignalToCustomerRequest()

    name = (
        payload.name
        or signal.author_name
        or signal.author_handle
        or f"Lead from Signal #{signal.id}"
    )

    email = payload.email or make_lead_email(signal)
    email = ensure_unique_email(db, email)

    phone = payload.phone or "Unknown"
    company = payload.company or "Unmatched Leads"

    customer = Customer(
        name=name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        company=company.strip(),
        source="signal_conversion",
    )

    db.add(customer)
    db.flush()

    related_actions = attach_signal_and_actions_to_customer(
        db=db,
        signal=signal,
        customer=customer,
    )

    return {
        "message": "Signal converted to customer successfully.",
        "signal": serialize_signal(signal),
        "customer": serialize_customer(customer),
        "updated_actions": [serialize_action(action) for action in related_actions],
        "updated_actions_count": len(related_actions),
    }


# -------------------------
# Analytics Endpoint
# -------------------------

@router.get("/analytics")
def get_signal_analytics(db: Session = Depends(get_db)):
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

    other = (
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

    actions_from_signals = (
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

    source_rows = (
        db.query(SocialSignal.source, func.count(SocialSignal.id))
        .group_by(SocialSignal.source)
        .all()
    )

    intent_rows = (
        db.query(SocialSignal.intent, func.count(SocialSignal.id))
        .group_by(SocialSignal.intent)
        .all()
    )

    risk_rows = (
        db.query(SocialSignal.risk_level, func.count(SocialSignal.id))
        .group_by(SocialSignal.risk_level)
        .all()
    )

    latest_signals = (
        db.query(SocialSignal)
        .order_by(SocialSignal.created_at.desc(), SocialSignal.id.desc())
        .limit(6)
        .all()
    )

    top_risk_signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.risk_level == "high")
        .order_by(SocialSignal.created_at.desc(), SocialSignal.id.desc())
        .limit(5)
        .all()
    )

    conversion_rate = 0
    if total_signals > 0:
        conversion_rate = round((actions_from_signals / total_signals) * 100, 1)

    match_rate = 0
    if total_signals > 0:
        match_rate = round((matched_signals / total_signals) * 100, 1)

    return {
        "summary": {
            "total_signals": total_signals,
            "high_risk_signals": high_risk_signals,
            "medium_risk_signals": medium_risk_signals,
            "low_risk_signals": low_risk_signals,
            "complaints": complaints,
            "inquiries": inquiries,
            "praise": praise,
            "other": other,
            "matched_signals": matched_signals,
            "unmatched_signals": unmatched_signals,
            "actions_from_signals": actions_from_signals,
            "pending_signal_actions": pending_signal_actions,
            "high_priority_signal_actions": high_priority_signal_actions,
            "conversion_rate": conversion_rate,
            "match_rate": match_rate,
        },
        "by_source": [
            {"source": row[0] or "unknown", "count": row[1]}
            for row in source_rows
        ],
        "by_intent": [
            {"intent": row[0] or "unknown", "count": row[1]}
            for row in intent_rows
        ],
        "by_risk": [
            {"risk_level": row[0] or "unknown", "count": row[1]}
            for row in risk_rows
        ],
        "latest_signals": [serialize_signal(signal) for signal in latest_signals],
        "top_risk_signals": [serialize_signal(signal) for signal in top_risk_signals],
    }


# -------------------------
# Read Endpoints
# -------------------------
@router.get("/customer/{customer_id}")
def get_customer_signal_workspace(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    signals = (
        db.query(SocialSignal)
        .filter(SocialSignal.customer_id == customer_id)
        .order_by(SocialSignal.created_at.desc(), SocialSignal.id.desc())
        .all()
    )

    actions = (
        db.query(Action)
        .filter(Action.customer_id == customer_id)
        .order_by(Action.created_at.desc(), Action.id.desc())
        .all()
    )

    total_signals = len(signals)
    high_risk_signals = len([s for s in signals if s.risk_level == "high"])
    complaints = len([s for s in signals if s.intent == "complaint"])
    inquiries = len([s for s in signals if s.intent == "inquiry"])
    praise = len([s for s in signals if s.intent == "praise"])

    pending_actions = len([a for a in actions if a.status == "pending"])
    completed_actions = len([a for a in actions if a.status == "completed"])
    high_priority_actions = len(
        [a for a in actions if a.status == "pending" and a.priority == "high"]
    )

    latest_signal = signals[0] if signals else None
    latest_action = actions[0] if actions else None

    if high_risk_signals > 0 or high_priority_actions > 0:
        relationship_status = "needs_attention"
    elif inquiries > 0 or pending_actions > 0:
        relationship_status = "active_opportunity"
    elif total_signals > 0:
        relationship_status = "engaged"
    else:
        relationship_status = "quiet"

    return {
        "customer": serialize_customer(customer),
        "summary": {
            "total_signals": total_signals,
            "high_risk_signals": high_risk_signals,
            "complaints": complaints,
            "inquiries": inquiries,
            "praise": praise,
            "total_actions": len(actions),
            "pending_actions": pending_actions,
            "completed_actions": completed_actions,
            "high_priority_actions": high_priority_actions,
            "relationship_status": relationship_status,
            "latest_signal": serialize_signal(latest_signal) if latest_signal else None,
            "latest_action": serialize_action(latest_action) if latest_action else None,
        },
        "signals": [serialize_signal(signal) for signal in signals],
        "actions": [serialize_action(action) for action in actions],
    }
@router.get("/")
def get_signals(
    source: str = Query(default=""),
    intent: str = Query(default=""),
    risk_level: str = Query(default=""),
    only_unmatched: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(SocialSignal)

    if source:
        query = query.filter(SocialSignal.source == source.strip())

    if intent:
        query = query.filter(SocialSignal.intent == intent.strip())

    if risk_level:
        query = query.filter(SocialSignal.risk_level == risk_level.strip())

    if only_unmatched:
        query = query.filter(SocialSignal.customer_id.is_(None))

    signals = (
        query
        .order_by(SocialSignal.created_at.desc(), SocialSignal.id.desc())
        .limit(limit)
        .all()
    )

    return [serialize_signal(signal) for signal in signals]