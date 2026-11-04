from database import get_connection, init_db

init_db()

with get_connection() as conn:
    for table in ("generated_quotes", "quotes", "corrections"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(table, ":", n)
    for row in conn.execute("SELECT source_file FROM generated_quotes"):
        print("  généré :", row["source_file"])
    for row in conn.execute("SELECT source_file FROM quotes"):
        print("  enregistré :", row["source_file"])
    for row in conn.execute("SELECT source_file, kind FROM corrections"):
        print("  correction :", row["source_file"], row["kind"])