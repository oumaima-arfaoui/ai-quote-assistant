from database import get_connection, init_db

init_db()
with get_connection() as conn:
    rows = conn.execute("SELECT id, source_file, status FROM requests ORDER BY source_file")
    for row in rows:
        print(f"{row['id']:>3} | {row['source_file']:<24} | {row['status']}")