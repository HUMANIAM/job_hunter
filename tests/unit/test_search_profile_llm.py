from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from search_profile.llm.profile import (
    SEARCH_PROFILE_SCHEMA_VERSION,
    SearchProfileDocument,
    SearchProfileExtractor,
    SearchProfilePayload,
    compute_source_text_hash,
    render_search_profile_user_message,
)


def _profile_payload_dict() -> dict[str, object]:
    return {
        "skills": [
            {"name": " Python ", "strength": "core"},
        ],
        "languages": [
            {"name": " English ", "level": "professional"},
        ],
        "protocols": [
            {"name": " CAN ", "strength": "strong"},
        ],
        "standards": [
            {"name": " IEC 61508 ", "strength": "secondary"},
        ],
        "domains": [
            {"name": " Semiconductor ", "strength": "strong"},
        ],
        "seniority_hint": " Senior ",
        "years_experience_total": 7,
        "candidate_constraints": {
            "preferred_locations": [" Eindhoven ", "eindhoven"],
            "excluded_locations": [],
            "preferred_workplace_types": [" Hybrid "],
            "excluded_workplace_types": [],
            "requires_visa_sponsorship": None,
            "avoid_export_control_roles": True,
            "notes": [" Avoid export-controlled programs ", "avoid export-controlled programs"],
        },
        "evidence": {
            "skills": ["7 years of Python development"],
            "languages": ["Professional English"],
            "protocols": ["Worked with CAN diagnostics"],
            "standards": ["Applied IEC 61508 in safety projects"],
            "domains": ["Semiconductor equipment projects"],
            "seniority_hint": ["Senior software engineer"],
            "years_experience_total": ["7 years of experience"],
            "candidate_constraints": ["Prefers hybrid work and avoids export-controlled roles"],
        },
    }


def test_search_profile_schema_matches_runtime_models() -> None:
    schema_path = Path("search_profile/llm/search_profile_schema.json")

    with schema_path.open("r", encoding="utf-8") as file_handle:
        schema = json.load(file_handle)

    assert schema["required"] == list(SearchProfileDocument.model_fields.keys())
    assert list(schema["properties"].keys()) == list(SearchProfileDocument.model_fields.keys())

    profile_schema = schema["$defs"]["searchProfile"]
    assert profile_schema["required"] == list(SearchProfilePayload.model_fields.keys())
    assert list(profile_schema["properties"].keys()) == list(
        SearchProfilePayload.model_fields.keys()
    )


def test_render_search_profile_user_message_includes_schema_context_and_text() -> None:
    rendered = render_search_profile_user_message(
        "Senior Python engineer with CAN and IEC 61508 experience.",
        candidate_context={"target_locations": ["Eindhoven"]},
    )

    assert "{{search_profile_schema_json}}" not in rendered
    assert "{{candidate_context_json}}" not in rendered
    assert '"strength": "core | strong | secondary | exposure"' in rendered
    assert '"years_experience_total": null' in rendered
    assert '"target_locations": [' in rendered
    assert '"Eindhoven"' in rendered
    assert "Senior Python engineer with CAN and IEC 61508 experience." in rendered


def test_search_profile_payload_normalizes_fields() -> None:
    payload = SearchProfilePayload.model_validate(_profile_payload_dict())

    assert payload.skills[0].name == "python"
    assert payload.languages[0].name == "english"
    assert payload.protocols[0].name == "can"
    assert payload.standards[0].name == "iec 61508"
    assert payload.domains[0].name == "semiconductor"
    assert payload.seniority_hint == "senior"
    assert payload.candidate_constraints.preferred_locations == ["Eindhoven"]
    assert payload.candidate_constraints.notes == ["Avoid export-controlled programs"]


def test_search_profile_payload_requires_evidence_for_non_empty_fields() -> None:
    payload = _profile_payload_dict()
    payload["evidence"] = {
        **payload["evidence"],
        "skills": [],
    }

    with pytest.raises(ValueError, match="missing evidence for 'skills'"):
        SearchProfilePayload.model_validate(payload)


def test_search_profile_extractor_returns_schema_document() -> None:
    calls: list[dict[str, object]] = []

    class FakeCompletions:
        def parse(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=SearchProfilePayload.model_validate(
                                _profile_payload_dict()
                            ),
                            refusal=None,
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    extractor = SearchProfileExtractor(
        client=fake_client,
        model="gpt-test",
        timeout_seconds=9.0,
    )

    document = extractor.extract(
        "Senior Python engineer with CAN and IEC 61508 experience.",
        candidate_context={"target_locations": ["Eindhoven"]},
    )

    assert document == SearchProfileDocument(
        source_text_hash=compute_source_text_hash(
            "Senior Python engineer with CAN and IEC 61508 experience."
        ),
        schema_version=SEARCH_PROFILE_SCHEMA_VERSION,
        profile=SearchProfilePayload.model_validate(_profile_payload_dict()),
    )
    assert calls[0]["model"] == "gpt-test"
    assert calls[0]["response_format"] is SearchProfilePayload
    assert '"target_locations": [' in calls[0]["messages"][1]["content"]
