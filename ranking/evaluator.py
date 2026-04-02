from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Protocol


class EvaluatableJob(Protocol):
    title: str | None
    description_text: str | None
    languages: list[object] | None
    required_languages: list[str] | None
    restrictions: list[object] | None
    years_experience_requirement: object | None
    min_years_experience: int | None


@dataclass
class HardFilterPolicy:
    excluded_job_types: set[str]
    excluded_required_languages: set[str]
    require_export_control_clearance_absent: bool
    max_min_years_experience: int | None


DEFAULT_HARD_FILTER_POLICY = HardFilterPolicy(
    excluded_job_types={"internship", "thesis", "graduation_assignment"},
    excluded_required_languages={"dutch"},
    require_export_control_clearance_absent=True,
    max_min_years_experience=7,
)

EXCLUDED_JOB_TYPE_PATTERNS = {
    "internship": re.compile(r"(?<![a-z0-9])internships?(?![a-z0-9])"),
    "thesis": re.compile(r"(?<![a-z0-9])thesis(?![a-z0-9])"),
    "graduation_assignment": re.compile(
        r"(?<![a-z0-9])graduation assignments?(?![a-z0-9])"
    ),
}
EXPORT_CONTROL_CLEARANCE_MARKERS = (
    "export control",
    "security clearance",
)


KEEP_KEYWORDS = [
    "c++",
    "python",
    "software engineer",
    "software designer",
    "embedded",
    "firmware",
    "control",
    "controls",
    "machine control",
    "real-time",
    "rtos",
    "linux",
    "system software",
    "systems engineering",
    "mechatronics software",
    "automation",
    "robotics",
    "computer vision",
    "algorithm",
    "performance",
    "high-tech",
    "signal processing",
    "image processing",
    "ml",
    "machine learning",
    "inference",
]

LOW_SIGNAL_DESCRIPTION_KEYWORDS = {
    "control",
    "controls",
    "performance",
    "high-tech",
}


def compile_keyword_patterns(keywords: Iterable[str]) -> tuple[re.Pattern[str], ...]:
    patterns: list[re.Pattern[str]] = []
    for keyword in keywords:
        escaped = re.escape(keyword.lower())
        patterns.append(re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"))
    return tuple(patterns)


KEEP_PATTERNS = compile_keyword_patterns(KEEP_KEYWORDS)


def matched_keywords(
    text: str,
    keywords: list[str],
    patterns: Iterable[re.Pattern[str]],
) -> list[str]:
    normalized_text = text.lower()
    return [
        keyword
        for keyword, pattern in zip(keywords, patterns)
        if pattern.search(normalized_text)
    ]


def detect_job_types(title: str) -> list[str]:
    normalized_title = title.lower()
    return [
        job_type
        for job_type, pattern in EXCLUDED_JOB_TYPE_PATTERNS.items()
        if pattern.search(normalized_title)
    ]


def has_export_control_or_clearance_restriction(restrictions: Iterable[str]) -> bool:
    return any(
        marker in restriction.lower()
        for restriction in restrictions
        for marker in EXPORT_CONTROL_CLEARANCE_MARKERS
    )


def _get_field(value: object, field_name: str) -> object | None:
    if isinstance(value, dict):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _required_languages(job: EvaluatableJob) -> list[str]:
    languages = getattr(job, "languages", None)
    if languages is not None:
        extracted_languages: list[str] = []
        for language in languages:
            if _get_field(language, "requirement_level") != "required":
                continue
            name = _get_field(language, "name")
            if isinstance(name, str):
                extracted_languages.append(name.lower())
        return extracted_languages

    return [
        language.lower()
        for language in (getattr(job, "required_languages", None) or [])
    ]


def _restriction_values(job: EvaluatableJob) -> list[str]:
    raw_restrictions = getattr(job, "restrictions", None) or []
    values: list[str] = []
    for restriction in raw_restrictions:
        if isinstance(restriction, str):
            values.append(restriction)
            continue

        value = _get_field(restriction, "value")
        if isinstance(value, str):
            values.append(value)
    return values


def _min_years_experience(job: EvaluatableJob) -> int | None:
    years_requirement = getattr(job, "years_experience_requirement", None)
    if years_requirement is not None:
        min_years = _get_field(years_requirement, "min_years")
        if isinstance(min_years, int) or min_years is None:
            return min_years

    legacy_value = getattr(job, "min_years_experience", None)
    return (
        legacy_value if isinstance(legacy_value, int) or legacy_value is None else None
    )


def evaluate_hard_filters(
    job: EvaluatableJob,
    policy: HardFilterPolicy = DEFAULT_HARD_FILTER_POLICY,
) -> dict | None:
    title = job.title or ""
    matched_job_types = [
        job_type
        for job_type in detect_job_types(title)
        if job_type in policy.excluded_job_types
    ]
    if matched_job_types:
        return {
            "decision": "skip",
            "reason": "hard_filter_exclude_job_type",
            "skip_hits": [f"job_type:{job_type}" for job_type in matched_job_types],
            "title_hits": [],
            "description_hits": [],
        }

    matched_languages = sorted(
        set(_required_languages(job)) & policy.excluded_required_languages
    )
    if matched_languages:
        return {
            "decision": "skip",
            "reason": "hard_filter_required_language",
            "skip_hits": [
                f"required_language:{language}" for language in matched_languages
            ],
            "title_hits": [],
            "description_hits": [],
        }

    restrictions = _restriction_values(job)
    if (
        policy.require_export_control_clearance_absent
        and has_export_control_or_clearance_restriction(restrictions)
    ):
        return {
            "decision": "skip",
            "reason": "hard_filter_export_control_clearance",
            "skip_hits": ["restriction:export_control_or_security_clearance"],
            "title_hits": [],
            "description_hits": [],
        }

    min_years_experience = _min_years_experience(job)
    if (
        policy.max_min_years_experience is not None
        and min_years_experience is not None
        and min_years_experience > policy.max_min_years_experience
    ):
        return {
            "decision": "skip",
            "reason": "hard_filter_min_years_experience",
            "skip_hits": [f"min_years_experience:{min_years_experience}"],
            "title_hits": [],
            "description_hits": [],
        }

    return None


def evaluate_job(
    job: EvaluatableJob,
    hard_filter_policy: HardFilterPolicy = DEFAULT_HARD_FILTER_POLICY,
) -> dict:
    title = job.title or ""
    description = job.description_text or ""

    hard_filter_evaluation = evaluate_hard_filters(job, hard_filter_policy)
    if hard_filter_evaluation is not None:
        return hard_filter_evaluation

    title_hits = matched_keywords(title, KEEP_KEYWORDS, KEEP_PATTERNS)
    if title_hits:
        return {
            "decision": "keep",
            "reason": "title_keep_match",
            "skip_hits": [],
            "title_hits": title_hits,
            "description_hits": [],
        }

    description_hits_all = matched_keywords(description, KEEP_KEYWORDS, KEEP_PATTERNS)
    description_hits = [
        keyword
        for keyword in description_hits_all
        if keyword not in LOW_SIGNAL_DESCRIPTION_KEYWORDS
    ]

    if len(description_hits) >= 2:
        return {
            "decision": "keep",
            "reason": "description_keep_match",
            "skip_hits": [],
            "title_hits": [],
            "description_hits": description_hits,
        }

    return {
        "decision": "skip",
        "reason": "insufficient_keep_signal",
        "skip_hits": [],
        "title_hits": [],
        "description_hits": description_hits,
    }
