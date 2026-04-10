import pytest
from pydantic import ValidationError

from clients.profiling.vacancy_profile_model import (
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
