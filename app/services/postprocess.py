# app/services/postprocess.py - deterministic cleanup of LLM output

from itertools import combinations

from app.services.invoice_schema import InvoiceData

CURRENCY_SYMBOLS = {
    "$": "USD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY",
    "₹": "INR", "C$": "CAD", "A$": "AUD",
}
TOLERANCE = 0.01
MAX_ITEMS_TO_SEARCH = 12  # subset search grows fast, so cap it


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE + 1e-9


def normalize_currency(data: InvoiceData) -> None:
    """Turn symbols into 3-letter codes, and upper-case codes."""
    if data.currency is None:
        return
    value = data.currency.strip()
    if value in CURRENCY_SYMBOLS:
        data.currency = CURRENCY_SYMBOLS[value]
    elif len(value) == 3 and value.isalpha():
        data.currency = value.upper()


def trim_line_items(data: InvoiceData) -> None:
    """If the items already add up, do nothing. Otherwise, keep the smallest
    group of items whose amounts add up to the subtotal or total."""
    items = [i for i in data.line_items if i.amount is not None]
    targets = [data.subtotal] if data.subtotal is not None else []
    if not items or not targets or len(items) > MAX_ITEMS_TO_SEARCH:
        return
    if any(_close(sum(i.amount for i in items), t) for t in targets):
        return  # already consistent

    for size in range(1, len(items)):
        matches = [
            group
            for group in combinations(items, size)
            if any(_close(sum(i.amount for i in group), t) for t in targets)
        ]
        if len(matches) == 1:  # only act when the answer is unambiguous
            data.line_items = list(matches[0])
            return


def clean_invoice(data: InvoiceData) -> InvoiceData:
    """Run every cleanup rule and return the same object."""
    normalize_currency(data)
    trim_line_items(data)
    return data