from html import escape
from types import SimpleNamespace

import pytest

from quote_html import eur, num, quote_to_html


def make_line(**overrides):
    data = dict(
        label="Pose de lavabo",
        quantity=2,
        unit="u",
        unit_price_ht_eur=100.0,
        vat_rate_percent=10.0,
        total_ht_eur=200.0,
        reason=None,
        note=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def make_quote(lines=None, complete=True):
    return SimpleNamespace(
        lines=lines if lines is not None else [make_line()],
        complete=complete,
        total_ht_eur=200.0,
        total_vat_eur=20.0,
        total_ttc_eur=220.0,
    )


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, "—"),
        (0, "0,00 €"),
        (12.5, "12,50 €"),
        (1234.5, "1 234,50 €"),
        (1000000, "1 000 000,00 €"),
    ],
)
def test_eur_formatting(value, expected):
    assert eur(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(None, "—"), (2.0, "2"), (2.5, "2,5"), (0.25, "0,25")],
)
def test_num_formatting(value, expected):
    assert num(value) == expected


def test_banner_says_it_is_a_draft_that_was_not_sent():
    html = quote_to_html(make_quote())

    assert "BROUILLON" in html
    assert "document non envoyé" in html


def test_line_values_are_formatted():
    html = quote_to_html(make_quote())

    assert "Pose de lavabo" in html
    assert "100,00 €" in html
    assert "200,00 €" in html
    assert "10 %" in html


def test_reason_and_note_are_shown_in_their_own_blocks():
    line = make_line(reason="Le client veut un lavabo", note="À vérifier")
    html = quote_to_html(make_quote([line]))

    assert '<div class="small">Le client veut un lavabo</div>' in html
    assert '<div class="note">À vérifier</div>' in html


def test_missing_values_show_a_dash():
    line = make_line(
        quantity=None, unit=None, unit_price_ht_eur=None,
        vat_rate_percent=None, total_ht_eur=None,
    )
    html = quote_to_html(make_quote([line]))

    # quantity, unit price, VAT and total cells (the unit cell is not class "r")
    assert html.count('<td class="r">—</td>') == 4
    assert "<td>—</td>" in html


def test_totals_are_shown():
    html = quote_to_html(make_quote())

    assert "220,00 €" in html
    assert "20,00 €" in html


def test_incomplete_quote_shows_a_warning():
    html = quote_to_html(make_quote(complete=False))

    assert "Devis incomplet" in html


def test_complete_quote_has_no_warning():
    html = quote_to_html(make_quote(complete=True))

    assert "Devis incomplet" not in html


def test_client_block_needs_a_record():
    html = quote_to_html(make_quote(), record=None)

    assert "Client :" not in html


def test_client_without_name_or_address_shows_dashes():
    record = SimpleNamespace(name=None, site_address=None)
    html = quote_to_html(make_quote(), record=record)

    assert "<b>Client :</b> —" in html
    assert "<b>Adresse du chantier :</b> —" in html


def test_texts_are_escaped():
    line = make_line(
        label="<script>alert(1)</script>", reason="a & b", note="<i>x</i>"
    )
    record = SimpleNamespace(name="<b>Bob</b>", site_address="1 <rue>")
    html = quote_to_html(make_quote([line]), record=record)

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "a &amp; b" in html
    assert "&lt;i&gt;x&lt;/i&gt;" in html
    assert "<b>Bob</b>" not in html
    assert "&lt;b&gt;Bob&lt;/b&gt;" in html
    assert "1 &lt;rue&gt;" in html


def test_company_name_is_escaped():
    html = quote_to_html(make_quote(), company="Dupont & Fils <SARL>")

    assert "Dupont &amp; Fils &lt;SARL&gt;" in html


def test_default_company_is_still_the_placeholder():
    html = quote_to_html(make_quote())

    assert escape("[Nom de l'entreprise]") in html