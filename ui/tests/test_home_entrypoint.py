from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _make_supported_profile(profile_id: int):
    from tests.data.candidate import make_candidate_profile_endpoint_record
    from ui.candidate.profile_mapper import map_candidate_profile

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


def test_app_entrypoint_renders_home_page_from_file(monkeypatch) -> None:
    from ui.candidate.service import CandidateProfileService

    def fake_get_profile(self, profile_id: int):
        return _make_supported_profile(profile_id)

    monkeypatch.setattr(CandidateProfileService, "get_profile", fake_get_profile)

    app = AppTest.from_file("ui/app.py")

    app.run(timeout=5)

    assert len(app.error) == 0
    assert app.title[0].value == "Home"
    assert app.metric[0].label == "Primary role"
    assert app.metric[0].value == "software engineer 501"
