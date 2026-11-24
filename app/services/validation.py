# app/services/validation.py - rules that catch likely extraction mistakes

from datetime import date

from app.services.invoice_schema import InvoiceData

TOLERANCE = 0.01  # amounts may differ by one cent because of rounding


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE + 1e-9


def validate_invoice(data: InvoiceData) -> list[str]:
    """Return a list of problems. An empty list means no problems found."""
    errors: list[str] = []

    # Rule 1: important fields must be present
    for field in ("vendor_name", "invoice_number", "invoice_date", "total"):
        if getattr(data, field) is None:
            errors.append(f"Missing {field}")

    # Rule 2: the date must be a real, sensible date
    if data.invoice_date is not None:
        try:
            parsed = date.fromisoformat(data.invoice_date)
            if parsed.year < 1990 or parsed > date.today():
                errors.append(f"Date looks implausible: {data.invoice_date}")
        except ValueError:
            errors.append(f"Date is not a valid YYYY-MM-DD date: {data.invoice_date}")

    # Rule 3: currency must look like a 3-letter code
    if data.currency is not None:
        if len(data.currency) != 3 or not data.currency.isalpha():
            errors.append(f"Currency is not a 3-letter code: {data.currency}")

    # Rule 4: a zero total means a blank or misread invoice
    if data.total is not None and data.total == 0:
        errors.append("Total is zero")

    # Rule 5: subtotal + tax should equal total
    if None not in (data.subtotal, data.tax, data.total):
        if not _close(data.subtotal + data.tax, data.total):
            errors.append(
                f"Subtotal {data.subtotal} + tax {data.tax} does not equal total {data.total}"
            )

    # Rule 6: line item amounts should add up to the subtotal (or the total)
    amounts = [item.amount for item in data.line_items if item.amount is not None]
    if amounts:
        line_sum = sum(amounts)
        targets = [v for v in (data.subtotal, data.total) if v is not None]
        if targets and not any(_close(line_sum, t) for t in targets):
            errors.append(
                f"Line items add up to {line_sum:.2f}, which matches neither subtotal nor total"
            )

    return errors