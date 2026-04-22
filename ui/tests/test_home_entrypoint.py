from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


def _load_home_page_module(monkeypatch) -> object:
    module_path = Path(__file__).resolve().parents[1] / "pages" / "home.py"
    project_root = module_path.parents[2]
    filtered_sys_path = [
        entry
        for entry in sys.path
        if Path(entry or ".").resolve() != project_root
    ]
    monkeypatch.setattr(sys, "path", [str(module_path.parent), *filtered_sys_path])

    for name in tuple(sys.modules):
        if name == "ui" or name.startswith("ui."):
            sys.modules.pop(name)

    spec = importlib.util.spec_from_file_location(
        "streamlit_home_page_script",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_home_script_bootstraps_project_root_for_ui_imports(monkeypatch) -> None:
    module = _load_home_page_module(monkeypatch)

    assert str(Path(__file__).resolve().parents[2]) in sys.path
    assert callable(module.get_candidate_profile_service)


def test_home_page_renders_candidate_profile_from_file(monkeypatch) -> None:
    from ui.candidate.service import CandidateProfileService

    def fake_get_profile(self, profile_id: int):
        return _make_supported_profile(profile_id)

    monkeypatch.setattr(CandidateProfileService, "get_profile", fake_get_profile)

    app = AppTest.from_file("ui/pages/home.py")

    app.run(timeout=5)

    assert len(app.error) == 0
    assert app.title[0].value == "Home"
    assert app.metric[0].label == "Primary role"
    assert app.metric[0].value == "software engineer 501"
