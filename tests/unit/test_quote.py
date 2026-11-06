from types import SimpleNamespace

import pytest

from quote import (
    build_quote,
    line_from_catalog,
    line_unmatched,
    set_manual_price,
    set_quantity,
)


def make_item(item_id="A", price=30.0, vat=10.0, unit="m²"):
    """A fake catalog item with only the attributes quote.py reads."""
    return SimpleNamespace(
        item_id=item_id,
        service_name=f"Service {item_id}",
        unit=unit,
        unit_price_ht_eur=price,
        vat_rate_percent=vat,
    )


def sample_quote():
    """One catalog line without quantity, one line outside the catalog."""
    return build_quote([
        line_from_catalog(make_item("A", 30.0, 10.0), None),
        line_unmatched("Chauffe-eau"),
    ])


# --- lines and totals ---

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


# --- set_quantity ---

def test_set_quantity_prices_a_catalog_line():
    quote = set_quantity(sample_quote(), 0, 10)
    assert quote.lines[0].quantity == 10
    assert quote.lines[0].total_ht_eur == 300.0
    assert quote.lines[0].note is None
    assert quote.total_ht_eur == 300.0
    assert quote.complete is False  # the line outside the catalog is still unpriced


def test_set_quantity_does_not_modify_the_original_quote():
    original = sample_quote()
    set_quantity(original, 0, 10)
    assert original.lines[0].quantity is None
    assert original.total_ht_eur == 0.0


def test_set_quantity_refuses_a_line_without_price():
    with pytest.raises(ValueError):
        set_quantity(sample_quote(), 1, 5)


# --- set_manual_price ---

def test_manual_price_prices_an_unmatched_line():
    quote = set_manual_price(
        sample_quote(), 1, quantity=1, unit_price_ht=450.0, vat_rate_percent=10.0, unit="unité"
    )
    line = quote.lines[1]
    assert line.total_ht_eur == 450.0
    assert line.manual_price is True
    assert line.unit == "unité"
    assert "manuellement" in line.note
    assert quote.total_ht_eur == 450.0
    assert quote.total_vat_eur == 45.0
    assert quote.total_ttc_eur == 495.0


def test_manual_price_refuses_a_catalog_line():
    with pytest.raises(ValueError):
        set_manual_price(sample_quote(), 0, 1, 99.0, 20.0)


@pytest.mark.parametrize(
    "quantity, price, vat",
    [(0, 10.0, 20.0), (-1, 10.0, 20.0), (1, -5.0, 20.0), (1, 10.0, -1.0)],
)
def test_manual_price_refuses_invalid_values(quantity, price, vat):
    with pytest.raises(ValueError):
        set_manual_price(sample_quote(), 1, quantity, price, vat)


def test_quantity_can_be_changed_after_a_manual_price():
    quote = set_manual_price(sample_quote(), 1, 1, 450.0, 10.0)
    quote = set_quantity(quote, 1, 2)
    assert quote.lines[1].total_ht_eur == 900.0
    assert quote.total_ht_eur == 900.0