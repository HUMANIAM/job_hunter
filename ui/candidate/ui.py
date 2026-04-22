from __future__ import annotations

from dataclasses import asdict
from typing import Any

import streamlit as st

from ui.shared.profile_types import SupportedCandidateProfile


def _text(value: Any) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"


def _csv(items: list[str] | None) -> str:
    if not items:
        return "-"
    values = [str(item).strip() for item in items if str(item).strip()]
    return ", ".join(values) if values else "-"


def _feature_text(item: dict[str, Any]) -> str:
    name = str(item.get("name") or "").strip()
    strength = str(item.get("strength") or "").strip()

    parts = [part for part in [name, strength] if part]
    return " · ".join(parts) if parts else "-"


def _render_field(label: str, value: Any) -> None:
    st.caption(label)
    st.markdown(_text(value))


def _render_feature_list(items: list[dict[str, Any]] | None, empty_text: str) -> None:
    if not items:
        st.markdown(empty_text)
        return

    for item in items:
        st.markdown(f"- {_feature_text(item)}")


def _render_evidence(items: list[str] | None, key: str) -> None:
    if not items:
        return

    with st.expander("Evidence", expanded=False):
        for index, item in enumerate(items, start=1):
            st.markdown(f"{index}. {item}", help=key)


def render_candidate_profile(profile: SupportedCandidateProfile) -> None:
    payload = asdict(profile)

    role_titles = payload.get("role_titles", {})
    education = payload.get("education", {})
    experience = payload.get("experience", {})
    technical_experience = payload.get("technical_experience", {})
    languages = payload.get("languages", [])
    domain_background = payload.get("domain_background", [])

    st.subheader("Candidate Profile", divider="rainbow")

    with st.container(border=True):
        st.markdown("#### Role Titles")
        col1, col2 = st.columns(2)
        with col1:
            _render_field("Primary role", role_titles.get("primary"))
        with col2:
            _render_field("Alternatives", _csv(role_titles.get("alternatives")))
        _render_field("Confidence", role_titles.get("confidence"))
        _render_evidence(role_titles.get("evidence"), "role_titles_evidence")

    with st.container(border=True):
        st.markdown("#### Education")
        col1, col2 = st.columns(2)
        with col1:
            _render_field("Minimum level", education.get("min_level"))
        with col2:
            _render_field("Accepted fields", _csv(education.get("accepted_fields")))
        _render_field("Confidence", education.get("confidence"))
        _render_evidence(education.get("evidence"), "education_evidence")

    with st.container(border=True):
        st.markdown("#### Experience")
        col1, col2 = st.columns(2)
        with col1:
            _render_field("Minimum years", experience.get("min_years"))
        with col2:
            _render_field("Seniority band", experience.get("seniority_band"))
        _render_field("Confidence", experience.get("confidence"))
        _render_evidence(experience.get("evidence"), "experience_evidence")

    with st.container(border=True):
        st.markdown("#### Technical Experience")
        st.caption("Core features")
        _render_feature_list(
            technical_experience.get("technical_core_features"),
            "No core features",
        )
        st.divider()
        st.caption("Technologies")
        _render_feature_list(
            technical_experience.get("technologies"),
            "No technologies",
        )
        st.divider()
        _render_field("Confidence", technical_experience.get("confidence"))
        _render_evidence(
            technical_experience.get("evidence"),
            "technical_experience_evidence",
        )

    with st.container(border=True):
        st.markdown("#### Languages")
        _render_feature_list(languages, "No languages")

    with st.container(border=True):
        st.markdown("#### Domain Background")
        _render_feature_list(domain_background, "No domain background")