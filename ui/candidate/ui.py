from __future__ import annotations

from dataclasses import asdict
from typing import Any

import streamlit as st

from ui.shared.profile_types import SupportedCandidateProfile


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _csv(items: list[str] | None) -> str:
    if not items:
        return ""
    return ", ".join(items)


def _lines(items: list[str] | None) -> str:
    if not items:
        return ""
    return "\n".join(items)


def _feature_lines(items: list[dict[str, Any]] | None) -> str:
    if not items:
        return ""

    lines: list[str] = []
    for item in items:
        name = _text(item.get("name"))
        strength = _text(item.get("strength"))
        confidence = _text(item.get("confidence"))

        parts = [part for part in [name, strength, confidence] if part]
        if parts:
            lines.append(" | ".join(parts))

    return "\n".join(lines)


def _evidence_block(
    title: str,
    evidence: list[str] | None,
    *,
    key: str,
) -> None:
    st.text_area(
        title,
        value=_lines(evidence),
        height=110,
        disabled=True,
        key=key,
    )


def render_candidate_profile(profile: SupportedCandidateProfile) -> None:
    payload = asdict(profile)

    role_titles = payload.get("role_titles", {})
    education = payload.get("education", {})
    experience = payload.get("experience", {})
    technical_experience = payload.get("technical_experience", {})
    languages = payload.get("languages", [])
    domain_background = payload.get("domain_background", [])

    st.subheader("Candidate Profile")

    with st.container(border=True):
        st.markdown("#### Role Titles")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Primary role",
                value=_text(role_titles.get("primary")),
                disabled=True,
                key="role_titles_primary",
            )
        with col2:
            st.text_input(
                "Alternatives",
                value=_csv(role_titles.get("alternatives")),
                disabled=True,
                key="role_titles_alternatives",
            )

        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Confidence",
                value=_text(role_titles.get("confidence")),
                disabled=True,
                key="role_titles_confidence",
            )
        with col2:
            st.empty()

        _evidence_block(
            "Evidence",
            role_titles.get("evidence"),
            key="role_titles_evidence",
        )

    with st.container(border=True):
        st.markdown("#### Education")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Minimum level",
                value=_text(education.get("min_level")),
                disabled=True,
                key="education_min_level",
            )
        with col2:
            st.text_input(
                "Accepted fields",
                value=_csv(education.get("accepted_fields")),
                disabled=True,
                key="education_accepted_fields",
            )

        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Confidence",
                value=_text(education.get("confidence")),
                disabled=True,
                key="education_confidence",
            )
        with col2:
            st.empty()

        _evidence_block(
            "Evidence",
            education.get("evidence"),
            key="education_evidence",
        )

    with st.container(border=True):
        st.markdown("#### Experience")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Minimum years",
                value=_text(experience.get("min_years")),
                disabled=True,
                key="experience_min_years",
            )
        with col2:
            st.text_input(
                "Seniority band",
                value=_text(experience.get("seniority_band")),
                disabled=True,
                key="experience_seniority_band",
            )

        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Confidence",
                value=_text(experience.get("confidence")),
                disabled=True,
                key="experience_confidence",
            )
        with col2:
            st.empty()

        _evidence_block(
            "Evidence",
            experience.get("evidence"),
            key="experience_evidence",
        )

    with st.container(border=True):
        st.markdown("#### Technical Experience")
        st.text_area(
            "Core features",
            value=_feature_lines(technical_experience.get("technical_core_features")),
            height=150,
            disabled=True,
            key="technical_experience_core_features",
        )
        st.text_area(
            "Technologies",
            value=_feature_lines(technical_experience.get("technologies")),
            height=150,
            disabled=True,
            key="technical_experience_technologies",
        )
        st.text_input(
            "Confidence",
            value=_text(technical_experience.get("confidence")),
            disabled=True,
            key="technical_experience_confidence",
        )
        _evidence_block(
            "Evidence",
            technical_experience.get("evidence"),
            key="technical_experience_evidence",
        )

    with st.container(border=True):
        st.markdown("#### Languages")
        st.text_area(
            "Languages",
            value=_feature_lines(languages),
            height=120,
            disabled=True,
            key="languages",
        )

    with st.container(border=True):
        st.markdown("#### Domain Background")
        st.text_area(
            "Domain background",
            value=_feature_lines(domain_background),
            height=120,
            disabled=True,
            key="domain_background",
        )
