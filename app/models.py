# app/models.py - database tables

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    """One uploaded invoice file."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))  # name the user uploaded
    stored_filename: Mapped[str] = mapped_column(String(255))  # random name on disk
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    extractions: Mapped[list["Extraction"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Extraction(Base):
    """The structured data the AI pulled out of one document."""

    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    # Extracted invoice fields (all optional: the AI may not find every one)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str | None] = mapped_column(String(10))
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    line_items: Mapped[list | None] = mapped_column(JSONB)

    # Quality control
    confidence: Mapped[float | None] = mapped_column()
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_errors: Mapped[list | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="extractions")