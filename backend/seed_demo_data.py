import argparse
import random
from datetime import datetime, timedelta

from app.database import Base, engine, SessionLocal
from app.models.customer import Customer
from app.models.order import Order
from app.models.note import Note
from app.models.social_signal import SocialSignal
from app.models.action import Action
from app.models.import_log import ImportLog


random.seed(42)


FIRST_NAMES = [
    "Omar", "Lina", "Ahmad", "Maya", "Yousef", "Sara", "Khaled", "Nour",
    "Adam", "Leen", "Rami", "Huda", "Tariq", "Dina", "Sami", "Mona",
    "Zaid", "Rana", "Fadi", "Yara"
]

LAST_NAMES = [
    "Nasser", "Haddad", "Saleh", "Khalil", "Mansour", "Darwish", "Qasem",
    "Awad", "Hamdan", "Barakat", "Sabbah", "Najjar", "Khatib", "Zein"
]

COMPANIES = [
    "Nasser Tech", "Levant Retail", "Bright Media", "Atlas Logistics",
    "BluePeak Agency", "Urban Mart", "Cedar Solutions", "Nova Design Studio",
    "GreenLine Foods", "Falcon Systems", "SmartBuild", "VisionCare",
    "CloudPoint", "Elite Commerce", "Future Motors"
]

PRODUCTS = [
    "CRM Starter Plan", "CRM Business Plan", "AI Insights Add-on",
    "Support Automation Package", "Data Import Service", "Premium Dashboard",
    "Customer Intelligence Module", "Sales Pipeline Setup"
]

SOURCES = [
    "website_form", "support_ticket", "email", "api_webhook",
    "facebook", "instagram"
]


SIGNAL_TEMPLATES = [
    {
        "intent": "complaint",
        "sentiment": "negative",
        "risk_level": "high",
        "priority": "high",
        "action_type": "retention",
        "topic": "delayed response",
        "messages": [
            "My order is late and nobody is answering me. This is very frustrating.",
            "I contacted support twice and still have no update.",
            "The service stopped working and I need help immediately.",
            "I am disappointed with the delay. Please resolve this today.",
            "This issue is affecting my business and I need someone to contact me."
        ],
        "suggested_reply": "Sorry for the inconvenience. We are checking this urgently and will follow up with an update shortly."
    },
    {
        "intent": "inquiry",
        "sentiment": "neutral",
        "risk_level": "medium",
        "priority": "medium",
        "action_type": "follow_up",
        "topic": "pricing inquiry",
        "messages": [
            "I am interested in your CRM pricing. Can someone contact me?",
            "Do you offer a business plan for small companies?",
            "Can I book a demo for the AI CRM platform?",
            "I want to know more about the dashboard and AI features.",
            "How much does the customer intelligence module cost?"
        ],
        "suggested_reply": "Thanks for reaching out. We would be happy to explain the plans and help you choose the best option."
    },
    {
        "intent": "praise",
        "sentiment": "positive",
        "risk_level": "low",
        "priority": "low",
        "action_type": "upsell",
        "topic": "positive feedback",
        "messages": [
            "Great support team. The response was fast and helpful.",
            "The dashboard is very useful. Thanks for the great work.",
            "I like how easy it is to manage customers with this system.",
            "The AI recommendations are helpful for our sales team.",
            "Amazing experience so far. Everything works smoothly."
        ],
        "suggested_reply": "Thank you for the kind feedback. We are glad the platform is helping your team."
    },
    {
        "intent": "other",
        "sentiment": "neutral",
        "risk_level": "low",
        "priority": "low",
        "action_type": "review",
        "topic": "general message",
        "messages": [
            "Can you send me more information?",
            "I saw your platform and wanted to check what it does.",
            "Please share your company profile.",
            "I want to understand the available services.",
            "Can someone explain the next steps?"
        ],
        "suggested_reply": "Thank you for your message. Our team will review it and follow up shortly."
    },
]


NOTE_TEMPLATES = [
    "Customer asked about pricing and implementation timeline.",
    "Follow-up needed next week regarding business plan.",
    "Customer showed interest in AI recommendations.",
    "Support interaction was positive.",
    "Customer may need onboarding support.",
    "Potential upsell opportunity if engagement continues.",
    "Customer requested more details about dashboard analytics.",
]


