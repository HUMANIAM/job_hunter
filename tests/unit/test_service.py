from __future__ import annotations

from dataclasses import dataclass

from ranking import service as ranking_service


@dataclass
class FakeJob:
    title: str | None
    description_text: str | None
    url: str
    required_languages: list[str] | None = None
    restrictions: list[str] | None = None
    min_years_experience: int | None = None


def test_evaluate_jobs_builds_evaluated_jobs_and_kept_subset() -> None:
    jobs = [
        FakeJob(
            title="Controls Engineer",
            description_text="Control software for high-tech systems.",
            url="https://example.com/controls-engineer",
        ),
        FakeJob(
            title="Supply Chain Planner",
            description_text="Python dashboards and automation for operations.",
            url="https://example.com/supply-chain-planner",
            required_languages=["english", "dutch"],
        ),
    ]
    messages: list[str] = []

    result = ranking_service.evaluate_jobs(jobs, log_message=messages.append)

    assert result.kept_jobs == [jobs[0]]
    assert result.evaluated_jobs == [
        {
            "title": "Controls Engineer",
            "description_text": "Control software for high-tech systems.",
            "url": "https://example.com/controls-engineer",
            "required_languages": None,
            "restrictions": None,
            "min_years_experience": None,
            "decision": "keep",
            "reason": "title_keep_match",
            "skip_hits": [],
            "title_hits": ["controls"],
            "description_hits": [],
        },
        {
            "title": "Supply Chain Planner",
            "description_text": "Python dashboards and automation for operations.",
            "url": "https://example.com/supply-chain-planner",
            "required_languages": ["english", "dutch"],
            "restrictions": None,
            "min_years_experience": None,
            "decision": "skip",
            "reason": "hard_filter_required_language",
            "skip_hits": ["required_language:dutch"],
            "title_hits": [],
            "description_hits": [],
        },
    ]
    assert messages == [
        (
            "KEEP [1] 'Controls Engineer' | "
            "reason=title_keep_match | "
            "title_hits=['controls'] | "
            "description_hits=[]"
        ),
        (
            "SKIP [2] 'Supply Chain Planner' | "
            "reason=hard_filter_required_language | "
            "skip_hits=['required_language:dutch'] | "
            "description_hits=[]"
        ),
    ]
