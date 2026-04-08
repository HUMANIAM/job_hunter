from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Protocol

from shared.normalizer import normalize_taxonomy_name, normalize_text


BucketName = Literal[
    "skills",
    "languages",
    "protocols",
    "standards",
    "domains",
    "seniority",
    "years_experience",
]

DecisionStage = Literal["candidate_must_have", "job_must_have", "ranking"]
RankingStatus = Literal["match", "mismatch"]

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
class RejectionReason:
    stage: DecisionStage
    bucket: str
    reason: str
    expected: str | None = None
    actual: str | None = None


@dataclass
class RankingResult:
    job_id: str
    candidate_id: str
    score: float
    status: RankingStatus
    decision_stage: DecisionStage
    bucket_scores: BucketScore
    matched_features: list[FeatureMatch] = field(default_factory=list)
    missing_features: list[FeatureGap] = field(default_factory=list)
    rejection_reasons: list[RejectionReason] = field(default_factory=list)


@dataclass
class DerivedJobConstraint:
    kind: str
    bucket: str
    value: str | None
    min_years: int | None
    confidence: float


def _get_field(value: object, field_name: str) -> object | None:
    if isinstance(value, dict):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _normalize_name(value: object | None) -> str:
    if value is None:
        return ""
    return normalize_taxonomy_name(str(value))


def _normalize_label(value: object | None) -> str | None:
    normalized = normalize_text(str(value)) if value is not None else ""
    return normalized or None


def _contains_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left in right or right in left


def _matches_any_constraint(value: str, constraints: list[str]) -> bool:
    return any(_contains_match(value, constraint) for constraint in constraints)


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


def _coerce_string_list(value: object | None) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized_values: list[str] = []
    for item in value:
        normalized = normalize_text(str(item))
        if normalized:
            normalized_values.append(normalized)
    return list(dict.fromkeys(normalized_values))


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


def _build_candidate_indexes(profile: Any) -> dict[str, dict[str, object]]:
    return {
        "skills": _candidate_feature_index(getattr(profile, "skills", [])),
        "protocols": _candidate_feature_index(getattr(profile, "protocols", [])),
        "standards": _candidate_feature_index(getattr(profile, "standards", [])),
        "domains": _candidate_feature_index(getattr(profile, "domains", [])),
        "languages": _candidate_language_index(getattr(profile, "languages", [])),
    }


def _seniority_satisfies(job_value: object | None, candidate_value: object | None) -> bool:
    normalized_job_value = _normalize_name(job_value)
    normalized_candidate_value = _normalize_name(candidate_value)

    if normalized_job_value not in SENIORITY_WEIGHTS:
        return True
    if normalized_candidate_value not in SENIORITY_WEIGHTS:
        return False
    return SENIORITY_WEIGHTS[normalized_candidate_value] >= SENIORITY_WEIGHTS[normalized_job_value]


def _required_feature_constraints_from_bucket(
    bucket: str,
    items: Iterable[object],
) -> list[DerivedJobConstraint]:
    constraints: list[DerivedJobConstraint] = []
    for item in items:
        if _normalize_name(_get_field(item, "requirement_level")) != "required":
            continue
        name = _normalize_name(_get_field(item, "name"))
        if not name:
            continue
        constraints.append(
            DerivedJobConstraint(
                kind="feature",
                bucket=bucket,
                value=name,
                min_years=None,
                confidence=_safe_confidence(_get_field(item, "confidence")),
            )
        )
    return constraints


def _derive_job_constraints(job: JobLike) -> list[DerivedJobConstraint]:
    constraints: list[DerivedJobConstraint] = []
    seen_keys: set[tuple[str, str, str | None, int | None]] = set()

    def append_constraint(constraint: DerivedJobConstraint) -> None:
        key = (
            constraint.kind,
            constraint.bucket,
            constraint.value,
            constraint.min_years,
        )
        if key in seen_keys:
            return
        seen_keys.add(key)
        constraints.append(constraint)

    for bucket_name in ("skills", "languages", "protocols", "standards", "domains"):
        for constraint in _required_feature_constraints_from_bucket(
            bucket_name,
            _get_field(job, bucket_name) or [],
        ):
            append_constraint(constraint)

    seniority_value = _normalize_name(_get_field(_get_field(job, "seniority"), "value"))
    if seniority_value:
        append_constraint(
            DerivedJobConstraint(
                kind="seniority",
                bucket="seniority",
                value=seniority_value,
                min_years=None,
                confidence=_safe_confidence(
                    _get_field(_get_field(job, "seniority"), "confidence")
                ),
            )
        )

    years_requirement = _get_field(job, "years_experience_requirement")
    min_years = _get_field(years_requirement, "min_years")
    requirement_level = _normalize_name(_get_field(years_requirement, "requirement_level"))
    if isinstance(min_years, int) and min_years > 0 and requirement_level != "preferred":
        append_constraint(
            DerivedJobConstraint(
                kind="years_experience",
                bucket="years_experience",
                value=None,
                min_years=min_years,
                confidence=_safe_confidence(_get_field(years_requirement, "confidence")),
            )
        )

    return constraints


