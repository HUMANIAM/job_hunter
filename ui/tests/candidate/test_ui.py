from __future__ import annotations

import json

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


def candidate_profile_success_app() -> None:
    from tests.data.candidate import make_candidate_profile_endpoint_record
    from ui.candidate.profile_mapper import map_candidate_profile
    from ui.candidate.ui import main

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

    main(StubCandidateProfileService())


def candidate_profile_error_app() -> None:
    from ui.candidate.service import CandidateProfileServiceError
    from ui.candidate.ui import main

    class StubCandidateProfileService:
        def get_profile(self, profile_id: int):
            raise CandidateProfileServiceError(
                f"Failed to load candidate profile {profile_id}"
            )

    main(StubCandidateProfileService())


def test_render_candidate_profile_displays_supported_profile() -> None:
    app = AppTest.from_function(render_candidate_profile_app)

    app.run()

    assert app.title[0].value == "Candidate Profile"
    assert app.metric[0].label == "Primary role"
    assert app.metric[0].value == "software engineer"
    assert app.metric[1].label == "Languages"
    assert app.metric[1].value == "1"
    assert (
        json.loads(app.json[0].value)["role_titles"]["primary"] == "software engineer"
    )


def test_main_loads_profile_via_service_and_renders_it() -> None:
    app = AppTest.from_function(candidate_profile_success_app)

    app.run()
    app.number_input[0].set_value(7)
    app.button[0].click().run()

    assert len(app.error) == 0
    assert app.metric[0].label == "Primary role"
    assert app.metric[0].value == "software engineer 7"


def test_main_shows_service_error_when_loading_fails() -> None:
    app = AppTest.from_function(candidate_profile_error_app)

    app.run()
    app.number_input[0].set_value(7)
    app.button[0].click().run()

    assert len(app.error) == 1
    assert app.error[0].value == "Failed to load candidate profile 7"
    assert len(app.metric) == 0
