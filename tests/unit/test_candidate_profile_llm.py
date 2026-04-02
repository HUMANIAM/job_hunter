from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from candidate_profile.llm.profile import (
    CANDIDATE_PROFILE_SCHEMA_VERSION,
    DEFAULT_CANDIDATE_PROFILE_LLM_MODEL,
    DEFAULT_CANDIDATE_PROFILE_MAX_COMPLETION_TOKENS,
    CandidateProfileDocument,
    CandidateProfileExtractor,
    CandidateProfilePayload,
    compute_candidate_id,
    _load_system_message,
    compute_source_text_hash,
    render_candidate_profile_user_message,
)


def _profile_payload_dict() -> dict[str, object]:
    return {
        "skills": [
            {
                "name": " Python ",
                "strength": "core",
                "confidence": "0.97",
                "evidence": ["7 years of Python development"],
            },
        ],
        "languages": [
            {
                "name": " English ",
                "level": "professional",
                "confidence": 0.82,
                "evidence": ["Worked at ASML and BMW on international teams"],
            },
        ],
        "protocols": [
            {
                "name": " CAN ",
                "strength": "strong",
                "confidence": 0.88,
                "evidence": ["Worked with CAN diagnostics"],
            },
        ],
        "standards": [
            {
                "name": " IEC 61508 ",
                "strength": "secondary",
                "confidence": 0.72,
                "evidence": ["Applied IEC 61508 in safety projects"],
            },
        ],
        "domains": [
            {
                "name": " Semiconductor ",
                "strength": "strong",
                "confidence": 0.81,
                "evidence": ["Semiconductor equipment projects"],
            },
        ],
        "seniority": {
            "value": " Senior ",
            "confidence": 0.91,
            "evidence": ["Senior software engineer"],
        },
        "years_experience_total": {
            "value": 7,
            "confidence": 0.94,
            "evidence": ["7 years of experience"],
        },
        "candidate_constraints": {
            "preferred_locations": [" Eindhoven ", "eindhoven"],
            "excluded_locations": [],
            "preferred_workplace_types": [" Hybrid "],
            "excluded_workplace_types": [],
            "requires_visa_sponsorship": None,
            "avoid_export_control_roles": True,
            "notes": [
                " Avoid export-controlled programs ",
                "avoid export-controlled programs",
            ],
            "confidence": 0.74,
            "evidence": [
                "Eindhoven, Netherlands",
                "Current role in Eindhoven",
            ],
        },
    }


def test_candidate_profile_schema_matches_runtime_models() -> None:
    schema_path = Path("candidate_profile/llm/candidate_profile_schema.json")

    with schema_path.open("r", encoding="utf-8") as file_handle:
        schema = json.load(file_handle)

    assert schema["required"] == list(CandidateProfileDocument.model_fields.keys())
    assert list(schema["properties"].keys()) == list(
        CandidateProfileDocument.model_fields.keys()
    )

    profile_schema = schema["$defs"]["candidateProfile"]
    assert profile_schema["required"] == list(CandidateProfilePayload.model_fields.keys())
    assert list(profile_schema["properties"].keys()) == list(
        CandidateProfilePayload.model_fields.keys()
    )


def test_render_candidate_profile_user_message_includes_schema_context_and_text() -> None:
    rendered = render_candidate_profile_user_message(
        "Senior Python engineer with CAN and IEC 61508 experience.",
        candidate_context={"target_locations": ["Eindhoven"]},
    )

    assert "{{candidate_profile_schema_json}}" not in rendered
    assert "{{candidate_context_json}}" not in rendered
    assert '"strength": "core | strong | secondary | exposure"' in rendered
    assert '"confidence": 0.0' in rendered
    assert '"years_experience_total": {' in rendered
    assert '"value": null' in rendered
    assert '"target_locations": [' in rendered
    assert '"Eindhoven"' in rendered
    assert "Senior Python engineer with CAN and IEC 61508 experience." in rendered


def test_candidate_profile_payload_normalizes_fields() -> None:
    payload = CandidateProfilePayload.model_validate(_profile_payload_dict())

    assert payload.skills[0].name == "python"
    assert payload.skills[0].confidence == 0.97
    assert payload.languages[0].name == "english"
    assert payload.languages[0].confidence == 0.82
    assert payload.languages[0].evidence == [
        "Worked at ASML and BMW on international teams"
    ]
    assert payload.protocols[0].name == "can"
    assert payload.standards[0].name == "iec 61508"
    assert payload.domains[0].name == "semiconductor"
    assert payload.seniority.value == "senior"
    assert payload.years_experience_total.value == 7
    assert payload.candidate_constraints.preferred_locations == ["Eindhoven"]
    assert payload.candidate_constraints.notes == ["Avoid export-controlled programs"]


