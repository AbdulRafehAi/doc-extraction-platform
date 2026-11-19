# try_pdf.py - a small script to try our PDF reader by hand

import sys

from app.services.pdf_text import extract_text_from_pdf, has_real_text

path = sys.argv[1]
pages = extract_text_from_pdf(path)

print(f"Number of pages: {len(pages)}")
print(f"Has real text: {has_real_text(pages)}")
print("-" * 40)
for number, text in enumerate(pages, start=1):
    print(f"--- Page {number} ---")
    print(text)