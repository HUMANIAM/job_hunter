from __future__ import annotations

from dataclasses import dataclass, field

from ranking.evaluator import evaluate_job_match
from ranking.service import rank_job, rank_jobs


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
class CandidateConstraints:
    preferred_locations: list[str]
    excluded_locations: list[str]
    preferred_workplace_types: list[str]
    excluded_workplace_types: list[str]
    requires_visa_sponsorship: bool | None
    avoid_export_control_roles: bool | None
    notes: list[str]
    confidence: float
    evidence: list[str]


@dataclass
class CandidatePayload:
    skills: list[CandidateFeature]
    protocols: list[CandidateFeature]
    standards: list[CandidateFeature]
    domains: list[CandidateFeature]
    languages: list[CandidateLanguage]
    seniority: CandidateSeniority
    years_experience_total: CandidateYearsExperience
    candidate_constraints: CandidateConstraints


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
class JobConstraint:
    kind: str
    bucket: str
    value: str | None
    min_years: int | None
    confidence: float


@dataclass
class JobSeniority:
    value: str | None
    confidence: float


@dataclass
class JobYearsExperienceRequirement:
    min_years: int | None
    confidence: float
    requirement_level: str | None = "required"


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
    location: str | None = None
    remote_policy: str | None = None
    workplace_type: str | None = None
    job_constraints: list[JobConstraint] = field(default_factory=list)


def _candidate_document(
    *,
    preferred_locations: list[str] | None = None,
    excluded_locations: list[str] | None = None,
    preferred_workplace_types: list[str] | None = None,
    requires_visa_sponsorship: bool | None = False,
    avoid_export_control_roles: bool | None = False,
) -> CandidateDocument:
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
            candidate_constraints=CandidateConstraints(
                preferred_locations=preferred_locations or [],
                excluded_locations=excluded_locations or [],
                preferred_workplace_types=preferred_workplace_types or [],
                excluded_workplace_types=[],
                requires_visa_sponsorship=requires_visa_sponsorship,
                avoid_export_control_roles=avoid_export_control_roles,
                notes=[],
                confidence=0.8,
                evidence=["candidate preferences"],
            ),
        ),
    )


def _job_document(
    job_id: str,
    title: str,
    skill_name: str,
    *,
    protocol_name: str = "can",
    location: str | None = "Eindhoven",
    remote_policy: str | None = "Hybrid",
    job_constraints: list[JobConstraint] | None = None,
) -> JobDocument:
    return JobDocument(
        job_id=job_id,
        title=title,
        skills=[JobFeature(name=skill_name, requirement_level="required", confidence=1.0)],
        languages=[JobFeature(name="english", requirement_level="required", confidence=1.0)],
        protocols=[JobFeature(name=protocol_name, requirement_level="preferred", confidence=0.8)],
        standards=[],
        domains=[JobFeature(name="mechatronics", requirement_level="preferred", confidence=0.7)],
        seniority=JobSeniority(value="senior", confidence=0.8),
        years_experience_requirement=JobYearsExperienceRequirement(
            min_years=5,
            confidence=0.7,
            requirement_level="required",
        ),
        location=location,
        remote_policy=remote_policy,
        job_constraints=job_constraints or [],
    )


def test_evaluate_job_match_uses_stable_ids_and_match_status() -> None:
    result = evaluate_job_match(
        _candidate_document(),
        _job_document("embedded_engineer__1234567890", "Embedded Engineer", "python"),
    )

    assert result.job_id == "embedded_engineer__1234567890"
    assert result.candidate_id == "candidate_abc123"
    assert result.status == "match"
    assert result.decision_stage == "ranking"


def test_required_feature_missing_rejects_at_job_must_have_stage() -> None:
    result = evaluate_job_match(
        _candidate_document(),
        _job_document("planner__aaaabbbbb2", "Planner", "excel"),
    )

    assert result.status == "mismatch"
    assert result.decision_stage == "job_must_have"
    assert result.score == 0.0
    assert result.rejection_reasons[0].reason == "required_feature_missing"
    assert result.rejection_reasons[0].expected == "excel"


