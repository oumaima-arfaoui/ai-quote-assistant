from types import SimpleNamespace

from quote import build_quote, line_from_catalog, line_unmatched


def make_item(item_id="A", price=30.0, vat=10.0, unit="m²"):
    """A fake catalog item with only the attributes quote.py reads."""
    return SimpleNamespace(
        item_id=item_id,
        service_name=f"Service {item_id}",
        unit=unit,
        unit_price_ht_eur=price,
        vat_rate_percent=vat,
    )


def test_line_price_comes_from_catalog_item():
    line = line_from_catalog(make_item(price=30.0), 12)
    assert line.unit_price_ht_eur == 30.0
    assert line.total_ht_eur == 360.0
    assert line.note is None


def test_unknown_quantity_leaves_total_empty():
    line = line_from_catalog(make_item(), None)
    assert line.total_ht_eur is None
    assert line.unit_price_ht_eur == 30.0
    assert "quantité inconnue" in line.note


def test_unmatched_line_has_no_price():
    line = line_unmatched("Chauffe-eau")
    assert line.item_id is None
    assert line.unit_price_ht_eur is None
    assert line.total_ht_eur is None


def test_totals_with_two_vat_rates():
    quote = build_quote([
        line_from_catalog(make_item("A", 30.0, 10.0), 12),  # 360 HT, 36 TVA
        line_from_catalog(make_item("B", 50.0, 20.0), 2),   # 100 HT, 20 TVA
    ])
    assert quote.total_ht_eur == 460.0
    assert quote.total_vat_eur == 56.0
    assert quote.total_ttc_eur == 516.0
    assert quote.complete is True


def test_incomplete_quote_is_flagged_and_totals_are_partial():
    quote = build_quote([
        line_from_catalog(make_item("A", 30.0, 10.0), 12),
        line_from_catalog(make_item("B", 50.0, 20.0), None),
        line_unmatched("Chauffe-eau"),
    ])
    assert quote.total_ht_eur == 360.0
    assert quote.total_vat_eur == 36.0
    assert quote.total_ttc_eur == 396.0
    assert quote.complete is False


def test_empty_quote_is_not_complete():
    assert build_quote([]).complete is False