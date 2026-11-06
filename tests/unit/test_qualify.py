import pytest

from qualify import TOTAL_CHECKS, completeness_score, priority
from schema import QuoteRequest, Urgency

ALL_FIELDS = ["name", "phone", "email", "site_address", "availability", "work_types"]


def make_record(missing_count=0, **overrides):
    """A quote request with the first `missing_count` fields listed as missing."""
    data = dict(missing_fields=ALL_FIELDS[:missing_count])
    data.update(overrides)
    return QuoteRequest(**data)


def test_total_checks_is_five_fields_plus_work_types():
    assert TOTAL_CHECKS == 6


@pytest.mark.parametrize(
    "missing_count, expected",
    [(0, 100), (1, 83), (2, 67), (3, 50), (4, 33), (5, 17), (6, 0)],
)
def test_score_by_number_of_missing_fields(missing_count, expected):
    assert completeness_score(make_record(missing_count)) == expected


def test_non_quote_message_scores_zero():
    record = make_record(is_quote_request=False)

    assert completeness_score(record) == 0


def test_non_quote_message_has_no_priority_even_if_urgent():
    record = make_record(is_quote_request=False, urgency=Urgency.URGENT)

    assert priority(record) == "aucune"


def test_urgent_is_high_even_when_very_incomplete():
    record = make_record(5, urgency=Urgency.URGENT)

    assert priority(record) == "haute"


@pytest.mark.parametrize("urgency", [Urgency.NORMAL, Urgency.FLEXIBLE, Urgency.UNKNOWN])
def test_complete_non_urgent_request_is_medium(urgency):
    record = make_record(0, urgency=urgency)

    assert priority(record) == "moyenne"


def test_one_missing_field_is_still_medium():
    record = make_record(1, urgency=Urgency.NORMAL)

    assert completeness_score(record) == 83
    assert priority(record) == "moyenne"


def test_two_missing_fields_is_low():
    record = make_record(2, urgency=Urgency.NORMAL)

    assert completeness_score(record) == 67
    assert priority(record) == "basse"