from __future__ import annotations

from dataclasses import dataclass

from ranking.evaluator import evaluate_job_match
from ranking.service import rank_jobs


@dataclass
class CandidateFeature:
    name: str
    strength: str
    confidence: float


@dataclass
class CandidateLanguage:
    name: str
    level: str | None
    confidence: float


@dataclass
class CandidateYearsExperience:
    value: int | None
    confidence: float


@dataclass
class CandidateSeniority:
    value: str | None
    confidence: float


@dataclass
class CandidatePayload:
    skills: list[CandidateFeature]
    protocols: list[CandidateFeature]
    standards: list[CandidateFeature]
    domains: list[CandidateFeature]
    languages: list[CandidateLanguage]
    seniority: CandidateSeniority
    years_experience_total: CandidateYearsExperience


@dataclass
class CandidateDocument:
    candidate_id: str
    profile: CandidatePayload


@dataclass
class JobFeature:
    name: str
    requirement_level: str
    confidence: float


@dataclass
class JobSeniority:
    value: str | None
    confidence: float


@dataclass
class JobYearsExperienceRequirement:
    min_years: int | None
    confidence: float


@dataclass
class JobDocument:
    job_id: str
    title: str
    skills: list[JobFeature]
    languages: list[JobFeature]
    protocols: list[JobFeature]
    standards: list[JobFeature]
    domains: list[JobFeature]
    seniority: JobSeniority
    years_experience_requirement: JobYearsExperienceRequirement


def _candidate_document() -> CandidateDocument:
    return CandidateDocument(
        candidate_id="candidate_abc123",
        profile=CandidatePayload(
            skills=[CandidateFeature(name="python", strength="core", confidence=1.0)],
            protocols=[CandidateFeature(name="can", strength="strong", confidence=0.9)],
            standards=[],
            domains=[CandidateFeature(name="mechatronics", strength="secondary", confidence=0.8)],
            languages=[CandidateLanguage(name="english", level="fluent", confidence=1.0)],
            seniority=CandidateSeniority(value="senior", confidence=0.9),
            years_experience_total=CandidateYearsExperience(value=6, confidence=0.8),
        ),
    )


def _job_document(job_id: str, title: str, skill_name: str) -> JobDocument:
    return JobDocument(
        job_id=job_id,
        title=title,
        skills=[JobFeature(name=skill_name, requirement_level="required", confidence=1.0)],
        languages=[JobFeature(name="english", requirement_level="required", confidence=1.0)],
        protocols=[JobFeature(name="can", requirement_level="preferred", confidence=0.8)],
        standards=[],
        domains=[JobFeature(name="mechatronics", requirement_level="preferred", confidence=0.7)],
        seniority=JobSeniority(value="senior", confidence=0.8),
        years_experience_requirement=JobYearsExperienceRequirement(
            min_years=5,
            confidence=0.7,
        ),
    )


def test_evaluate_job_match_uses_stable_ids() -> None:
    result = evaluate_job_match(
        _candidate_document(),
        _job_document("embedded_engineer__1234567890", "Embedded Engineer", "python"),
    )

    assert result.job_id == "embedded_engineer__1234567890"
    assert result.candidate_id == "candidate_abc123"


def test_rank_jobs_sorts_results_and_preserves_id_fields() -> None:
    candidate = _candidate_document()
    better_job = _job_document("controls_engineer__aaaabbbbb1", "Controls Engineer", "python")
    weaker_job = _job_document(
        "planner__aaaabbbbb2",
        "Planner",
        "excel",
    )

    batch = rank_jobs(candidate, [weaker_job, better_job])

    assert [job.job_id for job in batch.ranked_jobs] == [
        "controls_engineer__aaaabbbbb1",
        "planner__aaaabbbbb2",
    ]
    assert [result["job_id"] for result in batch.results] == [
        "controls_engineer__aaaabbbbb1",
        "planner__aaaabbbbb2",
    ]
    assert all(result["candidate_id"] == "candidate_abc123" for result in batch.results)
