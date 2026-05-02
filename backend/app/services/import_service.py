import csv
import io
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.order import Order
from app.models.note import Note
from app.models.import_log import ImportLog
from app.services.rag_service import safe_rebuild_crm_knowledge_index
def normalize_text(value):
    return (value or "").strip()


def normalize_email(value):
    return normalize_text(value).lower()

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
    elif inserted == 0 and skipped > 0:
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
def import_customers_csv(file_content: bytes, file_name: str, db: Session):
    decoded = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    inserted = 0
    skipped = 0
    errors = []

    for row_number, row in enumerate(reader, start=2):
        name = normalize_text(row.get("name"))
        email = normalize_email(row.get("email"))
        phone = normalize_text(row.get("phone"))
        company = normalize_text(row.get("company"))

        if not name or not email or not phone or not company:
            skipped += 1
            errors.append(
                f"Row {row_number}: missing required fields (name, email, phone, company)."
            )
            continue

        existing_customer = (
            db.query(Customer)
            .filter(Customer.email.ilike(email))
            .first()
        )

        if existing_customer:
            skipped += 1
            errors.append(f"Row {row_number}: customer with email '{email}' already exists.")
            continue

        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            company=company,
            source="csv_import",
        )

        db.add(customer)
        inserted += 1

    db.commit()
    log = create_import_log(
        db=db,
        entity_type="customers",
        file_name=file_name,
        inserted=inserted,
        skipped=skipped,
        errors=errors,
    )
    safe_rebuild_crm_knowledge_index(db)
    return {
    "entity": "customers",
    "file_name": file_name,
    "inserted": inserted,
    "skipped": skipped,
    "errors": errors,
    "log_id": log.id,
    "status": log.status,
    "imported_at": log.created_at,
}


def import_orders_csv(file_content: bytes, file_name: str, db: Session):
    decoded = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    inserted = 0
    skipped = 0
    errors = []

    for row_number, row in enumerate(reader, start=2):
        customer_email = normalize_email(row.get("customer_email"))
        product_name = normalize_text(row.get("product_name"))
        amount_raw = normalize_text(row.get("amount"))

        if not customer_email or not product_name or not amount_raw:
            skipped += 1
            errors.append(
                f"Row {row_number}: missing required fields (customer_email, product_name, amount)."
            )
            continue

        try:
            amount = int(float(amount_raw))
        except ValueError:
            skipped += 1
            errors.append(f"Row {row_number}: invalid amount '{amount_raw}'.")
            continue

        customer = (
            db.query(Customer)
            .filter(Customer.email.ilike(customer_email))
            .first()
        )

        if not customer:
            skipped += 1
            errors.append(
                f"Row {row_number}: no customer found with email '{customer_email}'."
            )
            continue

        order = Order(
            customer_id=customer.id,
            product_name=product_name,
            amount=amount,
            source="csv_import",
        )

        db.add(order)
        inserted += 1

    db.commit()
    log = create_import_log(
        db=db,
        entity_type="orders",
        file_name=file_name,
        inserted=inserted,
        skipped=skipped,
        errors=errors,
    )
    safe_rebuild_crm_knowledge_index(db)
    return {
    "entity": "orders",
    "file_name": file_name,
    "inserted": inserted,
    "skipped": skipped,
    "errors": errors,
    "log_id": log.id,
    "status": log.status,
    "imported_at": log.created_at,
}

def import_notes_csv(file_content: bytes, file_name: str, db: Session):
    decoded = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    inserted = 0
    skipped = 0
    errors = []

    for row_number, row in enumerate(reader, start=2):
        customer_email = normalize_email(row.get("customer_email"))
        content = normalize_text(row.get("content"))

        if not customer_email or not content:
            skipped += 1
            errors.append(
                f"Row {row_number}: missing required fields (customer_email, content)."
            )
            continue

        customer = (
            db.query(Customer)
            .filter(Customer.email.ilike(customer_email))
            .first()
        )

        if not customer:
            skipped += 1
            errors.append(
                f"Row {row_number}: no customer found with email '{customer_email}'."
            )
            continue

        note = Note(
            customer_id=customer.id,
            content=content,
            source="csv_import",
        )

        db.add(note)
        inserted += 1

    db.commit()
    log = create_import_log(
    db=db,
    entity_type="notes",
    file_name=file_name,
    inserted=inserted,
    skipped=skipped,
    errors=errors,
    )
    safe_rebuild_crm_knowledge_index(db)
    return {
    "entity": "notes",
    "file_name": file_name,
    "inserted": inserted,
    "skipped": skipped,
    "errors": errors,
    "log_id": log.id,
    "status": log.status,
    "imported_at": log.created_at,
    }