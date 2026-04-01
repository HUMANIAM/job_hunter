from __future__ import annotations

import json

from sources.sioux import parser as sioux_parser


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
        lambda _page: "Build control systems for high-tech machines.",
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
        educational_background="Bachelor",
        workplace_type="Hybrid",
        fulltime_parttime="Full time",
        description_text="Build control systems for high-tech machines.",
    )
    assert messages[0] == (
        "opening vacancy page: "
        "https://vacancy.sioux.eu/vacancies/controls-engineer.html"
    )
    assert "title='Controls Engineer'" in messages[1]
