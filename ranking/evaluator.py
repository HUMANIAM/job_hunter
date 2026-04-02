# evaluator.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Protocol


BucketName = Literal[
    "skills",
    "languages",
    "protocols",
    "standards",
    "domains",
    "seniority",
    "years_experience",
]


STRENGTH_WEIGHTS: dict[str, float] = {
    "core": 1.00,
    "strong": 0.80,
    "secondary": 0.55,
    "exposure": 0.25,
}

REQUIREMENT_WEIGHTS: dict[str, float] = {
    "required": 1.00,
    "preferred": 0.60,
}

LANGUAGE_LEVEL_WEIGHTS: dict[str, float] = {
    "native": 1.00,
    "fluent": 0.90,
    "professional": 0.75,
    "conversational": 0.50,
    "basic": 0.25,
    "none": 0.00,
}

SENIORITY_WEIGHTS: dict[str, int] = {
    "junior": 1,
    "medior": 2,
    "senior": 3,
    "lead": 4,
    "principal": 5,
    "staff": 6,
}

BUCKET_WEIGHTS: dict[BucketName, float] = {
    "skills": 0.40,
    "languages": 0.10,
    "protocols": 0.15,
    "standards": 0.10,
    "domains": 0.15,
    "seniority": 0.05,
    "years_experience": 0.05,
}


class FeatureLike(Protocol):
    name: str
    confidence: float


class CandidateFeatureLike(FeatureLike, Protocol):
    strength: str


class CandidateLanguageLike(Protocol):
    name: str
    level: str | None
    confidence: float


class CandidateYearsExperienceLike(Protocol):
    value: int | None
    confidence: float


class CandidateSeniorityLike(Protocol):
    value: str | None
    confidence: float


class JobFeatureLike(FeatureLike, Protocol):
    requirement_level: str


class JobYearsExperienceLike(Protocol):
    min_years: int | None
    confidence: float


class JobSeniorityLike(Protocol):
    value: str | None
    confidence: float


class CandidateProfileRootLike(Protocol):
    candidate_id: str
    profile: Any


class JobLike(Protocol):
    job_id: str
    title: str
    skills: list[Any]
    languages: list[Any]
    protocols: list[Any]
    standards: list[Any]
    domains: list[Any]
    seniority: Any
    years_experience_requirement: Any


@dataclass
class BucketScore:
    skills: float
    languages: float
    protocols: float
    standards: float
    domains: float
    seniority: float
    years_experience: float


@dataclass
class FeatureMatch:
    bucket: BucketName
    job_value: str
    candidate_value: str
    score: float


@dataclass
class FeatureGap:
    bucket: BucketName
    job_value: str


@dataclass
class RankingResult:
    job_id: str
    candidate_id: str
    score: float
    bucket_scores: BucketScore
    matched_features: list[FeatureMatch] = field(default_factory=list)
    missing_features: list[FeatureGap] = field(default_factory=list)


def _get_field(value: object, field_name: str) -> object | None:
    if isinstance(value, dict):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _normalize_name(value: str | None) -> str:
    return (value or "").strip().lower()


def _safe_confidence(value: object) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    return 0.0


def _candidate_strength_weight(value: str | None) -> float:
    return STRENGTH_WEIGHTS.get((value or "").strip().lower(), 0.0)


def _job_requirement_weight(value: str | None) -> float:
    return REQUIREMENT_WEIGHTS.get((value or "").strip().lower(), 0.0)


def _language_level_weight(value: str | None) -> float:
    return LANGUAGE_LEVEL_WEIGHTS.get((value or "").strip().lower(), 0.0)


def _empty_bucket_scores() -> dict[BucketName, float]:
    return {
        "skills": 0.0,
        "languages": 0.0,
        "protocols": 0.0,
        "standards": 0.0,
        "domains": 0.0,
        "seniority": 0.0,
        "years_experience": 0.0,
    }


def _candidate_feature_index(items: Iterable[object]) -> dict[str, object]:
    indexed: dict[str, object] = {}
    for item in items:
        name = _normalize_name(_get_field(item, "name"))
        if not name:
            continue

        current = indexed.get(name)
        if current is None:
            indexed[name] = item
            continue

        current_strength = _candidate_strength_weight(_get_field(current, "strength"))
        current_confidence = _safe_confidence(_get_field(current, "confidence"))
        new_strength = _candidate_strength_weight(_get_field(item, "strength"))
        new_confidence = _safe_confidence(_get_field(item, "confidence"))

        if (new_strength, new_confidence) > (current_strength, current_confidence):
            indexed[name] = item

    return indexed


