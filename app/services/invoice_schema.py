# app/services/invoice_schema.py - the shape of extracted invoice data

from pydantic import BaseModel


class LineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None


class InvoiceData(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None  # we ask for YYYY-MM-DD
    currency: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    line_items: list[LineItem] = []