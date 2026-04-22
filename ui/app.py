from __future__ import annotations

from dataclasses import dataclass

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from ui.candidate.repo import CandidateProfileRepo
from ui.candidate.service import CandidateProfileService
from ui.pages.home import render_page as render_home_page
from ui.shared.api import ApiClient


@dataclass(frozen=True)
class AppServices:
    candidate_profile_service: CandidateProfileService


@st.cache_resource
def build_services() -> AppServices:
    api_client = ApiClient()
    candidate_profile_repo = CandidateProfileRepo(api_client=api_client)
    candidate_profile_service = CandidateProfileService(repo=candidate_profile_repo)
    return AppServices(candidate_profile_service=candidate_profile_service)


def main() -> None:
    st.set_page_config(page_title="Job Hunter", layout="wide")

    st.session_state["services"] = build_services()

    pg = st.navigation(
        [
            st.Page(render_home_page, title="Home", url_path="", default=True),
        ]
    )

    pg.run()


if get_script_run_ctx(suppress_warning=True) is not None:
    main()
