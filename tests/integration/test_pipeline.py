import pytest

import database
import pipeline
from schema import QuoteRequest, Urgency, WorkType


class FakeExtractor:
    """Stands in for the extraction chain: returns a canned record or raises."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        if self.error:
            raise self.error
        return self.result


class FakeDrafter:
    """Stands in for draft_reply: fails `failures` times, then answers."""

    def __init__(self, failures=0, text="Bonjour, nous revenons vers vous."):
        self.failures = failures
        self.text = text
        self.calls = 0

    def __call__(self, record):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("LLM indisponible")
        return self.text


def complete_record(**overrides):
    data = dict(
        name="Marie Dupont",
        phone="0600000000",
        email="marie@example.com",
        site_address="12 rue des Lilas, Lyon",
        availability="Le matin",
        work_types=[WorkType.PLUMBING],
    )
    data.update(overrides)
    return QuoteRequest(**data)


@pytest.fixture
def fakes(temp_db, monkeypatch):
    """Fake LLM pieces plus a temporary database; no waiting between retries."""
    monkeypatch.setattr(pipeline.time, "sleep", lambda seconds: None)

    class Fakes:
        pass

    env = Fakes()
    env.extractor = FakeExtractor(result=complete_record())
    env.drafter = FakeDrafter()
    monkeypatch.setattr(pipeline, "extract_with_retry", env.extractor)
    monkeypatch.setattr(pipeline, "draft_reply", env.drafter)
    return env


def get_row(source_file):
    with database.get_connection() as conn:
        return conn.execute(
            "SELECT * FROM requests WHERE source_file = ?", (source_file,)
        ).fetchone()


def test_complete_request_is_processed_and_saved(fakes):
    summary = pipeline.process_text("a.txt", "Fuite sous mon lavabo")

    assert summary == "en cours de traitement | 100% | priorité moyenne"
    row = get_row("a.txt")
    assert row["status"] == "en cours de traitement"
    assert row["completeness"] == 100
    assert row["priority"] == "moyenne"
    assert row["raw_text"] == "Fuite sous mon lavabo"
    assert row["draft_reply"] == "Bonjour, nous revenons vers vous."
    assert fakes.extractor.calls == [{"request_text": "Fuite sous mon lavabo"}]


def test_incomplete_request_is_flagged_with_its_missing_fields(fakes):
    fakes.extractor.result = complete_record(phone=None, email=None)

    summary = pipeline.process_text("a.txt", "Fuite sous mon lavabo")

    assert summary == "à compléter | 67% | priorité basse"
    row = get_row("a.txt")
    assert row["status"] == "à compléter"
    assert '"missing_fields":["phone","email"]' in row["record_json"].replace(" ", "")


def test_urgent_request_gets_high_priority(fakes):
    fakes.extractor.result = complete_record(urgency=Urgency.URGENT)

    pipeline.process_text("a.txt", "Fuite importante, urgent")

    assert get_row("a.txt")["priority"] == "haute"


def test_message_that_is_not_a_quote_request_gets_no_reply(fakes):
    fakes.extractor.result = QuoteRequest(is_quote_request=False)

    summary = pipeline.process_text("a.txt", "Quels sont vos horaires ?")

    assert summary == "hors demande | 0% | priorité aucune"
    row = get_row("a.txt")
    assert row["draft_reply"] is None
    assert fakes.drafter.calls == 0


def test_extraction_failure_keeps_the_message_for_manual_review(fakes):
    fakes.extractor.error = RuntimeError("modèle indisponible")

    summary = pipeline.process_text("a.txt", "Fuite sous mon lavabo")

    assert summary.startswith("à vérifier")
    row = get_row("a.txt")
    assert row["status"] == "à vérifier"
    assert row["raw_text"] == "Fuite sous mon lavabo"
    assert row["draft_reply"] is None
    assert "Fuite sous mon lavabo" in row["record_json"]
    assert fakes.drafter.calls == 0


def test_draft_reply_failing_every_time_leaves_the_reply_empty(fakes):
    fakes.drafter.failures = 99

    pipeline.process_text("a.txt", "Fuite sous mon lavabo")

    assert fakes.drafter.calls == 3
    row = get_row("a.txt")
    assert row["draft_reply"] is None
    assert row["status"] == "en cours de traitement"


def test_draft_reply_is_retried_and_can_succeed_on_the_third_try(fakes):
    fakes.drafter.failures = 2

    pipeline.process_text("a.txt", "Fuite sous mon lavabo")

    assert fakes.drafter.calls == 3
    assert get_row("a.txt")["draft_reply"] == "Bonjour, nous revenons vers vous."


@pytest.mark.parametrize("text", ["", "   \n  "])
def test_empty_message_is_refused_and_nothing_is_saved(fakes, text):
    with pytest.raises(ValueError):
        pipeline.process_text("a.txt", text)

    assert get_row("a.txt") is None
    assert fakes.extractor.calls == []


def test_rerun_keeps_a_validated_decision(fakes):
    pipeline.process_text("a.txt", "Fuite sous mon lavabo")
    database.update_status("a.txt", "validé")

    fakes.extractor.result = complete_record(phone=None)
    pipeline.process_text("a.txt", "Fuite sous mon lavabo, version 2")

    row = get_row("a.txt")
    assert row["status"] == "validé"
    assert row["raw_text"] == "Fuite sous mon lavabo, version 2"
    assert row["completeness"] == 83


def test_process_reads_the_file_and_uses_its_name(fakes, tmp_path):
    message = tmp_path / "demande_01.txt"
    message.write_text("Bonjour, j'ai une fuite. Merci", encoding="utf-8")

    pipeline.process(message)

    assert get_row("demande_01.txt")["raw_text"] == "Bonjour, j'ai une fuite. Merci"