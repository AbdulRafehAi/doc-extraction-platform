# tests/test_validation.py - tests for the validation rules

from app.services.invoice_schema import InvoiceData, LineItem
from app.services.validation import validate_invoice


def make(**overrides) -> InvoiceData:
    """A correct invoice (invoice1.pdf). Tests change only what they need."""
    base = dict(
        vendor_name="DEMO - Sliced Invoices",
        invoice_number="INV-3337",
        invoice_date="2016-01-25",
        currency="USD",
        subtotal=85.0,
        tax=8.5,
        total=93.5,
        line_items=[LineItem(description="Web Design", amount=85.0)],
    )
    base.update(overrides)
    return InvoiceData(**base)


def test_correct_invoice_has_no_errors():
    assert validate_invoice(make()) == []


def test_invoice2_ground_truth_passes():
    """Canada Post: no subtotal or tax, five rows that add up to the total."""
    data = make(
        vendor_name="Canada Post",
        invoice_number="90000001620",
        invoice_date="2025-06-21",
        currency="CAD",
        subtotal=None,
        tax=None,
        total=1673.01,
        line_items=[
            LineItem(amount=97.98),
            LineItem(amount=216.90),
            LineItem(amount=1240.00),
            LineItem(amount=168.13),
            LineItem(amount=-50.00),
        ],
    )
    assert validate_invoice(data) == []


def test_invoice2_real_model_mistake_is_flagged():
    """What qwen2.5:3b actually returned for invoice 2."""
    data = make(invoice_number=None, subtotal=97.98, tax=216.9, total=1240.0)
    errors = validate_invoice(data)
    assert any("Missing invoice_number" in e for e in errors)
    assert any("does not equal total" in e for e in errors)


def test_blank_invoice_is_flagged():
    data = make(
        vendor_name=None, invoice_number=None, subtotal=None, tax=None,
        total=0.0, line_items=[],
    )
    errors = validate_invoice(data)
    assert "Total is zero" in errors
    assert "Missing vendor_name" in errors


def test_impossible_date_is_flagged():
    errors = validate_invoice(make(invoice_date="2023-13-45"))
    assert any("not a valid" in e for e in errors)


def test_bad_currency_is_flagged():
    errors = validate_invoice(make(currency="$"))
    assert any("3-letter" in e for e in errors)


def test_line_items_that_do_not_add_up_are_flagged():
    data = make(line_items=[LineItem(amount=85.0), LineItem(amount=9.74)])
    errors = validate_invoice(data)
    assert any("Line items add up" in e for e in errors)


def test_known_limit_shipping_mislabelled_as_tax_is_not_caught():
    """Invoice 5: the model called the 172.16 shipping charge 'tax'.
    The arithmetic still works, so no rule can notice. We document this
    limit instead of hiding it."""
    data = make(
        vendor_name="SuperStore", invoice_number="49674",
        invoice_date="2013-02-20", subtotal=8204.16, tax=172.16,
        total=8376.32, line_items=[LineItem(amount=8204.16)],
    )
    assert validate_invoice(data) == []