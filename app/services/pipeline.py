# app/services/pipeline.py - the full extraction pipeline for one document

from datetime import date
from decimal import Decimal
from pathlib import Path
from app.services.postprocess import clean_invoice
from app.config import settings
from app.database import SessionLocal
from app.models import Document, Extraction
from app.services.llm_extract import extract_invoice_data
from app.services.pdf_text import extract_text_from_pdf, has_real_text
from app.services.validation import validate_invoice


def _money(value: float | None) -> Decimal | None:
    """Convert a float to an exact Decimal for the database."""
    return None if value is None else Decimal(str(value))


def _parse_date(value: str | None) -> date | None:
    """Turn 'YYYY-MM-DD' into a date. Bad values become None (validation already flagged them)."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def process_document(document_id: int) -> None:
    """Read, extract, validate and save. Runs in the background."""
    db = SessionLocal()  # its own session, separate from the web request
    try:
        try:
            document = db.get(Document, document_id)
            if document is None:
                return

            path = Path(settings.upload_dir) / document.stored_filename
            if path.suffix.lower() != ".pdf":
                raise ValueError("Images need OCR, which is not built yet.")

            text = "\n".join(extract_text_from_pdf(path))
            if not has_real_text([text]):
                raise ValueError("This PDF looks scanned. OCR is not built yet.")

            data = clean_invoice(extract_invoice_data(text))
            errors = validate_invoice(data)

            # A simple rule-based score, NOT a probability from the model:
            # start at 1.0 and lose 0.25 for every problem found.
            confidence = max(0.0, 1.0 - 0.25 * len(errors))

            db.add(
                Extraction(
                    document_id=document.id,
                    vendor_name=data.vendor_name,
                    invoice_number=data.invoice_number,
                    invoice_date=_parse_date(data.invoice_date),
                    currency=data.currency,
                    subtotal=_money(data.subtotal),
                    tax=_money(data.tax),
                    total=_money(data.total),
                    line_items=[item.model_dump() for item in data.line_items],
                    confidence=confidence,
                    needs_review=bool(errors),
                    validation_errors=errors,
                )
            )
            document.status = "needs_review" if errors else "completed"
            document.error_message = None
            db.commit()
        except Exception as error:
            db.rollback()
            document = db.get(Document, document_id)
            if document is not None:
                document.status = "failed"
                document.error_message = str(error)[:500]
                db.commit()
    finally:
        db.close()