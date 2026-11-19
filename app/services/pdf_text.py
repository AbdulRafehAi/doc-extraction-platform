# app/services/pdf_text.py - read text from PDF files

from pathlib import Path

import pymupdf


def extract_text_from_pdf(path: str | Path) -> list[str]:
    """Open a PDF and return the text of each page as a list of strings."""
    pages = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            pages.append(page.get_text())
    return pages


def has_real_text(pages: list[str], min_chars: int = 50) -> bool:
    """Decide if the PDF has real text, or is probably a scanned picture.

    A scanned PDF gives back almost no text, so if the total number of
    characters is tiny, we will need OCR instead.
    """
    total = sum(len(page.strip()) for page in pages)
    return total >= min_chars