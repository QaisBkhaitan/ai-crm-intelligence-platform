from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.models.import_log import ImportLog
from app.database import get_db
from app.services.import_service import (
    import_customers_csv,
    import_orders_csv,
    import_notes_csv,
)

router = APIRouter(prefix="/imports", tags=["Imports"])


def validate_csv_file(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")


@router.post("/customers")
async def import_customers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    validate_csv_file(file)
    content = await file.read()
    return import_customers_csv(content, file.filename, db)


@router.post("/orders")
async def import_orders(file: UploadFile = File(...), db: Session = Depends(get_db)):
    validate_csv_file(file)
    content = await file.read()
    return import_orders_csv(content, file.filename, db)


@router.post("/notes")
async def import_notes(file: UploadFile = File(...), db: Session = Depends(get_db)):
    validate_csv_file(file)
    content = await file.read()
    return import_notes_csv(content, file.filename, db)

@router.get("/history")
def get_import_history(db: Session = Depends(get_db)):
    logs = db.query(ImportLog).order_by(ImportLog.created_at.desc()).all()

    return [
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