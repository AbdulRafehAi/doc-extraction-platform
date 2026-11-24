# evaluate.py - score the LLM extraction against our hand-written answers
# Usage: python evaluate.py [model_name]

import json
import sys
import time
from pathlib import Path

from app.config import settings
from app.services.llm_extract import extract_invoice_data
from app.services.pdf_text import extract_text_from_pdf, has_real_text

SAMPLES = Path("samples")
EXPECTED_FILE = Path("eval/expected.json")
FIELDS = [
    "vendor_name", "invoice_number", "invoice_date",
    "currency", "subtotal", "tax", "total",
]


def same(expected, got) -> bool:
    """Compare one field. Numbers may differ by a cent; text ignores case."""
    if expected is None or got is None:
        return expected is None and got is None
    if isinstance(expected, (int, float)):
        return isinstance(got, (int, float)) and abs(expected - got) < 0.01
    return str(expected).strip().casefold() == str(got).strip().casefold()


def line_items_match(expected: list, got: list) -> bool:
    """Same number of items, and the same set of amounts."""
    if len(expected) != len(got):
        return False
    expected_amounts = sorted(round(i["amount"] or 0, 2) for i in expected)
    got_amounts = sorted(round(i.amount or 0, 2) for i in got)
    return expected_amounts == got_amounts


model = sys.argv[1] if len(sys.argv) > 1 else settings.ollama_model
only = sys.argv[2:]  # optional: file names to run, e.g. invoice1.pdf invoice2.pdf
expected_all = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))
if only:
    expected_all = {k: v for k, v in expected_all.items() if k in only}

print(f"Model: {model}\n")
results = []
total_checks = 0
total_correct = 0

for filename, expected in expected_all.items():
    path = SAMPLES / filename
    if not path.exists():
        print(f"{filename}: SKIPPED (file not found in samples/)")
        continue

    text = "\n".join(extract_text_from_pdf(path))
    if not has_real_text([text]):
        print(f"{filename}: SKIPPED (scanned, needs OCR)")
        continue

    start = time.time()
    try:
        got = extract_invoice_data(text, model)
    except Exception as error:  # a crash counts as everything wrong
        print(f"{filename}: ERROR {error}")
        total_checks += len(FIELDS) + 1
        results.append({"file": filename, "error": str(error)})
        continue
    seconds = time.time() - start

    wrong = []
    for field in FIELDS:
        if not same(expected[field], getattr(got, field)):
            wrong.append(f"{field} (expected {expected[field]!r}, got {getattr(got, field)!r})")
    if not line_items_match(expected["line_items"], got.line_items):
        wrong.append(f"line_items (expected {len(expected['line_items'])} items, got {len(got.line_items)})")

    checks = len(FIELDS) + 1
    correct = checks - len(wrong)
    total_checks += checks
    total_correct += correct
    print(f"{filename}: {correct}/{checks} correct in {seconds:.0f}s")
    for problem in wrong:
        print(f"    WRONG: {problem}")
    time.sleep(20)  # let the CPU cool down between invoices

print("\n" + "=" * 40)
if total_checks:
    print(f"Overall: {total_correct}/{total_checks} = {100 * total_correct / total_checks:.0f}% field accuracy")

stamp = time.strftime("%Y%m%d_%H%M%S")
out = Path("eval") / f"results_{model.replace(':', '_')}_{stamp}.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"Saved details to {out}")