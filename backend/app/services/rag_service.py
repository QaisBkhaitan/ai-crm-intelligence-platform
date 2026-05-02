import os
from typing import List

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.note import Note
from app.models.order import Order
from app.models.import_log import ImportLog

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "crm_knowledge"

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2",
    device="cpu",
    normalize_embeddings=False,
)

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_function,
)


def _customer_doc(customer: Customer) -> tuple[str, str, dict]:
    doc_id = f"customer-{customer.id}"
    document = (
        f"Customer profile\n"
        f"Name: {customer.name}\n"
        f"Company: {customer.company}\n"
        f"Email: {customer.email}\n"
        f"Phone: {customer.phone}\n"
        f"Source: {customer.source}\n"
        f"Created At: {customer.created_at}\n"
        f"Updated At: {customer.updated_at}\n"
    )
    metadata = {
        "entity_type": "customer",
        "customer_id": customer.id,
        "customer_name": customer.name,
        "company": customer.company,
        "source": customer.source,
    }
    return doc_id, document, metadata


def _note_doc(note: Note, customer: Customer | None) -> tuple[str, str, dict]:
    doc_id = f"note-{note.id}"
    customer_name = customer.name if customer else "Unknown"
    company = customer.company if customer else "Unknown"
    document = (
        f"Customer note\n"
        f"Customer Name: {customer_name}\n"
        f"Company: {company}\n"
        f"Note Content: {note.content}\n"
        f"Source: {note.source}\n"
        f"Created At: {note.created_at}\n"
    )
    metadata = {
        "entity_type": "note",
        "note_id": note.id,
        "customer_id": note.customer_id,
        "customer_name": customer_name,
        "company": company,
        "source": note.source,
    }
    return doc_id, document, metadata


def _order_doc(order: Order, customer: Customer | None) -> tuple[str, str, dict]:
    doc_id = f"order-{order.id}"
    customer_name = customer.name if customer else "Unknown"
    company = customer.company if customer else "Unknown"
    document = (
        f"Customer order\n"
        f"Customer Name: {customer_name}\n"
        f"Company: {company}\n"
        f"Product Name: {order.product_name}\n"
        f"Amount: {order.amount}\n"
        f"Source: {order.source}\n"
        f"Created At: {order.created_at}\n"
    )
    metadata = {
        "entity_type": "order",
        "order_id": order.id,
        "customer_id": order.customer_id,
        "customer_name": customer_name,
        "company": company,
        "source": order.source,
    }
    return doc_id, document, metadata


def _import_log_doc(log: ImportLog) -> tuple[str, str, dict]:
    doc_id = f"import-{log.id}"
    document = (
        f"Import log\n"
        f"Entity Type: {log.entity_type}\n"
        f"File Name: {log.file_name}\n"
        f"Inserted Count: {log.inserted_count}\n"
        f"Skipped Count: {log.skipped_count}\n"
        f"Error Count: {log.error_count}\n"
        f"Status: {log.status}\n"
        f"Created At: {log.created_at}\n"
    )
    metadata = {
        "entity_type": "import_log",
        "import_log_id": log.id,
        "status": log.status,
        "file_name": log.file_name,
    }
    return doc_id, document, metadata


def rebuild_crm_knowledge_index(db: Session):
    # clear existing collection contents
    existing = collection.get()
    existing_ids = existing.get("ids", [])
    if existing_ids:
        collection.delete(ids=existing_ids)

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[dict] = []

    customers = db.query(Customer).all()
    customer_map = {customer.id: customer for customer in customers}

    for customer in customers:
        doc_id, doc_text, metadata = _customer_doc(customer)
        ids.append(doc_id)
        documents.append(doc_text)
        metadatas.append(metadata)

    notes = db.query(Note).all()
    for note in notes:
        customer = customer_map.get(note.customer_id)
        doc_id, doc_text, metadata = _note_doc(note, customer)
        ids.append(doc_id)
        documents.append(doc_text)
        metadatas.append(metadata)

    orders = db.query(Order).all()
    for order in orders:
        customer = customer_map.get(order.customer_id)
        doc_id, doc_text, metadata = _order_doc(order, customer)
        ids.append(doc_id)
        documents.append(doc_text)
        metadatas.append(metadata)

    import_logs = db.query(ImportLog).all()
    for log in import_logs:
        doc_id, doc_text, metadata = _import_log_doc(log)
        ids.append(doc_id)
        documents.append(doc_text)
        metadatas.append(metadata)

    if ids:
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    return {
        "message": "CRM knowledge index rebuilt successfully.",
        "indexed_documents": len(ids),
        "collection_name": COLLECTION_NAME,
    }


def search_crm_knowledge(
    query_text: str,
    n_results: int = 5,
    entity_type: str = "",
):
    if not query_text.strip():
        return {"items": []}

    where_filter = None
    if entity_type.strip():
        where_filter = {"entity_type": entity_type.strip()}

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_filter,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else []

    items = []
    for i, doc in enumerate(documents):
        items.append(
            {
                "id": ids[i] if i < len(ids) else None,
                "document": doc,
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else None,
            }
        )

    return {
        "query": query_text,
        "entity_type": entity_type,
        "count": len(items),
        "items": items,
    }
def safe_rebuild_crm_knowledge_index(db: Session):
    try:
        return rebuild_crm_knowledge_index(db)
    except Exception as e:
        return {
            "message": "RAG rebuild failed",
            "error": str(e),
        }