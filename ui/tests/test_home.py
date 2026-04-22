from __future__ import annotations

from streamlit.testing.v1 import AppTest


def home_page_with_services_app() -> None:
    import streamlit as st
    from types import SimpleNamespace

    from tests.data.candidate import make_candidate_profile_endpoint_record
    from ui.candidate.profile_mapper import map_candidate_profile
    from ui.pages.home import render_page

    class StubCandidateProfileService:
        def get_profile(self, profile_id: int):
            persisted_record = make_candidate_profile_endpoint_record(
                uploaded_cv_id=profile_id
            )
            persisted_record.role_titles_json["primary"] = (
                f"software engineer {profile_id}"
            )
            payload = {
                "role_titles": persisted_record.role_titles_json,
                "education": persisted_record.education_json,
                "experience": persisted_record.experience_json,
                "technical_experience": persisted_record.technical_experience_json,
                "languages": persisted_record.languages_json,
                "domain_background": persisted_record.domain_background_json,
            }
            return map_candidate_profile(payload)

    st.session_state["services"] = SimpleNamespace(
        candidate_profile_service=StubCandidateProfileService()
    )
    render_page()


def home_page_without_services_app() -> None:
    from ui.pages.home import render_page

    render_page()


def test_home_page_uses_session_services() -> None:
    app = AppTest.from_function(home_page_with_services_app)

    app.run()

    assert len(app.error) == 0
    assert app.title[0].value == "Home"
    assert app.metric[0].label == "Primary role"
    assert app.metric[0].value == "software engineer 501"


def test_home_page_requires_services_in_session_state() -> None:
    app = AppTest.from_function(home_page_without_services_app)

    app.run()

    assert len(app.error) == 1
    assert app.error[0].value == "Application services are not available"