def _candidate_language_index(items: Iterable[object]) -> dict[str, object]:
    indexed: dict[str, object] = {}
    for item in items:
        name = _normalize_name(_get_field(item, "name"))
        if not name:
            continue

        current = indexed.get(name)
        if current is None:
            indexed[name] = item
            continue

        current_level = _language_level_weight(_get_field(current, "level"))
        current_confidence = _safe_confidence(_get_field(current, "confidence"))
        new_level = _language_level_weight(_get_field(item, "level"))
        new_confidence = _safe_confidence(_get_field(item, "confidence"))

        if (new_level, new_confidence) > (current_level, current_confidence):
            indexed[name] = item

    return indexed


def _score_feature_bucket(
    *,
    bucket: BucketName,
    job_items: Iterable[object],
    candidate_items: Iterable[object],
) -> tuple[float, list[FeatureMatch], list[FeatureGap]]:
    candidate_index = _candidate_feature_index(candidate_items)
    numerator = 0.0
    denominator = 0.0
    matches: list[FeatureMatch] = []
    gaps: list[FeatureGap] = []

    for job_item in job_items:
        job_name = _normalize_name(_get_field(job_item, "name"))
        if not job_name:
            continue

        requirement_level = _get_field(job_item, "requirement_level")
        job_importance = (
            _job_requirement_weight(requirement_level)
            * _safe_confidence(_get_field(job_item, "confidence"))
        )
        if job_importance <= 0:
            continue

        denominator += job_importance
        candidate_item = candidate_index.get(job_name)
        if candidate_item is None:
            gaps.append(FeatureGap(bucket=bucket, job_value=job_name))
            continue

        candidate_quality = (
            _candidate_strength_weight(_get_field(candidate_item, "strength"))
            * _safe_confidence(_get_field(candidate_item, "confidence"))
        )
        contribution = job_importance * candidate_quality
        numerator += contribution

        matches.append(
            FeatureMatch(
                bucket=bucket,
                job_value=job_name,
                candidate_value=job_name,
                score=round(candidate_quality, 6),
            )
        )

    if denominator == 0:
        return 0.0, matches, gaps

    return numerator / denominator, matches, gaps


def _score_language_bucket(
    *,
    job_items: Iterable[object],
    candidate_items: Iterable[object],
) -> tuple[float, list[FeatureMatch], list[FeatureGap]]:
    candidate_index = _candidate_language_index(candidate_items)
    numerator = 0.0
    denominator = 0.0
    matches: list[FeatureMatch] = []
    gaps: list[FeatureGap] = []

    for job_item in job_items:
        job_name = _normalize_name(_get_field(job_item, "name"))
        if not job_name:
            continue

        job_importance = (
            _job_requirement_weight(_get_field(job_item, "requirement_level"))
            * _safe_confidence(_get_field(job_item, "confidence"))
        )
        if job_importance <= 0:
            continue

        denominator += job_importance
        candidate_item = candidate_index.get(job_name)
        if candidate_item is None:
            gaps.append(FeatureGap(bucket="languages", job_value=job_name))
            continue

        candidate_quality = (
            _language_level_weight(_get_field(candidate_item, "level"))
            * _safe_confidence(_get_field(candidate_item, "confidence"))
        )
        contribution = job_importance * candidate_quality
        numerator += contribution

        matches.append(
            FeatureMatch(
                bucket="languages",
                job_value=job_name,
                candidate_value=job_name,
                score=round(candidate_quality, 6),
            )
        )

    if denominator == 0:
        return 0.0, matches, gaps

    return numerator / denominator, matches, gaps


