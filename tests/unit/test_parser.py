from __future__ import annotations

import json

from sources.sioux import parser_back as sioux_parser


def test_parse_job_posting_json_ld_blocks_extracts_location_country() -> None:
    # Given: a JobPosting schema block with location metadata
    json_ld_blocks = [
        json.dumps(
            {
                "@context": "https://schema.org/",
                "@type": "JobPosting",
                "jobLocation": {
                    "address": {
                        "addressLocality": "Eindhoven",
                        "addressCountry": "NL",
                    }
                },
                "employmentType": "Full time",
            }
        )
    ]

    # When: the structured metadata is parsed
    metadata = sioux_parser.parse_job_posting_json_ld_blocks(json_ld_blocks)

    # Then: the structured location fields should be available
    assert metadata == {
        "location": "Eindhoven",
        "country": "NL",
        "employment_type": "Full time",
    }


def test_resolve_job_metadata_prefers_job_tags(monkeypatch) -> None:
    # Given: job-tag metadata and a schema fallback with overlapping fields
    monkeypatch.setattr(
        sioux_parser,
        "extract_job_tags",
        lambda _page: {
            "location": "Eindhoven",
            "employment": "Full time",
            "education level": "Bachelor",
        },
    )
    monkeypatch.setattr(
        sioux_parser,
        "extract_job_posting_metadata",
        lambda _page: {
            "location": "Fallback City",
            "country": "NL",
            "employment_type": "Fallback employment",
        },
    )

    # When: the metadata is resolved for a vacancy page
    metadata = sioux_parser.resolve_job_metadata(object())

    # Then: explicit job tags should win, with schema data kept as fallback
    assert metadata == {
        "location": "Eindhoven",
        "country": "NL",
        "educational_background": "Bachelor",
        "fulltime_parttime": "Full time",
    }


def test_extract_skill_lists_from_text_splits_required_and_preferred() -> None:
    text = """
    What do you bring to the table?
    Bachelor’s or master’s degree in computer science, Embedded Systems, Electrical Engineering or similar
    You have recent experience with C++, Qt, linux and embedded environments
    Knowledge of mechatronics is a plus
    What can you expect in return from Sioux?
    Flexible 32-40 hour working week
    """

    required_skills, preferred_skills = sioux_parser.extract_skill_lists_from_text(
        text
    )

    assert required_skills == [
        (
            "Bachelor’s or master’s degree in computer science, "
            "Embedded Systems, Electrical Engineering or similar"
        ),
        "You have recent experience with C++, Qt, linux and embedded environments",
    ]
    assert preferred_skills == ["Knowledge of mechatronics is a plus"]


def test_extract_skill_lists_from_flattened_text_uses_fallback_split() -> None:
    text = (
        "Embedded Software Engineer What do you bring to the table? "
        "Bachelor’s or master’s degree in computer science, Embedded Systems, "
        "Electrical Engineering or similar "
        "You have 2-3 years of experience in technical software development "
        "You have recent experience with C++, Qt, linux and embedded environments "
        "You understand software architecture and design patterns "
        "You are fluent in Dutch and English (written and verbal) "
        "Knowledge of mechatronics is a plus "
        "What can you expect in return from Sioux? Flexible 32-40 hour working week"
    )

    required_skills, preferred_skills = sioux_parser.extract_skill_lists_from_text(
        text
    )

    assert required_skills == [
        (
            "Bachelor’s or master’s degree in computer science, "
            "Embedded Systems, Electrical Engineering or similar"
        ),
        "You have 2-3 years of experience in technical software development",
        "You have recent experience with C++, Qt, linux and embedded environments",
        "You understand software architecture and design patterns",
        "You are fluent in Dutch and English (written and verbal)",
    ]
    assert preferred_skills == ["Knowledge of mechatronics is a plus"]


def test_resolve_experience_fields_prefers_parseable_requirement_line() -> None:
    min_years, max_years, experience_text = sioux_parser.resolve_experience_fields(
        "Senior",
        [
            "You have 2-3 years of experience in technical software development",
            "You understand software architecture and design patterns",
        ],
        ["Knowledge of mechatronics is a plus"],
    )

    assert min_years == 2
    assert max_years == 3
    assert (
        experience_text
        == "You have 2-3 years of experience in technical software development"
    )


