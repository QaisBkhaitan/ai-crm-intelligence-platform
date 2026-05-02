from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.note import Note
from app.services.rag_service import safe_rebuild_crm_knowledge_index
router = APIRouter(prefix="/notes", tags=["Notes"])


class NoteCreate(BaseModel):
    content: str


@router.get("/{customer_id}")
def get_notes(customer_id: int, db: Session = Depends(get_db)):
    notes = db.query(Note).filter(Note.customer_id == customer_id).all()

    return [
        {
            "id": note.id,
            "customer_id": note.customer_id,
            "content": note.content,
            "source": note.source,
            "created_at": note.created_at,
        }
        for note in notes
    ]


@router.post("/{customer_id}")
def add_note(customer_id: int, note: NoteCreate, db: Session = Depends(get_db)):
    new_note = Note(
        customer_id=customer_id,
        content=note.content,
        source="manual",
    )

    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    safe_rebuild_crm_knowledge_index(db)
    return {
        "id": new_note.id,
        "customer_id": new_note.customer_id,
        "content": new_note.content,
        "source": new_note.source,
        "created_at": new_note.created_at,
    }