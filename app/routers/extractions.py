# app/routers/extractions.py - endpoints for human review

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, Extraction
from app.schemas import ExtractionOut, ExtractionUpdate
from app.services.invoice_schema import InvoiceData
from app.services.validation import validate_invoice

router = APIRouter(prefix="/extractions", tags=["extractions"])


def _money(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _get_or_404(db: Session, extraction_id: int) -> Extraction:
    extraction = db.get(Extraction, extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found.")
    return extraction


@router.get("/review", response_model=list[ExtractionOut])
def list_needing_review(db: Session = Depends(get_db)):
    """Extractions that a person still has to look at, newest first."""
    return db.scalars(
        select(Extraction)
        .where(Extraction.needs_review.is_(True), Extraction.reviewed.is_(False))
        .order_by(Extraction.id.desc())
    ).all()


@router.put("/{extraction_id}", response_model=ExtractionOut)
def correct_extraction(
    extraction_id: int, update: ExtractionUpdate, db: Session = Depends(get_db)
):
    """Save a human's corrections, then re-run the validation rules."""
    extraction = _get_or_404(db, extraction_id)

    extraction.vendor_name = update.vendor_name
    extraction.invoice_number = update.invoice_number
    extraction.invoice_date = update.invoice_date
    extraction.currency = update.currency
    extraction.subtotal = _money(update.subtotal)
    extraction.tax = _money(update.tax)
    extraction.total = _money(update.total)
    extraction.line_items = update.line_items or []

    data = InvoiceData(
        vendor_name=update.vendor_name,
        invoice_number=update.invoice_number,
        invoice_date=update.invoice_date.isoformat() if update.invoice_date else None,
        currency=update.currency,
        subtotal=update.subtotal,
        tax=update.tax,
        total=update.total,
        line_items=update.line_items or [],
    )
    errors = validate_invoice(data)
    extraction.validation_errors = errors
    extraction.needs_review = bool(errors)
    extraction.confidence = max(0.0, 1.0 - 0.25 * len(errors))

    document = db.get(Document, extraction.document_id)
    if document is not None:
        document.status = "needs_review" if errors else "completed"

    db.commit()
    db.refresh(extraction)
    return extraction


@router.post("/{extraction_id}/approve", response_model=ExtractionOut)
def approve_extraction(extraction_id: int, db: Session = Depends(get_db)):
    """A person confirms the data is correct, even if a rule still complains."""
    extraction = _get_or_404(db, extraction_id)
    extraction.reviewed = True
    extraction.reviewed_at = datetime.now(timezone.utc)
    extraction.needs_review = False

    document = db.get(Document, extraction.document_id)
    if document is not None:
        document.status = "approved"

    db.commit()
    db.refresh(extraction)
    return extraction