def random_date_within_days(days=90):
    return datetime.utcnow() - timedelta(
        days=random.randint(0, days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def random_phone():
    return f"+97059{random.randint(1000000, 9999999)}"


def clear_existing_data(db):
    db.query(Action).delete()
    db.query(SocialSignal).delete()
    db.query(Order).delete()
    db.query(Note).delete()
    db.query(ImportLog).delete()
    db.query(Customer).delete()
    db.commit()


def create_customers(db, count):
    customers = []

    for i in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        company = random.choice(COMPANIES)

        customer = Customer(
            name=name,
            email=f"{first.lower()}.{last.lower()}.{i}@example.com",
            phone=random_phone(),
            company=company,
            source=random.choice(["csv_import", "website_form", "manual", "api_webhook"]),
            created_at=random_date_within_days(120),
        )

        db.add(customer)
        customers.append(customer)

    db.commit()

    for customer in customers:
        db.refresh(customer)

    return customers


def create_orders(db, customers):
    orders = []

    for customer in customers:
        order_count = random.choices(
            population=[0, 1, 2, 3, 4, 5],
            weights=[15, 25, 25, 18, 12, 5],
            k=1,
        )[0]

        for _ in range(order_count):
            amount = random.choice([99, 149, 199, 249, 399, 499, 799, 999, 1499])

            order = Order(
                customer_id=customer.id,
                product_name=random.choice(PRODUCTS),
                amount=amount,
                source=random.choice(["manual", "csv_import", "website_form"]),
                created_at=random_date_within_days(100),
            )

            db.add(order)
            orders.append(order)

    db.commit()
    return orders


def create_notes(db, customers):
    notes = []

    for customer in customers:
        note_count = random.choices(
            population=[0, 1, 2, 3],
            weights=[20, 40, 30, 10],
            k=1,
        )[0]

        for _ in range(note_count):
            note = Note(
                customer_id=customer.id,
                content=random.choice(NOTE_TEMPLATES),
                source=random.choice(["manual", "ai", "support_ticket"]),
                created_at=random_date_within_days(80),
            )

            db.add(note)
            notes.append(note)

    db.commit()
    return notes


def create_signal_and_action(db, customers, index):
    template = random.choice(SIGNAL_TEMPLATES)
    source = random.choice(SOURCES)

    should_match_customer = random.random() < 0.7

    matched_customer = random.choice(customers) if should_match_customer else None

    if matched_customer:
        author_name = matched_customer.name
        author_handle = matched_customer.email
        customer_id = matched_customer.id
    else:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        author_name = f"{first} {last}"
        author_handle = f"{first.lower()}.{last.lower()}.lead{index}@example.com"
        customer_id = None

    content = random.choice(template["messages"])

    signal = SocialSignal(
        customer_id=customer_id,
        source=source,
        author_name=author_name,
        author_handle=author_handle,
        content=content,
        sentiment=template["sentiment"],
        intent=template["intent"],
        risk_level=template["risk_level"],
        external_post_url=None,
        created_at=random_date_within_days(45),
    )

    db.add(signal)
    db.flush()

    action = None

    should_create_action = template["intent"] in ["complaint", "inquiry", "praise"]

    if should_create_action:
        confidence = round(random.uniform(0.68, 0.96), 2)

        if template["intent"] == "complaint":
            title = f"Resolve high-risk issue for {author_name}"
            reason = "Customer signal indicates frustration or possible churn risk."
            description = (
                f"A negative customer signal was detected and requires urgent follow-up.\n\n"
                f"Original Signal: {content}\n"
                f"Topic: {template['topic']}\n"
                f"Business Impact: Possible retention risk.\n"
                f"AI Confidence: {confidence}\n"
                f"Suggested Reply: {template['suggested_reply']}"
            )

        elif template["intent"] == "inquiry":
            title = f"Follow up with interested lead: {author_name}"
            reason = "Customer signal indicates buying interest or pricing intent."
            description = (
                f"A customer or lead asked for more information and should be contacted.\n\n"
                f"Original Signal: {content}\n"
                f"Topic: {template['topic']}\n"
                f"Business Impact: Potential sales opportunity.\n"
                f"AI Confidence: {confidence}\n"
                f"Suggested Reply: {template['suggested_reply']}"
            )

        else:
            title = f"Explore upsell opportunity with {author_name}"
            reason = "Positive customer feedback may indicate expansion potential."
            description = (
                f"A positive customer signal was detected and can be used for relationship building.\n\n"
                f"Original Signal: {content}\n"
                f"Topic: {template['topic']}\n"
                f"Business Impact: Potential upsell or advocacy opportunity.\n"
                f"AI Confidence: {confidence}\n"
                f"Suggested Reply: {template['suggested_reply']}"
            )

        status = random.choices(
            population=["pending", "completed", "cancelled"],
            weights=[70, 22, 8],
            k=1,
        )[0]

        action = Action(
            customer_id=customer_id,
            signal_id=signal.id,
            action_type=template["action_type"],
            title=title,
            description=description,
            reason=reason,
            suggested_reply=template["suggested_reply"],
            ai_confidence=confidence,
            priority=template["priority"],
            status=status,
            source="ai",
            created_at=signal.created_at + timedelta(minutes=random.randint(1, 20)),
            completed_at=random_date_within_days(20) if status == "completed" else None,
        )

        db.add(action)

    return signal, action


def create_signals_and_actions(db, customers, count):
    signals = []
    actions = []

    for i in range(count):
        signal, action = create_signal_and_action(db, customers, i)
        signals.append(signal)

        if action:
            actions.append(action)

    db.commit()

    return signals, actions


def create_import_logs(db):
    logs = [
        ImportLog(
            entity_type="customers",
            file_name="demo_customers.csv",
            inserted_count=120,
            skipped_count=4,
            error_count=4,
            status="partial_success",
            created_at=random_date_within_days(25),
        ),
        ImportLog(
            entity_type="orders",
            file_name="demo_orders.csv",
            inserted_count=260,
            skipped_count=8,
            error_count=8,
            status="partial_success",
            created_at=random_date_within_days(20),
        ),
        ImportLog(
            entity_type="notes",
            file_name="demo_notes.csv",
            inserted_count=180,
            skipped_count=0,
            error_count=0,
            status="success",
            created_at=random_date_within_days(15),
        ),
    ]

    db.add_all(logs)
    db.commit()

    return logs


def main():
    parser = argparse.ArgumentParser(description="Seed demo data for AI CRM.")
    parser.add_argument("--reset", action="store_true", help="Delete existing demo data before seeding.")
    parser.add_argument("--customers", type=int, default=120)
    parser.add_argument("--signals", type=int, default=350)

    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        if args.reset:
            clear_existing_data(db)

        customers = create_customers(db, args.customers)
        orders = create_orders(db, customers)
        notes = create_notes(db, customers)
        signals, actions = create_signals_and_actions(db, customers, args.signals)
        logs = create_import_logs(db)

        print("Demo data seeded successfully.")
        print(f"Customers: {len(customers)}")
        print(f"Orders: {len(orders)}")
        print(f"Notes: {len(notes)}")
        print(f"Signals: {len(signals)}")
        print(f"Actions: {len(actions)}")
        print(f"Import logs: {len(logs)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()