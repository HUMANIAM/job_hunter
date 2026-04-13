from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from shared.llm import (
    OpenAIStructuredExtractor,
    build_json_schema_example,
    get_openai_client,
    render_template,
    resolve_json_schema_node,
)


def test_resolve_json_schema_node_merges_local_ref_overrides() -> None:
    root_schema = {
        "$defs": {
            "payload": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
            }
        }
    }

    resolved = resolve_json_schema_node(
        {
            "$ref": "#/$defs/payload",
            "description": "runtime override",
        },
        root_schema,
    )

    assert resolved == {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
        },
        "description": "runtime override",
    }


def test_build_json_schema_example_renders_nested_schema_shapes() -> None:
    root_schema = {
        "$defs": {
            "nullableKind": {
                "enum": ["alpha", None],
            }
        },
        "type": "object",
        "properties": {
            "kind": {"$ref": "#/$defs/nullableKind"},
            "count": {"type": "integer"},
            "confidence": {"type": "number"},
            "flags": {"type": "array", "items": {"type": "boolean"}},
            "nested": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
            },
        },
    }

    assert build_json_schema_example(root_schema, root_schema) == {
        "kind": "alpha | null",
        "count": 0,
        "confidence": 0.0,
        "flags": [False],
        "nested": {
            "name": "string",
        },
    }


def test_render_template_replaces_all_placeholders() -> None:
    rendered = render_template(
        "Hello {{name}}, {{name}} likes {{thing}}.",
        {
            "{{name}}": "Sioux",
            "{{thing}}": "structured extraction",
        },
    )

    assert rendered == "Hello Sioux, Sioux likes structured extraction."


def test_get_openai_client_reads_api_key_from_env_helper(monkeypatch) -> None:
    captured: list[tuple[str, str]] = []

    class FakeOpenAI:
        def __init__(self, *, api_key: str) -> None:
            captured.append(("client", api_key))

    get_openai_client.cache_clear()
    monkeypatch.setattr("shared.llm.require_env_value", lambda name, *, error_context: f"{name}:{error_context}")
    monkeypatch.setattr("shared.llm.OpenAI", FakeOpenAI)

    client = get_openai_client(error_context="Eligibility evaluation")

    assert isinstance(client, FakeOpenAI)
    assert captured == [("client", "OPENAI_API_KEY:Eligibility evaluation")]


def test_openai_structured_extractor_parses_structured_response() -> None:
    class ParsedPayload(BaseModel):
        value: str

    calls: list[dict[str, object]] = []

    class FakeCompletions:
        def parse(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=ParsedPayload(value="ok"),
                            refusal=None,
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    extractor = OpenAIStructuredExtractor(
        client=fake_client,
        model="gpt-test",
        response_format=ParsedPayload,
        system_message="system message",
        render_user_message=lambda payload: f"user:{payload}",
        operation_name="Test extraction",
        timeout_seconds=12.0,
        max_completion_tokens=321,
    )

    result = extractor.extract("payload")

    assert result == ParsedPayload(value="ok")
    assert calls == [
        {
            "model": "gpt-test",
            "n": 1,
            "temperature": 0.0,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "max_completion_tokens": 321,
            "store": False,
            "response_format": ParsedPayload,
            "messages": [
                {"role": "system", "content": "system message"},
                {"role": "user", "content": "user:payload"},
            ],
            "timeout": 12.0,
        }
    ]


def test_openai_structured_extractor_raises_on_refusal() -> None:
    class ParsedPayload(BaseModel):
        value: str

    class FakeCompletions:
        def parse(self, **_: object) -> object:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=None,
                            refusal="policy",
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    extractor = OpenAIStructuredExtractor(
        client=fake_client,
        model="gpt-test",
        response_format=ParsedPayload,
        system_message="system message",
        render_user_message=lambda payload: f"user:{payload}",
        operation_name="Test extraction",
    )

    try:
        extractor.extract("payload")
    except RuntimeError as error:
        assert str(error) == "Test extraction refused the request: policy"
    else:
        raise AssertionError("expected refusal to raise RuntimeError")


def test_openai_structured_extractor_logs_request_diagnostics_on_exception(
    capsys,
) -> None:
    class ParsedPayload(BaseModel):
        value: str

    class FakeResponse:
        status_code = 400
        text = '{"error":"invalid json"}'

        def json(self) -> dict[str, str]:
            return {"error": "invalid json"}

    class FakeError(Exception):
        def __init__(self) -> None:
            super().__init__("request failed")
            self.status_code = 400
            self.body = {"error": {"message": "bad request"}}
            self.response = FakeResponse()

    class FakeCompletions:
        def parse(self, **_: object) -> object:
            raise FakeError()

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    extractor = OpenAIStructuredExtractor(
        client=fake_client,
        model="gpt-test",
        response_format=ParsedPayload,
        system_message="system message",
        render_user_message=lambda payload: f"user:{payload}",
        operation_name="Test extraction",
        timeout_seconds=7.0,
        max_completion_tokens=222,
    )

    with pytest.raises(FakeError, match="request failed"):
        extractor.extract({"job_id": 7, "score": float("nan")})

    captured = capsys.readouterr()
    assert "OpenAIStructuredExtractor request failed" in captured.err
    assert '"operation_name": "Test extraction"' in captured.err
    assert '"response_format": "ParsedPayload"' in captured.err
    assert '"payload_type": "dict"' in captured.err
    assert '"payload_preview"' in captured.err
    assert '"exception_type": "FakeError"' in captured.err
    assert '"status_code": 400' in captured.err
    assert '"response_json"' in captured.err
    assert '"strict_json_serializable": true' in captured.err
