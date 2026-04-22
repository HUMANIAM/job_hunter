from __future__ import annotations

import streamlit as st

from ui.candidate.ui import render_profile_section


def get_profile_id_from_page_state() -> int:
    raw_value = st.query_params.get("profile_id", "501")

    try:
        profile_id = int(raw_value)
    except (TypeError, ValueError):
        st.error("Invalid profile_id query parameter")
        st.stop()

    return profile_id


def render_page() -> None:
    st.title("Home")

    services = st.session_state.get("services")
    if services is None:
        st.error("Application services are not available")
        st.stop()

    profile_id = get_profile_id_from_page_state()

    render_profile_section(
        service=services.candidate_profile_service,
        profile_id=profile_id,
    )
