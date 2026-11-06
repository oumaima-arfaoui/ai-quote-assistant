import pytest

import database


def add(source_file="a.txt", **overrides):
    data = dict(
        source_file=source_file,
        raw_text="Bonjour",
        record_json="{}",
        draft_reply="Réponse",
        status="nouveau",
        completeness=50,
        priority="moyenne",
    )
    data.update(overrides)
    database.save_request(**data)


def get_row(source_file):
    with database.get_connection() as conn:
        return conn.execute(
            "SELECT * FROM requests WHERE source_file = ?", (source_file,)
        ).fetchone()


def count_rows(table):
    with database.get_connection() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# --- requests -------------------------------------------------------------


def test_saving_the_same_file_twice_keeps_one_row(temp_db):
    add(raw_text="v1", draft_reply="r1", completeness=30)
    add(raw_text="v2", draft_reply="r2", completeness=80)

    assert count_rows("requests") == 1
    row = get_row("a.txt")
    assert row["raw_text"] == "v2"
    assert row["draft_reply"] == "r2"
    assert row["completeness"] == 80


@pytest.mark.parametrize("decision", ["validé", "rejeté"])
def test_rerun_keeps_a_final_decision(temp_db, decision):
    add(status="nouveau")
    database.update_status("a.txt", decision)

    add(status="à vérifier", raw_text="nouvelle version")

    row = get_row("a.txt")
    assert row["status"] == decision
    assert row["raw_text"] == "nouvelle version"


def test_rerun_overwrites_a_non_final_status(temp_db):
    add(status="nouveau")

    add(status="à vérifier")

    assert get_row("a.txt")["status"] == "à vérifier"


def test_update_status_changes_only_that_request(temp_db):
    add("a.txt")
    add("b.txt")

    database.update_status("a.txt", "validé")

    assert get_row("a.txt")["status"] == "validé"
    assert get_row("b.txt")["status"] == "nouveau"


def test_list_requests_orders_by_priority_then_completeness(temp_db):
    add("a.txt", priority="basse", completeness=90)
    add("b.txt", priority="haute", completeness=10)
    add("c.txt", priority="moyenne", completeness=40)
    add("d.txt", priority="moyenne", completeness=80)
    add("e.txt", priority="aucune", completeness=100)

    order = [row["source_file"] for row in database.list_requests()]

    assert order == ["b.txt", "d.txt", "c.txt", "a.txt", "e.txt"]


def test_search_request_ids(temp_db):
    add("a.txt", raw_text="Fuite d'eau dans la cuisine")
    add("b.txt", raw_text="Peinture du salon")

    ids = database.search_request_ids("cuisine")

    assert ids == {get_row("a.txt")["id"]}
    assert database.search_request_ids("jardin") == set()


def test_get_request_by_id(temp_db):
    add("a.txt", raw_text="Bonjour")
    request_id = get_row("a.txt")["id"]

    assert database.get_request(request_id)["raw_text"] == "Bonjour"
    assert database.get_request(9999) is None


# --- saved quote, final reply, generated quote ---------------------------

SAVE_AND_GET = [
    pytest.param(database.save_quote, database.get_saved_quote, id="quote"),
    pytest.param(database.save_final_reply, database.get_final_reply, id="reply"),
    pytest.param(
        database.save_generated_quote, database.get_generated_quote, id="generated"
    ),
]


@pytest.mark.parametrize("save, get", SAVE_AND_GET)
def test_saved_value_reloads_and_can_be_overwritten(temp_db, save, get):
    save("a.txt", "premier")
    assert get("a.txt") == "premier"

    save("a.txt", "second")
    assert get("a.txt") == "second"


@pytest.mark.parametrize("save, get", SAVE_AND_GET)
def test_missing_value_returns_none(temp_db, save, get):
    assert get("inconnu.txt") is None


# --- corrections ----------------------------------------------------------


def all_corrections():
    with database.get_connection() as conn:
        return conn.execute("SELECT * FROM corrections").fetchall()


def test_a_real_change_is_logged_as_a_correction(temp_db):
    database.log_correction("a.txt", "reply", "texte brouillon", "texte corrigé")

    rows = all_corrections()
    assert len(rows) == 1
    assert rows[0]["original"] == "texte brouillon"
    assert rows[0]["final"] == "texte corrigé"


def test_going_back_to_the_original_removes_the_correction(temp_db):
    database.log_correction("a.txt", "reply", "brouillon", "corrigé")

    database.log_correction("a.txt", "reply", "brouillon", "brouillon")

    assert all_corrections() == []


def test_whitespace_only_difference_is_not_a_correction(temp_db):
    database.log_correction("a.txt", "reply", "brouillon", "  brouillon \n")

    assert all_corrections() == []


def test_a_second_correction_replaces_the_first(temp_db):
    database.log_correction("a.txt", "reply", "brouillon", "version 1")
    database.log_correction("a.txt", "reply", "brouillon", "version 2")

    rows = all_corrections()
    assert len(rows) == 1
    assert rows[0]["final"] == "version 2"