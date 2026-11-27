# app/schemas.py - the shape of data the API returns

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    size_bytes: int
    status: str
    error_message: str | None = None
    created_at: datetime


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    vendor_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    currency: str | None
    subtotal: float | None
    tax: float | None
    total: float | None
    line_items: list[dict] | None
    confidence: float | None
    needs_review: bool
    validation_errors: list[str] | None
    created_at: datetime
    reviewed: bool
    reviewed_at: datetime | None
    

    class ExtractionUpdate(BaseModel):
    """Corrected values sent by a human reviewer."""

    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    line_items: list[dict] | None = None