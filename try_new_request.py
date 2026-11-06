from database import get_connection, init_db
from pipeline import process_text

init_db()

# 1. an empty message is refused
try:
    process_text("empty.txt", "   ")
except ValueError as e:
    print("Refusé :", e)

# 2. a real message is processed and stored
text = (
    "Bonjour, je voudrais faire poser un lavabo dans ma salle d'eau. "
    "Marie Dupont, 06 00 00 00 00, 5 rue Test, 31000 Toulouse. Merci."
)
print(process_text("test_manual_input.txt", text))

with get_connection() as conn:
    row = conn.execute(
        "SELECT id, status, completeness, priority FROM requests WHERE source_file = ?",
        ("test_manual_input.txt",),
    ).fetchone()
    print(dict(row))
    conn.execute("DELETE FROM requests WHERE source_file = ?", ("test_manual_input.txt",))