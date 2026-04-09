from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from eligibility.job_eligibility_view import (
    DEFAULT_JOB_ELIGIBILITY_VIEW_LLM_MODEL,
    DEFAULT_JOB_ELIGIBILITY_VIEW_MAX_COMPLETION_TOKENS,
    JobEligibilityViewExtractor,
    JobEligibilityViewPayload,
    _load_system_message,
    render_job_eligibility_view_user_message,
)


def _job_eligibility_payload_dict() -> dict[str, object]:
    return {
        "role_families": {
            "allowed": [" Embedded Software ", "embedded software"],
        },
        "locations": {
            "allowed": [" Eindhoven ", "eindhoven"],
            "excluded": [" Germany "],
        },
        "job_conditions": {
            "excluded": [" Driving License Required "],
        },
    }


def test_job_eligibility_schema_matches_runtime_model() -> None:
    schema_path = Path("eligibility/job_eligibility_profile_schema.json")

    with schema_path.open("r", encoding="utf-8") as file_handle:
        schema = json.load(file_handle)

    profile_schema = schema["$defs"]["jobEligibilityProfile"]
    assert list(profile_schema["properties"].keys()) == list(
        JobEligibilityViewPayload.model_fields.keys()
    )


def test_render_job_eligibility_view_user_message_includes_job_profile_json() -> None:
    rendered = render_job_eligibility_view_user_message(
        {
            "title": "Controls Engineer",
            "location": "Eindhoven",
        }
    )

    assert "{{JOB_PROFILE}}" not in rendered
    assert "{{job_profile_json}}" not in rendered
    assert '"title": "Controls Engineer"' in rendered
    assert '"location": "Eindhoven"' in rendered


def test_job_eligibility_view_system_message_has_no_schema_injection() -> None:
    system_message = _load_system_message()

    assert "{{JOB_ELIGIBILITY_PROFILE_SCHEMA}}" not in system_message
    assert "configured response schema" in system_message
    assert "JOB_ELIGIBILITY_PROFILE_SCHEMA:" not in system_message
    assert "Empty arrays are allowed." in system_message


def test_job_eligibility_view_payload_normalizes_fields() -> None:
    payload = JobEligibilityViewPayload.model_validate(_job_eligibility_payload_dict())

    assert payload.role_families.allowed == ["embedded software"]
    assert payload.locations.allowed == ["eindhoven"]
    assert payload.locations.excluded == ["germany"]
    assert payload.job_conditions.excluded == ["driving license required"]


def test_job_eligibility_view_payload_allows_empty_lists() -> None:
    payload = JobEligibilityViewPayload.model_validate(
        {
            "languages": {
                "allowed": [],
                "excluded": [],
            }
        }
    )

    assert payload.languages.allowed == []
    assert payload.languages.excluded == []


def test_job_eligibility_view_extractor_uses_rendered_messages() -> None:
    calls: list[dict[str, object]] = []

    class FakeCompletions:
        def parse(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=JobEligibilityViewPayload.model_validate(
                                _job_eligibility_payload_dict()
                            ),
                            refusal=None,
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    extractor = JobEligibilityViewExtractor(
        client=fake_client,
        model="gpt-test",
        timeout_seconds=9.0,
    )

    payload = extractor.extract(
        {
            "title": "Controls Engineer",
            "location": "Eindhoven",
        }
    )

    assert payload == JobEligibilityViewPayload.model_validate(
        _job_eligibility_payload_dict()
    )
    assert calls[0]["model"] == "gpt-test"
    assert (
        calls[0]["max_completion_tokens"]
        == DEFAULT_JOB_ELIGIBILITY_VIEW_MAX_COMPLETION_TOKENS
    )
    assert calls[0]["response_format"] is JobEligibilityViewPayload
    assert "{{JOB_ELIGIBILITY_PROFILE_SCHEMA}}" not in calls[0]["messages"][0]["content"]
    assert "{{JOB_PROFILE}}" not in calls[0]["messages"][1]["content"]
    assert '"title": "Controls Engineer"' in calls[0]["messages"][1]["content"]


def test_job_eligibility_view_defaults_target_mini_model() -> None:
    assert DEFAULT_JOB_ELIGIBILITY_VIEW_LLM_MODEL == "gpt-5.4-mini"
