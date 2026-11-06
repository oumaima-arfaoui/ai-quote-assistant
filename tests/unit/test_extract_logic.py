import pytest

from extract import (
    QUESTIONS,
    REQUIRED_BY_WORK,
    REQUIRED_FIELDS,
    build_questions,
    compute_missing,
)
from schema import QuoteRequest, WorkType


def make_request(**overrides):
    """A complete plumbing request; override fields to break it."""
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


def test_complete_request_has_nothing_missing():
    assert compute_missing(make_request()) == []


def test_non_quote_message_has_nothing_missing():
    request = QuoteRequest(is_quote_request=False)

    assert compute_missing(request) == []


def test_empty_request_lists_base_fields_then_work_types():
    request = QuoteRequest()

    assert compute_missing(request) == [
        "name", "phone", "email", "site_address", "availability", "work_types",
    ]


@pytest.mark.parametrize("work_type", [WorkType.PAINTING, WorkType.RENOVATION])
def test_painting_and_renovation_require_a_surface(work_type):
    request = make_request(work_types=[work_type])

    assert compute_missing(request) == ["surface_m2"]


@pytest.mark.parametrize("work_type", [WorkType.PAINTING, WorkType.RENOVATION])
def test_surface_given_removes_the_requirement(work_type):
    request = make_request(work_types=[work_type], surface_m2=40)

    assert compute_missing(request) == []


def test_plumbing_does_not_require_a_surface():
    request = make_request(work_types=[WorkType.PLUMBING])

    assert "surface_m2" not in compute_missing(request)


def test_surface_is_listed_once_with_two_work_types():
    request = make_request(work_types=[WorkType.PAINTING, WorkType.RENOVATION])

    assert compute_missing(request).count("surface_m2") == 1


def test_build_questions_follows_missing_fields_order():
    request = make_request()
    request.missing_fields = ["email", "surface_m2"]

    assert build_questions(request) == [QUESTIONS["email"], QUESTIONS["surface_m2"]]


def test_build_questions_ignores_unknown_fields():
    request = make_request()
    request.missing_fields = ["shoe_size", "phone"]

    assert build_questions(request) == [QUESTIONS["phone"]]


def test_build_questions_is_empty_when_nothing_is_missing():
    assert build_questions(make_request()) == []


def test_every_possible_missing_field_has_a_question():
    possible = set(REQUIRED_FIELDS) | {"work_types"}
    for fields in REQUIRED_BY_WORK.values():
        possible |= set(fields)

    assert possible <= set(QUESTIONS)