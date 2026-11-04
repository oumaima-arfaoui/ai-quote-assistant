from pathlib import Path

from database import get_connection, get_saved_quote, init_db
from quote import Quote
from quote_html import quote_to_html
from schema import QuoteRequest

init_db()
source = "04_two_works.txt"

saved = get_saved_quote(source)
if not saved:
    raise SystemExit("Pas de devis enregistré pour 04 : enregistrez-en un dans l'app.")
quote = Quote.model_validate_json(saved)

with get_connection() as conn:
    row = conn.execute(
        "SELECT record_json FROM requests WHERE source_file = ?", (source,)
    ).fetchone()
record = QuoteRequest.model_validate_json(row["record_json"])

out = Path("data/devis_04.html")
out.write_text(quote_to_html(quote, record), encoding="utf-8")
print("Écrit :", out.resolve())