def test_parse_experience_years_supports_at_least_pattern() -> None:
    min_years, max_years = sioux_parser.parse_experience_years(
        "At least 6 years of experience in software testing"
    )

    assert min_years == 6
    assert max_years is None


def test_extract_required_degrees_prefers_background_order_and_deduplicates() -> None:
    required_degrees = sioux_parser.extract_required_degrees(
        "Master, Bachelor",
        [
            (
                "Bachelor’s or master’s degree in computer science, "
                "Embedded Systems, Electrical Engineering or similar"
            ),
        ],
    )

    assert required_degrees == ["Master", "Bachelor"]


def test_extract_required_degrees_falls_back_to_requirement_text() -> None:
    required_degrees = sioux_parser.extract_required_degrees(
        None,
        [
            (
                "A completed Secondary Vocational Education (MBO-4) "
                "Mechatronics education or a Bachelor’s degree in Mechatronics"
            ),
        ],
    )

    assert required_degrees == ["Secondary vocational education", "Bachelor"]


def test_extract_language_requirements_splits_required_and_preferred() -> None:
    required_languages, preferred_languages = (
        sioux_parser.extract_language_requirements(
            [
                "You are fluent in Dutch and English (written and verbal)",
                "Strong analytical skills and a proactive mindset",
            ],
            [
                "German is a plus",
                "Knowledge of mechatronics is a plus",
            ],
        )
    )

    assert required_languages == ["Dutch", "English"]
    assert preferred_languages == ["German"]


def test_extract_industry_domains_preserves_first_mention_order() -> None:
    domains = sioux_parser.extract_industry_domains(
        (
            "You support clients in the semiconductor, analytical, and medical "
            "equipment industries with high-tech solutions."
        )
    )

    assert domains == ["Semiconductor", "Analytical", "Medical", "High-tech"]


def test_parse_hours_per_week_extracts_range_from_description() -> None:
    min_hours, max_hours = sioux_parser.parse_hours_per_week(
        "Flexible working hours of 32- 40 hours per week in an inspiring environment."
    )

    assert min_hours == 32
    assert max_hours == 40


def test_resolve_remote_policy_uses_description_work_from_home_signal() -> None:
    remote_policy = sioux_parser.resolve_remote_policy(
        None,
        "Flexible 32-40 hour working week, with room to work from home.",
    )

    assert remote_policy == "Hybrid"


def test_extract_work_location_fields_derives_client_site_and_region() -> None:
    (
        work_locations_text,
        client_site_required,
        travel_region,
    ) = sioux_parser.extract_work_location_fields(
        (
            "From our office in Delft and at our clients' sites, you will work on "
            "challenging projects mainly in the Randstad area."
        )
    )

    assert work_locations_text == "From our office in Delft and at our clients' sites"
    assert client_site_required is True
    assert travel_region == "Randstad area"


def test_extract_recruiter_fields_parses_contact_tail() -> None:
    (
        recruiter_name,
        recruiter_role,
        recruiter_email,
        recruiter_phone,
    ) = sioux_parser.extract_recruiter_fields(
        (
            "Privacy Notice for applicants Pre-employment screening and background "
            "checks might be part of your application procedure. Your personal "
            "information is managed in compliance with the GDPR regulations. "
            "Jettine van Dongen Talent acquisition +31 (0)40 - 2677100 "
            "jobs@sioux.eu Are you interested?"
        )
    )

    assert recruiter_name == "Jettine van Dongen"
    assert recruiter_role == "Talent acquisition"
    assert recruiter_email == "jobs@sioux.eu"
    assert recruiter_phone == "+31 (0)40 - 2677100"


