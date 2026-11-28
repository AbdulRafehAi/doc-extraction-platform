# tests/test_postprocess.py - tests for the cleanup rules

from app.services.invoice_schema import InvoiceData, LineItem
from app.services.postprocess import clean_invoice


def test_dollar_sign_becomes_usd():
    assert clean_invoice(InvoiceData(currency="$")).currency == "USD"


def test_lowercase_code_is_uppercased():
    assert clean_invoice(InvoiceData(currency="cad")).currency == "CAD"


def test_missing_currency_stays_missing():
    assert clean_invoice(InvoiceData()).currency is None


def test_consistent_items_are_untouched():
    data = InvoiceData(
        subtotal=100.0,
        line_items=[LineItem(amount=60.0), LineItem(amount=40.0)],
    )
    assert len(clean_invoice(data).line_items) == 2


def test_extra_items_from_totals_block_are_removed():
    """Invoice 3: the model returned the chair plus junk rows."""
    data = InvoiceData(
        subtotal=48.71,
        total=50.10,
        line_items=[
            LineItem(description="Chair", amount=48.71),
            LineItem(description="junk", amount=9.74),
            LineItem(description="junk", amount=11.13),
        ],
    )
    result = clean_invoice(data)
    assert [i.description for i in result.line_items] == ["Chair"]


def test_ambiguous_match_is_left_alone():
    """Two different single items both match, so we must not guess."""
    data = InvoiceData(
        subtotal=10.0,
        line_items=[LineItem(amount=10.0), LineItem(amount=10.0), LineItem(amount=3.0)],
    )
    assert len(clean_invoice(data).line_items) == 3


def test_no_targets_means_no_change():
    data = InvoiceData(line_items=[LineItem(amount=5.0), LineItem(amount=6.0)])
    assert len(clean_invoice(data).line_items) == 2