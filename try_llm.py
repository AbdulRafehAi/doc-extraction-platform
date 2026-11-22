# try_llm.py - try the full chain: PDF -> text -> LLM -> structured data
# Usage: python try_llm.py samples\invoice1.pdf [model_name]

import sys
import time

from app.services.llm_extract import extract_invoice_data
from app.services.pdf_text import extract_text_from_pdf

pages = extract_text_from_pdf(sys.argv[1])
text = "\n".join(pages)
model = sys.argv[2] if len(sys.argv) > 2 else None

start = time.time()
result = extract_invoice_data(text, model)
print(result.model_dump_json(indent=2))
print(f"\nTook {time.time() - start:.1f} seconds")