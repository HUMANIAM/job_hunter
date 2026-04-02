from __future__ import annotations

import os

import pytest

from sources.sioux.llm import SiouxLlmExtractor
from sources.sioux.parser import SiouxJobDeterministic

pytestmark = [
    pytest.mark.openai_integration,
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY is required for live OpenAI integration tests",
    ),
    pytest.mark.skipif(
        os.environ.get("RUN_OPENAI_INTEGRATION_TESTS") != "1",
        reason="set RUN_OPENAI_INTEGRATION_TESTS=1 to run live OpenAI integration tests",
    ),
]


@pytest.fixture(scope="module")
def extractor() -> SiouxLlmExtractor:
    return SiouxLlmExtractor.from_env()


def _make_job(
    *,
    title: str,
    description_text: str,
    disciplines: list[str] | None = None,
) -> SiouxJobDeterministic:
    return SiouxJobDeterministic(
        title=title,
        url="https://vacancy.sioux.eu/vacancies/test-role.html",
        disciplines=disciplines or [],
        location=None,
        team=None,
        work_experience=None,
        min_years_experience=None,
        max_years_experience=None,
        experience_text=None,
        educational_background=None,
        required_degrees=[],
        industry_domains=[],
        workplace_type=None,
        fulltime_parttime=None,
        min_hours_per_week=None,
        max_hours_per_week=None,
        remote_policy=None,
        work_locations_text=None,
        client_site_required=None,
        travel_region=None,
        recruiter_name=None,
        recruiter_role=None,
        recruiter_email=None,
        recruiter_phone=None,
        description_text=description_text,
    )


def _lowered_names(
    values: list[object], requirement_level: str | None = None
) -> set[str]:
    lowered_values: set[str] = set()
    for value in values:
        if (
            requirement_level is not None
            and getattr(value, "requirement_level") != requirement_level
        ):
            continue
        lowered_values.add(getattr(value, "name").lower())
    return lowered_values


def _restriction_values(values: list[object]) -> str:
    return " ".join(getattr(value, "value").lower() for value in values)


def test_openai_extractor_returns_empty_and_null_for_unsupported_fields(
    extractor: SiouxLlmExtractor,
) -> None:
    job = _make_job(
        title="Operations Coordinator",
        description_text=(
            "You help teams stay aligned, schedule meetings, and keep internal "
            "projects moving. We value ownership, communication, and curiosity. "
            "No specific technologies, human languages, standards, domains, or "
            "eligibility requirements are stated in this text."
        ),
    )

    result = extractor.extract(job)

    assert result.skills == []
    assert result.languages == []
    assert result.protocols == []
    assert result.standards == []
    assert result.domains == []
    assert result.seniority.value is None
    assert result.restrictions == []
    assert result.seniority.evidence == []


def test_openai_extractor_recognizes_all_schema_fields(
    extractor: SiouxLlmExtractor,
) -> None:
    job = _make_job(
        title="Senior Embedded Software Engineer",
        disciplines=["Embedded", "Software"],
        description_text=(
            "Requirements\n"
            "- Senior embedded software engineer role.\n"
            "- You must have hands-on experience with Python, C++, and Embedded Linux.\n"
            "- Fluent English and Dutch are required.\n"
            "- You must know CAN, SPI, and I2C.\n"
            "- You must apply IEC 61508, SIL 2, and MISRA.\n"
            "- Experience in semiconductor and medical devices is required.\n"
            "- You must already hold EU work authorization and be eligible for Dutch security clearance.\n"
            "Nice to have\n"
            "- Qt and FreeRTOS are a plus.\n"
            "- German is a plus.\n"
            "- EtherCAT is a plus.\n"
            "- ISO 26262 is a plus.\n"
            "- Robotics is a plus.\n"
        ),
    )

    result = extractor.extract(job)
    required_skills = _lowered_names(result.skills, "required")
    preferred_skills = _lowered_names(result.skills, "preferred")
    required_languages = _lowered_names(result.languages, "required")
    preferred_languages = _lowered_names(result.languages, "preferred")
    required_protocols = _lowered_names(result.protocols, "required")
    preferred_protocols = _lowered_names(result.protocols, "preferred")
    required_standards = _lowered_names(result.standards, "required")
    preferred_standards = _lowered_names(result.standards, "preferred")
    required_domains = _lowered_names(result.domains, "required")
    preferred_domains = _lowered_names(result.domains, "preferred")
    restrictions_text = _restriction_values(result.restrictions)

    assert "python" in required_skills
    assert "c++" in required_skills
    assert any("embedded linux" in value for value in required_skills)
    assert "qt" in preferred_skills
    assert "freertos" in preferred_skills
    assert required_languages >= {"english", "dutch"}
    assert "german" in preferred_languages
    assert required_protocols >= {"can", "spi", "i2c"}
    assert "ethercat" in preferred_protocols
    assert "iec 61508" in required_standards
    assert "sil 2" in required_standards or "sil" in required_standards
    assert "misra" in required_standards
    assert "iso 26262" in preferred_standards
    assert "semiconductor" in required_domains
    assert any("medical" in value for value in required_domains)
    assert "robotics" in preferred_domains
    assert result.seniority.value == "senior"
    assert "work authorization" in restrictions_text
    assert "security clearance" in restrictions_text

    assert all(value.evidence for value in result.skills)
    assert all(value.evidence for value in result.languages)
    assert all(value.evidence for value in result.protocols)
    assert all(value.evidence for value in result.standards)
    assert all(value.evidence for value in result.domains)
    assert result.seniority.evidence
    assert all(value.evidence for value in result.restrictions)


def test_openai_extractor_handles_mixed_null_and_non_null_outputs(
    extractor: SiouxLlmExtractor,
) -> None:
    job = _make_job(
        title="Medior Software Engineer",
        description_text=(
            "Requirements\n"
            "- Medior software engineering role.\n"
            "- Python is required.\n"
            "- Fluent English is required.\n"
            "- CAN is required.\n"
            "The text does not mention any preferred skills, preferred languages, "
            "standards, preferred protocols, domains, or legal restrictions.\n"
        ),
    )

    result = extractor.extract(job)

    assert "python" in _lowered_names(result.skills, "required")
    assert _lowered_names(result.skills, "preferred") == set()
    assert _lowered_names(result.languages, "required") == {"english"}
    assert _lowered_names(result.languages, "preferred") == set()
    assert _lowered_names(result.protocols, "required") == {"can"}
    assert _lowered_names(result.protocols, "preferred") == set()
    assert result.standards == []
    assert result.domains == []
    assert result.seniority.value == "medior"
    assert result.restrictions == []

    assert all(value.evidence for value in result.skills)
    assert all(value.evidence for value in result.languages)
    assert all(value.evidence for value in result.protocols)
    assert result.seniority.evidence
