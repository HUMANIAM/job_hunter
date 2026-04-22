from __future__ import annotations

from dataclasses import asdict
from typing import Any

import streamlit as st

from ui.candidate.service import (
    CandidateProfileService,
    CandidateProfileServiceError,
)
from ui.shared.profile_types import SupportedCandidateProfile


SESSION_PROFILE_KEY = "candidate_profile"


def render_value(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if isinstance(nested_value, (dict, list)):
                st.markdown(f"**{key}**")
                with st.container(border=True):
                    render_value(nested_value)
            else:
                st.write(f"**{key}:** {nested_value}")
        return

    if isinstance(value, list):
        if not value:
            st.write("-")
            return

        for item in value:
            if isinstance(item, (dict, list)):
                with st.container(border=True):
                    render_value(item)
            else:
                st.markdown(f"- {item}")
        return

    st.write(value)


def render_supported_field(field: dict[str, Any], *, title: str) -> None:
    st.subheader(title)

    confidence = field.get("confidence")
    evidence = field.get("evidence", [])
    handled_keys = {"confidence", "evidence"}

    if "primary" in field:
        st.write(f"**Primary:** {field['primary']}")
        handled_keys.add("primary")

    if "alternatives" in field:
        alternatives = field.get("alternatives") or []
        st.write(
            f"**Alternatives:** {', '.join(alternatives) if alternatives else '-'}"
        )
        handled_keys.add("alternatives")

    if "min_level" in field:
        st.write(f"**Minimum level:** {field.get('min_level') or '-'}")
        handled_keys.add("min_level")

    if "accepted_fields" in field:
        accepted_fields = field.get("accepted_fields") or []
        st.write(
            f"**Accepted fields:** {', '.join(accepted_fields) if accepted_fields else '-'}"
        )
        handled_keys.add("accepted_fields")

    if confidence is not None:
        st.write(f"**Confidence:** {confidence}")

    if evidence:
        with st.expander("Evidence", expanded=False):
            for item in evidence:
                st.markdown(f"- {item}")
    else:
        st.write("**Evidence:** -")

    extra = {key: value for key, value in field.items() if key not in handled_keys}
    if extra:
        with st.container(border=True):
            st.caption("More details")
            render_value(extra)


def render_feature_list(items: list[Any], *, title: str) -> None:
    st.subheader(title)

    if not items:
        st.info("No data")
        return

    for index, item in enumerate(items, start=1):
        with st.container(border=True):
            st.markdown(f"**Item {index}**")
            render_value(item)


def render_candidate_profile(profile: SupportedCandidateProfile) -> None:
    payload = asdict(profile)

    st.title("Candidate Profile")

    role_titles = payload.get("role_titles", {})
    education = payload.get("education", {})
    experience = payload.get("experience", {})
    technical_experience = payload.get("technical_experience", {})
    languages = payload.get("languages", [])
    domain_background = payload.get("domain_background", [])

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "Overview",
            "Role Titles",
            "Education",
            "Experience",
            "Technical Experience",
            "Languages",
            "Domain Background",
        ]
    )

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Primary role", role_titles.get("primary", "-"))
            st.metric("Languages", len(languages))
        with col2:
            st.metric(
                "Accepted education fields",
                len(education.get("accepted_fields", [])),
            )
            st.metric("Domain background items", len(domain_background))

    with tab2:
        render_supported_field(role_titles, title="Role Titles")

    with tab3:
        render_supported_field(education, title="Education")

    with tab4:
        render_supported_field(experience, title="Experience")

    with tab5:
        render_supported_field(technical_experience, title="Technical Experience")

    with tab6:
        render_feature_list(languages, title="Languages")

    with tab7:
        render_feature_list(domain_background, title="Domain Background")

    with st.expander("Raw JSON", expanded=False):
        st.json(payload)


def _load_profile(
    *,
    service: CandidateProfileService,
    profile_id: int,
) -> SupportedCandidateProfile | None:
    try:
        with st.spinner("Loading candidate profile..."):
            return service.get_profile(profile_id)
    except CandidateProfileServiceError as exc:
        st.error(str(exc))
        return None
    except Exception as exc:
        st.error(f"Unexpected error while loading candidate profile: {exc}")
        return None


def main(service: CandidateProfileService) -> None:
    st.set_page_config(page_title="Candidate Profile", layout="wide")

    st.sidebar.header("Source")
    profile_id = st.sidebar.number_input(
        "uploaded_cv_id",
        min_value=1,
        step=1,
        value=1,
    )

    if st.sidebar.button("Load profile", type="primary"):
        profile = _load_profile(service=service, profile_id=profile_id)
        if profile is not None:
            st.session_state[SESSION_PROFILE_KEY] = profile

    profile = st.session_state.get(SESSION_PROFILE_KEY)
    if profile is None:
        st.info("Load a candidate profile from the sidebar.")
        return

    if not isinstance(profile, SupportedCandidateProfile):
        st.error(
            "Stored candidate profile has an unsupported shape. Reload the profile."
        )
        return

    render_candidate_profile(profile)


def render_profile_section(
    *,
    service: CandidateProfileService,
    profile_id: int,
) -> None:
    st.header("Candidate")

    profile = _load_profile(service=service, profile_id=profile_id)
    if profile is None:
        return

    render_candidate_profile(profile)
