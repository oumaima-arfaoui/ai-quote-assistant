from pathlib import Path

from database import get_generated_quote, get_saved_quote, init_db
from quote import Quote

init_db()
for name, getter in (("généré", get_generated_quote), ("enregistré", get_saved_quote)):
    data = getter("04_two_works.txt")
    if data is None:
        print(name, ": aucun")
        continue
    q = Quote.model_validate_json(data)
    print(name, ":", [l.reason for l in q.lines])

print("quote.py passe la raison :", "sel.reason" in Path("quote.py").read_text(encoding="utf-8"))
