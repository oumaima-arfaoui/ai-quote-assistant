# quote_html.py
from html import escape

STYLE = """
body { font-family: Arial, sans-serif; max-width: 900px; margin: 30px auto; color: #222; }
h1 { margin-bottom: 4px; }
.banner { background: #fff3cd; border: 1px solid #e0c36a; padding: 10px; margin: 14px 0; }
.warn { background: #f8d7da; border: 1px solid #d99; padding: 10px; margin: 14px 0; }
table { border-collapse: collapse; width: 100%; margin-top: 16px; }
th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
.r { text-align: right; white-space: nowrap; }
.small { font-size: 12px; color: #666; margin-top: 2px; }
.note { font-size: 12px; color: #a33; margin-top: 2px; }
.totals { margin-top: 16px; margin-left: auto; width: 320px; }
.totals td { border: none; padding: 3px 8px; }
"""


def eur(value):
    if value is None:
        return "—"
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " €"


def num(value):
    if value is None:
        return "—"
    return f"{value:g}".replace(".", ",")


def quote_to_html(quote, record=None, company="[Nom de l'entreprise]"):
    """Build an HTML draft quote. Every text is escaped."""
    rows = ""
    for line in quote.lines:
        extra = ""
        if line.reason:
            extra += f'<div class="small">{escape(line.reason)}</div>'
        if line.note:
            extra += f'<div class="note">{escape(line.note)}</div>'
        vat = f"{num(line.vat_rate_percent)} %" if line.vat_rate_percent is not None else "—"
        rows += (
            "<tr>"
            f"<td>{escape(line.label)}{extra}</td>"
            f'<td class="r">{num(line.quantity)}</td>'
            f"<td>{escape(line.unit or '—')}</td>"
            f'<td class="r">{eur(line.unit_price_ht_eur)}</td>'
            f'<td class="r">{vat}</td>'
            f'<td class="r">{eur(line.total_ht_eur)}</td>'
            "</tr>"
        )

    client = ""
    if record is not None:
        name = getattr(record, "name", None) or "—"
        address = getattr(record, "site_address", None) or "—"
        client = f"<p><b>Client :</b> {escape(name)}<br><b>Adresse du chantier :</b> {escape(address)}</p>"

    warning = ""
    if not quote.complete:
        warning = (
            '<div class="warn">Devis incomplet : certaines lignes doivent être '
            "complétées par le professionnel avant tout envoi.</div>"
        )

    return (
        "<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>"
        f"<title>Devis brouillon</title><style>{STYLE}</style></head><body>"
        f"<h1>Devis (brouillon)</h1><div>{escape(company)}</div>"
        '<div class="banner"><b>BROUILLON</b> : document non envoyé, '
        "à vérifier et valider par le professionnel.</div>"
        f"{client}{warning}"
        "<table><tr><th>Désignation</th><th>Qté</th><th>Unité</th>"
        "<th>Prix unitaire HT</th><th>TVA</th><th>Total HT</th></tr>"
        f"{rows}</table>"
        '<table class="totals">'
        f'<tr><td>Total HT</td><td class="r">{eur(quote.total_ht_eur)}</td></tr>'
        f'<tr><td>TVA</td><td class="r">{eur(quote.total_vat_eur)}</td></tr>'
        f'<tr><td><b>Total TTC</b></td><td class="r"><b>{eur(quote.total_ttc_eur)}</b></td></tr>'
        "</table></body></html>"
    )