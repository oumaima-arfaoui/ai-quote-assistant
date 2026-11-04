import difflib

from database import get_connection, init_db

init_db()

with get_connection() as conn:
    rows = conn.execute(
        "SELECT source_file, kind, original, final, updated_at FROM corrections"
    ).fetchall()

if not rows:
    print("Aucune correction enregistrée.")

for row in rows:
    print(f"\n===== {row['source_file']} | {row['kind']} | {row['updated_at']} =====")
    diff = difflib.unified_diff(
        row["original"].splitlines(), row["final"].splitlines(),
        fromfile="original", tofile="final", lineterm="",
    )
    print("\n".join(diff))