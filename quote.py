# quote.py
from typing import Optional
from pydantic import BaseModel


class QuoteLine(BaseModel):
    # Line matched to a catalog item
    item_id: Optional[str] = None          # None if the work is not in the catalog
    label: str                             # service name, or the requested work if unmatched
    quantity: Optional[float] = None       # None if unknown
    unit: Optional[str] = None
    unit_price_ht_eur: Optional[float] = None
    vat_rate_percent: Optional[float] = None
    total_ht_eur: Optional[float] = None   # None if the line cannot be priced
    note: Optional[str] = None    # e.g. "à compléter par le professionnel"
    reason: Optional[str] = None           # why the selector chose this item (informative only)
    manual_price: bool = False             # True if the price was typed by the professional

class Quote(BaseModel):
    lines: list[QuoteLine] = []
    total_ht_eur: float = 0.0
    total_vat_eur: float = 0.0
    total_ttc_eur: float = 0.0
    complete: bool = False
def line_from_catalog(item, quantity: Optional[float], reason: Optional[str] = None) -> QuoteLine:
    """Priced line. The price comes ONLY from the catalog item."""
    line = QuoteLine(
        item_id=item.item_id,
        label=item.service_name,
        quantity=quantity,
        unit=item.unit,
        unit_price_ht_eur=item.unit_price_ht_eur,
        vat_rate_percent=item.vat_rate_percent,
        reason=reason,
    )
    if quantity is None:
        line.note = "à compléter par le professionnel (quantité inconnue)"
    else:
        line.total_ht_eur = round(quantity * item.unit_price_ht_eur, 2)
    return line
   


def line_unmatched(work: str) -> QuoteLine:
    """Line for work that is not in the catalog: no price at all."""
    return QuoteLine(label=work, note="à compléter par le professionnel (hors catalogue)")
def build_quote(lines: list[QuoteLine]) -> Quote:
    """Assemble a Quote and compute the totals in code (never by the LLM)."""
    total_ht = 0.0
    total_vat = 0.0
    complete = len(lines) > 0

    for line in lines:
        if line.total_ht_eur is None:
            complete = False          # this line still needs the professional
            continue
        total_ht += line.total_ht_eur
        total_vat += line.total_ht_eur * (line.vat_rate_percent or 0) / 100

    total_ht = round(total_ht, 2)
    total_vat = round(total_vat, 2)
    return Quote(
        lines=lines,
        total_ht_eur=total_ht,
        total_vat_eur=total_vat,
        total_ttc_eur=round(total_ht + total_vat, 2),
        complete=complete,
    )
def quote_from_selection(selection, catalog) -> Quote:
    """Turn the LLM's selection into a priced draft quote.
    Prices come from the catalog only. `selection` is a match.Selection."""
    lines = []
    seen = set()
    for sel in selection.lines:
        if sel.item_id in seen or sel.item_id not in catalog:
            continue                      # skip duplicates and unknown ids
        seen.add(sel.item_id)
        lines.append(line_from_catalog(catalog[sel.item_id], sel.quantity, sel.reason))
    for work in selection.unmatched_work:
        lines.append(line_unmatched(work))
    return build_quote(lines)    
def set_quantity(quote: Quote, index: int, quantity: float) -> Quote:
    """The professional enters a quantity for line number `index`; totals are recomputed."""
    lines = [line.model_copy() for line in quote.lines]
    line = lines[index]
    if line.unit_price_ht_eur is None:
        raise ValueError("Cette ligne n'a pas de prix : à chiffrer manuellement.")
    line.quantity = quantity
    line.total_ht_eur = round(quantity * line.unit_price_ht_eur, 2)
    line.note = None
    return build_quote(lines)
def set_manual_price(
    quote: Quote,
    index: int,
    quantity: float,
    unit_price_ht: float,
    vat_rate_percent: float,
    unit: Optional[str] = None,
) -> Quote:
    """The professional prices a line that is not in the catalog.
    The price is typed by a human and the line is marked as manual."""
    if quantity <= 0 or unit_price_ht < 0 or vat_rate_percent < 0:
        raise ValueError("Quantité, prix ou TVA invalide.")
    lines = [line.model_copy() for line in quote.lines]
    line = lines[index]
    if line.item_id is not None:
        raise ValueError("Cette ligne vient du catalogue : son prix ne se modifie pas ici.")
    line.quantity = quantity
    line.unit = unit or line.unit
    line.unit_price_ht_eur = unit_price_ht
    line.vat_rate_percent = vat_rate_percent
    line.total_ht_eur = round(quantity * unit_price_ht, 2)
    line.manual_price = True
    line.note = "prix saisi manuellement par le professionnel"
    return build_quote(lines)
if __name__ == "__main__":
    from types import SimpleNamespace
    a = SimpleNamespace(item_id="A", service_name="Service A", unit="m²",
                        unit_price_ht_eur=30.0, vat_rate_percent=10.0)
    b = SimpleNamespace(item_id="B", service_name="Service B", unit="u",
                        unit_price_ht_eur=50.0, vat_rate_percent=20.0)

    q1 = build_quote([line_from_catalog(a, 12), line_from_catalog(b, 2)])
    print(q1.total_ht_eur, q1.total_vat_eur, q1.total_ttc_eur, q1.complete)

    q2 = build_quote([line_from_catalog(a, 12), line_from_catalog(b, None),
                      line_unmatched("Chauffe-eau")])
    print(q2.total_ht_eur, q2.total_vat_eur, q2.total_ttc_eur, q2.complete)