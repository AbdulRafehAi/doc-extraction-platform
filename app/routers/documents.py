# app/routers/documents.py - endpoints for uploading and listing documents

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Document
from app.schemas import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


@router.post("/upload", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Receive an invoice file, save it on disk, and record it in the database."""
    original_name = file.filename or "unnamed"
    extension = Path(original_name).suffix.lower()

    # 1. Check the file type
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: PDF, PNG, JPG.",
        )

    # 2. Read the file and check its size
    contents = file.file.read()
    size = len(contents)
    if size == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if size > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum is {settings.max_upload_mb} MB.",
        )

    # 3. Save it under a random name
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    (upload_dir / stored_name).write_bytes(contents)

    # 4. Record it in the database
    document = Document(
        filename=original_name,
        stored_filename=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
    )
    db.add(document)
    db.commit()
    db.refresh(document)  # loads the generated id and created_at
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    """Return all documents, newest first."""
    return db.scalars(select(Document).order_by(Document.id.desc())).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """Return one document, or a 404 error if it does not exist."""
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document