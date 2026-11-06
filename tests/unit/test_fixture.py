import sqlite3

import database


def test_temp_db_is_isolated_and_has_tables(temp_db):
    assert database.DB_PATH == str(temp_db)
    assert database.DB_PATH != "data/agent.db"

    conn = sqlite3.connect(temp_db)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    conn.close()

    assert "requests" in tables