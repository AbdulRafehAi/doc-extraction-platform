# app/services/llm_extract.py - ask the local LLM to extract invoice fields

import httpx

from app.config import settings
from app.services.invoice_schema import InvoiceData

SYSTEM_PROMPT = """You extract data from invoice text.
Rules:
- Use only information that appears in the text. Never guess.
- If a field is not present, use null.
- invoice_date must be in YYYY-MM-DD format.
- currency is a 3-letter code such as USD.
- Numbers must be plain numbers without currency symbols.
- vendor_name is the company that issued the invoice (the sender), not the customer.
- Include every line item."""


def extract_invoice_data(text: str) -> InvoiceData:
    """Send invoice text to Ollama and return validated structured data."""
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "format": InvoiceData.model_json_schema(),  # forces the output shape
        "options": {"temperature": 0},  # 0 = most consistent answers
    }
    response = httpx.post(
        f"{settings.ollama_base_url}/api/chat", json=payload, timeout=300
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return InvoiceData.model_validate_json(content)