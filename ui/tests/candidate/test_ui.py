from __future__ import annotations

from streamlit.testing.v1 import AppTest


def render_candidate_profile_app() -> None:
    from tests.data.candidate import make_candidate_profile_endpoint_record
    from ui.candidate.profile_mapper import map_candidate_profile
    from ui.candidate.ui import render_candidate_profile

    persisted_record = make_candidate_profile_endpoint_record(uploaded_cv_id=42)
    payload = {
        "role_titles": persisted_record.role_titles_json,
        "education": persisted_record.education_json,
        "experience": persisted_record.experience_json,
        "technical_experience": persisted_record.technical_experience_json,
        "languages": persisted_record.languages_json,
        "domain_background": persisted_record.domain_background_json,
    }

    render_candidate_profile(map_candidate_profile(payload))


def test_render_candidate_profile_displays_supported_profile() -> None:
    app = AppTest.from_function(render_candidate_profile_app)

    app.run()

    assert app.subheader[0].value == "Candidate Profile"
    assert app.caption[0].value == "Primary role"
    assert app.markdown[1].value == "software engineer"
    assert app.caption[1].value == "Alternatives"
    assert app.markdown[2].value == "backend engineer, full stack developer"
    assert app.markdown[4].value == "1. cv title"
    assert app.markdown[5].value == "2. cv description"
