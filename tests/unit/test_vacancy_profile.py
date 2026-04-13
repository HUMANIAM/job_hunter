import sys

import pytest
from pydantic import ValidationError

from clients.job_profiling.profiling.vacancy_profile_model import (
    Education,
    RoleTitles,
    VacancyProfile,
)


def test_role_titles_normalizes_dedupes_and_limits_alternatives() -> None:
    role_titles = RoleTitles(
        primary=" Mechatronics Technician ",
        alternatives=[
            " Service Technician ",
            "mechatronics technician",
            " Prototype Technician ",
            "service technician",
            " Technician ",
            " Assembler ",
            " System Technician ",
        ],
        confidence="0.975",
        evidence=[
            " h1: Mechatronics Technician ",
            "h1: Mechatronics Technician",
            " h2: As a Mechatronics Technician, you are responsible ",
        ],
    )

    assert role_titles.primary == "mechatronics technician"
    assert role_titles.alternatives == [
        "service technician",
        "prototype technician",
        "technician",
        "assembler",
        "system technician",
    ]
    assert role_titles.confidence == 0.975
    assert role_titles.evidence == [
        "h1: Mechatronics Technician",
        "h2: As a Mechatronics Technician, you are responsible",
    ]


def test_role_titles_requires_non_empty_primary() -> None:
    with pytest.raises(ValidationError, match="primary role title must not be empty"):
        RoleTitles(
            primary="   ",
            confidence=0.9,
            evidence=["h1: Mechatronics Technician"],
        )


def test_role_titles_requires_non_empty_evidence() -> None:
    with pytest.raises(ValidationError, match="evidence must not be empty"):
        RoleTitles(
            primary="mechatronics technician",
            confidence=0.9,
            evidence=[],
        )


def test_role_titles_requires_confidence_between_zero_and_one() -> None:
    with pytest.raises(ValidationError, match="confidence must be between 0 and 1"):
        RoleTitles(
            primary="mechatronics technician",
            confidence=1.5,
            evidence=["h1: Mechatronics Technician"],
        )


def test_education_normalizes_and_keeps_support_metadata() -> None:
    education = Education(
        min_level=" Bachelor ",
        accepted_fields=[
            " Computer Engineering ",
            "embedded systems",
            "computer engineering",
        ],
        confidence="0.83",
        evidence=[
            " Bachelor degree in Computer Engineering ",
            "Bachelor degree in Computer Engineering",
        ],
    )

    assert education.min_level == "bachelor"
    assert education.accepted_fields == [
        "computer engineering",
        "embedded systems",
    ]
    assert education.confidence == 0.83
    assert education.evidence == ["Bachelor degree in Computer Engineering"]


def test_education_defaults_empty_support_when_unset() -> None:
    education = Education()

    assert education.min_level is None
    assert education.accepted_fields == []
    assert education.confidence == 0.0
    assert education.evidence == []


def test_education_requires_evidence_when_requirements_are_set() -> None:
    with pytest.raises(
        ValidationError,
        match="evidence must not be empty when education requirements are set",
    ):
        Education(
            min_level="bachelor",
            confidence=0.84,
            evidence=[],
        )


def test_vacancy_profile_requires_role_titles_supporting_fields() -> None:
    with pytest.raises(ValidationError, match="Field required"):
        VacancyProfile.model_validate(
            {
                "role_titles": {
                    "primary": "mechatronics technician",
                    "alternatives": [],
                }
            }
        )


def test_vacancy_profile_exports_only_public_profile_symbol() -> None:
    vacancy_profile_module = sys.modules[VacancyProfile.__module__]
    assert vacancy_profile_module.__all__ == ["VacancyProfile"]
