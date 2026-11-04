from pathlib import Path

from database import get_generated_quote, get_saved_quote, init_db
from quote import Quote

init_db()

gen = Quote.model_validate_json(get_generated_quote("04_two_works.txt"))
sav = Quote.model_validate_json(get_saved_quote("04_two_works.txt"))

print("quantités générées     :", [l.quantity for l in gen.lines])
print("quantités enregistrées :", [l.quantity for l in sav.lines])
same = gen.model_dump_json(indent=2).strip() == sav.model_dump_json(indent=2).strip()
print("devis identiques       :", same)
print("app.py contient le log :", '"quote"' in Path("app.py").read_text(encoding="utf-8"))