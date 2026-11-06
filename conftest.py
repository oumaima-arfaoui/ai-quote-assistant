import pytest

import database


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """A fresh empty SQLite database for one test, deleted afterwards."""
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_file))
    database.init_db()
    return db_file