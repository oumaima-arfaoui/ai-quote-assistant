from types import SimpleNamespace

from quote import build_quote, line_from_catalog, line_unmatched, set_manual_price, set_quantity

# 1. price a line outside the catalog by hand
q = build_quote([line_unmatched("Chauffe-eau")])
q = set_manual_price(q, 0, quantity=1, unit_price_ht=450.0, vat_rate_percent=10.0, unit="unité")
line = q.lines[0]
print(line.total_ht_eur, line.manual_price, line.note)
print(q.total_ht_eur, q.total_vat_eur, q.total_ttc_eur, q.complete)

# 2. the quantity can still be changed afterwards
q = set_quantity(q, 0, 2)
print(q.lines[0].total_ht_eur, q.total_ht_eur)

# 3. a catalog line is refused
item = SimpleNamespace(item_id="A", service_name="Service A", unit="m²",
                       unit_price_ht_eur=30.0, vat_rate_percent=10.0)
q2 = build_quote([line_from_catalog(item, 2)])
try:
    set_manual_price(q2, 0, 1, 99.0, 20.0)
except ValueError as e:
    print("Refusé :", e)

# 4. invalid values are refused
try:
    set_manual_price(q, 0, 0, 10.0, 20.0)
except ValueError as e:
    print("Refusé :", e)