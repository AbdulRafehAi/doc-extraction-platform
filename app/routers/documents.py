# app/routers/documents.py - endpoints for uploading, extracting and listing documents

import uuid
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Document, Extraction
from app.schemas import DocumentOut, ExtractionOut
from app.services.pipeline import process_document

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


@router.post("/upload", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Receive an invoice file, save it on disk, and record it in the database."""
    original_name = file.filename or "unnamed"
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: PDF, PNG, JPG.",
        )

    contents = file.file.read()
    size = len(contents)
    if size == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if size > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum is {settings.max_upload_mb} MB.",
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    (upload_dir / stored_name).write_bytes(contents)

    document = Document(
        filename=original_name,
        stored_filename=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post("/{document_id}/extract", response_model=DocumentOut, status_code=202)
def start_extraction(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start extraction in the background and reply immediately."""
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if document.status == "processing":
        raise HTTPException(status_code=409, detail="Extraction is already running.")

    document.status = "processing"
    document.error_message = None
    db.commit()
    db.refresh(document)

    background_tasks.add_task(process_document, document.id)
    return document


@router.get("/{document_id}/extraction", response_model=ExtractionOut)
def get_extraction(document_id: int, db: Session = Depends(get_db)):
    """Return the newest extraction result for a document."""
    extraction = db.scalars(
        select(Extraction)
        .where(Extraction.document_id == document_id)
        .order_by(Extraction.id.desc())
    ).first()
    if extraction is None:
        raise HTTPException(status_code=404, detail="No extraction for this document yet.")
    return extraction

@router.get("/{document_id}/file")
def get_document_file(document_id: int, db: Session = Depends(get_db)):
    """Return the original uploaded file so a reviewer can look at it."""
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    path = Path(settings.upload_dir) / document.stored_filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File is missing on disk.")
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.filename,
        content_disposition_type="inline",
    )
    
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