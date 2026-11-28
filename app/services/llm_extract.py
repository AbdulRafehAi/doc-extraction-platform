# app/services/llm_extract.py - ask the local LLM to extract invoice fields

import json

import httpx

from app.config import settings
from app.services.invoice_schema import InvoiceData

SYSTEM_PROMPT = """You extract data from invoice text.
Rules:
- Use only information that appears in the text. Never guess.
- If a field is not present, use null.
- The text comes from a PDF, so labels and values may be on separate lines,
  and a block of values may come BEFORE the block of labels that describe
  them. Match them in order: the first value goes with the first label.
- invoice_date must be in YYYY-MM-DD format.
- currency is a 3-letter code. Use it only if the currency is clear from the
  text. A "$" sign alone means USD. Never infer currency from an address.
- Numbers must be plain numbers without currency symbols.
- vendor_name is the company that issued the invoice (the "From" side or the
  name at the top), not the customer (the "Bill To" / "To" side).
- line_items are the rows of the items table only. Each product or service
  is ONE item. A category or code line under a product (for example
  "Chairs, Furniture, FUR-CH-1") is part of that item, not a new item.
- Table headings such as "Qty", "Service", "Rate" are NOT line items.
- Subtotal, discount, shipping, tax and total are NOT line items.
- tax is only an amount labelled Tax, VAT or GST. Shipping and discount are
  never tax. If there is no tax label, tax is null.
- Reply with JSON only."""

EXAMPLES = [
    # Example 1: labels and values in order
    (
        """Invoice
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
$118.00""",
        {
            "vendor_name": "Acme Print Co",
            "invoice_number": "A-1042",
            "invoice_date": "2021-03-03",
            "currency": "USD",
            "subtotal": 100.0,
            "tax": 18.0,
            "total": 118.0,
            "line_items": [
                {"description": "Business cards", "quantity": 2,
                 "unit_price": 50.0, "amount": 100.0}
            ],
        },
    ),
    # Example 2: value block BEFORE the label block, discount and shipping, no tax
    (
        """INVOICE
# 7781
Northwind Supplies
Bill To:
Dana Lee
Ship To:
Austin, Texas, United States
Jul 14 2020
Standard
$59.00
Date:
Ship Mode:
Balance Due:
Item Quantity Rate Amount
Desk Lamp, Black 2 $30.00 $60.00
Lighting, Home, LGT-DL-9
$60.00
$6.00
$5.00
$59.00
Subtotal:
Discount (10%):
Shipping:
Total:
Notes:
Thanks for your business!""",
        {
            "vendor_name": "Northwind Supplies",
            "invoice_number": "7781",
            "invoice_date": "2020-07-14",
            "currency": "USD",
            "subtotal": 60.0,
            "tax": None,
            "total": 59.0,
            "line_items": [
                {"description": "Desk Lamp, Black", "quantity": 2,
                 "unit_price": 30.0, "amount": 60.0}
            ],
        },
    ),
]


def extract_invoice_data(text: str, model: str | None = None) -> InvoiceData:
    """Send invoice text to Ollama and return validated structured data."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for example_input, example_output in EXAMPLES:
        messages.append({"role": "user", "content": example_input})
        messages.append({"role": "assistant", "content": json.dumps(example_output)})
    messages.append({"role": "user", "content": text})

    payload = {
        "model": model or settings.ollama_model,
        "messages": messages,
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