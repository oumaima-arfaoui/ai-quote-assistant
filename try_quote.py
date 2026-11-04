from pathlib import Path

from catalog import load_catalog
from extract import chain, compute_missing
from match import select_lines
from quote import quote_from_selection, set_quantity

catalog = load_catalog()
for path in sorted(Path("data/requests").glob("*.txt")):
    record = chain.invoke({"request_text": path.read_text(encoding="utf-8")})
    record.missing_fields = compute_missing(record)
    if not record.is_quote_request:
        continue

    quote = quote_from_selection(select_lines(record), catalog)
    print(f"\n===== {path.name} =====")
    for line in quote.lines:
        detail = f"{line.total_ht_eur} € HT" if line.total_ht_eur is not None else line.note
        print(f"  {line.label} | qté : {line.quantity} | {detail}")
    print(f"  TOTAL HT {quote.total_ht_eur} | TVA {quote.total_vat_eur} | TTC {quote.total_ttc_eur} | complet : {quote.complete}")
    
    
    
print("\n===== TEST set_quantity sur 04 =====")
record = chain.invoke({"request_text": Path("data/requests/04_two_works.txt").read_text(encoding="utf-8")})
record.missing_fields = compute_missing(record)
quote = quote_from_selection(select_lines(record), catalog)

for i, line in enumerate(quote.lines):
    print(i, line.label, "|", line.unit_price_ht_eur, "€ HT /", line.unit)
priced = [i for i, l in enumerate(quote.lines) if l.unit_price_ht_eur is not None]

# 1. enter quantity 10 on the first two priced lines
q = quote
for i in priced[:2]:
    q = set_quantity(q, i, 10)
for line in q.lines:
    print(" ", line.label, "|", line.quantity, "|", line.total_ht_eur, "|", line.note)
print("TOTAL HT", q.total_ht_eur, "| TVA", q.total_vat_eur, "| TTC", q.total_ttc_eur, "| complet :", q.complete)

# 2. an unmatched line must be refused
unmatched = [i for i, l in enumerate(quote.lines) if l.unit_price_ht_eur is None]
try:
    set_quantity(q, unmatched[0], 5)
except ValueError as e:
    print("Refusé comme prévu :", e)