def test_candidate_preferred_location_mismatch_rejects_at_candidate_stage() -> None:
    result = evaluate_job_match(
        _candidate_document(preferred_locations=["Eindhoven"]),
        _job_document(
            "controls_engineer__aaaabbbbb1",
            "Controls Engineer",
            "python",
            location="Delft",
        ),
    )

    assert result.status == "mismatch"
    assert result.decision_stage == "candidate_must_have"
    assert result.rejection_reasons[0].reason == "preferred_location_not_matched"
    assert result.rejection_reasons[0].actual == "Delft"


def test_candidate_preferred_location_contains_match_accepts_country_variant() -> None:
    result = evaluate_job_match(
        _candidate_document(preferred_locations=["Eindhoven, Netherlands"]),
        _job_document(
            "controls_engineer__aaaabbbbb1",
            "Controls Engineer",
            "python",
            location="Eindhoven",
        ),
    )

    assert result.status == "match"
    assert result.decision_stage == "ranking"


def test_candidate_excluded_location_contains_match_rejects_at_candidate_stage() -> None:
    result = evaluate_job_match(
        _candidate_document(excluded_locations=["Eindhoven, Netherlands"]),
        _job_document(
            "controls_engineer__aaaabbbbb1",
            "Controls Engineer",
            "python",
            location="Eindhoven",
        ),
    )

    assert result.status == "mismatch"
    assert result.decision_stage == "candidate_must_have"
    assert result.rejection_reasons[0].reason == "excluded_location_matched"
    assert result.rejection_reasons[0].actual == "Eindhoven"


def test_job_work_authorization_unknown_rejects_at_job_stage() -> None:
    result = evaluate_job_match(
        _candidate_document(requires_visa_sponsorship=None),
        _job_document(
            "embedded_engineer__legal1",
            "Embedded Engineer",
            "python",
            job_constraints=[
                JobConstraint(
                    kind="restriction",
                    bucket="restrictions",
                    value="work_authorization",
                    min_years=None,
                    confidence=1.0,
                )
            ],
        ),
    )

    assert result.status == "mismatch"
    assert result.decision_stage == "job_must_have"
    assert result.rejection_reasons[0].reason == "work_authorization_unknown"


def test_ranking_threshold_can_reject_after_filters_pass() -> None:
    result = evaluate_job_match(
        _candidate_document(),
        _job_document("controls_engineer__threshold", "Controls Engineer", "python"),
        match_score_threshold=0.95,
    )

    assert result.status == "mismatch"
    assert result.decision_stage == "ranking"
    assert result.rejection_reasons[0].reason == "score_below_threshold"
    assert result.score > 0.0


def test_rank_job_preserves_id_fields() -> None:
    result = rank_job(
        _candidate_document(),
        _job_document("embedded_engineer__1234567890", "Embedded Engineer", "python"),
    )

    assert result["job_id"] == "embedded_engineer__1234567890"
    assert result["candidate_id"] == "candidate_abc123"
    assert result["status"] == "match"


def test_rank_jobs_sorts_matches_before_mismatches() -> None:
    candidate = _candidate_document()
    better_job = _job_document("controls_engineer__aaaabbbbb1", "Controls Engineer", "python")
    weaker_match = _job_document(
        "support_engineer__aaaabbbbb3",
        "Support Engineer",
        "python",
        protocol_name="ethercat",
    )
    mismatch = _job_document("planner__aaaabbbbb2", "Planner", "excel")

    batch = rank_jobs(candidate, [mismatch, weaker_match, better_job])

    assert [job.job_id for job in batch.ranked_jobs] == [
        "controls_engineer__aaaabbbbb1",
        "support_engineer__aaaabbbbb3",
        "planner__aaaabbbbb2",
    ]
    assert [result["job_id"] for result in batch.results] == [
        "controls_engineer__aaaabbbbb1",
        "support_engineer__aaaabbbbb3",
        "planner__aaaabbbbb2",
    ]
    assert batch.results[0]["status"] == "match"
    assert batch.results[-1]["status"] == "mismatch"