def _job_constraints(job: JobLike) -> list[DerivedJobConstraint]:
    raw_constraints = _get_field(job, "job_constraints")
    if raw_constraints is None or raw_constraints == []:
        return _derive_job_constraints(job)

    constraints: list[DerivedJobConstraint] = []
    for constraint in raw_constraints:
        constraints.append(
            DerivedJobConstraint(
                kind=_normalize_name(_get_field(constraint, "kind")),
                bucket=_normalize_name(_get_field(constraint, "bucket")),
                value=_normalize_name(_get_field(constraint, "value")),
                min_years=(
                    _get_field(constraint, "min_years")
                    if isinstance(_get_field(constraint, "min_years"), int)
                    else None
                ),
                confidence=_safe_confidence(_get_field(constraint, "confidence")),
            )
        )
    return constraints


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
            _job_requirement_weight(str(requirement_level) if requirement_level is not None else None)
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
        numerator += job_importance * candidate_quality

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

        requirement_level = _get_field(job_item, "requirement_level")
        job_importance = (
            _job_requirement_weight(str(requirement_level) if requirement_level is not None else None)
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
        numerator += job_importance * candidate_quality

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
    if job_value not in SENIORITY_WEIGHTS:
        return 0.0, [], []
    if candidate_value not in SENIORITY_WEIGHTS:
        return 0.0, [], [FeatureGap(bucket="seniority", job_value=job_value)]

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

    score = (
        min(candidate_years / min_years, 1.0)
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


def _candidate_must_have_reasons(
    candidate_profile: CandidateProfileRootLike,
    job: JobLike,
) -> list[RejectionReason]:
    profile = candidate_profile.profile
    constraints = getattr(profile, "candidate_constraints", None)
    if constraints is None:
        return []

    reasons: list[RejectionReason] = []
    job_location = _normalize_name(_get_field(job, "location"))
    job_workplace_type = _normalize_name(
        _get_field(job, "remote_policy") or _get_field(job, "workplace_type")
    )

    preferred_locations = [
        _normalize_name(value)
        for value in _coerce_string_list(_get_field(constraints, "preferred_locations"))
    ]
    if preferred_locations and not job_location:
        reasons.append(
            RejectionReason(
                stage="candidate_must_have",
                bucket="location",
                reason="preferred_location_unknown",
                expected=", ".join(preferred_locations),
                actual=None,
            )
        )
    elif preferred_locations and not _matches_any_constraint(
        job_location,
        preferred_locations,
    ):
        reasons.append(
            RejectionReason(
                stage="candidate_must_have",
                bucket="location",
                reason="preferred_location_not_matched",
                expected=", ".join(preferred_locations),
                actual=_normalize_label(_get_field(job, "location")),
            )
        )

    excluded_locations = [
        _normalize_name(value)
        for value in _coerce_string_list(_get_field(constraints, "excluded_locations"))
    ]
    if job_location and _matches_any_constraint(job_location, excluded_locations):
        reasons.append(
            RejectionReason(
                stage="candidate_must_have",
                bucket="location",
                reason="excluded_location_matched",
                expected=_normalize_label(_get_field(job, "location")),
                actual=_normalize_label(_get_field(job, "location")),
            )
        )

    preferred_workplace_types = [
        _normalize_name(value)
        for value in _coerce_string_list(_get_field(constraints, "preferred_workplace_types"))
    ]
    if preferred_workplace_types and not job_workplace_type:
        reasons.append(
            RejectionReason(
                stage="candidate_must_have",
                bucket="workplace_type",
                reason="preferred_workplace_type_unknown",
                expected=", ".join(preferred_workplace_types),
                actual=None,
            )
        )
    elif preferred_workplace_types and job_workplace_type not in preferred_workplace_types:
        reasons.append(
            RejectionReason(
                stage="candidate_must_have",
                bucket="workplace_type",
                reason="preferred_workplace_type_not_matched",
                expected=", ".join(preferred_workplace_types),
                actual=(
                    _normalize_label(_get_field(job, "remote_policy"))
                    or _normalize_label(_get_field(job, "workplace_type"))
                ),
            )
        )

    excluded_workplace_types = [
        _normalize_name(value)
        for value in _coerce_string_list(_get_field(constraints, "excluded_workplace_types"))
    ]
    if job_workplace_type and job_workplace_type in excluded_workplace_types:
        reasons.append(
            RejectionReason(
                stage="candidate_must_have",
                bucket="workplace_type",
                reason="excluded_workplace_type_matched",
                expected=(
                    _normalize_label(_get_field(job, "remote_policy"))
                    or _normalize_label(_get_field(job, "workplace_type"))
                ),
                actual=(
                    _normalize_label(_get_field(job, "remote_policy"))
                    or _normalize_label(_get_field(job, "workplace_type"))
                ),
            )
        )

    requires_visa_sponsorship = _get_field(constraints, "requires_visa_sponsorship")
    avoid_export_control_roles = _get_field(constraints, "avoid_export_control_roles")
    for constraint in _job_constraints(job):
        if constraint.kind != "restriction" or not constraint.value:
            continue
        if requires_visa_sponsorship is True and constraint.value in {
            "work_authorization",
            "citizenship",
        }:
            reasons.append(
                RejectionReason(
                    stage="candidate_must_have",
                    bucket="restrictions",
                    reason="candidate_requires_visa_sponsorship",
                    expected=constraint.value,
                    actual="candidate requires visa sponsorship",
                )
            )
        if avoid_export_control_roles is True and constraint.value == "controlled_technology":
            reasons.append(
                RejectionReason(
                    stage="candidate_must_have",
                    bucket="restrictions",
                    reason="candidate_avoids_export_control_roles",
                    expected=constraint.value,
                    actual="candidate avoids export-control roles",
                )
            )

    return reasons


def _job_restriction_reason(
    *,
    constraint_value: str,
    candidate_constraints: object | None,
) -> RejectionReason | None:
    requires_visa_sponsorship = _get_field(candidate_constraints, "requires_visa_sponsorship")
    avoid_export_control_roles = _get_field(
        candidate_constraints,
        "avoid_export_control_roles",
    )

    if constraint_value == "work_authorization":
        if requires_visa_sponsorship is False:
            return None
        return RejectionReason(
            stage="job_must_have",
            bucket="restrictions",
            reason=(
                "work_authorization_unknown"
                if requires_visa_sponsorship is None
                else "work_authorization_not_satisfied"
            ),
            expected="work_authorization",
            actual=(
                None
                if requires_visa_sponsorship is None
                else "candidate requires visa sponsorship"
            ),
        )

    if constraint_value == "citizenship":
        return RejectionReason(
            stage="job_must_have",
            bucket="restrictions",
            reason="citizenship_eligibility_unknown",
            expected="citizenship",
            actual=None,
        )

    if constraint_value == "controlled_technology":
        if avoid_export_control_roles is True:
            return RejectionReason(
                stage="job_must_have",
                bucket="restrictions",
                reason="export_control_not_satisfied",
                expected="controlled_technology",
                actual="candidate avoids export-control roles",
            )
        return RejectionReason(
            stage="job_must_have",
            bucket="restrictions",
            reason="legal_eligibility_unknown",
            expected="controlled_technology",
            actual=None,
        )

    return RejectionReason(
        stage="job_must_have",
        bucket="restrictions",
        reason="restriction_eligibility_unknown",
        expected=constraint_value,
        actual=None,
    )


def _job_must_have_reasons(
    candidate_profile: CandidateProfileRootLike,
    job: JobLike,
) -> list[RejectionReason]:
    profile = candidate_profile.profile
    candidate_constraints = getattr(profile, "candidate_constraints", None)
    candidate_indexes = _build_candidate_indexes(profile)
    reasons: list[RejectionReason] = []

    for constraint in _job_constraints(job):
        if constraint.kind == "feature" and constraint.value:
            candidate_item = candidate_indexes.get(constraint.bucket, {}).get(constraint.value)
            if candidate_item is None:
                reasons.append(
                    RejectionReason(
                        stage="job_must_have",
                        bucket=constraint.bucket,
                        reason="required_feature_missing",
                        expected=constraint.value,
                        actual=None,
                    )
                )
            continue

        if constraint.kind == "seniority" and constraint.value:
            candidate_seniority = _get_field(getattr(profile, "seniority", None), "value")
            if not _seniority_satisfies(constraint.value, candidate_seniority):
                reasons.append(
                    RejectionReason(
                        stage="job_must_have",
                        bucket="seniority",
                        reason="seniority_not_satisfied",
                        expected=constraint.value,
                        actual=_normalize_label(candidate_seniority),
                    )
                )
            continue

        if constraint.kind == "years_experience" and constraint.min_years is not None:
            candidate_years = _get_field(
                getattr(profile, "years_experience_total", None),
                "value",
            )
            if not isinstance(candidate_years, int) or candidate_years < constraint.min_years:
                reasons.append(
                    RejectionReason(
                        stage="job_must_have",
                        bucket="years_experience",
                        reason="years_experience_not_satisfied",
                        expected=str(constraint.min_years),
                        actual=(
                            str(candidate_years)
                            if isinstance(candidate_years, int)
                            else None
                        ),
                    )
                )
            continue

        if constraint.kind == "restriction" and constraint.value:
            restriction_reason = _job_restriction_reason(
                constraint_value=constraint.value,
                candidate_constraints=candidate_constraints,
            )
            if restriction_reason is not None:
                reasons.append(restriction_reason)

    return reasons


def _mismatch_result(
    *,
    candidate_profile: CandidateProfileRootLike,
    job: JobLike,
    stage: DecisionStage,
    rejection_reasons: list[RejectionReason],
) -> RankingResult:
    return RankingResult(
        job_id=job.job_id,
        candidate_id=candidate_profile.candidate_id,
        score=0.0,
        status="mismatch",
        decision_stage=stage,
        bucket_scores=BucketScore(**_empty_bucket_scores()),
        matched_features=[],
        missing_features=[],
        rejection_reasons=rejection_reasons,
    )


def evaluate_job_match(
    candidate_profile: CandidateProfileRootLike,
    job: JobLike,
    *,
    match_score_threshold: float = 0.6,
) -> RankingResult:
    candidate_reasons = _candidate_must_have_reasons(candidate_profile, job)
    if candidate_reasons:
        return _mismatch_result(
            candidate_profile=candidate_profile,
            job=job,
            stage="candidate_must_have",
            rejection_reasons=candidate_reasons,
        )

    job_reasons = _job_must_have_reasons(candidate_profile, job)
    if job_reasons:
        return _mismatch_result(
            candidate_profile=candidate_profile,
            job=job,
            stage="job_must_have",
            rejection_reasons=job_reasons,
        )

    profile = candidate_profile.profile
    bucket_scores = _empty_bucket_scores()
    matched_features: list[FeatureMatch] = []
    missing_features: list[FeatureGap] = []

    for bucket_name, job_items, candidate_items in (
        ("skills", job.skills, getattr(profile, "skills", [])),
        ("protocols", job.protocols, getattr(profile, "protocols", [])),
        ("standards", job.standards, getattr(profile, "standards", [])),
        ("domains", job.domains, getattr(profile, "domains", [])),
    ):
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

    final_score = round(
        sum(BUCKET_WEIGHTS[bucket] * bucket_scores[bucket] for bucket in BUCKET_WEIGHTS),
        6,
    )

    rejection_reasons: list[RejectionReason] = []
    status: RankingStatus = "match"
    if final_score < match_score_threshold:
        status = "mismatch"
        rejection_reasons.append(
            RejectionReason(
                stage="ranking",
                bucket="score",
                reason="score_below_threshold",
                expected=f">={match_score_threshold:.3f}",
                actual=f"{final_score:.3f}",
            )
        )

    return RankingResult(
        job_id=job.job_id,
        candidate_id=candidate_profile.candidate_id,
        score=final_score,
        status=status,
        decision_stage="ranking",
        bucket_scores=BucketScore(**bucket_scores),
        matched_features=matched_features,
        missing_features=missing_features,
        rejection_reasons=rejection_reasons,
    )
