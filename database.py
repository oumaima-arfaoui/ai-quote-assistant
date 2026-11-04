import sqlite3

DB_PATH = "data/agent.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT UNIQUE,
                raw_text TEXT,
                record_json TEXT,
                draft_reply TEXT,
                status TEXT,
                completeness INTEGER,
                priority TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                source_file TEXT PRIMARY KEY,
                quote_json TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS replies (
                source_file TEXT PRIMARY KEY,
                final_reply TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                source_file TEXT,
                kind TEXT,
                original TEXT,
                final TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_file, kind)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generated_quotes (
                source_file TEXT PRIMARY KEY,
                quote_json TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_request(source_file, raw_text, record_json, draft_reply, status, completeness, priority):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO requests
            (source_file, raw_text, record_json, draft_reply, status, completeness, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_file) DO UPDATE SET
                raw_text = excluded.raw_text,
                record_json = excluded.record_json,
                draft_reply = excluded.draft_reply,
                completeness = excluded.completeness,
                priority = excluded.priority,
                status = CASE
                    WHEN requests.status IN ('validé', 'rejeté') THEN requests.status
                    ELSE excluded.status
                END
            """,
            (source_file, raw_text, record_json, draft_reply, status, completeness, priority),
        )


def list_requests():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, source_file, status, completeness, priority
            FROM requests
            ORDER BY
                CASE priority
                    WHEN 'haute' THEN 1
                    WHEN 'moyenne' THEN 2
                    WHEN 'basse' THEN 3
                    ELSE 4
                END,
                completeness DESC
            """
        ).fetchall()
def get_request(request_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM requests WHERE id = ?", (request_id,)
        ).fetchone()
        
def save_quote(source_file, quote_json):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO quotes (source_file, quote_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_file) DO UPDATE SET
                quote_json = excluded.quote_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (source_file, quote_json),
        )


def get_saved_quote(source_file):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT quote_json FROM quotes WHERE source_file = ?", (source_file,)
        ).fetchone()
    return row["quote_json"] if row else None
def update_status(source_file, status):
    with get_connection() as conn:
        conn.execute(
            "UPDATE requests SET status = ? WHERE source_file = ?",
            (status, source_file),
        )
        
def save_final_reply(source_file, final_reply):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO replies (source_file, final_reply, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_file) DO UPDATE SET
                final_reply = excluded.final_reply,
                updated_at = CURRENT_TIMESTAMP
            """,
            (source_file, final_reply),
        )


def get_final_reply(source_file):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT final_reply FROM replies WHERE source_file = ?", (source_file,)
        ).fetchone()
    return row["final_reply"] if row else None
def search_request_ids(query):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM requests WHERE raw_text LIKE ?", (f"%{query}%",)
        ).fetchall()
    return {row["id"] for row in rows}
def log_correction(source_file, kind, original, final):
    """Keep one correction per (request, kind). If the final text equals the original, there is no correction."""
    with get_connection() as conn:
        if (original or "").strip() == (final or "").strip():
            conn.execute(
                "DELETE FROM corrections WHERE source_file = ? AND kind = ?",
                (source_file, kind),
            )
            return
        conn.execute(
            """
            INSERT INTO corrections (source_file, kind, original, final, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_file, kind) DO UPDATE SET
                original = excluded.original,
                final = excluded.final,
                updated_at = CURRENT_TIMESTAMP
            """,
            (source_file, kind, original, final),
        )
def save_generated_quote(source_file, quote_json):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO generated_quotes (source_file, quote_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_file) DO UPDATE SET
                quote_json = excluded.quote_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (source_file, quote_json),
        )


def get_generated_quote(source_file):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT quote_json FROM generated_quotes WHERE source_file = ?", (source_file,)
        ).fetchone()
    return row["quote_json"] if row else None