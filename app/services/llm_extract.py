# app/services/llm_extract.py - ask the local LLM to extract invoice fields

import json

import httpx

from app.config import settings
from app.services.invoice_schema import InvoiceData

SYSTEM_PROMPT = """You extract data from invoice text.
Rules:
- Use only information that appears in the text. Never guess.
- If a field is not present, use null.
- The text comes from a PDF, so labels and values may be on separate lines.
  Match each label with its value (for example "Invoice Number" then "A-1".)
- invoice_date must be in YYYY-MM-DD format.
- currency is a 3-letter code. Use it only if the currency is clear from the
  text. A "$" sign alone means USD. Never infer currency from an address.
- Numbers must be plain numbers without currency symbols.
- vendor_name is the company that issued the invoice (the "From" side),
  not the customer (the "To" side).
- line_items are the rows of the items table. Table column headings such as
  "Qty", "Service", "Rate" are NOT line items. Subtotal, tax and total
  are NOT line items.
- Reply with JSON only."""

# One worked example. It is deliberately a DIFFERENT invoice from our test file.
EXAMPLE_INPUT = """Invoice
From:
Acme Print Co
9 Market Road
Springfield
Invoice Number
A-1042
Invoice Date
March 3, 2021
Due Date
April 2, 2021
To:
Bright Cafe
44 Oak Lane
Qty
Description
Unit Price
Amount
2
Business cards
$50.00
$100.00
Subtotal
$100.00
Tax
$18.00
Total
$118.00"""

EXAMPLE_OUTPUT = {
    "vendor_name": "Acme Print Co",
    "invoice_number": "A-1042",
    "invoice_date": "2021-03-03",
    "currency": "USD",
    "subtotal": 100.0,
    "tax": 18.0,
    "total": 118.0,
    "line_items": [
        {
            "description": "Business cards",
            "quantity": 2,
            "unit_price": 50.0,
            "amount": 100.0,
        }
    ],
}


def extract_invoice_data(text: str, model: str | None = None) -> InvoiceData:
    """Send invoice text to Ollama and return validated structured data."""
    payload = {
        "model": model or settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": EXAMPLE_INPUT},
            {"role": "assistant", "content": json.dumps(EXAMPLE_OUTPUT)},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "format": InvoiceData.model_json_schema(),
        "options": {"temperature": 0, "seed": 42},
    }
    response = httpx.post(
        f"{settings.ollama_base_url}/api/chat", json=payload, timeout=600
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return InvoiceData.model_validate_json(content)