def test_candidate_profile_payload_requires_evidence_for_extracted_features() -> None:
    payload = _profile_payload_dict()
    payload["skills"] = [
        {
            **payload["skills"][0],
            "evidence": [],
        }
    ]

    with pytest.raises(
        ValueError,
        match="evidence must not be empty for extracted feature items",
    ):
        CandidateProfilePayload.model_validate(payload)


def test_candidate_profile_payload_keeps_indirect_language_evidence() -> None:
    payload = _profile_payload_dict()
    payload["languages"] = [
        {
            "name": "English",
            "level": None,
            "confidence": 0.68,
            "evidence": [
                "Born in Egypt",
                "Worked at ASML and BMW on international teams",
            ],
        }
    ]

    parsed = CandidateProfilePayload.model_validate(payload)

    assert parsed.languages[0].evidence == [
        "Born in Egypt",
        "Worked at ASML and BMW on international teams",
    ]


def test_candidate_profile_payload_requires_evidence_for_non_empty_constraints() -> None:
    payload = _profile_payload_dict()
    payload["candidate_constraints"] = {
        **payload["candidate_constraints"],
        "evidence": [],
    }

    with pytest.raises(
        ValueError,
        match="evidence must not be empty when candidate_constraints are set",
    ):
        CandidateProfilePayload.model_validate(payload)


def test_candidate_profile_system_message_guides_inference_confidence_and_clues() -> None:
    system_message = _load_system_message()

    assert "Some fields are conservative aggregate judgments" in system_message
    assert 'even if the CV never says "X years of experience" directly' in system_message
    assert "Do not double-count overlapping roles." in system_message
    assert "Bounded semantic inference is allowed" in system_message
    assert "`0.0` to `1.0`" in system_message
    assert "birthplace or nationality context" in system_message
    assert "ASML, BMW, or Google can support likely `english`" in system_message
    assert "need not literally name the inferred language" in system_message


def test_candidate_profile_defaults_target_stronger_model_and_larger_output_budget() -> None:
    assert DEFAULT_CANDIDATE_PROFILE_LLM_MODEL == "gpt-5.4-mini"
    assert DEFAULT_CANDIDATE_PROFILE_MAX_COMPLETION_TOKENS == 3000


def test_candidate_profile_extractor_returns_schema_document() -> None:
    calls: list[dict[str, object]] = []

    class FakeCompletions:
        def parse(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=CandidateProfilePayload.model_validate(
                                _profile_payload_dict()
                            ),
                            refusal=None,
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    extractor = CandidateProfileExtractor(
        client=fake_client,
        model="gpt-test",
        timeout_seconds=9.0,
    )

    document = extractor.extract(
        "Senior Python engineer with CAN and IEC 61508 experience.",
        candidate_context={"target_locations": ["Eindhoven"]},
    )

    assert document == CandidateProfileDocument(
        candidate_id=compute_candidate_id(
            "Senior Python engineer with CAN and IEC 61508 experience."
        ),
        source_text_hash=compute_source_text_hash(
            "Senior Python engineer with CAN and IEC 61508 experience."
        ),
        schema_version=CANDIDATE_PROFILE_SCHEMA_VERSION,
        profile=CandidateProfilePayload.model_validate(_profile_payload_dict()),
    )
    assert calls[0]["model"] == "gpt-test"
    assert (
        calls[0]["max_completion_tokens"]
        == DEFAULT_CANDIDATE_PROFILE_MAX_COMPLETION_TOKENS
    )
    assert calls[0]["response_format"] is CandidateProfilePayload
    assert '"target_locations": [' in calls[0]["messages"][1]["content"]


def test_candidate_profile_extractor_uses_explicit_candidate_id() -> None:
    class FakeCompletions:
        def parse(self, **_kwargs: object) -> object:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=CandidateProfilePayload.model_validate(
                                _profile_payload_dict()
                            ),
                            refusal=None,
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    extractor = CandidateProfileExtractor(
        client=fake_client,
        model="gpt-test",
        timeout_seconds=9.0,
    )

    document = extractor.extract(
        "Senior Python engineer with CAN and IEC 61508 experience.",
        candidate_id=" Ibrahim_Saad_CV ",
    )

    assert document.candidate_id == "Ibrahim_Saad_CV"
