from pathlib import Path

import pytest

import catalog as catalog_module
from catalog import load_catalog
from match import SelectedLine, Selection
from quote import (
    build_quote,
    line_from_catalog,
    quote_from_selection,
    set_manual_price,
    set_quantity,
)

REAL_CATALOG = Path(__file__).resolve().parents[2] / "data" / "company" / "catalog.csv"


@pytest.fixture
def catalog(monkeypatch):
    """The real catalog.csv, found whatever the working directory is."""
    monkeypatch.setattr(catalog_module, "CATALOG_PATH", REAL_CATALOG)
    return load_catalog()


def selected(item_id, quantity=None, reason="Correspond à la demande"):
    return SelectedLine(item_id=item_id, quantity=quantity, reason=reason)


def test_real_catalog_loads_and_is_sane(catalog):
    assert len(catalog) > 0
    for item_id, item in catalog.items():
        assert item.item_id == item_id
        assert item.unit_price_ht_eur > 0
        assert item.vat_rate_percent >= 0
        assert item.service_name
        assert item.unit


def test_every_price_comes_from_the_catalog(catalog):
    selection = Selection(lines=[selected(item_id, 1) for item_id in catalog])

    quote = quote_from_selection(selection, catalog)

    assert len(quote.lines) == len(catalog)
    for line in quote.lines:
        item = catalog[line.item_id]
        assert line.label == item.service_name
        assert line.unit == item.unit
        assert line.unit_price_ht_eur == item.unit_price_ht_eur
        assert line.vat_rate_percent == item.vat_rate_percent


def test_two_catalog_lines_give_the_right_totals(catalog):
    # 30 m2 of painting (18.00) + 30 m2 of wall preparation (4.50), VAT 20 %
    selection = Selection(
        lines=[selected("PEINT-002", 30), selected("PEINT-001", 30)]
    )

    quote = quote_from_selection(selection, catalog)

    assert [line.total_ht_eur for line in quote.lines] == [540.0, 135.0]
    assert quote.total_ht_eur == 675.0
    assert quote.total_vat_eur == 135.0
    assert quote.total_ttc_eur == 810.0
    assert quote.complete is True


def test_reason_is_kept_for_the_professional(catalog):
    selection = Selection(lines=[selected("PEINT-002", 10, reason="Peinture des murs")])

    quote = quote_from_selection(selection, catalog)

    assert quote.lines[0].reason == "Peinture des murs"


def test_unknown_id_is_dropped(catalog):
    selection = Selection(lines=[selected("PEINT-002", 10), selected("FAKE-999", 5)])

    quote = quote_from_selection(selection, catalog)

    assert [line.item_id for line in quote.lines] == ["PEINT-002"]
    assert quote.total_ht_eur == 180.0


def test_duplicate_id_keeps_only_the_first_line(catalog):
    selection = Selection(lines=[selected("PEINT-002", 10), selected("PEINT-002", 99)])

    quote = quote_from_selection(selection, catalog)

    assert len(quote.lines) == 1
    assert quote.lines[0].quantity == 10
    assert quote.total_ht_eur == 180.0


def test_unknown_quantity_leaves_the_line_unpriced_and_quote_incomplete(catalog):
    selection = Selection(lines=[selected("PLOMB-001", None)])

    quote = quote_from_selection(selection, catalog)

    line = quote.lines[0]
    assert line.unit_price_ht_eur == 65.0
    assert line.total_ht_eur is None
    assert "quantité inconnue" in line.note
    assert quote.complete is False
    assert quote.total_ht_eur == 0.0


def test_unmatched_work_becomes_an_unpriced_line(catalog):
    selection = Selection(
        lines=[selected("PEINT-002", 10)], unmatched_work=["Chauffe-eau"]
    )

    quote = quote_from_selection(selection, catalog)

    assert len(quote.lines) == 2
    unmatched = quote.lines[1]
    assert unmatched.item_id is None
    assert unmatched.label == "Chauffe-eau"
    assert unmatched.unit_price_ht_eur is None
    assert unmatched.total_ht_eur is None
    assert "hors catalogue" in unmatched.note
    assert quote.total_ht_eur == 180.0  # only the priced line counts
    assert quote.complete is False


def test_empty_selection_gives_an_empty_incomplete_quote(catalog):
    quote = quote_from_selection(Selection(), catalog)

    assert quote.lines == []
    assert quote.total_ttc_eur == 0.0
    assert quote.complete is False


def test_professional_enters_the_missing_quantity(catalog):
    quote = quote_from_selection(Selection(lines=[selected("PLOMB-001", None)]), catalog)

    quote = set_quantity(quote, 0, 2)

    assert quote.lines[0].total_ht_eur == 130.0
    assert quote.total_ht_eur == 130.0
    assert quote.total_vat_eur == 26.0
    assert quote.total_ttc_eur == 156.0
    assert quote.complete is True


def test_professional_prices_the_out_of_catalog_line_by_hand(catalog):
    selection = Selection(
        lines=[selected("PEINT-002", 10)], unmatched_work=["Chauffe-eau"]
    )
    quote = quote_from_selection(selection, catalog)

    quote = set_manual_price(quote, 1, 1, 400.0, 10.0, unit="u")

    assert quote.lines[1].manual_price is True
    assert quote.lines[0].manual_price is False
    assert quote.total_ht_eur == 580.0   # 180 + 400
    assert quote.total_vat_eur == 76.0   # 36 (20 %) + 40 (10 %)
    assert quote.total_ttc_eur == 656.0
    assert quote.complete is True