def _score_seniority(
    *,
    job_seniority: object,
    candidate_seniority: object,
) -> tuple[float, list[FeatureMatch], list[FeatureGap]]:
    job_value = _normalize_name(_get_field(job_seniority, "value"))
    candidate_value = _normalize_name(_get_field(candidate_seniority, "value"))

    if not job_value:
        return 0.0, [], []

    if candidate_value not in SENIORITY_WEIGHTS:
        return 0.0, [], [FeatureGap(bucket="seniority", job_value=job_value)]

    if job_value not in SENIORITY_WEIGHTS:
        return 0.0, [], []

    job_level = SENIORITY_WEIGHTS[job_value]
    candidate_level = SENIORITY_WEIGHTS[candidate_value]

    if candidate_level >= job_level:
        level_score = 1.0
    elif candidate_level == job_level - 1:
        level_score = 0.5
    else:
        level_score = 0.0

    score = (
        level_score
        * _safe_confidence(_get_field(job_seniority, "confidence"))
        * _safe_confidence(_get_field(candidate_seniority, "confidence"))
    )

    if score <= 0.0:
        return 0.0, [], [FeatureGap(bucket="seniority", job_value=job_value)]

    return (
        score,
        [
            FeatureMatch(
                bucket="seniority",
                job_value=job_value,
                candidate_value=candidate_value,
                score=round(score, 6),
            )
        ],
        [],
    )


def _score_years_experience(
    *,
    job_years_requirement: object,
    candidate_years_experience: object,
) -> tuple[float, list[FeatureMatch], list[FeatureGap]]:
    min_years = _get_field(job_years_requirement, "min_years")
    candidate_years = _get_field(candidate_years_experience, "value")

    if not isinstance(min_years, int) or min_years <= 0:
        return 0.0, [], []

    if not isinstance(candidate_years, int) or candidate_years < 0:
        return 0.0, [], [FeatureGap(bucket="years_experience", job_value=str(min_years))]

    ratio = min(candidate_years / min_years, 1.0)
    score = (
        ratio
        * _safe_confidence(_get_field(job_years_requirement, "confidence"))
        * _safe_confidence(_get_field(candidate_years_experience, "confidence"))
    )

    return (
        score,
        [
            FeatureMatch(
                bucket="years_experience",
                job_value=str(min_years),
                candidate_value=str(candidate_years),
                score=round(score, 6),
            )
        ],
        [],
    )


def evaluate_job_match(
    candidate_profile: CandidateProfileRootLike,
    job: JobLike,
) -> RankingResult:
    profile = candidate_profile.profile

    bucket_scores = _empty_bucket_scores()
    matched_features: list[FeatureMatch] = []
    missing_features: list[FeatureGap] = []

    feature_buckets: tuple[tuple[BucketName, Iterable[object], Iterable[object]], ...] = (
        ("skills", job.skills, getattr(profile, "skills", [])),
        ("protocols", job.protocols, getattr(profile, "protocols", [])),
        ("standards", job.standards, getattr(profile, "standards", [])),
        ("domains", job.domains, getattr(profile, "domains", [])),
    )

    for bucket_name, job_items, candidate_items in feature_buckets:
        bucket_score, matches, gaps = _score_feature_bucket(
            bucket=bucket_name,
            job_items=job_items,
            candidate_items=candidate_items,
        )
        bucket_scores[bucket_name] = round(bucket_score, 6)
        matched_features.extend(matches)
        missing_features.extend(gaps)

    language_score, language_matches, language_gaps = _score_language_bucket(
        job_items=job.languages,
        candidate_items=getattr(profile, "languages", []),
    )
    bucket_scores["languages"] = round(language_score, 6)
    matched_features.extend(language_matches)
    missing_features.extend(language_gaps)

    seniority_score, seniority_matches, seniority_gaps = _score_seniority(
        job_seniority=job.seniority,
        candidate_seniority=getattr(profile, "seniority", None),
    )
    bucket_scores["seniority"] = round(seniority_score, 6)
    matched_features.extend(seniority_matches)
    missing_features.extend(seniority_gaps)

    years_score, years_matches, years_gaps = _score_years_experience(
        job_years_requirement=job.years_experience_requirement,
        candidate_years_experience=getattr(profile, "years_experience_total", None),
    )
    bucket_scores["years_experience"] = round(years_score, 6)
    matched_features.extend(years_matches)
    missing_features.extend(years_gaps)

    final_score = sum(
        BUCKET_WEIGHTS[bucket] * bucket_scores[bucket]
        for bucket in BUCKET_WEIGHTS
    )

    return RankingResult(
        job_id=job.job_id,
        candidate_id=candidate_profile.candidate_id,
        score=round(final_score, 6),
        bucket_scores=BucketScore(**bucket_scores),
        matched_features=matched_features,
        missing_features=missing_features,
    )
