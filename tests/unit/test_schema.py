import pytest
from pydantic import ValidationError

from schema import QuoteRequest, Urgency, WorkType


def test_defaults_of_an_empty_request():
    request = QuoteRequest()

    assert request.is_quote_request is True
    assert request.name is None
    assert request.work_types == []
    assert request.urgency == Urgency.UNKNOWN
    assert request.surface_m2 is None
    assert request.missing_fields == []


@pytest.mark.parametrize(
    "junk",
    [".", "...", "   ", "", "-", "null", "None", "N/A", "inconnu", "Non précisé", "non renseigné"],
)
def test_junk_strings_become_none(junk):
    request = QuoteRequest(name=junk)

    assert request.name is None


def test_validator_applies_to_every_text_field():
    request = QuoteRequest(
        name=".", email="n/a", phone="null", site_address="-",
        availability="inconnu", description="...",
    )

    assert request.name is None
    assert request.email is None
    assert request.phone is None
    assert request.site_address is None
    assert request.availability is None
    assert request.description is None


def test_real_value_is_kept_and_stripped():
    request = QuoteRequest(name="  Marie Dupont  ")

    assert request.name == "Marie Dupont"


def test_none_stays_none():
    request = QuoteRequest(name=None)

    assert request.name is None


def test_work_types_accept_strings_and_become_enums():
    request = QuoteRequest(work_types=["plomberie", "peinture"])

    assert request.work_types == [WorkType.PLUMBING, WorkType.PAINTING]


def test_unknown_work_type_is_refused():
    with pytest.raises(ValidationError):
        QuoteRequest(work_types=["jardinage"])


def test_unknown_urgency_is_refused():
    with pytest.raises(ValidationError):
        QuoteRequest(urgency="tres tres urgent")


def test_surface_is_a_number():
    request = QuoteRequest(surface_m2=65)

    assert request.surface_m2 == 65.0