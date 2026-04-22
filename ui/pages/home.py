from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure package imports work when Streamlit launches this page directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.candidate.repo import CandidateProfileRepo
from ui.candidate.service import CandidateProfileService
from ui.candidate.ui import render_profile_section
from ui.shared.api import ApiClient


@st.cache_resource
def get_candidate_profile_service() -> CandidateProfileService:
    api_client = ApiClient()
    repo = CandidateProfileRepo(api_client=api_client)
    return CandidateProfileService(repo=repo)


def get_profile_id_from_page_state() -> int:
    raw_value = st.query_params.get("profile_id", "501")

    try:
        profile_id = int(raw_value)
    except (TypeError, ValueError):
        st.error("Invalid profile_id query parameter")
        st.stop()

    if profile_id <= 0:
        st.error("profile_id must be a positive integer")
        st.stop()

    return profile_id


def main() -> None:
    st.set_page_config(page_title="Home", layout="wide")

    st.title("Home")

    profile_id = get_profile_id_from_page_state()
    service = get_candidate_profile_service()

    render_profile_section(
        service=service,
        profile_id=profile_id,
    )


if __name__ == "__main__":
    main()
