from __future__ import annotations
from copy import deepcopy

from clients.candidate_profiling.candidate_profiling_model import (
    CandidateProfile,
    CandidateProfileRecord,
)
from shared.profiling_model import RoleTitles


primary_role_title = "software engineer"
alternatives = ["backend engineer", "full stack developer"]
confidence = 0.95
evidence = ["cv title", "cv description"]

role_titles = RoleTitles(
    primary=primary_role_title,
    alternatives=alternatives,
    confidence=confidence,
    evidence=evidence,
)

education_min_level = "bachelor"
education_accepted_fields = ["computer science"]
education_confidence = 0.9
education_evidence = ["education section"]

education_json = {
    "min_level": education_min_level,
    "accepted_fields": list(education_accepted_fields),
    "confidence": education_confidence,
    "evidence": list(education_evidence),
}

experience_min_years = 5
experience_seniority_band = "senior"
experience_confidence = 0.9
experience_evidence = ["work experience summary"]

experience_json = {
    "min_years": experience_min_years,
    "seniority_band": experience_seniority_band,
    "confidence": experience_confidence,
    "evidence": list(experience_evidence),
}

technical_core_feature_name = "python"
technical_core_feature_strength = "core"
technical_core_feature_confidence = 0.95
technical_core_feature_evidence = ["skills section"]

technical_core_feature = {
    "name": technical_core_feature_name,
    "strength": technical_core_feature_strength,
    "confidence": technical_core_feature_confidence,
    "evidence": list(technical_core_feature_evidence),
}

technology_name = "postgresql"
technology_strength = "strong"
technology_confidence = 0.9
technology_evidence = ["project history"]

technology = {
    "name": technology_name,
    "strength": technology_strength,
    "confidence": technology_confidence,
    "evidence": list(technology_evidence),
}

technical_experience_json = {
    "technical_core_features": [deepcopy(technical_core_feature)],
    "technologies": [deepcopy(technology)],
}

domain_background_name = "healthcare"
domain_background_strength = "secondary"
domain_background_confidence = 0.8
domain_background_evidence = ["domain experience"]

domain_background = {
    "name": domain_background_name,
    "strength": domain_background_strength,
    "confidence": domain_background_confidence,
    "evidence": list(domain_background_evidence),
}

domain_background_json = [
    deepcopy(domain_background)
]

language_name = "english"
language_strength = "strong"
language_confidence = 1.0
language_evidence = ["cv language section"]

language = {
    "name": language_name,
    "strength": language_strength,
    "confidence": language_confidence,
    "evidence": list(language_evidence),
}

languages_json = [
    deepcopy(language)
]

candidate_profile_record = CandidateProfileRecord(
    id=1,
    uploaded_cv_id=1,
    role_title_primary=primary_role_title,
    role_titles_json={
        "primary": role_titles.primary,
        "alternatives": list(role_titles.alternatives),
        "confidence": role_titles.confidence,
        "evidence": list(role_titles.evidence),
    },
    education_json=deepcopy(education_json),
    experience_json=deepcopy(experience_json),
    technical_experience_json=deepcopy(technical_experience_json),
    languages_json=deepcopy(languages_json),
    domain_background_json=deepcopy(domain_background_json),
)


def make_candidate_profile(
    *,
    primary_role_title: str | None = None,
    alternatives: list[str] | None = None,
    confidence: float | None = None,
    evidence: list[str] | None = None,
) -> CandidateProfile:
    resolved_primary_role_title = primary_role_title or role_titles.primary
    resolved_alternatives = (
        alternatives
        if alternatives is not None
        else role_titles.alternatives
    )
    resolved_confidence = (
        confidence if confidence is not None else role_titles.confidence
    )
    resolved_evidence = (
        evidence if evidence is not None else list(role_titles.evidence)
    )

    resolved_role_titles = RoleTitles(
        primary=resolved_primary_role_title,
        alternatives=resolved_alternatives,
        confidence=resolved_confidence,
        evidence=resolved_evidence,
    )

    return CandidateProfile(role_titles=resolved_role_titles)


def make_candidate_profile_record(
    *,
    id: int | None = None,
    uploaded_cv_id: int | None = None,
    role_title_primary: str | None = None,
    role_titles_json: dict[str, object] | None = None,
    education_json: dict[str, object] | None = None,
    experience_json: dict[str, object] | None = None,
    technical_experience_json: dict[str, object] | None = None,
    domain_background_json: list[dict[str, object]] | None = None,
    ) -> CandidateProfileRecord:
    profile_record = candidate_profile_record
    return CandidateProfileRecord(
        id=profile_record.id if id is None else id,
        uploaded_cv_id=(
            profile_record.uploaded_cv_id
            if uploaded_cv_id is None
            else uploaded_cv_id
        ),
        role_title_primary=(
            profile_record.role_title_primary
            if role_title_primary is None
            else role_title_primary
        ),
        role_titles_json=(
            deepcopy(profile_record.role_titles_json)
            if role_titles_json is None
            else role_titles_json
        ),
        education_json=(
            deepcopy(profile_record.education_json)
            if education_json is None
            else education_json
        ),
        experience_json=(
            deepcopy(profile_record.experience_json)
            if experience_json is None
            else experience_json
        ),
        technical_experience_json=(
            deepcopy(profile_record.technical_experience_json)
            if technical_experience_json is None
            else technical_experience_json
        ),
        domain_background_json=(
            deepcopy(profile_record.domain_background_json)
            if domain_background_json is None
            else domain_background_json
        ),
    )


def make_candidate_profile_endpoint_record(
    *,
    uploaded_cv_id: int = 501,
) -> CandidateProfileRecord:
    record = make_candidate_profile_record(
        uploaded_cv_id=uploaded_cv_id,
        role_titles_json={
            "primary": role_titles.primary,
            "alternatives": list(role_titles.alternatives),
            "confidence": role_titles.confidence,
            "evidence": list(role_titles.evidence),
        },
        education_json=deepcopy(education_json),
        experience_json=deepcopy(experience_json),
        technical_experience_json=deepcopy(technical_experience_json),
        domain_background_json=deepcopy(domain_background_json),
    )
    record.languages_json = deepcopy(languages_json)
    return record
