from __future__ import annotations

import clients.candidate_profiling.candidate_profiling as candidate_profiling_module
from clients.candidate_profiling.candidate_profile_model import CandidateProfile


def test_render_candidate_profile_user_message_includes_source_text() -> None:
    rendered = candidate_profiling_module.render_candidate_profile_user_message(
        "Senior embedded software engineer"
    )

    assert "{{SOURCE_TEXT}}" not in rendered
    assert "Senior embedded software engineer" in rendered
    assert "technical_core_features" in rendered


def test_render_candidate_profile_user_message_replaces_triple_backticks() -> None:
    rendered = candidate_profiling_module.render_candidate_profile_user_message(
        "```danger```"
    )

    assert "```" not in rendered
    assert "'''danger'''" in rendered


def test_profile_candidate_text_delegates_to_shared_extractor(monkeypatch) -> None:
    extracted_calls: list[dict[str, object]] = []
    expected_profile = CandidateProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software engineer",
                "alternatives": [],
                "confidence": 0.94,
                "evidence": ["Senior Embedded Software Engineer"],
            }
        }
    )

    def fake_extract_profile(
        source_text: str,
        *,
        profile_model: type[object],
        profile_llm_user_message: str,
    ) -> CandidateProfile:
        extracted_calls.append(
            {
                "source_text": source_text,
                "profile_model": profile_model,
                "profile_llm_user_message": profile_llm_user_message,
            }
        )
        return expected_profile

    monkeypatch.setattr(
        candidate_profiling_module,
        "extract_profile",
        fake_extract_profile,
    )

    profile = candidate_profiling_module.profile_candidate_text(
        "Senior Embedded Software Engineer"
    )

    assert profile == expected_profile
    assert extracted_calls == [
        {
            "source_text": "Senior Embedded Software Engineer",
            "profile_model": CandidateProfile,
            "profile_llm_user_message": (
                candidate_profiling_module.render_candidate_profile_user_message(
                    "Senior Embedded Software Engineer"
                )
            ),
        }
    ]
