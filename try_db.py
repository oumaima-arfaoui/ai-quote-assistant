from database import get_connection, get_saved_quote, init_db, save_quote
from quote import Quote, QuoteLine

init_db()
print("Avant :", get_saved_quote("test.txt"))

q = Quote(lines=[QuoteLine(label="Ligne test", quantity=2, total_ht_eur=10.0)], total_ht_eur=10.0)
save_quote("test.txt", q.model_dump_json())
saved = Quote.model_validate_json(get_saved_quote("test.txt"))
print("Après :", saved.lines[0].label, saved.total_ht_eur)

q.total_ht_eur = 99.0
save_quote("test.txt", q.model_dump_json())   # same key: must update, not duplicate
print("Mise à jour :", Quote.model_validate_json(get_saved_quote("test.txt")).total_ht_eur)

with get_connection() as conn:
    print("Nombre de lignes test :", conn.execute("SELECT COUNT(*) FROM quotes WHERE source_file = 'test.txt'").fetchone()[0])
    conn.execute("DELETE FROM quotes WHERE source_file = 'test.txt'")