def test_fetch_job_returns_sioux_job(monkeypatch) -> None:
    # Given: a vacancy page with a readable title and parser subhelpers
    class FakeTitleLocator:
        @property
        def first(self) -> "FakeTitleLocator":
            return self

        def inner_text(self, timeout: int | None = None) -> str:
            return "  Controls Engineer  "

    class FakePage:
        def goto(self, *_args, **_kwargs) -> None:
            return None

        def wait_for_timeout(self, *_args, **_kwargs) -> None:
            return None

        def locator(self, selector: str) -> FakeTitleLocator:
            assert selector == "h1"
            return FakeTitleLocator()

    monkeypatch.setattr(
        sioux_parser,
        "resolve_job_metadata",
        lambda _page: {
            "location": "Eindhoven",
            "country": "NL",
            "educational_background": "Bachelor",
            "fulltime_parttime": "Full time",
        },
    )
    monkeypatch.setattr(
        sioux_parser,
        "extract_value_by_label",
        lambda _page, label: {
            "Team": "Embedded",
            "Work experience": "Senior",
            "Educational background": None,
            "Workplace type": "Hybrid",
            "Fulltime/parttime": None,
        }[label],
    )
    monkeypatch.setattr(
        sioux_parser,
        "extract_description_text",
        lambda _page: (
            "Build control systems for semiconductor and medical high-tech machines. "
            "From our office in Delft and at our clients' sites, you will work on "
            "challenging projects mainly in the Randstad area. "
            "Flexible 32-40 hour working week, with room to work from home. "
            "Privacy Notice for applicants Pre-employment screening and background "
            "checks might be part of your application procedure. Your personal "
            "information is managed in compliance with the GDPR regulations. "
            "Jettine van Dongen Talent acquisition +31 (0)40 - 2677100 "
            "jobs@sioux.eu Are you interested?"
        ),
    )
    monkeypatch.setattr(
        sioux_parser,
        "extract_skill_lists",
        lambda _page: (
            [
                "Bachelor’s degree in computer science",
                "You have 2-3 years of experience in technical software development",
                "You are fluent in Dutch and English (written and verbal)",
                "Recent experience with C++ and Linux",
            ],
            [
                "German is a plus",
                "Knowledge of mechatronics is a plus",
            ],
        ),
    )
    messages: list[str] = []

    # When: the parser fetches and parses the vacancy page
    job = sioux_parser.fetch_job(
        FakePage(),
        "https://vacancy.sioux.eu/vacancies/controls-engineer.html",
        disciplines=["Software", "Controls"],
        log_message=messages.append,
    )

    # Then: the parser should return the Sioux job dataclass with normalized fields
    assert job == sioux_parser.SiouxJob(
        title="Controls Engineer",
        url="https://vacancy.sioux.eu/vacancies/controls-engineer.html",
        disciplines=["Controls", "Software"],
        location="Eindhoven",
        team="Embedded",
        work_experience="Senior",
        min_years_experience=2,
        max_years_experience=3,
        experience_text="You have 2-3 years of experience in technical software development",
        educational_background="Bachelor",
        required_degrees=["Bachelor"],
        required_languages=["Dutch", "English"],
        preferred_languages=["German"],
        industry_domains=["Semiconductor", "Medical", "High-tech"],
        workplace_type="Hybrid",
        fulltime_parttime="Full time",
        min_hours_per_week=32,
        max_hours_per_week=40,
        remote_policy="Hybrid",
        work_locations_text=(
            "From our office in Delft and at our clients' sites"
        ),
        client_site_required=True,
        travel_region="Randstad area",
        recruiter_name="Jettine van Dongen",
        recruiter_role="Talent acquisition",
        recruiter_email="jobs@sioux.eu",
        recruiter_phone="+31 (0)40 - 2677100",
        required_skills=[
            "Bachelor’s degree in computer science",
            "You have 2-3 years of experience in technical software development",
            "You are fluent in Dutch and English (written and verbal)",
            "Recent experience with C++ and Linux",
        ],
        preferred_skills=[
            "German is a plus",
            "Knowledge of mechatronics is a plus",
        ],
        description_text=(
            "Build control systems for semiconductor and medical high-tech machines. "
            "From our office in Delft and at our clients' sites, you will work on "
            "challenging projects mainly in the Randstad area. "
            "Flexible 32-40 hour working week, with room to work from home. "
            "Privacy Notice for applicants Pre-employment screening and background "
            "checks might be part of your application procedure. Your personal "
            "information is managed in compliance with the GDPR regulations. "
            "Jettine van Dongen Talent acquisition +31 (0)40 - 2677100 "
            "jobs@sioux.eu Are you interested?"
        ),
    )
    assert messages[0] == (
        "opening vacancy page: "
        "https://vacancy.sioux.eu/vacancies/controls-engineer.html"
    )
    assert "title='Controls Engineer'" in messages[1]
