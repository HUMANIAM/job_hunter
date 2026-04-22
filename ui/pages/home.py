from __future__ import annotations

import streamlit as st

from ui.candidate.service import CandidateProfileService, CandidateProfileServiceError
from ui.candidate.ui import render_candidate_profile
from ui.shared.profile_types import SupportedCandidateProfile


def get_profile_id_from_page_state() -> int:
    raw_value = st.query_params.get("profile_id", "501")

    try:
        profile_id = int(raw_value)
    except (TypeError, ValueError):
        st.error("Invalid profile_id query parameter")
        st.stop()

    return profile_id


def load_candidate_profile(
    *,
    service: CandidateProfileService,
    profile_id: int,
) -> SupportedCandidateProfile | None:
    try:
        with st.spinner("Loading candidate profile..."):
            profile = service.get_profile(profile_id)
    except CandidateProfileServiceError as exc:
        st.error(str(exc))
        return None
    except Exception as exc:
        st.error(f"Unexpected error while loading candidate profile: {exc}")
        return None

    return profile

def render_page() -> None:
    st.title("Home")

    services = st.session_state.get("services")
    if services is None:
        st.error("Application services are not available")
        st.stop()

    profile_id = get_profile_id_from_page_state()
    candidate_profile = load_candidate_profile(
        service=services.candidate_profile_service,
        profile_id=profile_id,
    )
    if candidate_profile is None:
        return

    render_candidate_profile(candidate_profile)
